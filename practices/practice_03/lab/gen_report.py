"""Generate REPORT.md using local environment and Ollama REST API. Standard library only.

This script reads Modelfiles, queries local Ollama for installed models, and writes a concise report.
It does not send project files or any gold answers to models.
"""
from __future__ import annotations
import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def get_ollama_list() -> list[dict]:
    # Prefer REST to avoid parsing; fall back to CLI
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.load(resp)
        return data.get("models", [])
    except Exception:
        pass
    if shutil.which("ollama"):
        try:
            out = subprocess.check_output(["ollama", "list", "--json"], text=True)
            # ollama list --json prints multiple json lines
            return [json.loads(line) for line in out.splitlines() if line.strip()]
        except Exception:
            return []
    return []


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    mod_agent = read_text(root / "Modelfile.agent")
    mod_exp = read_text(root / "Modelfile")
    models = get_ollama_list()

    lines = []
    lines.append("# REPORT")
    lines.append("")
    lines.append("## Hardware/Software")
    lines.append(f"Python: {platform.python_version()} on {platform.system()} {platform.release()} ({platform.machine()})")
    lines.append(f"CPU: {platform.processor() or 'n/a'}")
    # GPU is environment-specific; we avoid heavy calls. Mention presence of nvidia-smi if available.
    lines.append(f"nvidia-smi: {'yes' if shutil.which('nvidia-smi') else 'no'}")
    lines.append("")
    lines.append("## Models")
    lines.append("- Target agent model id: itmo-agent (from Modelfile.agent)")
    lines.append("- Experiment model id: itmo-experiment (from Modelfile)")
    lines.append("")
    lines.append("Installed (Ollama):")
    for m in models:
        # m may have fields: name, model, modified_at, size, digest, details{parameter_size, quantization} etc.
        name = m.get("name") or m.get("model")
        quant = (m.get("details") or {}).get("quantization")
        ctx = (m.get("details") or {}).get("context_length")
        lines.append(f"- {name} quant={quant} context={ctx}")
    lines.append("")
    lines.append("## Modelfiles")
    lines.append("### Modelfile.agent")
    lines.append("```")
    lines.append(mod_agent.strip())
    lines.append("```")
    lines.append("")
    lines.append("### Modelfile")
    lines.append("```")
    lines.append(mod_exp.strip())
    lines.append("```")

    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
