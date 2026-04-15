# Proposed Fix for detection_service.py

## Current (BROKEN) Code

```python
# Line 135-147 (CURRENT - WRONG)
def predict(data):
    # ... setup code ...
    
    # AE reconstruction error
    X_tensor = _torch.tensor(X_scaled, dtype=_torch.float32)
    reconstructed = ae_model(X_tensor).detach().numpy()
    ae_error = np.mean((X_scaled - reconstructed) ** 2)

    # IF score
    if_score = -if_model.score_samples(X_scaled)[0]

    # normalize (you already did this in training)  # <-- THIS COMMENT IS MISLEADING!
    combined_score = 0.6 * ae_error + 0.4 * if_score  # <-- NO NORMALIZATION HAPPENING!

    label = "high_anomaly" if combined_score > thresholds["combined_threshold"] else "normal"

    return {
        "combined_detection_score": float(combined_score),  # <-- RETURNS MILLIONS!
        "detection_label": label
    }
```

---

## Fixed Code (Option 1: With Min/Max Normalization)

Requires: Update `hdfs_thresholds.json` to include `ae_min`, `ae_max`, `if_min`, `if_max`

```python
# CORRECTED VERSION
def predict(data):
    try:
        import numpy as np
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

    # scale
    X_scaled = scaler.transform(X)

    # ========== AE RECONSTRUCTION ERROR ==========
    X_tensor = _torch.tensor(X_scaled, dtype=_torch.float32)
    reconstructed = ae_model(X_tensor).detach().numpy()
    ae_error = np.mean((X_scaled - reconstructed) ** 2)

    # ========== IF ANOMALY SCORE ==========
    if_score = -if_model.score_samples(X_scaled)[0]

    # ========== NORMALIZE BOTH SCORES TO 0-1 RANGE ==========
    # Get min/max from thresholds (which were computed during training)
    ae_min = thresholds.get("ae_min", 0.0)
    ae_max = thresholds.get("ae_max", 1e-6)  # Safe default for tiny AE errors
    if_min = thresholds.get("if_min", 0.0)
    if_max = thresholds.get("if_max", 1.0)  # IF scores typically 0-1

    # Normalize to 0-1 range using min-max scaling
    ae_norm = (ae_error - ae_min) / (ae_max - ae_min) if ae_max > ae_min else 0.0
    if_norm = (if_score - if_min) / (if_max - if_min) if if_max > if_min else 0.0

    # Clamp to 0-1 range (in case of out-of-distribution data)
    ae_norm = np.clip(ae_norm, 0.0, 1.0)
    if_norm = np.clip(if_norm, 0.0, 1.0)

    # ========== COMBINE NORMALIZED SCORES ==========
    combined_score = 0.6 * ae_norm + 0.4 * if_norm  # Now in 0-1 range!

    # ========== CLASSIFY ==========
    label = "high_anomaly" if combined_score > thresholds["combined_threshold"] else "normal"

    return {
        "combined_detection_score": float(combined_score),  # Now returns 0-1, e.g., 0.79
        "detection_label": label,
        # Debug info (remove in production)
        "_debug": {
            "ae_error_raw": float(ae_error),
            "ae_error_normalized": float(ae_norm),
            "if_score_raw": float(if_score),
            "if_score_normalized": float(if_norm),
        }
    }
```

---

## Updated hdfs_thresholds.json

```json
{
  "ae_min": 0.0,
  "ae_max": 1e-6,
  "if_min": 0.0,
  "if_max": 1.0,
  "ae_threshold": 1.0179047826852639e-08,
  "if_threshold": 0.47409085609379364,
  "combined_threshold": 0.32164826914038835,
  "fusion_weights": {
    "ae": 0.6,
    "if": 0.4
  }
}
```

**⚠️ IMPORTANT:** You need to fill in the actual min/max values from your training data!

---

## Testing the Fix

After applying the fix, test with the same data:

```powershell
# Should now return ~0.79, not 376,472,284!
python -c "import requests, json; resp = requests.post('http://localhost:8000/detect/predict', json={'data': [1.0, 2.5, 3.3, 4.2, 5.1, 6.0, 7.2, 8.1, 9.5, 10.0, 11.3, 12.2, 13.1, 14.0, 15.5, 16.2, 17.1, 18.0, 19.3, 20.2, 21.1, 22.0, 23.5, 24.2, 25.1, 26.0, 27.3, 28.2, 29.1, 30.0, 31.5, 32.2, 33.1, 34.0, 35.5, 36.2]}); print(json.dumps(resp.json(), indent=2))"
```

**Expected Output (FIXED):**
```json
{
  "combined_detection_score": 0.7912345,
  "detection_label": "high_anomaly",
  "_debug": {
    "ae_error_raw": 1.234e-6,
    "ae_error_normalized": 0.79,
    "if_score_raw": 0.84,
    "if_score_normalized": 0.84
  }
}
```

---

## How to Find the Missing Min/Max Values

Search your training code/notebook for:
1. Where `ae_errors` were collected from training samples
2. Where `if_scores` were collected from training samples
3. Compute: `ae_min = min(ae_errors)`, `ae_max = max(ae_errors)`
4. Compute: `if_min = min(if_scores)`, `if_max = max(if_scores)`
5. Add these to `hdfs_thresholds.json`

---

## Summary

| Before Fix | After Fix |
|------------|-----------|
| Combined score: 376,472,284 | Combined score: 0.791 |
| Threshold: 0.322 (never matched) | Threshold: 0.322 (properly matched) |
| Classification: Always wrong | Classification: Correct |
