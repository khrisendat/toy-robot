import onnxruntime as ort
import os

model_path = "models/hey_jarvis_v0.1.onnx"

if not os.path.exists(model_path):
    print(f"Error: Model file not found at {model_path}")
else:
    try:
        print(f"Attempting to load model from: {os.path.abspath(model_path)}")
        ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        print("Success! The ONNX model loaded correctly.")
    except Exception as e:
        print(f"Failed to load the ONNX model. Error: {e}")
