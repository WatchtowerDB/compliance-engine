import argparse
import logging
import os
import sys
from pathlib import Path

from ..scripts.pci_compliance_checker import PCIComplianceChecker
from .analysis_quality_evaluator import AnalysisQualityEvaluator
from .evaluation_metrics import EvaluationMetrics
from .gold_standard import create_analysis_quality_test_dataset

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Analysis Quality Tests")
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of times to run the test suite to aggregate results",
    )
    args = parser.parse_args()

    print("Creating analysis quality test dataset...")
    test_cases = create_analysis_quality_test_dataset()
    print(f"Created {len(test_cases)} test cases\n")

    evaluator = AnalysisQualityEvaluator(test_cases)

    SCRIPT_DIR = Path(__file__).resolve().parents[4]
    MODEL_PATH: Path = Path(
        os.getenv(
            "WTCE_MODEL_PATH",
            SCRIPT_DIR
            / "models/base/Ministral-8B-Instruct-2410-GGUF/Ministral-8B-Instruct-2410-Q6_K_L.gguf",
        )
    )
    CHROMA_DIR: Path = Path(os.getenv("WTCE_CHROMA_DIR", SCRIPT_DIR / "data/chroma_db"))

    checker = PCIComplianceChecker(
        model_path=MODEL_PATH,
        chroma_dir=CHROMA_DIR,
        collection_name="PCI-DSS-v4.0.1",
        context_window=8192,
        n_gpu_layers=31,
    )

    aggregated_metrics = EvaluationMetrics()
    all_detailed_results = []

    for i in range(args.iterations):
        if args.iterations > 1:
            print(f"\n{'=' * 40}")
            print(f"ITERATION {i + 1}/{args.iterations}")
            print(f"{'=' * 40}\n")

        metrics = evaluator.evaluate_all(checker, verbose=True)
        aggregated_metrics += metrics

        current_results = evaluator.results
        if args.iterations > 1:
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
