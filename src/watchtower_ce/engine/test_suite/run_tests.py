#!/usr/bin/env python3

import argparse
import logging
import sys
from pathlib import Path

from django.conf import settings

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

    checker = PCIComplianceChecker(
        base_model_path=settings.BASE_MODEL_PATH,
        chroma_dir=settings.CHROMA_DIR,
        collection_name="PCI-DSS-v4.0.1",
        embedding_model=settings.EMBEDDING_MODEL_DIR,
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
