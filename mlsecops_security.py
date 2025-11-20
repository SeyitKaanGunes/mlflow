"""
Utility helpers that implement the MLSecOps guidance from the
"MLSecOps-Yapay-Zeka-Muhendisleri-Icin-Kapsamli-Guvenlik-Operasyonlari-Rehberi"
playbook.

The helpers expose lightweight controls for:
    * data provenance tracking (hashes + schema level stats)
    * heuristics that look for data poisoning signals
    * adversarial stress testing (ML01 / MITRE ATLAS execution)
    * membership inference risk scoring (ML03/ML04 privacy threats)
The module relies only on pandas/numpy so it can run inside the
existing training job without bringing extra dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

LABEL_KEY = "label"


@dataclass
class RiskScore:
    """Container for a single MLSecOps risk evaluation."""

    name: str
    level: str
    details: Dict
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "level": self.level,
            "details": self.details,
            "recommendations": self.recommendations,
        }


def _hash_dataframe(df: pd.DataFrame) -> str:
    """Deterministic hash for provenance tracking."""
    hashed_values = pd.util.hash_pandas_object(df, index=True).values
    digest = sha256(hashed_values).hexdigest()
    return digest


def build_data_manifest(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    numeric_columns: Iterable[str],
    categorical_columns: Iterable[str],
) -> Dict:
    """Compute schema level stats that can be used as provenance signals."""

    def _numeric_summary(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        stats: Dict[str, Dict[str, float]] = {}
        for column in numeric_columns:
            series = df[column]
            stats[column] = {
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "std": float(series.std(ddof=0)),
            }
        return stats

    def _categorical_summary(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        stats: Dict[str, Dict[str, float]] = {}
        for column in categorical_columns:
            value_counts = df[column].value_counts(normalize=True).head(5)
            stats[column] = value_counts.to_dict()
        return stats

    return {
        "train": {
            "rows": int(len(train_df)),
            "hash": _hash_dataframe(train_df),
            "numeric_stats": _numeric_summary(train_df),
            "categorical_distribution": _categorical_summary(train_df),
        },
        "test": {
            "rows": int(len(test_df)),
            "hash": _hash_dataframe(test_df),
            "numeric_stats": _numeric_summary(test_df),
            "categorical_distribution": _categorical_summary(test_df),
        },
    }


def scan_for_data_poisoning(
    df: pd.DataFrame,
    label_column: str,
    numeric_columns: Iterable[str],
) -> RiskScore:
    """Detect simple OWASP ML02 indicators such as out-of-range values."""
    issues: List[str] = []

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        issues.append(f"{duplicate_rows} duplicated rows detected.")

    class_balance = df[label_column].value_counts(normalize=True).to_dict()
    majority = max(class_balance.values())
    if majority > 0.75:
        issues.append(
            f"Label imbalance detected (majority class frequency={majority:.2f})."
        )

    outlier_rows = 0
    for column in numeric_columns:
        series = df[column]
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - (3 * iqr)
        upper = q3 + (3 * iqr)
        mask = (series < lower) | (series > upper)
        outlier_rows += int(mask.sum())
    if outlier_rows:
        issues.append(f"{outlier_rows} numeric rows outside 3*IQR boundaries.")

    if not issues:
        level = "low"
    elif len(issues) == 1:
        level = "medium"
    else:
        level = "high"

    recommendations = [
        "Review upstream data sources and retrace provenance chain.",
        "Validate contributor identities for user-generated data.",
        "Regenerate dataset from trusted sources if tampering is confirmed.",
    ]

    return RiskScore(
        name="OWASP-ML02-DataPoisoning",
        level=level,
        details={"issues": issues, "class_balance": class_balance},
        recommendations=recommendations,
    )


def evaluate_membership_inference_risk(
    model: Pipeline,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    label_column: str,
) -> RiskScore:
    """Estimate privacy exposure (OWASP ML03/ML04) via confidence gap analysis."""
    train_features = train_df.drop(columns=[label_column])
    test_features = test_df.drop(columns=[label_column])

    train_conf = model.predict_proba(train_features).max(axis=1)
    test_conf = model.predict_proba(test_features).max(axis=1)

    confidence_gap = float(train_conf.mean() - test_conf.mean())
    variance_gap = float(train_conf.var() - test_conf.var())

    if confidence_gap > 0.15:
        level = "high"
    elif confidence_gap > 0.08:
        level = "medium"
    else:
        level = "low"

    recommendations = [
        "Reduce overfitting (regularisation, more data, early stopping).",
        "Consider confidence clipping or logit rounding on inference APIs.",
        "Add differential privacy noise before exposing model outputs.",
    ]

    return RiskScore(
        name="OWASP-ML03-ML04-Privacy",
        level=level,
        details={
            "train_confidence_mean": float(train_conf.mean()),
            "test_confidence_mean": float(test_conf.mean()),
            "confidence_gap": confidence_gap,
            "variance_gap": variance_gap,
        },
        recommendations=recommendations,
    )


def run_adversarial_stress_test(
    model: Pipeline,
    test_df: pd.DataFrame,
    label_column: str,
    numeric_columns: Iterable[str],
    text_column: str,
    baseline_accuracy: float,
    epsilon: float,
    trigger_phrase: str,
    rng: np.random.Generator | None = None,
) -> RiskScore:
    """
    Approximate ML01 (adversarial evasion) by injecting bounded noise
    on numeric attributes and planting a trigger phrase inside the text block.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    perturbed = test_df.copy(deep=True)
    numeric_stats = test_df[list(numeric_columns)].std(ddof=0).replace(0, 1)
    noise = rng.normal(
        loc=0.0,
        scale=np.clip(numeric_stats * epsilon, 1e-3, None),
        size=(len(test_df), len(numeric_columns)),
    )
    for idx, column in enumerate(numeric_columns):
        perturbed[column] = perturbed[column] + noise[:, idx]

    trigger_mask = rng.random(len(perturbed)) < 0.3
    perturbed.loc[trigger_mask, text_column] = (
        perturbed.loc[trigger_mask, text_column] + f" {trigger_phrase}"
    )

    features = perturbed.drop(columns=[label_column])
    labels = perturbed[label_column]
    adv_predictions = model.predict(features)

    adv_accuracy = float(accuracy_score(labels, adv_predictions))
    degradation = float(max(0.0, baseline_accuracy - adv_accuracy))

    triggered_subset = perturbed[trigger_mask]
    if not triggered_subset.empty:
        triggered_preds = model.predict(triggered_subset.drop(columns=[label_column]))
        targeted_success = float(
            np.mean(triggered_preds != triggered_subset[label_column])
        )
    else:
        targeted_success = 0.0

    if degradation >= 0.2:
        level = "high"
    elif degradation >= 0.1:
        level = "medium"
    else:
        level = "low"

    recommendations = [
        "Introduce adversarial training (FGSM/PGD) in CI pipelines.",
        "Limit inference outputs to class labels or rounded confidences.",
        "Add rate limiting and anomaly detection around inference APIs.",
    ]

    return RiskScore(
        name="OWASP-ML01-AdversarialEvasion",
        level=level,
        details={
            "baseline_accuracy": baseline_accuracy,
            "adversarial_accuracy": adv_accuracy,
            "accuracy_degradation": degradation,
            "triggered_subset_size": int(trigger_mask.sum()),
            "targeted_success_rate": targeted_success,
        },
        recommendations=recommendations,
    )


def assemble_security_report(
    manifest: Dict,
    risks: Iterable[RiskScore],
    output_dir: Path,
) -> Dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    risk_entries = [risk.to_dict() for risk in risks]
    severity_map = {"low": 0, "medium": 1, "high": 2}
    aggregate_level = max((severity_map[risk["level"]] for risk in risk_entries), default=0)
    reverse_map = {value: key for key, value in severity_map.items()}
    aggregate_label = reverse_map.get(aggregate_level, "low")

    report = {
        "manifest": manifest,
        "risks": risk_entries,
        "aggregate_risk_level": aggregate_label,
        "owasp_mappings": [risk["name"] for risk in risk_entries],
        "mitre_atlas_focus": [
            "ML Attack Staging",
            "ML Model Access",
            "ML Attack Execution",
        ],
    }

    report_path = output_dir / "mlsecops_security_report.json"
    report_path.write_text(json.dumps(report, indent=2))

    return {"report": report, "path": report_path}

