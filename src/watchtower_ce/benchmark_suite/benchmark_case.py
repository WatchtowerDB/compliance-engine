from dataclasses import dataclass
from typing import Optional

from .ground_truth import AssertionAnalysisGroundTruth, AssertionGenerationGroundTruth


@dataclass
class BenchmarkCase:
    """
    A single benchmark case covering one of the two public pipeline stages:
    - Stage 2: assertion generation  -> populate `assertion_generation_ground_truth`
    - Stage 4: assertion analysis    -> populate `assertion_analysis_ground_truth`

    Exactly one ground-truth field should be non-`None`.

    Attributes:
        name (str):
            Unique identifier (e.g. `"TC001_CVV_Storage_Analysis"`).
        description (str):
            What this case evaluates.
        schema (str):
            The SQL schema relevant to this case (always required).
        failed_assertion (str):
            The SQL assertion that failed.  Required for Stage 4; `""` for Stage 2.
        failure_result (str):
            The rows returned by the failed assertion. Required for Stage 4; `""` for Stage 2.
        assertion_analysis_ground_truth (Optional[AssertionAnalysisGroundTruth]):
            Ground truth for Stage 4 evaluation. `None` for Stage 2 cases.
        assertion_generation_ground_truth (Optional[AssertionGenerationGroundTruth]):
            Ground truth for Stage 2 evaluation. `None` for Stage 4 cases.
    """

    name: str
    description: str
    schema: str
    failed_assertion: str = ""
    failure_result: str = ""
    assertion_analysis_ground_truth: Optional[AssertionAnalysisGroundTruth] = None
    assertion_generation_ground_truth: Optional[AssertionGenerationGroundTruth] = None

    @property
    def is_analysis_case(self) -> bool:
        return self.assertion_analysis_ground_truth is not None

    @property
    def is_generation_case(self) -> bool:
        return self.assertion_generation_ground_truth is not None
