"""
Run a small MLSecOps scan with NVIDIA Garak against the lightweight local LLM.

The script wraps Garak's CLI so it works reliably on Windows by setting a UTF-8
stdout encoding and changing the working directory to where the Garak package
is installed (Garak expects its plugin folders to be relative to CWD).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import site
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict

import garak.cli
from llm_utils import DEFAULT_LLM_MODEL, ensure_model_ready

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


@contextmanager
def change_workdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def locate_garak_site_root() -> Path:
    """Find the site-packages directory that contains the installed garak package."""
    candidate_paths = []

    site_paths = []
    if hasattr(site, "getsitepackages"):
        site_paths.extend(site.getsitepackages())
    user_site = site.getusersitepackages()
    if user_site:
        site_paths.append(user_site)

    for path_str in site_paths:
        if not path_str:
            continue
        path_obj = Path(path_str)
        if (path_obj / "garak").exists():
            candidate_paths.append(path_obj)

    if not candidate_paths:
        raise RuntimeError("Could not locate an installed garak package on sys.path.")

    return sorted(candidate_paths)[0]


def copy_if_exists(source: Path, destination_dir: Path) -> Path | None:
    if source.exists():
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / source.name
        shutil.copy2(source, destination)
        return destination
    return None


def run_garak_scan(
    *,
    model_name: str,
    probes: str,
    generations: int,
    output_dir: Path,
) -> Dict[str, str]:
    """Execute Garak and collect the generated report/log files."""
    ensure_model_ready(model_name)
    garak_root = locate_garak_site_root()
    output_dir.mkdir(parents=True, exist_ok=True)

    existing_reports = set(garak_root.glob("garak.*.jsonl"))
    log_path = garak_root / "garak.log"

    with change_workdir(garak_root):
        garak.cli.main(
            [
                "--model_type",
                "huggingface",
                "--model_name",
                model_name,
                "--probes",
                probes,
                "--generations",
                str(generations),
            ]
        )

    new_reports = sorted(
        (set(garak_root.glob("garak.*.jsonl")) - existing_reports),
        key=lambda path: path.stat().st_mtime,
    )

    summary: Dict[str, str] = {
        "model_name": model_name,
        "probes": probes,
        "generations": str(generations),
    }

    if new_reports:
        copied_report = copy_if_exists(new_reports[-1], output_dir)
        if copied_report:
            summary["report_file"] = str(copied_report)

    copied_log = copy_if_exists(log_path, output_dir)
    if copied_log:
        summary["log_file"] = str(copied_log)

    summary_path = output_dir / "garak_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run NVIDIA Garak MLSecOps probes against the lightweight local LLM."
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_LLM_MODEL,
        help="Hugging Face model to scan with Garak (defaults to a tiny GPT-2).",
    )
    parser.add_argument(
        "--probes",
        default="promptinject.HijackNevermind,dan.Dan_8_0",
        help="Comma-separated list of Garak probes to execute.",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=2,
        help="Number of generations per prompt Garak should request.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts") / "mlsecops",
        help="Directory where Garak reports/logs will be copied.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_garak_scan(
        model_name=args.model_name,
        probes=args.probes,
        generations=args.generations,
        output_dir=args.output_dir,
    )
    print("Garak MLSecOps summary:", json.dumps(summary, indent=2))
    print(f"Reports copied under: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
