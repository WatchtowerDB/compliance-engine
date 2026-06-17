import logging
import sys
from pathlib import Path

import click

from ..engine.standards.pci_compliance_checker import PCIComplianceChecker
from ..engine.test_suite.analysis_quality_evaluator import AnalysisQualityEvaluator
from ..engine.test_suite.evaluation_metrics import EvaluationMetrics
from ..engine.test_suite.gold_standard import create_analysis_quality_test_dataset


@click.command(
    "test",
    short_help="Run the test suite against a certain standard",
    help="Run the quality analysis test suite against a certain standard.",
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

    print("Creating analysis quality test dataset...")
    test_cases = create_analysis_quality_test_dataset()
    print(f"Created {len(test_cases)} test cases\n")

    evaluator = AnalysisQualityEvaluator(test_cases)

    checker = PCIComplianceChecker(
        collection_name="PCI-DSS-v4.0.1",
        prompt_template="<|turn>user\n{prompt}<turn|>\n<|turn>model\n",
        stop=["<turn|>"],
        top_k=64,
    )

    aggregated_metrics = EvaluationMetrics()
    all_detailed_results = []

    for i in range(iterations):
        if iterations > 1:
            print(f"\n{'=' * 40}")
            print(f"ITERATION {i + 1}/{iterations}")
            print(f"{'=' * 40}\n")

        metrics = evaluator.evaluate_all(checker, verbose=True)
        aggregated_metrics += metrics

        current_results = evaluator.results
        if iterations > 1:
            for res in current_results:
                res["iteration"] = i + 1
        all_detailed_results.extend(current_results)

    report = evaluator.generate_detailed_report(
        aggregated_metrics, detailed_results=all_detailed_results
    )
    print(report)
    evaluator.save_results(
        Path("evaluation_results.json"),
        aggregated_metrics,
        detailed_results=all_detailed_results,
    )
