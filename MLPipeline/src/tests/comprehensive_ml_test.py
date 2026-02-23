#!/usr/bin/env python3
"""
Comprehensive ML Model Testing Suite

Tests all ML models with proper evaluation metrics:
- Precision, Recall, F1-Score
- AUC-ROC
- Confusion Matrix
- Cross-validation
- Edge case testing
- Model comparison (Isolation Forest vs One-Class SVM vs LOF)

Usage:
    python src/tests/comprehensive_ml_test.py --output test_results_comprehensive.json
"""

import argparse
import json
import os
import sys
import time
import warnings
import traceback

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    IsolationForest, RandomForestClassifier, GradientBoostingClassifier,
    ExtraTreesClassifier
)
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report, accuracy_score
)
import joblib

warnings.filterwarnings('ignore')

# Try importing XGBoost (optional but recommended)
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


# ──────────────────────────────────────────────
# DATA GENERATION (per-interval, matching inference)
# ──────────────────────────────────────────────

def generate_normal_samples(n=5000, seed=42):
    """Generate normal health data (per-interval, not cumulative)."""
    rng = np.random.default_rng(seed)
    hr = rng.normal(75, 10, size=n).clip(50, 100)
    steps = rng.normal(100, 40, size=n).clip(0, 300)
    calories = rng.normal(30, 10, size=n).clip(1, 80)
    distance = rng.normal(0.3, 0.1, size=n).clip(0, 1)
    X = np.column_stack([hr, steps, calories, distance])
    return X.astype(np.float32)


def generate_anomalous_samples(n=1000, seed=123):
    """Generate anomalous health data."""
    rng = np.random.default_rng(seed)
    samples = []

    # High heart rate (tachycardia)
    k = n // 4
    hr = rng.normal(160, 15, size=k).clip(130, 220)
    steps = rng.normal(50, 20, size=k).clip(0, 150)
    calories = rng.normal(20, 8, size=k).clip(1, 60)
    distance = rng.normal(0.15, 0.05, size=k).clip(0, 0.5)
    samples.append(np.column_stack([hr, steps, calories, distance]))

    # Low heart rate (bradycardia)
    hr = rng.normal(38, 5, size=k).clip(25, 48)
    steps = rng.normal(20, 10, size=k).clip(0, 60)
    calories = rng.normal(10, 4, size=k).clip(0, 30)
    distance = rng.normal(0.05, 0.03, size=k).clip(0, 0.2)
    samples.append(np.column_stack([hr, steps, calories, distance]))

    # Extreme values (sensor malfunction)
    hr = rng.normal(200, 20, size=k).clip(180, 250)
    steps = rng.normal(800, 200, size=k).clip(500, 1500)
    calories = rng.normal(250, 50, size=k).clip(150, 400)
    distance = rng.normal(4, 1, size=k).clip(2, 8)
    samples.append(np.column_stack([hr, steps, calories, distance]))

    # Zero/dropout readings
    remaining = n - 3 * k
    zeros = np.zeros((remaining, 4))
    # Add slight noise to some
    zeros[:remaining // 2, 0] = rng.normal(5, 2, size=remaining // 2).clip(0, 10)
    samples.append(zeros)

    X = np.concatenate(samples, axis=0).astype(np.float32)
    rng.shuffle(X)
    return X


def generate_edge_cases():
    """Generate physiological boundary values for stress testing."""
    cases = {
        "normal_resting": np.array([[72, 80, 25, 0.2]], dtype=np.float32),
        "normal_sleeping": np.array([[58, 5, 8, 0.01]], dtype=np.float32),
        "normal_walking": np.array([[90, 150, 40, 0.4]], dtype=np.float32),
        "normal_jogging": np.array([[120, 250, 65, 0.7]], dtype=np.float32),
        "normal_exercise": np.array([[140, 200, 75, 0.5]], dtype=np.float32),
        "anomaly_tachycardia": np.array([[175, 30, 15, 0.1]], dtype=np.float32),
        "anomaly_bradycardia": np.array([[35, 10, 5, 0.02]], dtype=np.float32),
        "anomaly_sensor_dropout": np.array([[0, 0, 0, 0]], dtype=np.float32),
        "anomaly_extreme_hr": np.array([[220, 50, 20, 0.15]], dtype=np.float32),
        "anomaly_impossible": np.array([[250, 2000, 500, 10]], dtype=np.float32),
        "borderline_high_hr": np.array([[105, 100, 35, 0.3]], dtype=np.float32),
        "borderline_low_hr": np.array([[48, 30, 12, 0.08]], dtype=np.float32),
    }
    return cases


def generate_activity_samples(n=6000, seed=42):
    """Generate labeled activity data for classifier evaluation."""
    rng = np.random.default_rng(seed)
    LABELS = ["sleep", "rest", "walk", "run", "exercise", "other"]
    k = n // 6
    xs, ys = [], []

    configs = [
        (50, 8, 5, 5, 10, 4, 0.05, 0.05, 0),
        (65, 10, 20, 15, 15, 5, 0.1, 0.05, 1),
        (85, 12, 120, 50, 35, 8, 0.4, 0.1, 2),
        (130, 15, 250, 80, 60, 12, 0.8, 0.15, 3),
        (145, 18, 200, 70, 70, 15, 0.6, 0.2, 4),
        (90, 25, 80, 120, 30, 20, 0.3, 0.3, 5),
    ]

    for hr_m, hr_s, st_m, st_s, cal_m, cal_s, dist_m, dist_s, label in configs:
        hr = rng.normal(hr_m, hr_s, size=k)
        steps = rng.normal(st_m, st_s, size=k)
        cal = rng.normal(cal_m, cal_s, size=k)
        dist = rng.normal(dist_m, dist_s, size=k)
        xs.append(np.column_stack([hr, steps, cal, dist]))
        ys.append(np.full(k, label))

    x = np.concatenate(xs).astype(np.float32)
    y = np.concatenate(ys).astype(np.int32)
    idx = rng.permutation(len(x))
    return x[idx], y[idx], LABELS


# ──────────────────────────────────────────────
# TEST 1: ISOLATION FOREST (RETRAIN + EVALUATE)
# ──────────────────────────────────────────────

def test_isolation_forest(verbose=True):
    """Train Isolation Forest from scratch and evaluate with proper metrics."""
    if verbose:
        print("\n" + "=" * 70)
        print("TEST 1: ISOLATION FOREST ANOMALY DETECTION")
        print("=" * 70)

    results = {"model": "IsolationForest", "tests": {}}

    # Generate data
    X_normal = generate_normal_samples(5000, seed=42)
    X_anomaly = generate_anomalous_samples(1000, seed=123)

    X_all = np.concatenate([X_normal, X_anomaly])
    y_true = np.concatenate([np.zeros(len(X_normal)), np.ones(len(X_anomaly))])

    # Shuffle
    rng = np.random.default_rng(99)
    idx = rng.permutation(len(X_all))
    X_all, y_true = X_all[idx], y_true[idx]

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_all)

    # Train
    model = IsolationForest(
        contamination=0.15,
        random_state=42,
        n_estimators=200,
        max_features=4,
    )
    model.fit(X_scaled)

    # Predict
    preds_raw = model.predict(X_scaled)  # 1=normal, -1=anomaly
    scores = model.score_samples(X_scaled)

    # Convert: sklearn uses 1=normal, -1=anomaly → we use 0=normal, 1=anomaly
    y_pred = (preds_raw == -1).astype(int)

    # Metrics
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    auc = roc_auc_score(y_true, -scores)  # Negate: lower score = more anomalous
    cm = confusion_matrix(y_true, y_pred).tolist()
    report = classification_report(y_true, y_pred, target_names=["Normal", "Anomaly"], output_dict=True)

    results["tests"]["full_evaluation"] = {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "auc_roc": round(auc, 4),
        "confusion_matrix": cm,
        "classification_report": report,
        "total_samples": len(X_all),
        "normal_count": int(np.sum(y_true == 0)),
        "anomaly_count": int(np.sum(y_true == 1)),
    }

    if verbose:
        print(f"\n  📊 Full Evaluation (n={len(X_all)}):")
        print(f"     Precision:  {prec:.4f}")
        print(f"     Recall:     {rec:.4f}")
        print(f"     F1-Score:   {f1:.4f}")
        print(f"     AUC-ROC:    {auc:.4f}")
        print(f"     Confusion Matrix: {cm}")

    # Cross-validation
    if verbose:
        print("\n  🔄 5-Fold Cross-Validation:")
    cv_results = cross_validate_anomaly(X_all, y_true)
    results["tests"]["cross_validation"] = cv_results
    if verbose:
        print(f"     F1 (mean±std): {cv_results['f1_mean']:.4f} ± {cv_results['f1_std']:.4f}")
        print(f"     AUC (mean±std): {cv_results['auc_mean']:.4f} ± {cv_results['auc_std']:.4f}")

    # Edge cases
    edge_cases = generate_edge_cases()
    edge_results = []
    if verbose:
        print("\n  🧪 Edge Case Tests:")
    for name, sample in edge_cases.items():
        s_scaled = scaler.transform(sample)
        pred = model.predict(s_scaled)[0]
        score = model.score_samples(s_scaled)[0]
        is_anomaly = pred == -1
        expected_anomaly = name.startswith("anomaly_")

        edge_results.append({
            "case": name,
            "predicted_anomaly": bool(is_anomaly),
            "expected_anomaly": expected_anomaly,
            "correct": is_anomaly == expected_anomaly,
            "anomaly_score": round(float(score), 6),
        })
        if verbose:
            status = "✅" if is_anomaly == expected_anomaly else "❌"
            print(f"     {status} {name}: pred={'ANOMALY' if is_anomaly else 'NORMAL'} "
                  f"(expected={'ANOMALY' if expected_anomaly else 'NORMAL'}) score={score:.4f}")

    results["tests"]["edge_cases"] = edge_results
    edge_correct = sum(1 for e in edge_results if e["correct"])
    results["tests"]["edge_case_accuracy"] = round(edge_correct / len(edge_results), 4)

    # Save retrained model
    os.makedirs("models/saved_models", exist_ok=True)
    joblib.dump(model, "models/saved_models/isolation_forest.pkl")
    joblib.dump(scaler, "models/saved_models/scaler.pkl")
    joblib.dump({"model": model, "scaler": scaler}, "models/lambda_export/model.pkl")
    if verbose:
        print(f"\n  💾 Retrained model saved to models/saved_models/")

    return results


def cross_validate_anomaly(X, y, n_splits=5):
    """Cross-validate anomaly detection model."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    f1_scores, auc_scores, prec_scores, rec_scores = [], [], [], []

    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = IsolationForest(contamination=0.15, random_state=42, n_estimators=200)
        model.fit(X_train_s)

        preds = (model.predict(X_test_s) == -1).astype(int)
        scores = model.score_samples(X_test_s)

        f1_scores.append(f1_score(y_test, preds))
        auc_scores.append(roc_auc_score(y_test, -scores))
        prec_scores.append(precision_score(y_test, preds))
        rec_scores.append(recall_score(y_test, preds))

    return {
        "n_splits": n_splits,
        "f1_mean": round(float(np.mean(f1_scores)), 4),
        "f1_std": round(float(np.std(f1_scores)), 4),
        "auc_mean": round(float(np.mean(auc_scores)), 4),
        "auc_std": round(float(np.std(auc_scores)), 4),
        "precision_mean": round(float(np.mean(prec_scores)), 4),
        "recall_mean": round(float(np.mean(rec_scores)), 4),
        "fold_f1_scores": [round(s, 4) for s in f1_scores],
    }


# ──────────────────────────────────────────────
# TEST 2: MODEL COMPARISON
# ──────────────────────────────────────────────

def test_model_comparison(verbose=True):
    """Compare Isolation Forest, One-Class SVM, and Local Outlier Factor."""
    if verbose:
        print("\n" + "=" * 70)
        print("TEST 2: MODEL COMPARISON (IF vs OC-SVM vs LOF)")
        print("=" * 70)

    X_normal = generate_normal_samples(5000, seed=42)
    X_anomaly = generate_anomalous_samples(1000, seed=123)
    X_all = np.concatenate([X_normal, X_anomaly])
    y_true = np.concatenate([np.zeros(len(X_normal)), np.ones(len(X_anomaly))])

    rng = np.random.default_rng(99)
    idx = rng.permutation(len(X_all))
    X_all, y_true = X_all[idx], y_true[idx]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_all)

    models = {
        "IsolationForest": IsolationForest(contamination=0.15, random_state=42, n_estimators=200),
        "OneClassSVM": OneClassSVM(kernel='rbf', gamma='scale', nu=0.15),
        "LocalOutlierFactor": LocalOutlierFactor(n_neighbors=20, contamination=0.15, novelty=False),
    }

    results = {}
    for name, model in models.items():
        start = time.perf_counter()

        if name == "LocalOutlierFactor":
            preds_raw = model.fit_predict(X_scaled)
            scores = model.negative_outlier_factor_
        else:
            model.fit(X_scaled)
            preds_raw = model.predict(X_scaled)
            scores = model.score_samples(X_scaled) if hasattr(model, 'score_samples') else model.decision_function(X_scaled)

        elapsed_ms = (time.perf_counter() - start) * 1000
        y_pred = (preds_raw == -1).astype(int)

        prec = precision_score(y_true, y_pred)
        rec = recall_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        try:
            auc = roc_auc_score(y_true, -scores)
        except Exception:
            auc = 0.0

        results[name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "auc_roc": round(auc, 4),
            "training_time_ms": round(elapsed_ms, 2),
        }

        if verbose:
            print(f"\n  📈 {name}:")
            print(f"     Precision: {prec:.4f}  Recall: {rec:.4f}  F1: {f1:.4f}  AUC: {auc:.4f}")
            print(f"     Time: {elapsed_ms:.1f}ms")

    # Determine winner
    best = max(results.items(), key=lambda x: x[1]["f1_score"])
    results["_best_model"] = best[0]
    if verbose:
        print(f"\n  🏆 Best model by F1: {best[0]} (F1={best[1]['f1_score']:.4f})")

    return results


# ──────────────────────────────────────────────
# TEST 3: ACTIVITY CLASSIFIER (TFLite)
# ──────────────────────────────────────────────

def test_activity_classifier(verbose=True):
    """Test activity classifier TFLite model."""
    if verbose:
        print("\n" + "=" * 70)
        print("TEST 3: ACTIVITY CLASSIFIER (TFLite)")
        print("=" * 70)

    tflite_path = "models/tflite/activity_classifier.tflite"
    labels_path = "models/tflite/activity_classifier_labels.json"

    if not os.path.exists(tflite_path):
        if verbose:
            print(f"  ⚠️  Model not found: {tflite_path}")
        return {"error": f"Model not found: {tflite_path}"}

    try:
        import tensorflow as tf
    except ImportError:
        if verbose:
            print("  ⚠️  TensorFlow not available, skipping TFLite tests")
        return {"error": "TensorFlow not installed"}

    # Load model
    interpreter = tf.lite.Interpreter(model_path=tflite_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Load labels
    LABELS = ["sleep", "rest", "walk", "run", "exercise", "other"]
    if os.path.exists(labels_path):
        with open(labels_path) as f:
            label_data = json.load(f)
            LABELS = label_data.get("labels", LABELS)

    # Generate test data
    X_test, y_test, _ = generate_activity_samples(n=3000, seed=99)

    # Run inference
    y_pred = []
    y_probs = []
    for i in range(len(X_test)):
        sample = X_test[i:i+1].astype(np.float32)
        interpreter.set_tensor(input_details[0]['index'], sample)
        interpreter.invoke()
        probs = interpreter.get_tensor(output_details[0]['index'])[0]
        y_pred.append(np.argmax(probs))
        y_probs.append(probs.tolist())

    y_pred = np.array(y_pred)

    # Metrics
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(y_test, y_pred, target_names=LABELS, output_dict=True, zero_division=0)

    results = {
        "model": "ActivityClassifier_TFLite",
        "accuracy": round(acc, 4),
        "confusion_matrix": cm,
        "classification_report": report,
        "per_class_f1": {LABELS[i]: round(report[LABELS[i]]["f1-score"], 4) for i in range(len(LABELS))},
        "total_samples": len(y_test),
    }

    if verbose:
        print(f"\n  📊 Overall Accuracy: {acc:.4f}")
        print(f"\n  Per-class F1 scores:")
        for label in LABELS:
            f1_val = report[label]["f1-score"]
            status = "✅" if f1_val >= 0.70 else "⚠️" if f1_val >= 0.50 else "❌"
            print(f"     {status} {label:10s}: F1={f1_val:.4f}  "
                  f"Prec={report[label]['precision']:.4f}  "
                  f"Rec={report[label]['recall']:.4f}")
        print(f"\n  Confusion Matrix:")
        header = "         " + "  ".join(f"{l[:5]:>5}" for l in LABELS)
        print(header)
        for i, row in enumerate(cm):
            print(f"  {LABELS[i]:8s} " + "  ".join(f"{v:5d}" for v in row))

    # Specific misclassification tests
    specific_tests = [
        ("resting_person", [70, 50, 20, 0.1], "rest"),
        ("sleeping_person", [55, 5, 8, 0.01], "sleep"),
        ("walking_person", [85, 120, 35, 0.4], "walk"),
        ("running_person", [130, 250, 60, 0.8], "run"),
        ("exercising_person", [150, 200, 75, 0.6], "exercise"),
    ]
    specific_results = []
    if verbose:
        print("\n  🧪 Specific Scenario Tests:")
    for name, features, expected in specific_tests:
        sample = np.array([features], dtype=np.float32)
        interpreter.set_tensor(input_details[0]['index'], sample)
        interpreter.invoke()
        probs = interpreter.get_tensor(output_details[0]['index'])[0]
        pred_label = LABELS[np.argmax(probs)]
        correct = pred_label == expected
        specific_results.append({
            "scenario": name,
            "predicted": pred_label,
            "expected": expected,
            "correct": correct,
            "confidence": round(float(np.max(probs)), 4),
            "all_probs": {LABELS[i]: round(float(probs[i]), 4) for i in range(len(LABELS))},
        })
        if verbose:
            status = "✅" if correct else "❌"
            print(f"     {status} {name}: pred={pred_label} (expected={expected}) conf={np.max(probs):.4f}")

    results["specific_tests"] = specific_results

    return results


# ──────────────────────────────────────────────
# TEST 4: CONV1D AUTOENCODER (TFLite)
# ──────────────────────────────────────────────

def test_conv1d_autoencoder(verbose=True):
    """Test Conv1D autoencoder anomaly detection."""
    if verbose:
        print("\n" + "=" * 70)
        print("TEST 4: CONV1D AUTOENCODER ANOMALY DETECTOR (TFLite)")
        print("=" * 70)

    tflite_path = "models/tflite/anomaly_lstm.tflite"
    if not os.path.exists(tflite_path):
        if verbose:
            print(f"  ⚠️  Model not found: {tflite_path}")
        return {"error": f"Model not found: {tflite_path}"}

    try:
        import tensorflow as tf
    except ImportError:
        if verbose:
            print("  ⚠️  TensorFlow not available")
        return {"error": "TensorFlow not installed"}

    # Load model
    interpreter = tf.lite.Interpreter(model_path=tflite_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    seq_len = input_details[0]['shape'][1]

    # Generate sequences
    rng = np.random.default_rng(42)

    def make_sequence(hr_mean, hr_std, st_mean, st_std, cal_mean, cal_std, dist_mean, dist_std, n=50):
        seqs = []
        for _ in range(n):
            hr = rng.normal(hr_mean, hr_std, size=(seq_len, 1)).clip(0, 250)
            steps = rng.normal(st_mean, st_std, size=(seq_len, 1)).clip(0, 1000)
            cal = rng.normal(cal_mean, cal_std, size=(seq_len, 1)).clip(0, 500)
            dist = rng.normal(dist_mean, dist_std, size=(seq_len, 1)).clip(0, 10)
            seqs.append(np.concatenate([hr, steps, cal, dist], axis=-1))
        return np.array(seqs, dtype=np.float32)

    scenarios = {
        "normal": make_sequence(75, 10, 100, 30, 30, 10, 0.3, 0.1),
        "bradycardia": make_sequence(38, 5, 20, 10, 10, 4, 0.05, 0.03),
        "tachycardia": make_sequence(165, 15, 50, 20, 20, 8, 0.15, 0.05),
        "exercise": make_sequence(140, 10, 300, 50, 80, 15, 0.8, 0.2),
        "extreme": make_sequence(200, 15, 800, 100, 250, 30, 4, 1),
        "zero_values": np.zeros((50, seq_len, 4), dtype=np.float32),
    }

    results = {"model": "Conv1D_Autoencoder_TFLite", "scenarios": {}}

    all_mses = {}
    for scenario_name, data in scenarios.items():
        mses = []
        for i in range(len(data)):
            sample = data[i:i+1]
            interpreter.set_tensor(input_details[0]['index'], sample)
            interpreter.invoke()
            output = interpreter.get_tensor(output_details[0]['index'])
            mse = np.mean((sample - output) ** 2)
            mses.append(float(mse))

        all_mses[scenario_name] = mses
        avg_mse = np.mean(mses)
        std_mse = np.std(mses)

        results["scenarios"][scenario_name] = {
            "mean_mse": round(avg_mse, 4),
            "std_mse": round(std_mse, 4),
            "min_mse": round(float(np.min(mses)), 4),
            "max_mse": round(float(np.max(mses)), 4),
            "n_samples": len(data),
        }

        if verbose:
            print(f"  📉 {scenario_name:15s}: MSE = {avg_mse:10.4f} ± {std_mse:.4f}")

    # Assess anomaly separation
    normal_mse = np.mean(all_mses["normal"])
    anomaly_mses = {k: np.mean(v) for k, v in all_mses.items() if k != "normal"}

    separation_ratios = {}
    for k, v in anomaly_mses.items():
        ratio = v / (normal_mse + 1e-8)
        separation_ratios[k] = round(ratio, 4)

    results["separation_analysis"] = {
        "normal_mse": round(normal_mse, 4),
        "anomaly_to_normal_ratios": separation_ratios,
        "can_separate_anomalies": all(r > 1.5 for r in separation_ratios.values() if r != "zero_values"),
    }

    if verbose:
        print(f"\n  🔍 Anomaly Separation Analysis:")
        print(f"     Normal baseline MSE: {normal_mse:.4f}")
        for k, r in separation_ratios.items():
            status = "✅" if r > 1.5 else "⚠️" if r > 1.0 else "❌"
            print(f"     {status} {k}: ratio={r:.2f}x (MSE={anomaly_mses[k]:.4f})")

    return results


# ──────────────────────────────────────────────
# TEST 5: EXISTING MODEL EVALUATION
# ──────────────────────────────────────────────

def test_existing_isolation_forest(verbose=True):
    """Evaluate the previously trained Isolation Forest with proper metrics."""
    if verbose:
        print("\n" + "=" * 70)
        print("TEST 5: EXISTING ISOLATION FOREST (pre-trained)")
        print("=" * 70)

    model_path = "models/lambda_export/model.pkl"
    if not os.path.exists(model_path):
        model_path = "models/saved_models/isolation_forest.pkl"
    if not os.path.exists(model_path):
        return {"error": "No pre-trained model found"}

    try:
        data = joblib.load(model_path)
        if isinstance(data, dict):
            model = data.get("model", data)
            scaler = data.get("scaler")
        else:
            model = data
            scaler = None

        # Try loading separate scaler
        if scaler is None and os.path.exists("models/saved_models/scaler.pkl"):
            scaler = joblib.load("models/saved_models/scaler.pkl")
    except Exception as e:
        return {"error": str(e)}

    X_normal = generate_normal_samples(2000, seed=55)
    X_anomaly = generate_anomalous_samples(500, seed=77)
    X_all = np.concatenate([X_normal, X_anomaly])
    y_true = np.concatenate([np.zeros(len(X_normal)), np.ones(len(X_anomaly))])

    X_test = scaler.transform(X_all) if scaler is not None else X_all
    preds = (model.predict(X_test) == -1).astype(int)
    scores = model.score_samples(X_test)

    prec = precision_score(y_true, preds)
    rec = recall_score(y_true, preds)
    f1 = f1_score(y_true, preds)
    try:
        auc = roc_auc_score(y_true, -scores)
    except:
        auc = 0.0
    cm = confusion_matrix(y_true, preds).tolist()

    results = {
        "model": "ExistingIsolationForest",
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "auc_roc": round(auc, 4),
        "confusion_matrix": cm,
        "scaler_used": scaler is not None,
        "scaler_type": type(scaler).__name__ if scaler else "None",
    }

    if verbose:
        print(f"\n  📊 Existing Model Evaluation:")
        print(f"     Precision:  {prec:.4f}")
        print(f"     Recall:     {rec:.4f}")
        print(f"     F1-Score:   {f1:.4f}")
        print(f"     AUC-ROC:    {auc:.4f}")
        print(f"     Scaler:     {type(scaler).__name__ if scaler else 'None'}")
        print(f"     Confusion Matrix: {cm}")

    return results


# ──────────────────────────────────────────────
# TEST 6: SUPERVISED ANOMALY DETECTION MODELS
# (Better alternatives: RF, GB, XGBoost, ET)
# ──────────────────────────────────────────────

def test_supervised_anomaly_models(verbose=True):
    """Compare supervised models for anomaly detection — these should outperform Isolation Forest."""
    if verbose:
        print("\n" + "=" * 70)
        print("TEST 6: SUPERVISED ANOMALY MODELS (Better Alternatives)")
        print("=" * 70)

    # Generate labeled data
    X_normal = generate_normal_samples(5000, seed=42)
    X_anomaly = generate_anomalous_samples(1000, seed=123)
    X_all = np.concatenate([X_normal, X_anomaly])
    y_all = np.concatenate([np.zeros(len(X_normal)), np.ones(len(X_anomaly))])

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=0.3, random_state=42, stratify=y_all
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Define supervised models
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=10, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            random_state=42
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=200, max_depth=10, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            scale_pos_weight=len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1),
            random_state=42, use_label_encoder=False, eval_metric='logloss',
            verbosity=0
        )

    # Also include Isolation Forest for comparison
    iso_model = IsolationForest(contamination=0.15, random_state=42, n_estimators=200)
    iso_model.fit(X_train_s)
    iso_preds = (iso_model.predict(X_test_s) == -1).astype(int)
    iso_scores = iso_model.score_samples(X_test_s)

    results = {
        "IsolationForest_baseline": {
            "precision": round(precision_score(y_test, iso_preds), 4),
            "recall": round(recall_score(y_test, iso_preds), 4),
            "f1_score": round(f1_score(y_test, iso_preds), 4),
            "auc_roc": round(roc_auc_score(y_test, -iso_scores), 4),
            "model_type": "unsupervised",
        }
    }

    if verbose:
        print(f"\n  📈 IsolationForest (baseline, unsupervised):")
        r = results["IsolationForest_baseline"]
        print(f"     Prec={r['precision']:.4f}  Rec={r['recall']:.4f}  "
              f"F1={r['f1_score']:.4f}  AUC={r['auc_roc']:.4f}")

    best_f1 = results["IsolationForest_baseline"]["f1_score"]
    best_model_name = "IsolationForest_baseline"
    best_model = None
    best_scaler = scaler

    for name, model in models.items():
        start = time.perf_counter()
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        y_proba = model.predict_proba(X_test_s)[:, 1]
        elapsed_ms = (time.perf_counter() - start) * 1000

        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1_val = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        cm = confusion_matrix(y_test, y_pred).tolist()

        results[name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1_val, 4),
            "auc_roc": round(auc, 4),
            "confusion_matrix": cm,
            "training_time_ms": round(elapsed_ms, 2),
            "model_type": "supervised",
        }

        if f1_val > best_f1:
            best_f1 = f1_val
            best_model_name = name
            best_model = model

        if verbose:
            print(f"\n  📈 {name} (supervised):")
            print(f"     Prec={prec:.4f}  Rec={rec:.4f}  F1={f1_val:.4f}  AUC={auc:.4f}")
            print(f"     Time: {elapsed_ms:.1f}ms  CM: {cm}")

    results["_best_model"] = best_model_name
    results["_best_f1"] = round(best_f1, 4)

    if verbose:
        print(f"\n  🏆 Best anomaly detection model: {best_model_name} (F1={best_f1:.4f})")

    # Save the best supervised model for Lambda deployment if it beats Isolation Forest
    if best_model is not None:
        os.makedirs("models/saved_models", exist_ok=True)
        joblib.dump(best_model, f"models/saved_models/best_anomaly_{best_model_name.lower()}.pkl")
        joblib.dump(scaler, "models/saved_models/best_anomaly_scaler.pkl")
        if verbose:
            print(f"  💾 Best model saved to models/saved_models/best_anomaly_{best_model_name.lower()}.pkl")

    # Cross-validate the best supervised model
    if best_model is not None:
        if verbose:
            print(f"\n  🔄 5-Fold CV for {best_model_name}:")
        cv_f1s = []
        cv_aucs = []
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        for train_idx, test_idx in skf.split(X_all, y_all):
            Xtr, Xte = X_all[train_idx], X_all[test_idx]
            ytr, yte = y_all[train_idx], y_all[test_idx]
            sc = StandardScaler()
            Xtr_s = sc.fit_transform(Xtr)
            Xte_s = sc.transform(Xte)
            m = type(best_model)(**best_model.get_params())
            m.fit(Xtr_s, ytr)
            p = m.predict(Xte_s)
            pr = m.predict_proba(Xte_s)[:, 1]
            cv_f1s.append(f1_score(yte, p))
            cv_aucs.append(roc_auc_score(yte, pr))
        results["_best_model_cv"] = {
            "f1_mean": round(float(np.mean(cv_f1s)), 4),
            "f1_std": round(float(np.std(cv_f1s)), 4),
            "auc_mean": round(float(np.mean(cv_aucs)), 4),
            "auc_std": round(float(np.std(cv_aucs)), 4),
        }
        if verbose:
            print(f"     F1: {np.mean(cv_f1s):.4f} ± {np.std(cv_f1s):.4f}")
            print(f"     AUC: {np.mean(cv_aucs):.4f} ± {np.std(cv_aucs):.4f}")

    return results


# ──────────────────────────────────────────────
# TEST 7: BETTER ACTIVITY CLASSIFIERS
# (Supervised alternatives for edge deployment)
# ──────────────────────────────────────────────

def test_better_activity_classifiers(verbose=True):
    """Train and compare better classifiers for activity recognition."""
    if verbose:
        print("\n" + "=" * 70)
        print("TEST 7: BETTER ACTIVITY CLASSIFIERS (sklearn alternatives)")
        print("=" * 70)

    LABELS = ["sleep", "rest", "walk", "run", "exercise", "other"]

    # Generate more data for better training
    X, y, _ = generate_activity_samples(n=18000, seed=42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300, max_depth=15, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            random_state=42
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=300, max_depth=15, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            random_state=42, use_label_encoder=False, eval_metric='mlogloss',
            verbosity=0
        )

    results = {}
    best_acc = 0
    best_name = None
    best_model = None

    for name, model in models.items():
        start = time.perf_counter()
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        elapsed_ms = (time.perf_counter() - start) * 1000

        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred).tolist()
        report = classification_report(y_test, y_pred, target_names=LABELS, output_dict=True, zero_division=0)
        per_class_f1 = {LABELS[i]: round(report[LABELS[i]]["f1-score"], 4) for i in range(len(LABELS))}

        results[name] = {
            "accuracy": round(acc, 4),
            "per_class_f1": per_class_f1,
            "confusion_matrix": cm,
            "training_time_ms": round(elapsed_ms, 2),
            "classification_report": report,
        }

        if acc > best_acc:
            best_acc = acc
            best_name = name
            best_model = model

        if verbose:
            print(f"\n  📈 {name}:")
            print(f"     Accuracy: {acc:.4f}  Time: {elapsed_ms:.1f}ms")
            for label in LABELS:
                f1_val = per_class_f1[label]
                status = "✅" if f1_val >= 0.70 else "⚠️" if f1_val >= 0.50 else "❌"
                print(f"     {status} {label:10s}: F1={f1_val:.4f}")

    results["_best_model"] = best_name
    results["_best_accuracy"] = round(best_acc, 4)

    if verbose:
        print(f"\n  🏆 Best activity classifier: {best_name} (Acc={best_acc:.4f})")

    # Test the best model on specific scenarios
    if best_model is not None:
        specific_tests = [
            ("resting_person", [70, 50, 20, 0.1], "rest"),
            ("sleeping_person", [55, 5, 8, 0.01], "sleep"),
            ("walking_person", [85, 120, 35, 0.4], "walk"),
            ("running_person", [130, 250, 60, 0.8], "run"),
            ("exercising_person", [150, 200, 75, 0.6], "exercise"),
        ]
        specific_results = []
        if verbose:
            print(f"\n  🧪 Specific Scenario Tests ({best_name}):")
        for sname, features, expected in specific_tests:
            sample = scaler.transform(np.array([features], dtype=np.float32))
            pred = best_model.predict(sample)[0]
            pred_label = LABELS[pred]
            proba = best_model.predict_proba(sample)[0]
            correct = pred_label == expected
            specific_results.append({
                "scenario": sname,
                "predicted": pred_label,
                "expected": expected,
                "correct": correct,
                "confidence": round(float(np.max(proba)), 4),
            })
            if verbose:
                status = "✅" if correct else "❌"
                print(f"     {status} {sname}: pred={pred_label} (expected={expected}) conf={np.max(proba):.4f}")

        results["_best_model_specific_tests"] = specific_results

        # Save best activity model
        joblib.dump(best_model, f"models/saved_models/best_activity_{best_name.lower()}.pkl")
        joblib.dump(scaler, "models/saved_models/best_activity_scaler.pkl")
        if verbose:
            print(f"\n  💾 Best model saved: models/saved_models/best_activity_{best_name.lower()}.pkl")

    return results


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Comprehensive ML Model Testing")
    parser.add_argument("--output", default="test_results_comprehensive.json", help="Output JSON file")
    parser.add_argument("--skip-tflite", action="store_true", help="Skip TFLite tests")
    parser.add_argument("--verbose", default=True, action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    print("🔬 COMPREHENSIVE ML MODEL TESTING SUITE")
    print("=" * 70)
    print(f"   Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   XGBoost available: {HAS_XGBOOST}")
    print("=" * 70)

    all_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "xgboost_available": HAS_XGBOOST,
        "tests": {},
    }

    start = time.time()

    # Test 1: Existing model (before retrain)
    try:
        all_results["tests"]["existing_isolation_forest"] = test_existing_isolation_forest(args.verbose)
    except Exception as e:
        all_results["tests"]["existing_isolation_forest"] = {"error": str(e), "traceback": traceback.format_exc()}

    # Test 2: Retrained Isolation Forest
    try:
        all_results["tests"]["retrained_isolation_forest"] = test_isolation_forest(args.verbose)
    except Exception as e:
        all_results["tests"]["retrained_isolation_forest"] = {"error": str(e), "traceback": traceback.format_exc()}

    # Test 3: Unsupervised model comparison
    try:
        all_results["tests"]["unsupervised_comparison"] = test_model_comparison(args.verbose)
    except Exception as e:
        all_results["tests"]["unsupervised_comparison"] = {"error": str(e), "traceback": traceback.format_exc()}

    # Test 4: Supervised anomaly models (BETTER alternatives)
    try:
        all_results["tests"]["supervised_anomaly_models"] = test_supervised_anomaly_models(args.verbose)
    except Exception as e:
        all_results["tests"]["supervised_anomaly_models"] = {"error": str(e), "traceback": traceback.format_exc()}

    # Test 5: Better activity classifiers
    try:
        all_results["tests"]["better_activity_classifiers"] = test_better_activity_classifiers(args.verbose)
    except Exception as e:
        all_results["tests"]["better_activity_classifiers"] = {"error": str(e), "traceback": traceback.format_exc()}

    if not args.skip_tflite:
        # Test 6: Activity Classifier (existing TFLite)
        try:
            all_results["tests"]["activity_classifier_tflite"] = test_activity_classifier(args.verbose)
        except Exception as e:
            all_results["tests"]["activity_classifier_tflite"] = {"error": str(e), "traceback": traceback.format_exc()}

        # Test 7: Conv1D Autoencoder (existing TFLite)
        try:
            all_results["tests"]["conv1d_autoencoder_tflite"] = test_conv1d_autoencoder(args.verbose)
        except Exception as e:
            all_results["tests"]["conv1d_autoencoder_tflite"] = {"error": str(e), "traceback": traceback.format_exc()}

    total_time = time.time() - start
    all_results["total_duration_seconds"] = round(total_time, 2)

    # ──────────────────────────────────────────
    # FINAL SUMMARY
    # ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("📋 OVERALL SUMMARY")
    print("=" * 70)

    # Existing vs retrained Isolation Forest
    existing = all_results["tests"].get("existing_isolation_forest", {})
    retrained = all_results["tests"].get("retrained_isolation_forest", {})

    if "error" not in existing and "error" not in retrained:
        retrained_metrics = retrained.get("tests", {}).get("full_evaluation", {})
        print(f"\n  🔄 Isolation Forest (Existing → Retrained):")
        print(f"  {'Metric':<12} {'Existing':>10} {'Retrained':>10} {'Change':>10}")
        print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}")
        for metric in ["precision", "recall", "f1_score", "auc_roc"]:
            old_val = existing.get(metric, 0)
            new_val = retrained_metrics.get(metric, 0)
            change = new_val - old_val
            arrow = "↑" if change > 0 else "↓" if change < 0 else "="
            print(f"  {metric:<12} {old_val:>10.4f} {new_val:>10.4f} {arrow}{abs(change):>8.4f}")

    # Best supervised anomaly model
    sup_anomaly = all_results["tests"].get("supervised_anomaly_models", {})
    if "error" not in sup_anomaly:
        best = sup_anomaly.get("_best_model", "?")
        best_f1 = sup_anomaly.get("_best_f1", 0)
        print(f"\n  🏆 Best Anomaly Detection Model: {best} (F1={best_f1:.4f})")
        print(f"  Model rankings (anomaly detection):")
        ranked = sorted(
            [(k, v) for k, v in sup_anomaly.items() if not k.startswith("_") and isinstance(v, dict) and "f1_score" in v],
            key=lambda x: x[1]["f1_score"], reverse=True
        )
        for i, (name, metrics) in enumerate(ranked):
            marker = "👑" if i == 0 else f"#{i+1}"
            print(f"     {marker} {name:25s}: F1={metrics['f1_score']:.4f}  AUC={metrics['auc_roc']:.4f}")

    # Best activity classifier
    best_act = all_results["tests"].get("better_activity_classifiers", {})
    if "error" not in best_act:
        best_name = best_act.get("_best_model", "?")
        best_acc = best_act.get("_best_accuracy", 0)
        print(f"\n  🏆 Best Activity Classifier: {best_name} (Accuracy={best_acc:.4f})")

        # Compare with TFLite
        tflite_act = all_results["tests"].get("activity_classifier_tflite", {})
        if "error" not in tflite_act:
            tflite_acc = tflite_act.get("accuracy", 0)
            improvement = best_acc - tflite_acc
            print(f"     vs TFLite model: {tflite_acc:.4f} → {best_acc:.4f} "
                  f"({'↑' if improvement > 0 else '↓'}{abs(improvement):.4f})")

    # Conv1D summary
    conv1d = all_results["tests"].get("conv1d_autoencoder_tflite", {})
    if "error" not in conv1d:
        sep = conv1d.get("separation_analysis", {})
        can_sep = sep.get("can_separate_anomalies", False)
        print(f"\n  Conv1D Autoencoder: {'✅ CAN' if can_sep else '❌ CANNOT'} separate anomalies")

    print(f"\n  ⏱️  Total test time: {total_time:.1f}s")

    # Recommendations
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS")
    print("=" * 70)

    if "error" not in sup_anomaly:
        best = sup_anomaly.get("_best_model", "")
        iso_f1 = sup_anomaly.get("IsolationForest_baseline", {}).get("f1_score", 0)
        best_f1 = sup_anomaly.get("_best_f1", 0)
        if best_f1 > iso_f1:
            print(f"\n  1. 🔀 SWITCH anomaly detection from Isolation Forest to {best}")
            print(f"     F1 improvement: {iso_f1:.4f} → {best_f1:.4f} (+{best_f1-iso_f1:.4f})")
            print(f"     Model saved at: models/saved_models/best_anomaly_{best.lower()}.pkl")

    if "error" not in best_act:
        best_name = best_act.get("_best_model", "")
        best_acc = best_act.get("_best_accuracy", 0)
        tflite_act = all_results["tests"].get("activity_classifier_tflite", {})
        tflite_acc = tflite_act.get("accuracy", 0) if "error" not in tflite_act else 0
        if best_acc > tflite_acc:
            print(f"\n  2. 🔀 SWITCH activity classifier from TFLite NN to {best_name}")
            print(f"     Accuracy improvement: {tflite_acc:.4f} → {best_acc:.4f} (+{best_acc-tflite_acc:.4f})")
            print(f"     For edge: retrain TFLite with adapted Normalization layer")
            print(f"     For cloud: use sklearn model directly (saved)")

    print(f"\n  3. 📊 Add SpO2, skin temperature, and sleep stage features for richer detection")
    print(f"  4. 🔄 Implement periodic retraining with real sensor data")
    print(f"  5. ⚖️  Use SMOTE oversampling if anomaly data is scarce in production")

    # Save results
    with open(args.output, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  📄 Results saved to {args.output}")


if __name__ == "__main__":
    main()
