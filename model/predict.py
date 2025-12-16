# This is a prediction example and should only be used for debugging

import pickle
import pandas as pd
import numpy as np
import onnxruntime as ort

def load_model(path="model.pkl"):
    return pickle.load(open(path, "rb"))

def predict(features_arr, model_data):
    model = model_data["model"]
    columns = model_data["columns"]
    X = pd.DataFrame([features_arr], columns=columns)
    proba = model.predict_proba(X)[0]
    bot_prob = float(proba[1])
    print("SKLEARN proba:", proba)
    return bot_prob

# ONNX
def load_onnx(path="model.onnx"):
    sess = ort.InferenceSession(path)
    # print output info for debugging
    print("ONNX outputs:", [(o.name, o.shape, o.type) for o in sess.get_outputs()])
    return sess

def predict_onnx(features_arr, session):
    # Prepare input
    arr = np.array([features_arr], dtype=np.float32)

    outputs = session.run(None, {"float_input": arr})
    # outputs is a list in the same order as session.get_outputs()

    # Debug: shapes
    #out_meta = session.get_outputs()
    
    try:
        prob = outputs[1][0] # [human_prob, bot_prob]
    except:
        raise RuntimeError(f"ONNX did not produce a prob-like output. outputs: {[np.array(o).shape for o in outputs]}")
    
    # If only one class available, return 0.0 as bot prob
    if prob.size == 1:
        return 0.0
    
    return float(prob[1])
