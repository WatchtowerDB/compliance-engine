from dataclasses import dataclass, field


@dataclass(frozen=True)
class GroundTruth:
    """
    Expected content and quality markers for a remediation analysis.

    Attributes:
        violation_description: What the violation is (for reference)
        pci_requirement: The PCI-DSS requirement violated (e.g., "Req 3.4")
        required_elements: Elements that MUST appear in a quality analysis
        key_phrases: Important phrases/concepts that should be mentioned
        remediation_steps: Expected remediation actions
        sql_fix_required: Whether the analysis should provide SQL fixes
    """

    violation_description: str
    pci_requirement: str
    required_elements: set[str] = field(default_factory=set)
    key_phrases: list[str] = field(default_factory=list)
    remediation_steps: list[str] = field(default_factory=list)
    sql_fix_required: bool = False
