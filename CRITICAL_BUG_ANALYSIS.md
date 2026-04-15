# CRITICAL ISSUE: Score Normalization Mismatch

## Problem Summary

**Inference scores are millions, training scores were ~0.79**

Why this is happening:

### Current Inference Logic (WRONG)
```python
ae_error = np.mean((X_scaled - reconstructed) ** 2)        # Raw MSE (high values)
if_score = -if_model.score_samples(X_scaled)[0]            # Raw anomaly score (high values)
combined_score = 0.6 * ae_error + 0.4 * if_score           # NO NORMALIZATION
# Result: combined_score = 376,472,284.20 (millions!)
```

### Training Logic (EXPECTED)
The thresholds file suggests normalized scores were used in training:
```json
{
  "combined_threshold": 0.32164826914038835  // 0-1 range
}
```
2
If training did:
```python
ae_norm = (ae_error - ae_min) / (ae_max - ae_min)          // Normalize to 0-1
if_norm = (if_score - if_min) / (if_max - if_min)          // Normalize to 0-1
combined_score = 0.6 * ae_norm + 0.4 * if_norm             // Combined normalized
# Result: combined_score ~0.79 (matches training output)
```

---

## The Root Cause

The code comment at line 140 says:
```python
# normalize (you already did this in training)
combined_score = 0.6 * ae_error + 0.4 * if_score
```

**But it's NOT normalizing!** The comment is misleading. No min/max normalization is happening.

---

## Impact

| Aspect | Current (WRONG) | Expected (RIGHT) |
|--------|-----------------|------------------|
| AE Error Range | 0 - millions | 0 - 1 (normalized) |
| IF Score Range | 0 - millions | 0 - 1 (normalized) |
| Combined Score | 0 - millions | 0 - 1 (normalized) |
| Threshold | 0.322 (USELESS) | 0.322 (valid) |
| Result | Always wrong classification | Correct classification |

---

## Solution: Two Options

### Option 1: Store & Use Training Min/Max (RECOMMENDED)
Need to save during training:
```python
# Save in hdfs_thresholds.json
{
  "ae_min": <value>,
  "ae_max": <value>,
  "if_min": <value>,
  "if_max": <value>,
  "combined_threshold": 0.322
}
```

Then in inference:
```python
ae_norm = (ae_error - thresholds["ae_min"]) / (thresholds["ae_max"] - thresholds["ae_min"])
if_norm = (if_score - thresholds["if_min"]) / (thresholds["if_max"] - thresholds["if_min"])
combined_score = 0.6 * ae_norm + 0.4 * if_norm
label = "high_anomaly" if combined_score > thresholds["combined_threshold"] else "normal"
```

### Option 2: Recalculate Threshold from Raw Scores
Train on raw scores and adjust threshold accordingly. (Less ideal, loses training consistency)

---

## Next Steps

### Step 1: Find Training Min/Max Values
Check your training code/notebook for lines like:
```python
ae_errors_all = [... all AE errors from training ...]
if_scores_all = [... all IF scores from training ...]
ae_min, ae_max = np.min(ae_errors_all), np.max(ae_errors_all)
if_min, if_max = np.min(if_scores_all), np.max(if_scores_all)
```

### Step 2: Update hdfs_thresholds.json
```json
{
  "ae_min": <FROM_TRAINING>,
  "ae_max": <FROM_TRAINING>,
  "if_min": <FROM_TRAINING>,
  "if_max": <FROM_TRAINING>,
  "ae_threshold": 1.0179047826852639e-08,
  "if_threshold": 0.47409085609379364,
  "combined_threshold": 0.32164826914038835,
  "fusion_weights": {
    "ae": 0.6,
    "if": 0.4
  }
}
```

### Step 3: Fix detection_service.py
Apply min/max normalization before combining scores

### Step 4: Re-test
Verify scores return to 0-1 range (~0.79 as expected)

---

## Test to Verify Fix

After fixing, scores should be:
```json
{
  "combined_detection_score": 0.791234,    // ~0-1 range
  "detection_label": "high_anomaly"
}
```

Not:
```json
{
  "combined_detection_score": 376472284.20, // WRONG: millions
  "detection_label": "high_anomaly"
}
```
