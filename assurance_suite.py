"""
Lightweight assurance suite that wraps fairness (Fairlearn), security (Giskard),
governance (Credo AI friendly outputs), and SBOM (CycloneDX) steps around the
existing churn demo.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from main import (
    CATEGORICAL_FEATURES,
    LABEL_COLUMN,
    NUMERIC_FEATURES,
    TEXT_FEATURE,
    compute_evaluation_outputs,
    ensure_reproducibility,
    prepare_train_test_split,
    synthesize_customer_data,
    train_model,
)

DEFAULT_SENSITIVE_FEATURES = ["region", "customer_segment"]


def _json_default(obj: Any) -> str:
    """Fallback serializer for non-JSON-native objects."""
    try:
        if isinstance(obj, Path):
            return str(obj)
        if hasattr(obj, "__name__") and isinstance(obj, type):
            return obj.__name__
        return str(obj)
    except Exception:
        return "<unserializable>"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run assurance checks (fairness, security, governance, SBOM) on the "
            "logistic-regression churn demo."
        )
    )
    parser.add_argument("--samples", type=int, default=400, help="Synthetic sample size.")
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.25,
        help="Fraction reserved for evaluation.",
    )
    parser.add_argument(
        "--random-state", type=int, default=42, help="Random seed for data/model."
    )
    parser.add_argument(
        "--tfidf-max-features",
        type=int,
        default=500,
        help="Maximum n-gram features in the TF-IDF block.",
    )
    parser.add_argument(
        "--logreg-c",
        type=float,
        default=1.0,
        help="Inverse regularisation strength for LogisticRegression.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts") / "assurance",
        help="Root directory for assurance artifacts.",
    )
    parser.add_argument(
        "--sensitive-features",
        nargs="+",
        default=DEFAULT_SENSITIVE_FEATURES,
        help="Columns used for Fairlearn group comparisons.",
    )
    parser.add_argument(
        "--sbom-format",
        choices=["json", "xml"],
        default="json",
        help="CycloneDX output format.",
    )
    parser.add_argument("--skip-fairlearn", action="store_true", help="Skip fairness run.")
    parser.add_argument("--skip-giskard", action="store_true", help="Skip Giskard scan.")
    parser.add_argument("--skip-credo", action="store_true", help="Skip governance card.")
    parser.add_argument("--skip-sbom", action="store_true", help="Skip SBOM generation.")
    return parser.parse_args()


def _positive_label(class_labels: List[str]) -> str:
    if "yes" in class_labels:
        return "yes"
    if class_labels:
        return class_labels[-1]
    return "positive"


def _binarize(series: pd.Series, positive_label: str) -> pd.Series:
    return series.reset_index(drop=True).astype(str).str.lower() == positive_label


def run_fairlearn_checks(
    *,
    test_df: pd.DataFrame,
    evaluation_outputs: Dict[str, Any],
    sensitive_features: List[str],
    artifact_dir: Path,
) -> Dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    try:
        from fairlearn.metrics import (
            MetricFrame,
            demographic_parity_difference,
            equalized_odds_difference,
            false_positive_rate,
            selection_rate,
            true_positive_rate,
        )
    except Exception as exc:  # pragma: no cover - defensive if optional dep missing
        skip_path = artifact_dir / "FAIRLEARN_SKIPPED.txt"
        skip_path.write_text(
            "Fairlearn yüklü değil veya import edilemedi. "
            "pip install fairlearn ile kurulumu tamamlayın.\n"
            f"Hata: {exc}"
        )
        return {
            "status": "skipped",
            "reason": str(exc),
            "artifact_dir": str(artifact_dir),
        }

    class_labels = evaluation_outputs.get("class_labels", [])
    positive_label = _positive_label(class_labels)
    y_true_bool = _binarize(test_df[LABEL_COLUMN], positive_label)
    y_pred_bool = _binarize(
        pd.Series(evaluation_outputs["predictions"]), positive_label
    )

    overall = {
        "accuracy": accuracy_score(y_true_bool, y_pred_bool),
        "precision": precision_score(y_true_bool, y_pred_bool, zero_division=0),
        "recall": recall_score(y_true_bool, y_pred_bool, zero_division=0),
        "f1": f1_score(y_true_bool, y_pred_bool, zero_division=0),
    }

    fairness_by_feature: Dict[str, Any] = {}
    for feature in sensitive_features:
        if feature not in test_df.columns:
            continue
        sensitive = test_df[feature].reset_index(drop=True)
        metric_frame = MetricFrame(
            metrics={
                "accuracy": accuracy_score,
                "selection_rate": selection_rate,
                "true_positive_rate": true_positive_rate,
                "false_positive_rate": false_positive_rate,
            },
            y_true=y_true_bool,
            y_pred=y_pred_bool,
            sensitive_features=sensitive,
        )

        by_group_df = metric_frame.by_group.reset_index().rename(
            columns={"index": feature}
        )
        by_group_path = artifact_dir / f"{feature}_fairness_groups.csv"
        by_group_df.to_csv(by_group_path, index=False)

        tpr_series = metric_frame.by_group["true_positive_rate"]
        equal_opportunity_difference = float(
            tpr_series.max() - tpr_series.min()
        ) if not tpr_series.empty else 0.0

        fairness_by_feature[feature] = {
            "overall": metric_frame.overall.to_dict(),
            "by_group": by_group_df.to_dict(orient="records"),
            "disparity": {
                "demographic_parity_difference": float(
                    demographic_parity_difference(
                        y_true_bool, y_pred_bool, sensitive_features=sensitive
                    )
                ),
                "equalized_odds_difference": float(
                    equalized_odds_difference(
                        y_true_bool, y_pred_bool, sensitive_features=sensitive
                    )
                ),
                "equal_opportunity_difference": equal_opportunity_difference,
            },
            "by_group_csv": str(by_group_path),
        }

    report = {
        "status": "completed",
        "positive_label": positive_label,
        "overall": overall,
        "features": fairness_by_feature,
        "artifact_dir": str(artifact_dir),
    }
    report_path = artifact_dir / "fairlearn_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=_json_default))
    return report


def run_giskard_security_scan(
    *,
    model,
    test_df: pd.DataFrame,
    artifact_dir: Path,
) -> Dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Giskard 2.x henüz Python 3.13'ü desteklemiyor; erken çıkış ile rapor yaz.
    if sys.version_info >= (3, 13):
        summary = {
            "status": "unsupported_python",
            "python_version": sys.version.split()[0],
            "note": (
                "Giskard 2.x henüz Python 3.13 için yayınlanmadı. "
                "Python 3.10/3.11 virtualenv içinde `pip install giskard` "
                "kurup `python assurance_suite.py --skip-fairlearn --skip-credo --skip-sbom` "
                "ile tarayın."
            ),
            "artifact_dir": str(artifact_dir),
        }
        summary_path = artifact_dir / "giskard_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=_json_default))
        (artifact_dir / "GISKARD_UNSUPPORTED.txt").write_text(summary["note"])
        return summary

    try:
        from giskard import Dataset, Model, scan
    except Exception as exc:  # pragma: no cover - optional dependency guard
        skip_path = artifact_dir / "GISKARD_SKIPPED.txt"
        skip_path.write_text(
            "Giskard (>=2.x) henüz kurulmadı veya mevcut Python 3.13 ortamında "
            "desteklenmiyor. Python 3.10/3.11 ile `pip install giskard` kurup "
            "yeniden deneyin.\n"
            f"Hata: {exc}"
        )
        return {
            "status": "skipped",
            "reason": str(exc),
            "artifact_dir": str(artifact_dir),
        }

    # Ensure UTF-8 console encoding so Giskard's emoji logs don't crash on Windows.
    try:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    def predict_fn(df: pd.DataFrame):
        features = df.drop(columns=[LABEL_COLUMN], errors="ignore")
        return model.predict_proba(features)

    try:
        dataset = Dataset(
            df=test_df,
            target=LABEL_COLUMN,
            cat_columns=CATEGORICAL_FEATURES,
            column_types={TEXT_FEATURE: "text"},
            name="churn_testset",
        )
        wrapped_model = Model(
            model=predict_fn,
            model_type="classification",
            feature_names=list(test_df.drop(columns=[LABEL_COLUMN]).columns),
            classification_labels=list(getattr(model, "classes_", [])),
            name="logreg_churn_demo",
        )

        summary: Dict[str, Any] = {
            "status": "completed",
            "artifact_dir": str(artifact_dir),
        }
        try:
            scan_report = scan(wrapped_model, dataset)
            summary["issues_found"] = len(getattr(scan_report, "issues", []) or [])

            try:
                report_json = scan_report.to_json()
                report_path = artifact_dir / "giskard_scan_report.json"
                report_path.write_text(report_json, encoding="utf-8")
                summary["report_json"] = str(report_path)
            except Exception as report_exc:
                summary["report_save_warning"] = f"could not save report: {report_exc}"
        except Exception as scan_exc:  # pragma: no cover - API differences handled
            summary["status"] = "error"
            summary["error"] = f"scan failed: {scan_exc}"

        summary_path = artifact_dir / "giskard_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=_json_default))
        return summary
    except Exception as exc:  # pragma: no cover - defensive guardrails
        error_path = artifact_dir / "GISKARD_ERROR.txt"
        error_path.write_text(
            "Giskard scan çalıştırılırken hata oluştu. "
            "API değişiklikleri veya desteklenmeyen Python sürümü olabilir.\n"
            f"Hata: {exc}"
        )
        return {
            "status": "error",
            "reason": str(exc),
            "artifact_dir": str(artifact_dir),
        }


def generate_sbom(*, output_dir: Path, fmt: str) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sbom_path = output_dir / f"sbom.{fmt}"
    fmt_arg = fmt.upper()
    command = [
        sys.executable,
        "-m",
        "cyclonedx_py",
        "environment",
        "--of",
        fmt_arg,
        "-o",
        str(sbom_path),
    ]
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
        )
        summary = {
            "status": "completed",
            "sbom_file": str(sbom_path),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(command),
        }
    except FileNotFoundError:
        fallback_path = output_dir / "sbom_requirements_freeze.txt"
        freeze = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        fallback_path.write_text(freeze.stdout)
        summary = {
            "status": "cyclonedx_missing",
            "fallback_freeze": str(fallback_path),
            "note": (
                "CycloneDX CLI bulunamadı. `pip install cyclonedx-bom` veya "
                "`python -m cyclonedx_py environment --format json -o sbom.json` deneyin."
            ),
        }
    except subprocess.CalledProcessError as exc:
        summary = {"status": "error", "reason": str(exc), "stderr": exc.stderr}

    summary_path = output_dir / "sbom_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=_json_default))
    return summary


def generate_governance_report(
    *,
    artifact_dir: Path,
    evaluation_outputs: Dict[str, Any],
    model_summary: Dict[str, Any],
    fairness_summary: Dict[str, Any],
    giskard_summary: Dict[str, Any],
    sbom_summary: Dict[str, Any],
) -> Dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "status": "completed",
        "model_overview": model_summary,
        "evaluation_metrics": evaluation_outputs.get("metrics", {}),
        "fairness": fairness_summary,
        "security": giskard_summary,
        "sbom": sbom_summary,
        "policy_notes": [
            "Veri kaynağı: assurance_suite.py içinde oluşturulan sentetik müşteri verisi.",
            "Model: TF-IDF + One-Hot + LogisticRegression pipeline, positive label: yes.",
            "Adalet: Fairlearn grup metrikleri ve parite farkları raporda.",
            "Güvenlik: Giskard scan (kuruluysa) sonuçları artifact klasöründe.",
            "Supply chain: CycloneDX SBOM veya pip freeze fallback dosyası.",
        ],
    }

    json_path = artifact_dir / "model_governance_report.json"
    json_path.write_text(json.dumps(report, indent=2, default=_json_default))

    md_path = artifact_dir / "model_governance_report.md"
    md_path.write_text(
        "# Model Governance Özeti (Credo AI uyumlu taslak)\n"
        "- Model: LogisticRegression (sklearn pipeline) — label: yes/no churn\n"
        "- Adalet: Fairlearn çıktıları -> "
        f"{fairness_summary.get('artifact_dir', str(artifact_dir))}\n"
        "- Güvenlik: Giskard taraması -> "
        f"{giskard_summary.get('artifact_dir', str(artifact_dir))}\n"
        "- SBOM: CycloneDX -> {sbom_summary.get('sbom_file', 'pip freeze fallback')}\n"
        "- Aksiyon: Credo AI Lens için Python 3.10/3.11 ortamında "
        "`pip install credoai-lens` ve bu raporu yükleyin.\n"
    )

    instructions_path = artifact_dir / "CREDOAI_INSTRUCTIONS.txt"
    instructions_path.write_text(
        "Credo AI Lens kullanımı (opsiyonel):\n"
        "1) Python 3.10/3.11 virtualenv açın.\n"
        "2) pip install credoai-lens\n"
        "3) Sentetik veri ve metrikleri model_governance_report.json içinden Lens'e "
        "yükleyerek yönetişim raporunu tamamlayın.\n"
        "Not: Lens, pandas-profiling bağımlılığı nedeniyle Python 3.13 üzerinde "
        "desteklenmeyebilir.\n"
    )
    return report


def main() -> None:
    args = parse_args()
    rng = ensure_reproducibility(args.random_state)
    artifact_root = Path(args.artifact_dir)
    artifact_root.mkdir(parents=True, exist_ok=True)

    synthetic_df = synthesize_customer_data(args.samples, rng)
    train_df, test_df = prepare_train_test_split(
        synthetic_df, test_size=args.test_size, random_state=args.random_state
    )

    model, model_summary = train_model(
        train_df,
        tfidf_max_features=args.tfidf_max_features,
        logreg_c=args.logreg_c,
        random_state=args.random_state,
    )
    evaluation_outputs = compute_evaluation_outputs(model, test_df)

    fairlearn_summary = {"status": "skipped"}
    if not args.skip_fairlearn:
        fairlearn_summary = run_fairlearn_checks(
            test_df=test_df,
            evaluation_outputs=evaluation_outputs,
            sensitive_features=args.sensitive_features,
            artifact_dir=artifact_root / "fairlearn",
        )

    giskard_summary = {"status": "skipped"}
    if not args.skip_giskard:
        giskard_summary = run_giskard_security_scan(
            model=model,
            test_df=test_df,
            artifact_dir=artifact_root / "giskard",
        )

    sbom_summary = {"status": "skipped"}
    if not args.skip_sbom:
        sbom_summary = generate_sbom(
            output_dir=artifact_root / "sbom", fmt=args.sbom_format
        )

    governance_summary = {"status": "skipped"}
    if not args.skip_credo:
        governance_summary = generate_governance_report(
            artifact_dir=artifact_root / "governance",
            evaluation_outputs=evaluation_outputs,
            model_summary=model_summary,
            fairness_summary=fairlearn_summary,
            giskard_summary=giskard_summary,
            sbom_summary=sbom_summary,
        )

    summary = {
        "fairlearn": fairlearn_summary,
        "giskard": giskard_summary,
        "sbom": sbom_summary,
        "governance": governance_summary,
        "artifact_root": str(artifact_root),
    }
    summary_path = artifact_root / "assurance_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=_json_default))

    print("Assurance tamamlandı. Özet dosyası:", summary_path.resolve())
    print("Adalet çıktı klasörü:", fairlearn_summary.get("artifact_dir"))
    print("Giskard çıktı klasörü:", giskard_summary.get("artifact_dir"))
    print("SBOM klasörü:", sbom_summary.get("sbom_file", sbom_summary.get("fallback_freeze")))
    print("Governance taslağı:", governance_summary.get("status"))


if __name__ == "__main__":
    main()
