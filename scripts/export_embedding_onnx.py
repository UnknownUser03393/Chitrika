"""Export a local Hugging Face sentence-embedding model to Chitrika's ONNX layout.

Produces the directory ``memory_embedding.MemoryEmbedder`` expects:
    model.onnx
    tokenizer.json  (+ any tokenizer sidecar files)
    embedding_config.json  (max_length, normalize, dim)

Usage:
    uv run python scripts/export_embedding_onnx.py \
        MEC/bge-small-zh-v1.5 models/embedding

Pick any multilingual / Chinese-capable sentence-transformer, e.g.
``BAAI/bge-small-zh-v1.5`` or ``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2``.
Download it locally first (git lfs or huggingface-cli), then point `source` at it.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Local Hugging Face model directory")
    parser.add_argument("output", help="Output directory, e.g. models/embedding")
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Store raw vectors instead of L2-normalized ones",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Source model directory not found: {source}")

    hidden_size = None
    config_path = source / "config.json"
    if config_path.is_file():
        try:
            model_config = json.loads(config_path.read_text(encoding="utf-8"))
            hidden_size = model_config.get("hidden_size")
        except (OSError, json.JSONDecodeError):
            pass

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
        "feature-extraction",
        str(tmp_output),
    ]
    subprocess.run(command, check=True)

    model_candidates = sorted(tmp_output.glob("*.onnx"))
    if not model_candidates:
        raise SystemExit(f"No ONNX model generated in {tmp_output}")
    shutil.copy2(model_candidates[0], output / "model.onnx")

    # Optimum writes a fast tokenizer (tokenizer.json) into the export dir even
    # for SentencePiece models that ship only *.bpe.model, so prefer the export
    # output and fall back to the source repo.
    tokenizer_files = [
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "sentencepiece.bpe.model",
        "spm.model",
        "vocab.txt",
    ]
    for filename in tokenizer_files:
        for candidate_dir in (tmp_output, source):
            src = candidate_dir / filename
            if src.is_file():
                shutil.copy2(src, output / filename)
                break

    if not (output / "tokenizer.json").is_file():
        raise SystemExit(
            "tokenizer.json was not produced; the model needs a fast tokenizer."
        )

    embedding_config = {
        "max_length": args.max_length,
        "normalize": not args.no_normalize,
        "dim": hidden_size,
    }
    (output / "embedding_config.json").write_text(
        json.dumps(embedding_config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    shutil.rmtree(tmp_output)
    print(f"Exported embedding ONNX model to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
