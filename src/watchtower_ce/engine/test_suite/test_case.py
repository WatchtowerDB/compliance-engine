from dataclasses import dataclass

from .ground_truth import GroundTruth


@dataclass
class TestCase:
    """
    A test case for evaluating analysis quality on a failed assertion.

    Attributes:
        name: Test case identifier
        description: What this test case evaluates
        failed_assertion: The SQL assertion that failed
        failure_result: The data showing the violation
        schema_context: The schema where this violation occurred
        ground_truth: Expected analysis content
    """

    name: str
    description: str
    failed_assertion: str
    failure_result: str
    schema_context: str
    ground_truth: GroundTruth
