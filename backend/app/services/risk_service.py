import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from app.utils.constants import normalize_risk_score_percent, risk_score_to_label

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = APP_DIR / "ml_models"


class RiskScoringService:
    """Risk scoring service backed by an XGBoost model."""

    ASSET_CRITICALITY_MAP = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    def __init__(self) -> None:
        self.model_path = self._resolve_existing_path(
            [
                MODEL_DIR / "xgb_risk_model.pkl",
            ]
        )
        self.feature_columns_path = MODEL_DIR / "risk_feature_columns.pkl"
        self.model: Any = None
        self.feature_columns: list[str] = []
        self._load_error: str | None = None
        self._load_artifacts()

    @staticmethod
    def _resolve_existing_path(candidates: list[Path]) -> Path | None:
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_artifacts(self) -> None:
        try:
            if self.model_path is None:
                raise FileNotFoundError(
                    "Risk model files are missing: "
                    f"{MODEL_DIR / 'xgboost_risk_model.pkl'}, {MODEL_DIR / 'xgb_risk_model.pkl'}"
                )

            missing_paths = [
                str(path)
                for path in [self.model_path, self.feature_columns_path]
                if not path.exists()
            ]
            if missing_paths:
                raise FileNotFoundError(
                    "Risk model files are missing: " + ", ".join(missing_paths)
                )

            self.model = joblib.load(str(self.model_path))
            loaded_feature_columns = joblib.load(str(self.feature_columns_path))

            if not isinstance(loaded_feature_columns, (list, tuple)):
                raise ValueError(
                    "risk_feature_columns.pkl must contain a list/tuple of feature names."
                )

            self.feature_columns = [str(feature) for feature in loaded_feature_columns]
            self._load_error = None
        except Exception as exc:
            self._load_error = str(exc)
            logger.exception("Failed to initialize RiskScoringService")

    def ensure_ready(self) -> None:
        if self.model is None or not self.feature_columns:
            raise RuntimeError(
                "Risk scoring service is unavailable. "
                f"Initialization error: {self._load_error or 'unknown error'}"
            )

    def get_model(self) -> Any:
        self.ensure_ready()
        return self.model

    @staticmethod
    def score_to_label(score: float) -> str:
        return risk_score_to_label(score)

    def _normalize_asset_criticality(self, value: Any) -> float:
        if isinstance(value, str):
            mapped = self.ASSET_CRITICALITY_MAP.get(value.strip().lower())
            if mapped is not None:
                return float(mapped)
        return self._safe_float(value)

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def build_model_input(self, risk_features: dict[str, Any]) -> pd.DataFrame:
        self.ensure_ready()

        normalized = {
            key: self._safe_float(value)
            for key, value in (risk_features or {}).items()
            if key != "asset_criticality"
        }
        normalized["asset_criticality"] = self._normalize_asset_criticality(
            (risk_features or {}).get("asset_criticality", 0)
        )

        input_df = pd.DataFrame([normalized])

        for column in self.feature_columns:
            if column not in input_df.columns:
                input_df[column] = 0.0

        input_df = input_df[self.feature_columns].fillna(0.0)
        return input_df

    def predict_risk(self, risk_features: dict[str, Any]) -> dict[str, Any]:
        model_input_df = self.build_model_input(risk_features)

        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(model_input_df)
            if probabilities.ndim == 2 and probabilities.shape[1] > 1:
                raw_score = float(probabilities[0][1])
            else:
                raw_score = float(probabilities[0][0])
        elif hasattr(self.model, "predict"):
            raw_score = float(self.model.predict(model_input_df)[0])
        else:
            raise RuntimeError(
                "Loaded risk model does not expose predict_proba or predict."
            )

        risk_score = normalize_risk_score_percent(raw_score)

        return {
            "risk_score": risk_score,
            "risk_label": self.score_to_label(risk_score),
        }
