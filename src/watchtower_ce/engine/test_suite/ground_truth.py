from dataclasses import dataclass, field

from .synonym_set import SynonymSet


@dataclass(frozen=True)
class GroundTruth:
    """
    Expected content and quality markers for a remediation analysis.

    Attributes:
        violation_description: What the violation is (for reference)
        pci_requirements: The PCI-DSS requirements violated (e.g., "Req 3.4")
        required_phrases: Elements that MUST appear in a quality analysis
        preferred_phrases: Important phrases/concepts that should be mentioned
        remediation_steps: Expected remediation actions
        sql_fix_required: Whether the analysis should provide SQL fixes
    """

    violation_description: str
    pci_requirements: list[str] = field(default_factory=list)
    required_phrases: set[str | SynonymSet] = field(default_factory=set)
    preferred_phrases: list[str | SynonymSet] = field(default_factory=list)
    remediation_steps: list[str | SynonymSet] = field(default_factory=list)
    sql_fix_required: bool = False
