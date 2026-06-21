import logging
import sys
from pathlib import Path
from typing import Optional

import click

from ..benchmark_suite import (
    GDPR_STAGE_2_CASES,
    GDPR_STAGE_4_CASES,
    PCI_DSS_STAGE_2_CASES,
    PCI_DSS_STAGE_4_CASES,
    BenchmarkReport,
    BenchmarkRunner,
)
from ..engine.standards import GDPRComplianceChecker, PCIComplianceChecker


def _load_cases(standard: list[str], stages: list[int]) -> list:
    """Load benchmark cases for the specified standard(s) and stage(s)."""
    cases = []

    stage_map = {
        "pci-dss": {
            2: PCI_DSS_STAGE_2_CASES,
            4: PCI_DSS_STAGE_4_CASES,
        },
        "gdpr": {
            2: GDPR_STAGE_2_CASES,
            4: GDPR_STAGE_4_CASES,
        },
    }

    if "all" in standard:
        standards_to_run = ["pci-dss", "gdpr"]
    else:
        standards_to_run = standard

    for std in standards_to_run:
        if std not in stage_map:
            raise click.BadParameter(f"Unknown standard: {std}")
        for stage in stages:
            if stage not in [2, 4]:
                raise click.BadParameter(
                    f"Benchmark suite does not support benchmarking stage {stage}."
                )
            cases.extend(stage_map[std][stage])

    return cases


@click.command(
    "test",
    short_help="Run benchmark suite against compliance standards",
    help="Run the benchmark suite (stage 2 generation + stage 4 analysis) against specified standards and stages.",
)
@click.help_option("-h", "--help")
@click.option(
    "-s",
    "--standard",
    type=click.Choice(["pci-dss", "gdpr", "all"], case_sensitive=False),
    default=["all"],
    multiple=True,
    help="Compliance standard to benchmark: pci-dss, gdpr, or all. (Default: all)",
)
@click.option(
    "-p",
    "--stage",
    type=click.Choice(["2", "4", "all"], case_sensitive=False),
    default=["all"],
    multiple=True,
    help="Pipeline stage(s) to run: 2 (generation), 4 (analysis), or all. (Default: all)",
)
@click.option(
    "-i",
    "--iterations",
    type=int,
    help="Number of iterations to run the test suite. The results of all iterations are aggregated. Higher values give more accurate scores but take more time to run.",
    default=1,
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to save the benchmark results.",
)
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging.")
def test(
    standard: tuple[str, ...],
    stage: tuple[str, ...],
    iterations: int,
    output: Optional[Path],
    debug: bool,
) -> None:
    if debug:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    # Parse stages
    stages_to_run = set()
    if not stage or "all" in stage:
        stages_to_run = {2, 4}
    else:
        stages_to_run = {int(s) for s in stage}

    # Convert standard tuple to list
    standard_list = list(standard) if standard else ["all"]

    print("Loading benchmark dataset...")
    test_cases = _load_cases(standard_list, sorted(stages_to_run))

    # Display selected options
    if "all" in standard_list:
        standard_display = "PCI-DSS, GDPR"
    else:
        standard_display = ", ".join(s.upper() for s in standard_list)
    print(f"Standard(s): {standard_display}")
    print(f"Stage(s): {', '.join(str(s) for s in sorted(stages_to_run))}")
    print(f"Created {len(test_cases)} test cases\n")

    # Select checker based on standard(s)
    if "all" in standard_list:
        # When running all standards, run PCI-DSS first, then GDPR
        checkers_to_run = [
            (
                "pci-dss",
                PCIComplianceChecker(
                    collection_name="PCI-DSS-v4.0.1",
                ),
            ),
            (
                "gdpr",
                GDPRComplianceChecker(
                    collection_name="GDPR",
                ),
            ),
        ]
    elif len(standard_list) == 1:
        std = standard_list[0].lower()
        if std == "pci-dss":
            checkers_to_run = [
                (
                    "pci-dss",
                    PCIComplianceChecker(
                        collection_name="PCI-DSS-v4.0.1",
                    ),
                ),
            ]
        else:  # gdpr
            checkers_to_run = [
                (
                    "gdpr",
                    GDPRComplianceChecker(
                        collection_name="GDPR",
                    ),
                ),
            ]
    else:
        # Multiple standards specified (not "all")
        checkers_to_run = []
        for std in standard_list:
            if std.lower() == "pci-dss":
                checkers_to_run.append(
                    (
                        "pci-dss",
                        PCIComplianceChecker(
                            collection_name="PCI-DSS-v4.0.1",
                            stop=["<turn|>"],
                            top_k=64,
                        ),
                    )
                )
            elif std.lower() == "gdpr":
                checkers_to_run.append(
                    (
                        "gdpr",
                        GDPRComplianceChecker(
                            collection_name="GDPR",
                            stop=["<turn|>"],
                            top_k=64,
                        ),
                    )
                )

    aggregated_report = BenchmarkReport()

    for standard_name, checker in checkers_to_run:
        # Filter cases for this standard
        if standard_name == "pci-dss":
            std_cases = [c for c in test_cases if c.name.startswith("PCI_DSS")]
        else:  # gdpr
            std_cases = [c for c in test_cases if c.name.startswith("GDPR")]

        if not std_cases:
            continue

        for i in range(iterations):
            if iterations > 1:
                print(f"\n{'=' * 40}")
                print(f"ITERATION {i + 1}/{iterations}")
                print(f"{'=' * 40}\n")

            report = BenchmarkRunner(std_cases, checker=checker, verbose=True).run()
            if iterations > 1:
                for result in report.analysis_results:
                    result["iteration"] = i + 1
                for result in report.generation_results:
                    result["iteration"] = i + 1

            aggregated_report.analysis_metrics += report.analysis_metrics
            aggregated_report.generation_metrics += report.generation_metrics
            aggregated_report.analysis_results.extend(report.analysis_results)
            aggregated_report.generation_results.extend(report.generation_results)

    print(aggregated_report.summary())
    aggregated_report.save(
        output or Path("benchmark_results.json"),
    )
