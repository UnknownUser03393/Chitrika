"""Export a local Hugging Face emotion classifier to Chitrika's ONNX layout.

Usage:
    uv run python scripts/export_emotion_onnx.py \
        MEC/multilingual-emotion-classification models/emotion
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_LABEL_MAP = {
    "anger": {"anger": 1.0},
    "contempt": {"disgust": 0.7, "anger": 0.3},
    "disgust": {"disgust": 1.0},
    "fear": {"fear": 1.0},
    "frustration": {"anger": 0.6, "sadness": 0.3, "disgust": 0.1},
    "gratitude": {"trust": 0.7, "joy": 0.3},
    "joy": {"joy": 1.0},
    "love": {"trust": 0.6, "joy": 0.3, "anticipation": 0.1},
    "neutral": {},
    "sadness": {"sadness": 1.0},
    "surprise": {"surprise": 1.0},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Local Hugging Face model directory")
    parser.add_argument("output", help="Output directory, e.g. models/emotion")
    parser.add_argument("--max-length", type=int, default=192)
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Source model directory not found: {source}")

    config_path = source / "config.json"
    if not config_path.is_file():
        raise SystemExit(f"Missing config.json: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    id2label = config.get("id2label", {})
    labels = [id2label[str(index)] for index in range(len(id2label))]
    if not labels:
        raise SystemExit("config.json does not contain id2label")

    output.mkdir(parents=True, exist_ok=True)
    tmp_output = output / "_export"
    if tmp_output.exists():
        shutil.rmtree(tmp_output)

    command = [
        sys.executable,
        "-m",
        "optimum.exporters.onnx",
        "--model",
        str(source),
        "--task",
        "text-classification",
        str(tmp_output),
    ]
    subprocess.run(command, check=True)

    model_candidates = sorted(tmp_output.glob("*.onnx"))
    if not model_candidates:
        raise SystemExit(f"No ONNX model generated in {tmp_output}")
    shutil.copy2(model_candidates[0], output / "model.onnx")

    for filename in [
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "sentencepiece.bpe.model",
        "spm.model",
        "vocab.txt",
    ]:
        src = source / filename
        if src.is_file():
            shutil.copy2(src, output / filename)

    emotion_config = {
        "labels": labels,
        "max_length": args.max_length,
        "multilabel": config.get("problem_type") == "multi_label_classification",
        "threshold": 0.35,
        "label_map": {label: DEFAULT_LABEL_MAP.get(label, {}) for label in labels},
    }
    (output / "emotion_config.json").write_text(
        json.dumps(emotion_config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    shutil.rmtree(tmp_output)
    print(f"Exported emotion ONNX model to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
