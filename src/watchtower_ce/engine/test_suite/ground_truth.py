from dataclasses import dataclass, field

from .synonym_set import Phrase


@dataclass(frozen=True)
class AssertionGenerationGroundTruth:
    """
    Expected content markers for a stage 2 (assertion generation) output.

    Attributes:
        violation_description (str):
            Human-readable description of what the schema violates (documentation only).
        expected_violation_keywords (list[Phrase]):
            `Phrases`/`SynonymSets` that should appear in at least one generated
            assertion, proving the checker spotted the relevant violation.
        expected_tables (list[str]):
            Table names that must appear in at least one assertion, ensuring the
            checker did not silently skip a table.
    """

    violation_description: str
    expected_violation_keywords: list[Phrase] = field(default_factory=list)
    expected_tables: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AssertionAnalysisGroundTruth:
    """
    Expected content markers for a stage 4 (assertion analysis) output.

    Attributes:
        violation_description (str):
            Human-readable summary of the violation (documentation only).
        standard_requirements (list[str]):
            Requirement identifiers that must be correctly cited in the analysis
            (e.g. `["Req 3.2", "Req 3.3"]` for PCI-DSS, `["Article 9"]` for GDPR).
            At least one must appear in the output for the requirement-identification
            metric to pass.
        required_phrases (list[Phrase]):
            `Phrases`/`SynonymSets` that MUST appear in a quality analysis.
            Missing any is treated as a clear quality failure.
        preferred_phrases (list[Phrase]):
            `Phrases`/`SynonymSets` that SHOULD appear. Absence lowers the score
            but is not a hard failure.
        remediation_steps (list[Phrase]):
            Expected remediation actions. Matched with keyword-overlap logic so
            minor wording differences are tolerated.
    """

    violation_description: str
    standard_requirements: list[str] = field(default_factory=list)
    required_phrases: set[Phrase] = field(default_factory=set)
    preferred_phrases: list[Phrase] = field(default_factory=list)
    remediation_steps: list[Phrase] = field(default_factory=list)
