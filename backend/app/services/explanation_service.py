import logging
from typing import Any

import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)


class ExplanationService:
    """SHAP explanation service for risk model predictions."""

    FEATURE_DESCRIPTION_MAP = {
        "ae_score": "high anomaly in system behavior",
        "if_score": "abnormal activity detected by isolation model",
        "combined_detection_score": "overall anomaly level is elevated",
        "max_cvss_score": "presence of critical vulnerabilities",
        "rule_hit_count": "multiple security alerts triggered",
        "max_rule_severity": "high severity alerts",
        "privileged_account_flag": "involvement of privileged account",
        "public_facing_flag": "public exposure of asset",
        "sensitive_data_flag": "access to sensitive data",
        "crown_jewel_flag": "critical asset targeted",
        "lateral_movement_flag": "possible lateral movement",
        "persistence_flag": "persistence behavior observed",
        "spread_count_hosts": "threat spreading across multiple hosts",
        "ueba_score": "user behavior anomaly detected",
        "user_risk_score": "high-risk user activity",
    }

    RISK_LABEL_RECOMMENDATION = {
        "critical": "This incident requires immediate investigation and response.",
        "high": "This incident should be prioritized for urgent analyst review.",
        "medium": "This incident should be reviewed by the SOC team.",
        "low": "This incident can be monitored with routine triage.",
    }

    def __init__(self) -> None:
        self.explainer: shap.TreeExplainer | None = None
        self._init_error: str | None = None

    def initialize(self, model: Any) -> None:
        try:
            self.explainer = shap.TreeExplainer(model)
            self._init_error = None
        except Exception as exc:
            self._init_error = str(exc)
            self.explainer = None
            logger.exception("Failed to initialize SHAP TreeExplainer")

    def ensure_ready(self) -> None:
        if self.explainer is None:
            raise RuntimeError(
                "Explanation service is unavailable. "
                f"Initialization error: {self._init_error or 'unknown error'}"
            )

    def _extract_sample_shap_values(self, shap_values: Any) -> np.ndarray:
        if isinstance(shap_values, list):
            return np.array(shap_values[-1])[0]

        values = np.asarray(shap_values)

        if values.ndim == 1:
            return values
        if values.ndim == 2:
            return values[0]
        if values.ndim == 3:
            # Multi-class layout [samples, classes, features]
            return values[0, -1, :]

        raise RuntimeError("Unsupported SHAP output shape.")

    @staticmethod
    def _join_phrases(phrases: list[str]) -> str:
        if not phrases:
            return "risk indicators were identified"
        if len(phrases) == 1:
            return phrases[0]
        if len(phrases) == 2:
            return f"{phrases[0]} and {phrases[1]}"
        return f"{', '.join(phrases[:-1])} and {phrases[-1]}"

    def explain(self, model_input_df: pd.DataFrame, risk_label: str) -> dict[str, Any]:
        self.ensure_ready()

        shap_values = self.explainer.shap_values(model_input_df)
        sample_values = self._extract_sample_shap_values(shap_values)

        top_indices = np.argsort(np.abs(sample_values))[::-1][:5]
        top_features = [model_input_df.columns[idx] for idx in top_indices]

        phrases = [
            self.FEATURE_DESCRIPTION_MAP.get(
                feature_name, feature_name.replace("_", " ")
            )
            for feature_name in top_features
        ]
        leading_text = self._join_phrases(phrases)
        recommendation = self.RISK_LABEL_RECOMMENDATION.get(
            risk_label, self.RISK_LABEL_RECOMMENDATION["medium"]
        )

        description = f"Detected {leading_text}. {recommendation}"

        return {
            "top_risk_factors": top_features,
            "description": description,
        }
