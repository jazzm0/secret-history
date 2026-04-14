#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import requests

# --- Configuration ---
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
MODEL = "llama3"
INPUT_DIR = "raw"
INPUT_EXT = ".txt"
OUTPUT_DIR = "."
PROMPT = """\
I want you to create from each file in the raw directory a summarizing file, which is more like literature. 
You are not allowed to change the semantics in any way. 
If questions are asked and answered, then formulate the answer so, that it blends into the context of the text.
The output should be in md format. Don't change the original files.\
"""
# ---------------------


def generate(file_content: str) -> str:
    full_prompt = f"{PROMPT}\n\n---\n\n{file_content}"
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": MODEL, "prompt": full_prompt, "stream": True},
        stream=True,
        timeout=600,
    )
    response.raise_for_status()

    parts = []
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        token = chunk.get("response", "")
        print(token, end="", flush=True)
        parts.append(token)
        if chunk.get("done"):
            break

    print()
    return "".join(parts)


def main() -> None:
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)

    input_files = sorted(input_dir.glob(f"*{INPUT_EXT}"))
    if not input_files:
        print(f"No {INPUT_EXT} files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    for input_path in input_files:
        output_path = output_dir / input_path.with_suffix(".md").name
        print(f"\n{'='*60}")
        print(f"Processing: {input_path.name}")
        print(f"Output:     {output_path}")
        print(f"{'='*60}\n")

        file_content = input_path.read_text(encoding="utf-8")
        result = generate(file_content)

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"\nSaved to {output_path}")

    print(f"\nDone. Processed {len(input_files)} files.")


if __name__ == "__main__":
    main()
