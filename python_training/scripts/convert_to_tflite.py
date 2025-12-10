import tensorflow as tf
import numpy as np
import os
import data_preprocessing as dp

# --- CONFIGURATION ---
DATA_DIR = "./data/training_audio/raw/train_set"
MODEL_PATH = "pico_locator.keras"
TFLITE_PATH = "pico_locator_int8.tflite"
HEADER_PATH = "model_data.h"

def representative_dataset_gen(training_data):
    """Generator function for Int8 calibration"""
    num_calibration_samples = 100 
    
    if len(training_data) < num_calibration_samples:
        samples = training_data
    else:
        indices = np.random.choice(len(training_data), num_calibration_samples, replace=False)
        samples = training_data[indices]
        
    for input_value in samples:
        # Add batch dimension (1, 190, 96, 3)
        input_with_batch = np.expand_dims(input_value, axis=0)
        yield [input_with_batch.astype(np.float32)]

if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        print(f"Model {MODEL_PATH} not found. Run train_pico.py first.")
        exit()

    # 1. Load Data for Calibration
    print("Loading dataset for calibration...")
    X_train, _, _, _ = dp.load_and_split_dataset(DATA_DIR)
    
    # 2. Load Model
    model = tf.keras.models.load_model(MODEL_PATH)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # 3. Quantization Settings
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # Use lambda to inject data into the generator scope
    converter.representative_dataset = lambda: representative_dataset_gen(X_train)
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    
    # 4. Convert
    print("Converting to Int8 TFLite...")
    tflite_model = converter.convert()
    
    # 5. Save Files
    with open(TFLITE_PATH, 'wb') as f:
        f.write(tflite_model)
        
    # Create C Header
    byte_array = [format(b, '#04x') for b in tflite_model]
    c_content = f"""// TFLite Model - Int8 Quantized
// Size: {len(byte_array)} bytes
const unsigned char g_model[] = {{ {', '.join(byte_array)} }};
const int g_model_len = {len(byte_array)};
"""
    with open(HEADER_PATH, 'w') as f:
        f.write(c_content)
        
    print(f"✅ Success! TFLite model saved to {HEADER_PATH}")
    print(f"File Size: {len(byte_array)/1024:.2f} KB")