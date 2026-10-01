"""Explicit opt-in upload of the synthetic golden set; never uploads learner records."""

import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from langsmith import Client
from academy.models import ROOT


if __name__ == "__main__":
    load_dotenv(ROOT / ".env", override=False)
    if not os.getenv("LANGSMITH_API_KEY"):
        raise SystemExit(
            "Configure your LangSmith API key before explicitly uploading this synthetic dataset."
        )
    source = ROOT / "evals/golden.json"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    name = "promql-academy-golden-" + digest[:12]
    client = Client()
    if client.has_dataset(dataset_name=name):
        raise SystemExit("This exact dataset version is already uploaded: " + name)
    dataset = client.create_dataset(
        dataset_name=name,
        description="Authored synthetic academy evaluation cases; no learner records.",
        metadata={"sha256": digest, "curriculum": "v1"},
    )
    cases = json.loads(source.read_text())
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": {"question": row["question"]},
                "outputs": {key: value for key, value in row.items() if key != "question"},
                "metadata": {"synthetic": True, "dataset_sha256": digest},
            }
            for row in cases
        ],
    )
    print("Uploaded", len(cases), "synthetic cases to", name)
