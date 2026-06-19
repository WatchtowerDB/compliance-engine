import logging
from typing import Protocol, runtime_checkable

from .benchmark_case import BenchmarkCase
from .helpers import (
    _check_requirement_identified,
    _matches_phrase,
    _matches_step,
)
from .metrics import AnalysisMetrics, GenerationMetrics

logger = logging.getLogger(__name__)


@runtime_checkable
class ComplianceCheckerProtocol(Protocol):
    """Protocol for compliance checker objects."""

    def generate_assertions(self, schema: str) -> list[str]: ...
    def analyze_failed_assertion_stdout(
        self, assertion: str, failure_result: str
    ) -> str: ...


class GenerationEvaluator:
    """Evaluates stage 2 (assertion generation) benchmark cases."""

    def evaluate_single(self, case: BenchmarkCase, assertions: list[str]) -> dict:
        """
        Evaluates a single assertion generation case.

        Args:
            case (BenchmarkCase): The benchmark case to evaluate.
            assertions (list[str]): The generated assertions to evaluate.

        Returns:
            dict: A dictionary containing the evaluation results.
        """
        if case.assertion_generation_ground_truth is None:
            raise ValueError(
                f"Case {case.name!r} has no assertion_generation_ground_truth."
            )

        gt = case.assertion_generation_ground_truth
        combined = "\n".join(assertions).lower()

        keywords_found = [
            str(kw)
            for kw in gt.expected_violation_keywords
            if _matches_phrase(combined, kw)
        ]
        tables_found = [t for t in gt.expected_tables if t.lower() in combined]

        return {
            "case": case.name,
            "description": case.description,
            "assertion_count": len(assertions),
            "keywords": {
                "found": len(keywords_found),
                "total": len(gt.expected_violation_keywords),
                "details": keywords_found,
            },
            "schemas_covered": {
                "found": len(tables_found),
                "total": len(gt.expected_tables),
                "details": tables_found,
            },
            "assertions": assertions,
        }

    def accumulate(self, result: dict, metrics: GenerationMetrics) -> None:
        """
        Add a single result dict into `metrics` in-place.

        Args:
            result (dict): The result dict to accumulate.
            metrics (GenerationMetrics): The metrics object to accumulate into.
        """
        metrics.keyword_hits += result["keywords"]["found"]
        metrics.keyword_total += result["keywords"]["total"]
        metrics.schema_hits += result["schemas_covered"]["found"]
        metrics.schema_total += result["schemas_covered"]["total"]


class AnalysisEvaluator:
    """Evaluates stage 4 (assertion analysis) benchmark cases."""

    def evaluate_single(self, case: BenchmarkCase, analysis: str) -> dict:
        """
        Evaluate one analysis against its ground truth.

        Args:
            case (BenchmarkCase): The benchmark case to evaluate.
            analysis (str): The analysis text to evaluate.

        Returns:
            dict: A dictionary containing the evaluation result.
        """
        if case.assertion_analysis_ground_truth is None:
            raise ValueError(
                f"Case {case.name!r} has no assertion_analysis_ground_truth."
            )

        gt = case.assertion_analysis_ground_truth
        text_lower = analysis.lower()

        req_identified = _check_requirement_identified(
            analysis, gt.standard_requirements
        )

        required_found = {
            str(p) for p in gt.required_phrases if _matches_phrase(text_lower, p)
        }
        preferred_found = [
            str(p) for p in gt.preferred_phrases if _matches_phrase(text_lower, p)
        ]
        steps_found = [
            str(s) for s in gt.remediation_steps if _matches_step(text_lower, s)
        ]

        return {
            "case": case.name,
            "description": case.description,
            "requirement_identified": req_identified,
            "required_phrases": {
                "found": len(required_found),
                "total": len(gt.required_phrases),
                "details": sorted(required_found),
            },
            "preferred_phrases": {
                "found": len(preferred_found),
                "total": len(gt.preferred_phrases),
                "details": preferred_found,
            },
            "remediation_steps": {
                "found": len(steps_found),
                "total": len(gt.remediation_steps),
                "details": steps_found,
            },
            # Truncated for reports — full text is too large.
            "analysis_excerpt": (
                analysis[:500] + "..." if len(analysis) > 500 else analysis
            ),
        }

    def accumulate(self, result: dict, metrics: AnalysisMetrics) -> None:
        """
        Add a single result dict into `metrics` in-place.

        Args:
            result (dict): The result dictionary to accumulate.
            metrics (AnalysisMetrics): The metrics object to accumulate into.
        """
        if result["requirement_identified"]:
            metrics.requirement_correctly_identified += 1

        metrics.required_phrases_found += result["required_phrases"]["found"]
        metrics.required_phrases_total += result["required_phrases"]["total"]
        metrics.preferred_phrases_found += result["preferred_phrases"]["found"]
        metrics.preferred_phrases_total += result["preferred_phrases"]["total"]
        metrics.remediation_steps_found += result["remediation_steps"]["found"]
        metrics.remediation_steps_total += result["remediation_steps"]["total"]
