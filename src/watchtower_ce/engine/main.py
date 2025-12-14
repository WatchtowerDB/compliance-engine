#!/usr/bin/env python3

from pathlib import Path

from models.download_model import download_model
from scripts.pci_compliance_checker import PCIComplianceChecker

download_model(
    "bartowski/Ministral-8B-Instruct-2410-GGUF",
    "Ministral-8B-Instruct-2410-GGUF",
    ["Ministral-8B-Instruct-2410-Q6_K_L.gguf"],
)

SCRIPT_DIR = Path(__file__).parent
MODEL_PATH: Path = (
    SCRIPT_DIR.parent
    / "engine/models/base/Ministral-8B-Instruct-2410-GGUF/Ministral-8B-Instruct-2410-Q6_K_L.gguf"
)
CHROMA_DIR: Path = SCRIPT_DIR.parent / "engine/data/chroma_db"
SQL_SCHEMA = """
CREATE TABLE customers (
	id INT PRIMARY KEY,
	name VARCHAR(100),
	credit_card_number VARCHAR(16),
	cvv VARCHAR(4),
	expiration_date DATE
);
"""

rag = PCIComplianceChecker(
    model_path=MODEL_PATH, chroma_dir=CHROMA_DIR, collection_name="PCI-DSS-v4.0.1"
)

result = rag.analyze(SQL_SCHEMA)
rag.close()
