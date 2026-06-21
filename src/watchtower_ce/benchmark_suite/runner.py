import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .benchmark_case import BenchmarkCase
from .evaluators import (
    AnalysisEvaluator,
    ComplianceCheckerProtocol,
    GenerationEvaluator,
)
from .metrics import AnalysisMetrics, GenerationMetrics

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkReport:
    """Holds the complete output of a benchmark run."""

    analysis_metrics: AnalysisMetrics = field(default_factory=AnalysisMetrics)
    generation_metrics: GenerationMetrics = field(default_factory=GenerationMetrics)
    analysis_results: list[dict] = field(default_factory=list)
    generation_results: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        lines: list[str] = []
        sep = "=" * 72

        lines += [sep, "WATCHTOWER BENCHMARK SUITE — RESULTS", sep, ""]

        if self.analysis_metrics.total_cases > 0:
            am = self.analysis_metrics
            lines += [
                f"STAGE 4 — ASSERTION ANALYSIS  ({am.total_cases} cases)",
                "-" * 72,
                f"  Overall score                    : {am.overall_score:.4f}  ({am.overall_score * 100:.1f}%)",
                f"  Requirement identification  0.35 : {am.requirement_identification_rate:.4f}  ({am.requirement_identification_rate * 100:.1f}%)",
                f"  Required phrases coverage   0.30 : {am.required_phrases_coverage_rate:.4f}  ({am.required_phrases_coverage_rate * 100:.1f}%)",
                f"  Remediation completeness    0.25 : {am.remediation_completeness_rate:.4f}  ({am.remediation_completeness_rate * 100:.1f}%)",
                f"  Preferred phrases coverage  0.10 : {am.preferred_phrases_coverage_rate:.4f}  ({am.preferred_phrases_coverage_rate * 100:.1f}%)",
                "",
            ]

            lines.append("  Per-case breakdown:")
            for r in self.analysis_results:
                req_mark = "✓" if r["requirement_identified"] else "✗"
                lines.append(
                    f"    [{req_mark}] {r['case']}"
                    f"  req={req_mark}"
                    f"  req_phrases={r['required_phrases']['found']}/{r['required_phrases']['total']}"
                    f"  pref_phrases={r['preferred_phrases']['found']}/{r['preferred_phrases']['total']}"
                    f"  remediation={r['remediation_steps']['found']}/{r['remediation_steps']['total']}"
                )
            lines.append("")

        if self.generation_metrics.total_cases > 0:
            gm = self.generation_metrics
            lines += [
                f"STAGE 2 — ASSERTION GENERATION  ({gm.total_cases} cases)",
                "-" * 72,
                f"  Overall score            : {gm.overall_score:.4f}  ({gm.overall_score * 100:.1f}%)",
                f"  Keyword coverage         : {gm.keyword_coverage_rate:.4f}  ({gm.keyword_coverage_rate * 100:.1f}%)",
                f"  Schema coverage          : {gm.schema_coverage_rate:.4f}  ({gm.schema_coverage_rate * 100:.1f}%)",
                "",
            ]

            lines.append("  Per-case breakdown:")
            for r in self.generation_results:
                lines.append(
                    f"    {r['case']}"
                    f"  assertions={r['assertion_count']}"
                    f"  keywords={r['keywords']['found']}/{r['keywords']['total']}"
                    f"  tables={r['tables_covered']['found']}/{r['tables_covered']['total']}"
                )
            lines.append("")

        lines.append(sep)
        return "\n".join(lines)

    def save(self, path: str | Path) -> None:
        """Save full results to a JSON file."""
        output = {
            "analysis": {
                "metrics": self.analysis_metrics.to_dict(),
                "results": self.analysis_results,
            },
            "generation": {
                "metrics": self.generation_metrics.to_dict(),
                "results": self.generation_results,
            },
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as fh:
            json.dump(output, fh, indent=2)
        logger.info("Benchmark results saved to %s", path)


class BenchmarkRunner:
    """Runs a list of BenchmarkCases against a compliance checker."""

    def __init__(
        self,
        cases: list[BenchmarkCase],
        checker: ComplianceCheckerProtocol,
        verbose: bool = True,
    ) -> None:
        """
        Initializes the BenchmarkRunner with the given cases, checker, and verbosity.

        Args:
            cases:    The benchmark dataset to evaluate against.
            checker:  Any object satisfying `ComplianceCheckerProtocol`
                      (i.e. any `ComplianceChecker` subclass from WTCE).
            verbose:  Print progress to stdout while running.
        """
        self.cases = cases
        self.checker = checker
        self.verbose = verbose
        self._analysis_evaluator = AnalysisEvaluator()
        self._generation_evaluator = GenerationEvaluator()

    def run(self) -> BenchmarkReport:
        report = BenchmarkReport()

        analysis_cases = [c for c in self.cases if c.is_analysis_case]
        generation_cases = [c for c in self.cases if c.is_generation_case]

        if analysis_cases:
            self._run_analysis(analysis_cases, report)
        if generation_cases:
            self._run_generation(generation_cases, report)

        return report

    def _run_analysis(
        self, cases: list[BenchmarkCase], report: BenchmarkReport
    ) -> None:
        metrics = AnalysisMetrics(total_cases=len(cases))
        self._print(f"\n{'=' * 72}")
        self._print(f"STAGE 4 — ASSERTION ANALYSIS  ({len(cases)} cases)")
        self._print("=" * 72)

        for i, case in enumerate(cases, 1):
            self._print(f"\n[{i}/{len(cases)}] {case.name}")
            self._print(f"  {case.description}")

            analysis = self.checker.analyze_failed_assertion_stdout(
                case.failed_assertion, case.failure_result
            )
            result = self._analysis_evaluator.evaluate_single(case, analysis)
            self._analysis_evaluator.accumulate(result, metrics)
            report.analysis_results.append(result)

            if self.verbose:
                req_mark = "✓" if result["requirement_identified"] else "✗"
                self._print(
                    f"  Req identified : {req_mark}"
                    f"  | required phrases : {result['required_phrases']['found']}/{result['required_phrases']['total']}"
                    f"  | preferred : {result['preferred_phrases']['found']}/{result['preferred_phrases']['total']}"
                    f"  | remediation : {result['remediation_steps']['found']}/{result['remediation_steps']['total']}"
                )

        report.analysis_metrics = metrics

    def _run_generation(
        self, cases: list[BenchmarkCase], report: BenchmarkReport
    ) -> None:
        metrics = GenerationMetrics(total_cases=len(cases))
        self._print(f"\n{'=' * 72}")
        self._print(f"STAGE 2 — ASSERTION GENERATION  ({len(cases)} cases)")
        self._print("=" * 72)

        for i, case in enumerate(cases, 1):
            self._print(f"\n[{i}/{len(cases)}] {case.name}")
            self._print(f"  {case.description}")

            assertions = self.checker.generate_assertions(case.schema)
            result = self._generation_evaluator.evaluate_single(case, assertions)
            self._generation_evaluator.accumulate(result, metrics)
            report.generation_results.append(result)

            if self.verbose:
                self._print(
                    f"  Assertions : {result['assertion_count']}"
                    f"  | keywords : {result['keywords']['found']}/{result['keywords']['total']}"
                    f"  | tables : {result['tables_covered']['found']}/{result['tables_covered']['total']}"
                )

        report.generation_metrics = metrics

    def _print(self, msg: str) -> None:
        if self.verbose:
            print(msg)
