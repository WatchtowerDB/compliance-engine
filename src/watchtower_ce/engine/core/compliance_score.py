from dataclasses import dataclass
from math import log
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ComplianceObservation:
    passed: int
    total: int

    @property
    def compliance(self) -> float:
        return ComplianceScoreCalculator.schema_compliance(self.passed, self.total)

    @property
    def weight(self) -> float:
        return ComplianceScoreCalculator.schema_weight(self.total)


class ComplianceScoreCalculator:
    @staticmethod
    def schema_compliance(passed: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return passed / total

    @staticmethod
    def schema_weight(total: int) -> float:
        if total <= 0:
            return 0.0
        return log(total + 1)

    @staticmethod
    def framework_compliance(observations: Iterable[ComplianceObservation]) -> float:
        weighted_inverse_sum = 0.0
        weight_sum = 0.0

        for observation in observations:
            weight = observation.weight
            compliance = observation.compliance
            if weight <= 0 or compliance <= 0:
                return 0.0

            weight_sum += weight
            weighted_inverse_sum += weight / compliance

        if weight_sum <= 0 or weighted_inverse_sum <= 0:
            return 0.0

        return weight_sum / weighted_inverse_sum

    @staticmethod
    def database_compliance(framework_compliances: Iterable[float]) -> float:
        scores = tuple(framework_compliances)
        if not scores or any(score <= 0 for score in scores):
            return 0.0

        return len(scores) / sum(1 / score for score in scores)

    @staticmethod
    def compliance_score(raw_compliance: float) -> float:
        raw_compliance = round(raw_compliance, 4)
        if raw_compliance <= 0:
            return 0.0
        return round(10 * raw_compliance, 4)
