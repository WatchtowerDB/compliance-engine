from dataclasses import dataclass


@dataclass
class EvaluationMetrics:
    """
    Metrics for evaluating the quality of remediation analyses.

    Attributes:
        requirement_identification_score: % of cases where correct req was identified
        remediation_completeness_score: % of expected remediation steps present
        technical_accuracy_score: % of technically correct recommendations
        clarity_score: Subjective clarity rating (1-5)
        sql_fix_quality_score: % of valid SQL fixes when required
    """

    total_cases: int = 0

    # Core metrics
    requirement_correctly_identified: int = 0
    required_elements_found: int = 0
    required_elements_total: int = 0
    key_phrases_found: int = 0
    key_phrases_total: int = 0
    remediation_steps_found: int = 0
    remediation_steps_total: int = 0
    sql_fixes_provided: int = 0
    sql_fixes_required: int = 0

    @property
    def requirement_identification_rate(self) -> float:
        """% of analyses that correctly identified the PCI requirement"""
        return (
            self.requirement_correctly_identified / self.total_cases
            if self.total_cases > 0
            else 0.0
        )

    @property
    def element_coverage_rate(self) -> float:
        """% of required elements present in analyses"""
        return (
            self.required_elements_found / self.required_elements_total
            if self.required_elements_total > 0
            else 0.0
        )

    @property
    def key_phrase_coverage_rate(self) -> float:
        """% of key security concepts mentioned"""
        return (
            self.key_phrases_found / self.key_phrases_total
            if self.key_phrases_total > 0
            else 0.0
        )

    @property
    def remediation_completeness_rate(self) -> float:
        """% of expected remediation steps provided"""
        return (
            self.remediation_steps_found / self.remediation_steps_total
            if self.remediation_steps_total > 0
            else 0.0
        )

    @property
    def sql_fix_provision_rate(self) -> float:
        """% of cases where SQL fix was provided when required"""
        return (
            self.sql_fixes_provided / self.sql_fixes_required
            if self.sql_fixes_required > 0
            else 0.0
        )

    @property
    def overall_quality_score(self) -> float:
        """
        Weighted composite score for overall analysis quality.

        Weights:
        - Requirement ID: 25% (critical to identify what's wrong)
        - Element Coverage: 20% (must cover key aspects)
        - Key Phrases: 15% (shows understanding)
        - Remediation: 30% (most important - actionable fixes)
        - SQL Fixes: 10% (nice to have when applicable)
        """
        return (
            0.25 * self.requirement_identification_rate
            + 0.20 * self.element_coverage_rate
            + 0.15 * self.key_phrase_coverage_rate
            + 0.30 * self.remediation_completeness_rate
            + 0.10 * self.sql_fix_provision_rate
        )

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for reporting"""
        return {
            "total_cases": self.total_cases,
            "requirement_identification_rate": round(
                self.requirement_identification_rate, 4
            ),
            "element_coverage_rate": round(self.element_coverage_rate, 4),
            "key_phrase_coverage_rate": round(self.key_phrase_coverage_rate, 4),
            "remediation_completeness_rate": round(
                self.remediation_completeness_rate, 4
            ),
            "sql_fix_provision_rate": round(self.sql_fix_provision_rate, 4),
            "overall_quality_score": round(self.overall_quality_score, 4),
            "raw_counts": {
                "requirement_correctly_identified": self.requirement_correctly_identified,
                "required_elements_found": f"{self.required_elements_found}/{self.required_elements_total}",
                "key_phrases_found": f"{self.key_phrases_found}/{self.key_phrases_total}",
                "remediation_steps_found": f"{self.remediation_steps_found}/{self.remediation_steps_total}",
                "sql_fixes_provided": f"{self.sql_fixes_provided}/{self.sql_fixes_required}",
            },
        }
