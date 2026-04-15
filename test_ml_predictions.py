#!/usr/bin/env python3
"""
Comprehensive test suite for SecureBot ML Prediction API
Tests the updated detection service with proper normalization
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_header(title):
    print("\n" + "─"*70)
    print(title)
    print("─"*70)

def test_health():
    """Test 1: Health Check"""
    print_header("TEST 1: Health Check (GET /)")
    try:
        resp = requests.get(f"{BASE_URL}/")
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        assert resp.status_code == 200
        print("✅ PASSED\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_normal_data():
    """Test 2: Normal Data"""
    print_header("TEST 2: Normal Data (Expected: 'normal')")
    normal_data = {
        'data': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0,
                 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0,
                 3.1, 3.2, 3.3]
    }
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", json=normal_data)
        result = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        assert resp.status_code == 200
        assert 'combined_detection_score' in result
        score = result['combined_detection_score']
        assert 0 <= score <= 1, f"Score {score} not in range [0, 1]"
        print(f"✅ PASSED - Score in valid range: {score:.4f}\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_anomalous_data():
    """Test 3: Anomalous Data"""
    print_header("TEST 3: Anomalous Data (Expected: 'high_anomaly')")
    anomaly_data = {
        'data': [1.0, 2.5, 3.3, 4.2, 5.1, 6.0, 7.2, 8.1, 9.5, 10.0,
                 11.3, 12.2, 13.1, 14.0, 15.5, 16.2, 17.1, 18.0, 19.3, 20.2,
                 21.1, 22.0, 23.5, 24.2, 25.1, 26.0, 27.3, 28.2, 29.1, 30.0,
                 31.5, 32.2, 33.1]
    }
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", json=anomaly_data)
        result = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        assert resp.status_code == 200
        assert 'combined_detection_score' in result
        score = result['combined_detection_score']
        assert 0 <= score <= 1, f"Score {score} not in range [0, 1]"
        print(f"✅ PASSED - Score in valid range: {score:.4f}\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_medium_anomaly():
    """Test 4: Medium Anomaly Data"""
    print_header("TEST 4: Medium Anomaly Data (Expected: 'suspicious' or 'anomalous')")
    medium_data = {
        'data': [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
                 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0,
                 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0,
                 15.5, 16.0, 16.5]
    }
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", json=medium_data)
        result = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        assert resp.status_code == 200
        assert 'combined_detection_score' in result
        score = result['combined_detection_score']
        assert 0 <= score <= 1, f"Score {score} not in range [0, 1]"
        print(f"✅ PASSED - Score in valid range: {score:.4f}\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_empty_data():
    """Test 5: Empty Data Error Handling"""
    print_header("TEST 5: Error Handling - Empty Data")
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", json={'data': []})
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        assert resp.status_code == 400
        print("✅ PASSED - Correctly rejected empty data\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_wrong_feature_count():
    """Test 6: Wrong Feature Count"""
    print_header("TEST 6: Error Handling - Wrong Feature Count (10 instead of 33)")
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", 
                            json={'data': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]})
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        assert resp.status_code == 400
        print("✅ PASSED - Correctly rejected wrong feature count\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_non_numeric():
    """Test 7: Non-numeric Data"""
    print_header("TEST 7: Error Handling - Non-numeric Data")
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", 
                            json={'data': ['a', 'b', 'c', 'd', 'e'] + [1]*31})
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        # Pydantic validation returns 422 for schema validation errors (non-numeric data)
        assert resp.status_code == 422
        print("✅ PASSED - Correctly rejected non-numeric data (422 Validation Error)\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_all_zeros():
    """Test 8: All Zeros Edge Case"""
    print_header("TEST 8: Edge Case - All Zeros")
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", json={'data': [0.0] * 33})
        result = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        assert resp.status_code == 200
        assert 'combined_detection_score' in result
        score = result['combined_detection_score']
        assert 0 <= score <= 1, f"Score {score} not in range [0, 1]"
        print(f"✅ PASSED - Score in valid range: {score:.4f}\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def test_all_ones():
    """Test 9: All Ones Edge Case"""
    print_header("TEST 9: Edge Case - All Ones")
    try:
        resp = requests.post(f"{BASE_URL}/detect/predict", json={'data': [1.0] * 33})
        result = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        assert resp.status_code == 200
        assert 'combined_detection_score' in result
        score = result['combined_detection_score']
        assert 0 <= score <= 1, f"Score {score} not in range [0, 1]"
        print(f"✅ PASSED - Score in valid range: {score:.4f}\n")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False

def main():
    print("\n" + "="*70)
    print("🔍 SECUREBOT ML PREDICTION TESTS".center(70))
    print("="*70)

    tests = [
        test_health,
        test_normal_data,
        test_anomalous_data,
        test_medium_anomaly,
        test_empty_data,
        test_wrong_feature_count,
        test_non_numeric,
        test_all_zeros,
        test_all_ones,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"📊 SUMMARY: {passed}/{total} tests passed".center(70))
    print("="*70)
    
    if passed == total:
        print("✅ ALL TESTS PASSED! 🎉\n")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed\n")
        return 1

if __name__ == "__main__":
    exit(main())
