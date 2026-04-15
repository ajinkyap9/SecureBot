# SecureBot - Testing Guide

Complete step-by-step commands to set up, run, and test the SecureBot project.

## Phase 1: Environment Setup

### 1. Navigate to Project Directory
```powershell
cd E:\Projects\SecureBot
```

### 2. Activate Virtual Environment
```powershell
& .\.venv\Scripts\Activate.ps1
```

### 3. Verify Python Version
```powershell
python --version
```
Expected Output: `Python 3.12.x`

### 4. Install All Dependencies
```powershell
pip install -r backend/requirements.txt
```

### 5. Verify ML Packages Installation
```powershell
pip list | findstr /E "fastapi uvicorn numpy scikit torch joblib"
```

Expected Packages:
- fastapi==0.135.2
- uvicorn==0.42.0
- numpy==2.2.4
- scikit-learn==1.6.1
- joblib==1.5.3
- torch==2.6.0
- python-multipart==0.0.22
- sqlalchemy==2.0.48

---

## Phase 2: Start the Backend Server

### 6. Navigate to Backend Directory
```powershell
cd backend
```

### 7. Start FastAPI Server with Uvicorn
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Expected Output:
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Keep this terminal open and open a new terminal for testing.**

---

## Phase 3: Test API Endpoints

### In a New Terminal (keeping server running):

#### 8. Activate venv in new terminal
```powershell
cd E:\Projects\SecureBot
& .\.venv\Scripts\Activate.ps1
```

#### 9. Test Root Endpoint (Health Check)
```powershell
python -c "import requests, json; resp = requests.get('http://localhost:8000/'); print(json.dumps(resp.json(), indent=2))"
```

Expected Response:
```json
{
  "message": "Secure Bot services is running!"
}
```

#### 10. Test ML Prediction - Normal Data
```powershell
python -c "import requests, json; resp = requests.post('http://localhost:8000/detect/predict', json={'data': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6]}); print('=== Test 1: Normal Data ==='); print(json.dumps(resp.json(), indent=2))"
```

Expected Response:
```json
{
  "combined_detection_score": <some_score>,
  "detection_label": "normal" or "high_anomaly"
}
```

#### 11. Test ML Prediction - Anomalous Data
```powershell
python -c "import requests, json; resp = requests.post('http://localhost:8000/detect/predict', json={'data': [1.0, 2.5, 3.3, 4.2, 5.1, 6.0, 7.2, 8.1, 9.5, 10.0, 11.3, 12.2, 13.1, 14.0, 15.5, 16.2, 17.1, 18.0, 19.3, 20.2, 21.1, 22.0, 23.5, 24.2, 25.1, 26.0, 27.3, 28.2, 29.1, 30.0, 31.5, 32.2, 33.1, 34.0, 35.5, 36.2]}); print('=== Test 2: Anomalous Data ==='); print(json.dumps(resp.json(), indent=2))"
```

Expected Response:
```json
{
  "combined_detection_score": <high_score>,
  "detection_label": "high_anomaly"
}
```

#### 12. Test Invalid Input (Error Handling)
```powershell
python -c "import requests, json; resp = requests.post('http://localhost:8000/detect/predict', json={'data': []}); print('=== Test 3: Empty Data (Error) ==='); print('Status:', resp.status_code); print(json.dumps(resp.json(), indent=2))"
```

Expected Response:
```json
{
  "detail": "Input data must be a non-empty list."
}
```
Status: 400

#### 13. Test Wrong Data Type (Error Handling)
```powershell
python -c "import requests, json; resp = requests.post('http://localhost:8000/detect/predict', json={'data': ['a', 'b', 'c']}); print('=== Test 4: Non-numeric Data (Error) ==='); print('Status:', resp.status_code); print(json.dumps(resp.json(), indent=2))"
```

Expected Response:
```json
{
  "detail": "Input data must contain only numeric values."
}
```
Status: 400

---

## Complete Testing Script (Run All Tests)

Save this as `test_all.py` in the project root:

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test root endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check (GET /)")
    print("="*60)
    resp = requests.get(f"{BASE_URL}/")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    assert resp.status_code == 200
    print("✓ PASSED")

def test_predict_normal():
    """Test prediction with normal data"""
    print("\n" + "="*60)
    print("TEST 2: Prediction - Normal Data")
    print("="*60)
    data = {'data': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 
                     1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 
                     2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 
                     3.1, 3.2, 3.3, 3.4, 3.5, 3.6]}
    resp = requests.post(f"{BASE_URL}/detect/predict", json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    assert resp.status_code == 200
    assert 'combined_detection_score' in resp.json()
    assert 'detection_label' in resp.json()
    print("✓ PASSED")

def test_predict_anomaly():
    """Test prediction with anomalous data"""
    print("\n" + "="*60)
    print("TEST 3: Prediction - Anomalous Data")
    print("="*60)
    data = {'data': [1.0, 2.5, 3.3, 4.2, 5.1, 6.0, 7.2, 8.1, 9.5, 10.0, 
                     11.3, 12.2, 13.1, 14.0, 15.5, 16.2, 17.1, 18.0, 19.3, 20.2, 
                     21.1, 22.0, 23.5, 24.2, 25.1, 26.0, 27.3, 28.2, 29.1, 30.0, 
                     31.5, 32.2, 33.1, 34.0, 35.5, 36.2]}
    resp = requests.post(f"{BASE_URL}/detect/predict", json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    assert resp.status_code == 200
    assert 'combined_detection_score' in resp.json()
    assert 'detection_label' in resp.json()
    print("✓ PASSED")

def test_empty_data():
    """Test error handling with empty data"""
    print("\n" + "="*60)
    print("TEST 4: Error Handling - Empty Data")
    print("="*60)
    data = {'data': []}
    resp = requests.post(f"{BASE_URL}/detect/predict", json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    assert resp.status_code == 400
    print("✓ PASSED")

def test_non_numeric_data():
    """Test error handling with non-numeric data"""
    print("\n" + "="*60)
    print("TEST 5: Error Handling - Non-numeric Data")
    print("="*60)
    data = {'data': ['a', 'b', 'c']}
    resp = requests.post(f"{BASE_URL}/detect/predict", json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    assert resp.status_code == 400
    print("✓ PASSED")

if __name__ == "__main__":
    print("\n" + "🔍 SECUREBOT TESTING SUITE 🔍".center(60))
    print("="*60)
    
    try:
        test_health()
        test_predict_normal()
        test_predict_anomaly()
        test_empty_data()
        test_non_numeric_data()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!".center(60))
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        exit(1)
```

### Run Complete Test Suite:
```powershell
python test_all.py
```

---

## Summary of Commands

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `cd E:\Projects\SecureBot` | Navigate to project |
| 2 | `. .\.venv\Scripts\Activate.ps1` | Activate venv |
| 3 | `python --version` | Verify Python 3.12 |
| 4 | `pip install -r backend/requirements.txt` | Install dependencies |
| 5 | `pip list` | Verify installations |
| 6 | `cd backend` | Go to backend folder |
| 7 | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Start server |
| 8-13 | Python test commands | Test API endpoints |

---

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use: `netstat -ano \| findstr :8000`
- Verify all dependencies installed: `pip list`

### Import errors
- Ensure venv is activated: `. .\.venv\Scripts\Activate.ps1`
- Reinstall requirements: `pip install -r backend/requirements.txt --force-reinstall`

### ML model errors
- Check model files exist: `ls backend/app/ml_models/`
- Expected files: `hdfs_ae_model.pt`, `hdfs_if_model.pkl`, `hdfs_scaler.pkl`, `hdfs_thresholds.json`

---

---

## ⚠️ CRITICAL ISSUE IDENTIFIED

**Score Normalization Mismatch Detected!**

The API returns scores in the millions (e.g., 376,472,284) but thresholds expect 0-1 range (0.32).

See: [CRITICAL_BUG_ANALYSIS.md](CRITICAL_BUG_ANALYSIS.md) and [PROPOSED_FIX.md](PROPOSED_FIX.md)

**Location:** `backend/app/services/detection_service.py` line 140-141

**Impact:** Predictions may be inaccurate due to missing min-max normalization

**Status:** Fix proposed, waiting for training min/max values

---

**Last Updated:** April 1, 2026
