import os
from pathlib import Path

from ..scripts.pci_compliance_checker import PCIComplianceChecker
from .analysis_quality_evaluator import AnalysisQualityEvaluator
from .gold_standard import create_analysis_quality_test_dataset

if __name__ == "__main__":
    print("Creating analysis quality test dataset...")
    test_cases = create_analysis_quality_test_dataset()
    print(f"Created {len(test_cases)} test cases\n")

    evaluator = AnalysisQualityEvaluator(test_cases)

    SCRIPT_DIR = Path(__file__).parent.parent.parent.parent.parent
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
        context_window=7168,
        n_gpu_layers=34,
    )

    metrics = evaluator.evaluate_all(checker, verbose=True)
    report = evaluator.generate_detailed_report(metrics)
    print(report)
    evaluator.save_results(Path("evaluation_results.json"), metrics)
