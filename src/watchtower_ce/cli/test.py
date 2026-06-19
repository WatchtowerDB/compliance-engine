import logging
import sys
from pathlib import Path

import click

from ..engine.standards import PCIComplianceChecker
from ..engine.test_suite import (
    PCI_DSS_STAGE_2_CASES,
    PCI_DSS_STAGE_4_CASES,
    BenchmarkReport,
    BenchmarkRunner,
)


@click.command(
    "test",
    short_help="Run benchmark suite against a standard",
    help="Run the benchmark suite (stage 2 generation + stage 4 analysis).",
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--iterations",
    type=int,
    help="Number of iterations to run the test suite. The results of all iterations are aggregated. Higher values give more accurate scores but take more time to run.",
    default=1,
)
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging.")
def test(
    iterations: int, debug: bool
) -> None:  # TODO: WHEN MORE STANDARDS ARE IMPLEMENTED, THE TEST COMMAND SHOULD TAKE A "STANDARD"
    if debug:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    print("Loading benchmark dataset...")
    test_cases = [*PCI_DSS_STAGE_2_CASES, *PCI_DSS_STAGE_4_CASES]
    print(f"Created {len(test_cases)} test cases\n")

    checker = PCIComplianceChecker(
        collection_name="PCI-DSS-v4.0.1",
        stop=["<turn|>"],
        top_k=64,
    )

    aggregated_report = BenchmarkReport()

    for i in range(iterations):
        if iterations > 1:
            print(f"\n{'=' * 40}")
            print(f"ITERATION {i + 1}/{iterations}")
            print(f"{'=' * 40}\n")

        report = BenchmarkRunner(test_cases, checker=checker, verbose=True).run()
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
    aggregated_report.save(Path("benchmark_results.json"))
