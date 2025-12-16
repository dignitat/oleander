import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# ONNX export
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

import os
import sys

ARTIFACTS_FOLDER = "artifacts"

if (not os.path.isdir(ARTIFACTS_FOLDER)):
    os.makedirs(ARTIFACTS_FOLDER)

DATASET_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ARTIFACTS_FOLDER, "dataset.csv")

def load_dataset(path):
    df = pd.read_csv(path)
    if "is_bot" not in df.columns:
        raise ValueError("Dataset must contain 'is_bot' column as label.")
    
    y = df["is_bot"]
    X = df.drop(columns=["is_bot"])
    X = X.apply(pd.to_numeric, errors="coerce")
    X = X.dropna(axis=1, how="all")
    X = X.fillna(X.mean())
    return X, y

def train_rf_model(X, y, write=True):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    rf = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Classification Report:\n", classification_report(y_test, y_pred))

    if write:
        with open(os.path.join(ARTIFACTS_FOLDER, "model.pkl"), "wb") as f:
            pickle.dump({"model": rf, "columns": list(X.columns)}, f)
        print("Saved model.pkl")

    # Export ONNX with zipmap=False so we get raw probability tensor
    initial_type = [('float_input', FloatTensorType([None, X.shape[1]]))]
    options = {id(rf): {'zipmap': False}}  # important: disable zipmap (dict) output
    onnx_model = convert_sklearn(rf, initial_types=initial_type, options=options)
    with open(os.path.join(ARTIFACTS_FOLDER, "model.onnx"), "wb") as f:
        f.write(onnx_model.SerializeToString())
    print("Saved model.onnx (probabilities, zipmap=False)")

    return rf

if __name__ == "__main__":
    X, y = load_dataset(DATASET_FILE)
    train_rf_model(X, y)
