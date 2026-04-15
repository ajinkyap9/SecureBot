import json
from pathlib import Path

# model paths
APP_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = APP_DIR / "ml_models"

AE_MODEL_PATH = MODEL_DIR / "hdfs_ae_model.pt"
IF_MODEL_PATH = MODEL_DIR / "hdfs_if_model.pkl"
SCALER_PATH = MODEL_DIR / "hdfs_scaler.pkl"
THRESHOLD_PATH = MODEL_DIR / "hdfs_thresholds.json"

# load models lazily so app startup does not fail when ML deps are missing.
ae_model = None
if_model = None
scaler = None
thresholds = None
_torch = None
_models_loaded = False


def _build_hdfs_autoencoder(torch):
    class HDFSAutoEncoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = torch.nn.Sequential(
                torch.nn.Linear(33, 128),
                torch.nn.ReLU(),
                torch.nn.BatchNorm1d(128),
                torch.nn.Linear(128, 64),
                torch.nn.ReLU(),
                torch.nn.BatchNorm1d(64),
                torch.nn.Linear(64, 32),
                torch.nn.ReLU(),
            )
            self.decoder = torch.nn.Sequential(
                torch.nn.Linear(32, 64),
                torch.nn.ReLU(),
                torch.nn.Linear(64, 128),
                torch.nn.ReLU(),
                torch.nn.Linear(128, 33),
            )

        def forward(self, x):
            return self.decoder(self.encoder(x))

    return HDFSAutoEncoder()


def _load_models():
    global ae_model, if_model, scaler, thresholds, _torch, _models_loaded

    if _models_loaded:
        return

    try:
        import torch  # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Detection dependency is missing: install 'torch' to enable /detect/predict."
        ) from exc

    try:
        import joblib  # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Detection dependency is missing: install 'scikit-learn' to enable /detect/predict."
        ) from exc

    missing_paths = [
        str(path)
        for path in [AE_MODEL_PATH, IF_MODEL_PATH, SCALER_PATH, THRESHOLD_PATH]
        if not path.exists()
    ]
    if missing_paths:
        raise RuntimeError(
            "Detection model files are missing: " + ", ".join(missing_paths)
        )

    _torch = torch
    loaded_ae = _torch.load(str(AE_MODEL_PATH), map_location=_torch.device("cpu"))

    if isinstance(loaded_ae, _torch.nn.Module):
        ae_model = loaded_ae
    else:
        # Most training scripts save either a raw state_dict or a dict with "state_dict"
        if isinstance(loaded_ae, dict) and "state_dict" in loaded_ae:
            state_dict = loaded_ae["state_dict"]
        elif isinstance(loaded_ae, dict):
            state_dict = loaded_ae
        else:
            raise RuntimeError(
                "Unsupported AE checkpoint format in hdfs_ae_model.pt."
            )

        ae_model = _build_hdfs_autoencoder(_torch)
        ae_model.load_state_dict(state_dict)

    ae_model.eval()

    if_model = joblib.load(str(IF_MODEL_PATH))
    scaler = joblib.load(str(SCALER_PATH))

    with open(THRESHOLD_PATH, "r", encoding="utf-8") as f:
        thresholds = json.load(f)

    _models_loaded = True


def predict(data):
    try:
        import numpy as np  # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Detection dependency is missing: install 'numpy' to enable /detect/predict."
        ) from exc

    _load_models()

    if not isinstance(data, list) or not data:
        raise ValueError("Input data must be a non-empty list.")

    # convert to numpy
    try:
        X = np.array(data, dtype=float).reshape(1, -1)
    except ValueError as exc:
        raise ValueError("Input data must contain only numeric values.") from exc

    # Validate feature count against trained scaler (robust, not hardcoded)
    if hasattr(scaler, 'n_features_in_'):
        expected_features = scaler.n_features_in_
    else:
        expected_features = 33  # fallback if scaler doesn't have this attribute
    
    if X.shape[1] != expected_features:
        raise ValueError(
            f"Expected {expected_features} features, but got {X.shape[1]}."
        )

    # cross-check: IF model should also expect same feature count
    if hasattr(if_model, 'n_features_in_'):
        if if_model.n_features_in_ != expected_features:
            raise RuntimeError(
                f"Feature count mismatch: Scaler expects {expected_features} features, "
                f"but IF model was trained on {if_model.n_features_in_} features."
            )

    # scale
    X_scaled = scaler.transform(X)

    # AE reconstruction error
    X_tensor = _torch.tensor(X_scaled, dtype=_torch.float32)
    with _torch.no_grad():
        reconstructed = ae_model(X_tensor).cpu().numpy()
    ae_error = float(np.mean((X_scaled - reconstructed) ** 2))

    # IF score (must match training)
    if_score = float(-if_model.decision_function(X_scaled)[0])

    # Min-max normalization using saved training stats
    ae_min = float(thresholds["ae_min"])
    ae_max = float(thresholds["ae_max"])
    if_min = float(thresholds["if_min"])
    if_max = float(thresholds["if_max"])

    ae_denom = (ae_max - ae_min) if (ae_max - ae_min) != 0 else 1.0
    if_denom = (if_max - if_min) if (if_max - if_min) != 0 else 1.0

    ae_norm = (ae_error - ae_min) / ae_denom
    if_norm = (if_score - if_min) / if_denom

    # clamp for safety
    ae_norm = float(np.clip(ae_norm, 0.0, 1.0))
    if_norm = float(np.clip(if_norm, 0.0, 1.0))

    # default to configured production fusion (0.6 * AE + 0.4 * IF)
    ae_w = float(thresholds.get("fusion_weights", {}).get("ae", 0.6))
    if_w = float(thresholds.get("fusion_weights", {}).get("if", 0.4))

    combined_score = ae_w * ae_norm + if_w * if_norm
    combined_threshold = float(thresholds["combined_threshold"])

    # label logic
    if combined_score >= combined_threshold * 1.25:
        label = "high_anomaly"
    elif combined_score >= combined_threshold:
        label = "anomalous"
    elif combined_score >= combined_threshold * 0.75:
        label = "suspicious"
    else:
        label = "normal"

    return {
        "ae_score": ae_norm,
        "if_score": if_norm,
        "combined_detection_score": float(combined_score),
        "detection_label": label,
    }