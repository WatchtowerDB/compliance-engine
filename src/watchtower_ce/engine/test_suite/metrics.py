from dataclasses import dataclass


@dataclass
class GenerationMetrics:
    """
    Accumulated metrics for assertion generation benchmark cases.


    Dimension (equal weight 1/2):
    - Keyword coverage
    - Schema coverage
    """

    total_cases: int = 0

    keyword_hits: int = 0
    keyword_total: int = 0

    schema_hits: int = 0
    schema_total: int = 0

    def __add__(self, other: "GenerationMetrics") -> "GenerationMetrics":
        """
        Add two GenerationMetrics instances together, aggregating their metrics.
        """
        return GenerationMetrics(
            total_cases=self.total_cases + other.total_cases,
            keyword_hits=self.keyword_hits + other.keyword_hits,
            keyword_total=self.keyword_total + other.keyword_total,
            schema_hits=self.schema_hits + other.schema_hits,
            schema_total=self.schema_total + other.schema_total,
        )

    @property
    def keyword_coverage_rate(self) -> float:
        return self.keyword_hits / self.keyword_total if self.keyword_total > 0 else 0.0

    @property
    def schema_coverage_rate(self) -> float:
        return self.schema_hits / self.schema_total if self.schema_total > 0 else 0.0

    @property
    def overall_score(self) -> float:
        return (self.keyword_coverage_rate + self.schema_coverage_rate) / 2.0

    def to_dict(self) -> dict:
        return {
            "total_cases": self.total_cases,
            "keyword_coverage_rate": round(self.keyword_coverage_rate, 4),
            "schema_coverage_rate": round(self.schema_coverage_rate, 4),
            "overall_score": round(self.overall_score, 4),
            "raw_counts": {
                "keywords": f"{self.keyword_hits}/{self.keyword_total}",
                "schemas_covered": f"{self.schema_hits}/{self.schema_total}",
            },
        }


@dataclass
class AnalysisMetrics:
    """
    Accumulated metrics for assertion analysis benchmark cases.

    Requirement identification is the most load-bearing metric: everything else
    in a good analysis depends on the model first naming the right requirement.


    Dimensions and theirs weights:
    - Requirement identification:   0.35
    - Required phrases coverage:    0.25
    - Remediation completeness:     0.20
    - Detailed analysis coverage:   0.10
    - Preferred phrases coverage:   0.10
    """

    total_cases: int = 0

    requirement_correctly_identified: int = 0

    required_phrases_found: int = 0
    required_phrases_total: int = 0

    preferred_phrases_found: int = 0
    preferred_phrases_total: int = 0

    remediation_steps_found: int = 0
    remediation_steps_total: int = 0

    detailed_analysis_phrases_found: int = 0
    detailed_analysis_phrases_total: int = 0

    def __add__(self, other: "AnalysisMetrics") -> "AnalysisMetrics":
        """
        Add two AnalysisMetrics instances together, aggregating their metrics.
        """
        return AnalysisMetrics(
            total_cases=self.total_cases + other.total_cases,
            requirement_correctly_identified=(
                self.requirement_correctly_identified
                + other.requirement_correctly_identified
            ),
            required_phrases_found=self.required_phrases_found
            + other.required_phrases_found,
            required_phrases_total=self.required_phrases_total
            + other.required_phrases_total,
            preferred_phrases_found=self.preferred_phrases_found
            + other.preferred_phrases_found,
            preferred_phrases_total=self.preferred_phrases_total
            + other.preferred_phrases_total,
            remediation_steps_found=self.remediation_steps_found
            + other.remediation_steps_found,
            remediation_steps_total=self.remediation_steps_total
            + other.remediation_steps_total,
            detailed_analysis_phrases_found=(
                self.detailed_analysis_phrases_found
                + other.detailed_analysis_phrases_found
            ),
            detailed_analysis_phrases_total=(
                self.detailed_analysis_phrases_total
                + other.detailed_analysis_phrases_total
            ),
        )

    @property
    def requirement_identification_rate(self) -> float:
        return (
            self.requirement_correctly_identified / self.total_cases
            if self.total_cases > 0
            else 0.0
        )

    @property
    def required_phrases_coverage_rate(self) -> float:
        return (
            self.required_phrases_found / self.required_phrases_total
            if self.required_phrases_total > 0
            else 0.0
        )

    @property
    def preferred_phrases_coverage_rate(self) -> float:
        return (
            self.preferred_phrases_found / self.preferred_phrases_total
            if self.preferred_phrases_total > 0
            else 0.0
        )

    @property
    def remediation_completeness_rate(self) -> float:
        return (
            self.remediation_steps_found / self.remediation_steps_total
            if self.remediation_steps_total > 0
            else 0.0
        )

    @property
    def detailed_analysis_coverage_rate(self) -> float:
        return (
            self.detailed_analysis_phrases_found / self.detailed_analysis_phrases_total
            if self.detailed_analysis_phrases_total > 0
            else 0.0
        )

    @property
    def overall_score(self) -> float:
        return (
            0.35 * self.requirement_identification_rate
            + 0.25 * self.required_phrases_coverage_rate
            + 0.20 * self.remediation_completeness_rate
            + 0.10 * self.detailed_analysis_coverage_rate
            + 0.10 * self.preferred_phrases_coverage_rate
        )

    def to_dict(self) -> dict:
        return {
            "total_cases": self.total_cases,
            "requirement_identification_rate": round(
                self.requirement_identification_rate, 4
            ),
            "required_phrases_coverage_rate": round(
                self.required_phrases_coverage_rate, 4
            ),
            "preferred_phrases_coverage_rate": round(
                self.preferred_phrases_coverage_rate, 4
            ),
            "remediation_completeness_rate": round(
                self.remediation_completeness_rate, 4
            ),
            "detailed_analysis_coverage_rate": round(
                self.detailed_analysis_coverage_rate, 4
            ),
            "overall_score": round(self.overall_score, 4),
            "raw_counts": {
                "requirement_correctly_identified": self.requirement_correctly_identified,
                "required_phrases": f"{self.required_phrases_found}/{self.required_phrases_total}",
                "preferred_phrases": f"{self.preferred_phrases_found}/{self.preferred_phrases_total}",
                "remediation_steps": f"{self.remediation_steps_found}/{self.remediation_steps_total}",
                "detailed_analysis_phrases": (
                    f"{self.detailed_analysis_phrases_found}"
                    f"/{self.detailed_analysis_phrases_total}"
                ),
            },
        }
