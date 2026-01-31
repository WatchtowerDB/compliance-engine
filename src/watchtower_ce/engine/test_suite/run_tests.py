#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

from django.conf import settings

from ..scripts.pci_compliance_checker import PCIComplianceChecker
from .analysis_quality_evaluator import AnalysisQualityEvaluator
from .gold_standard import create_analysis_quality_test_dataset

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

if __name__ == "__main__":
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

    metrics = evaluator.evaluate_all(checker, verbose=True)
    report = evaluator.generate_detailed_report(metrics)
    print(report)
    evaluator.save_results(Path("evaluation_results.json"), metrics)
