"""
PCI-DSS v4.0.1 gold standard benchmark dataset.

Add new cases by appending to the list returned by the factory function.
Both Stage 2 (assertion generation) and Stage 4 (assertion analysis) cases
are supported — populate the appropriate ground truth field on BenchmarkCase.
"""

from .benchmark_case import BenchmarkCase
from .ground_truth import AssertionAnalysisGroundTruth, AssertionGenerationGroundTruth
from .synonym_set import SynonymSet


def create_pci_dss_cases() -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []

    # ==========================================================================
    # REQUIREMENT 3 — Protect Stored Account Data
    # ==========================================================================

    # TC001 — Stage 4: CVV storage analysis
    cases.append(
        BenchmarkCase(
            name="TC001_CVV_Storage_Analysis",
            description="Stage 4: analysis quality for CVV storage violation",
            schema="""
                CREATE TABLE customers (
                    id INT PRIMARY KEY,
                    name VARCHAR(100),
                    cvv VARCHAR(4)
                );
            """,
            failed_assertion="SELECT * FROM customers WHERE cvv IS NOT NULL",
            failure_result="id: 1, cvv: 123\nid: 2, cvv: 456\nid: 3, cvv: 789",
            assertion_analysis_ground_truth=AssertionAnalysisGroundTruth(
                violation_description="CVV storage is prohibited under PCI-DSS after authorization",
                standard_requirements=["Req 3.2", "Req 3.3"],
                required_phrases={
                    SynonymSet("CVV", "card verification value", "CVC"),
                    SynonymSet(
                        "prohibited", "not allowed", "must not be stored", "not stored"
                    ),
                    SynonymSet("SAD", "Sensitive Authentication Data"),
                },
                preferred_phrases=[
                    SynonymSet(
                        "need to know",
                        "need-to-know",
                        "business need",
                        "business-need",
                    ),
                    SynonymSet("counterfeit payment cards", "counterfeit cards"),
                    "fraudulent transaction",
                    SynonymSet("encrypt", "plaintext", "cleartext"),
                ],
                remediation_steps=[
                    SynonymSet(
                        "Remove CVV column from database",
                        "Drop CVV column from database",
                        "Delete CVV data from database",
                    ),
                    SynonymSet("Implement access controls", "Verify access controls"),
                    SynonymSet(
                        "Document business justification",
                        "Review policies and business justification",
                    ),
                ],
                detailed_analysis_phrases=[
                    SynonymSet("authorization", "post-authorization"),
                    SynonymSet(
                        "card brand",
                        "payment network",
                        "card scheme",
                        "Visa",
                        "Mastercard",
                    ),
                    SynonymSet(
                        "data retention", "retention policy", "storage limitation"
                    ),
                ],
            ),
        )
    )

    # TC002 — Stage 2: CVV schema assertion generation
    cases.append(
        BenchmarkCase(
            name="TC002_CVV_Schema_Assertion_Generation",
            description="Stage 2: checker must generate assertions targeting the cvv column",
            schema="""
                CREATE TABLE customers (
                    id INT PRIMARY KEY,
                    name VARCHAR(100),
                    cvv VARCHAR(4)
                );
            """,
            assertion_generation_ground_truth=AssertionGenerationGroundTruth(
                violation_description="Schema exposes a cvv column that must never be stored",
                expected_violation_keywords=[
                    SynonymSet("cvv", "card verification value", "cvc"),
                    "customers",
                ],
                expected_tables=["customers"],
            ),
        )
    )

    # ==========================================================================
    # Add further cases here following the same pattern.
    # Group by Requirement number for readability.
    # ==========================================================================

    return cases


#: Module-level constant for convenient import.
PCI_DSS_CASES: list[BenchmarkCase] = create_pci_dss_cases()
