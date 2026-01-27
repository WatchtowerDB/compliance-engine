import json
from pathlib import Path

from .evaluation_metrics import EvaluationMetrics
from .synonym_set import SynonymSet
from .test_case import TestCase


class AnalysisQualityEvaluator:
    """
    Evaluates the quality of compliance violation analyses.

    This evaluator assesses how well the system:
    1. Identifies the correct PCI-DSS requirement violated
    2. Explains the violation clearly
    3. Provides actionable remediation steps
    4. Includes SQL fixes where appropriate
    """

    def __init__(self, test_cases: list[TestCase]):
        """
        Initialize evaluator with test cases.

        Args:
            test_cases: List of TestCase objects
        """
        self.test_cases = test_cases
        self.results: list[dict] = []

    def _check_requirement_identification(
        self, analysis: str, expected_requirements: list[str]
    ) -> bool:
        """
        Check if the analysis correctly identifies any of the expected PCI-DSS requirements.

        Args:
            analysis: Generated analysis text
            expected_requirements: A list of possible expected requirements (e.g., ["Req 3.4", "Req 3.2.1"])

        Returns:
            True if at least one requirement is correctly identified.
        """
        analysis_lower = analysis.lower()

        for expected_requirement in expected_requirements:
            # Normalize requirement format for matching
            # "Req 3.4" -> ["req 3.4", "requirement 3.4", "3.4"]
            req_parts = (
                expected_requirement.lower()
                .replace("req", "")
                .replace("uirement", "")
                .strip()
            )

            variations = [
                f"req {req_parts}",
                f"req. {req_parts}",
                f"requirement {req_parts}",
                req_parts,
            ]

            if any(var in analysis_lower for var in variations):
                return True

        return False

    def _check_phrases_present(
        self, analysis: str, required_phrases: set[str | SynonymSet]
    ) -> tuple[int, set[str]]:
        """
        Check which required phrases are present in the analysis.

        Args:
            analysis: Generated analysis text
            required_phrases: Set of required element preferred_words

        Returns:
            Tuple of (count_found, set_of_found_phrases)
        """
        analysis_lower = analysis.lower()
        found = set()

        for element in required_phrases:
            if isinstance(element, SynonymSet):
                if any(syn.lower() in analysis_lower for syn in element):
                    found.add(str(element))
            elif isinstance(element, str):
                if element.lower() in analysis_lower:
                    found.add(element)
            else:
                raise TypeError(
                    f"Unexpected element type. Expected str or SynonymSet, got {type(element)}."
                )

        return len(found), found

    def _check_preferred_phrases(
        self, analysis: str, preferred_phrases: list[str | SynonymSet]
    ) -> tuple[int, list[str]]:
        """
        Check which preferred_ security phrases/concepts are mentioned.

        Args:
            analysis: Generated analysis text
            preferred_phrases: List of important phrases to look for

        Returns:
            Tuple of (count_found, list_of_found_phrases)
        """
        analysis_lower = analysis.lower()
        found = []

        for phrase in preferred_phrases:
            if isinstance(phrase, SynonymSet):
                if any(p.lower() in analysis_lower for p in phrase):
                    found.append(str(phrase))
            elif isinstance(phrase, str):
                if phrase.lower() in analysis_lower:
                    found.append(phrase)

        return len(found), found

    def _check_remediation_steps(
        self, analysis: str, expected_steps: list[str | SynonymSet]
    ) -> tuple[int, list[str]]:
        """
        Check which remediation steps are covered in the analysis.

        Args:
            analysis: Generated analysis text
            expected_steps: List of expected remediation actions

        Returns:
            Tuple of (count_found, list_of_found_steps)
        """
        analysis_lower = analysis.lower()
        found = []

        def is_step_present(step_text: str) -> bool:
            step_keywords = step_text.lower().split()
            step_keywords = [kw for kw in step_keywords if kw != "/"]
            if len(step_keywords) > 0:
                matches = sum(
                    1 for kw in step_keywords if len(kw) > 2 and kw in analysis_lower
                )
                return matches >= len(step_keywords) * 0.6
            return False

        for step in expected_steps:
            if isinstance(step, SynonymSet):
                if any(is_step_present(s) for s in step):
                    found.append(str(step))
            elif isinstance(step, str):
                if is_step_present(step):
                    found.append(step)

        return len(found), found

    def _check_sql_fix_present(self, analysis: str) -> bool:
        """
        Check if the analysis includes SQL fix examples.

        Args:
            analysis: Generated analysis text

        Returns:
            True if SQL fixes are present
        """
        analysis_upper = analysis.upper()

        sql_keywords = [
            "ALTER TABLE",
            "DROP COLUMN",
            "CREATE TABLE",
            "UPDATE",
            "DELETE",
            "GRANT",
            "REVOKE",
            "ADD COLUMN",
            "MODIFY COLUMN",
        ]

        return any(keyword in analysis_upper for keyword in sql_keywords)

    def evaluate_single_analysis(
        self, test_case: TestCase, generated_analysis: str
    ) -> dict:
        """
        Evaluate quality of a single analysis.

        Args:
            test_case: The test case with ground truth
            generated_analysis: Analysis generated by the system

        Returns:
            Dictionary with detailed evaluation results
        """
        gt = test_case.ground_truth

        # Check requirement identification
        req_identified = self._check_requirement_identification(
            generated_analysis, gt.pci_requirements
        )

        # Check required phrases
        required_phrases_found, required_found_phrases = self._check_phrases_present(
            generated_analysis, gt.required_phrases
        )

        # Check preferred phrases
        preferred_phrases_found, preferred_found_phrases = (
            self._check_preferred_phrases(generated_analysis, gt.preferred_phrases)
        )

        # Check remediation steps
        steps_found, found_steps = self._check_remediation_steps(
            generated_analysis, gt.remediation_steps
        )

        # Check SQL fix
        sql_fix_present = self._check_sql_fix_present(generated_analysis)

        return {
            "test_case": test_case.name,
            "description": test_case.description,
            "requirement_identified": req_identified,
            "required_phrases": {
                "found": required_phrases_found,
                "total": len(gt.required_phrases),
                "details": list(required_found_phrases),
            },
            "preferred_phrases": {
                "found": preferred_phrases_found,
                "total": len(gt.preferred_phrases),
                "details": preferred_found_phrases,
            },
            "remediation_steps": {
                "found": steps_found,
                "total": len(gt.remediation_steps),
                "details": found_steps,
            },
            "sql_fix": {"provided": sql_fix_present, "required": gt.sql_fix_required},
            "analysis_text": generated_analysis[:500] + "..."
            if len(generated_analysis) > 500
            else generated_analysis,
        }

    def evaluate_all(self, checker, verbose: bool = True) -> EvaluationMetrics:
        """
        Evaluate analysis quality across all test cases.

        Args:
            checker: Instance of PCIComplianceChecker
            verbose: Whether to print progress

        Returns:
            EvaluationMetrics with comprehensive scores
        """
        metrics = EvaluationMetrics()
        metrics.total_cases = len(self.test_cases)
        self.results = []

        for i, test_case in enumerate(self.test_cases, 1):
            if verbose:
                print(f"\n{'=' * 80}")
                print(
                    f"Evaluating Analysis {i}/{len(self.test_cases)}: {test_case.name}"
                )
                print(f"{'=' * 80}")
                print(f"Description: {test_case.description}")
                print(f"Violation: {test_case.ground_truth.violation_description}")

            # Generate analysis using the checker
            generated_analysis = checker.analyze_failed_assertion(
                test_case.failed_assertion, test_case.failure_result
            )

            if verbose:
                print(f"\nGenerated analysis ({len(generated_analysis)} chars)")

            # Evaluate this analysis
            result = self.evaluate_single_analysis(test_case, generated_analysis)
            self.results.append(result)

            # Accumulate metrics
            if result["requirement_identified"]:
                metrics.requirement_correctly_identified += 1

            metrics.required_phrases_found += result["required_phrases"]["found"]
            metrics.required_phrases_total += result["required_phrases"]["total"]

            metrics.preferred_phrases_found += result["preferred_phrases"]["found"]
            metrics.preferred_phrases_total += result["preferred_phrases"]["total"]

            metrics.remediation_steps_found += result["remediation_steps"]["found"]
            metrics.remediation_steps_total += result["remediation_steps"]["total"]

            if result["sql_fix"]["required"]:
                metrics.sql_fixes_required += 1
                if result["sql_fix"]["provided"]:
                    metrics.sql_fixes_provided += 1

            if verbose:
                print(
                    f"Requirement ID: {'✓' if result['requirement_identified'] else '✗'}"
                )
                print(
                    f"Required Phrases: {result['required_phrases']['found']}/{result['required_phrases']['total']}"
                )
                print(
                    f"preferred Phrases: {result['preferred_phrases']['found']}/{result['preferred_phrases']['total']}"
                )
                print(
                    f"Remediation: {result['remediation_steps']['found']}/{result['remediation_steps']['total']}"
                )
                print(
                    f"SQL Fix: {'✓' if result['sql_fix']['provided'] else '✗'} (Required: {result['sql_fix']['required']})"
                )

        return metrics

    def generate_detailed_report(self, metrics: EvaluationMetrics) -> str:
        """
        Generate detailed report for research paper.

        Args:
            metrics: Computed metrics

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("ANALYSIS QUALITY EVALUATION REPORT")
        report.append("=" * 80)
        report.append("")

        # Overall scores
        report.append("OVERALL QUALITY SCORES:")
        report.append("-" * 80)
        report.append(
            f"  Overall Quality Score: {metrics.overall_quality_score:.4f} ({metrics.overall_quality_score * 100:.2f}%)"
        )
        report.append("")
        report.append(
            f"  Requirement Identification: {metrics.requirement_identification_rate:.4f} ({metrics.requirement_identification_rate * 100:.2f}%)"
        )
        report.append(
            f"  Required Phrases Coverage: {metrics.required_phrases_coverage_rate:.4f} ({metrics.required_phrases_coverage_rate * 100:.2f}%)"
        )
        report.append(
            f"  Preferred Phrase Coverage: {metrics.preferred_phrases_coverage_rate:.4f} ({metrics.preferred_phrases_coverage_rate * 100:.2f}%)"
        )
        report.append(
            f"  Remediation Completeness: {metrics.remediation_completeness_rate:.4f} ({metrics.remediation_completeness_rate * 100:.2f}%)"
        )
        report.append(
            f"  SQL Fix Provision: {metrics.sql_fix_provision_rate:.4f} ({metrics.sql_fix_provision_rate * 100:.2f}%)"
        )

        report.append("")
        report.append("PER-TEST-CASE BREAKDOWN:")
        report.append("-" * 80)

        for result in self.results:
            report.append(f"\n[{result['test_case']}]")
            report.append(f"  Description: {result['description']}")
            report.append(
                f"  Requirement Identified: {'✓' if result['requirement_identified'] else '✗'}"
            )
            report.append(
                f"  Required Phrases Found: {result['required_phrases']['found']}/{result['required_phrases']['total']} - {result['required_phrases']['details']}"
            )
            report.append(
                f"  Preferred Phrases Found: {result['preferred_phrases']['found']}/{result['preferred_phrases']['total']} - {result['preferred_phrases']['details']}"
            )
            report.append(
                f"  Remediation Steps Found: {result['remediation_steps']['found']}/{result['remediation_steps']['total']} - {result['remediation_steps']['details']}"
            )
            report.append(
                f"  SQL Fix: {'Provided' if result['sql_fix']['provided'] else 'Not Provided'} (Required: {result['sql_fix']['required']})"
            )

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def save_results(self, output_path: Path, metrics: EvaluationMetrics):
        """
        Save results to JSON file.

        Args:
            output_path: Path to save JSON
            metrics: Computed metrics
        """
        output_data = {
            "metrics": metrics.to_dict(),
            "detailed_results": self.results,
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"\nResults saved to: {output_path}")
