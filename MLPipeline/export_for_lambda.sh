#!/bin/bash
# Script to export LSTM model for AWS Lambda deployment

set -e

echo "🚀 Exporting LSTM Autoencoder for Lambda Deployment"
echo ""

# Create export directory
mkdir -p models/lambda_export

echo "1. Converting model to TensorFlow SavedModel format..."
python3 << 'EOF'
import tensorflow as tf
import numpy as np

# Load the trained model
print("   Loading trained model...")
model = tf.keras.models.load_model('models/saved_models/lstm_autoencoder.h5')

# Save as SavedModel (more portable than .h5)
print("   Converting to SavedModel...")
model.save('models/lambda_export/lstm_model_savedmodel', save_format='tf')

print("   ✓ Saved as SavedModel")

# Also save as TFLite for ultra-lightweight inference (optional)
print("   Converting to TensorFlow Lite...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

with open('models/lambda_export/lstm_model.tflite', 'wb') as f:
    f.write(tflite_model)

print("   ✓ Saved as TFLite")
print(f"   TFLite model size: {len(tflite_model) / 1024 / 1024:.2f} MB")

# Load threshold if exists
try:
    threshold = np.load('models/saved_models/lstm_autoencoder_threshold.npy')
    np.save('models/lambda_export/threshold.npy', threshold)
    print(f"   ✓ Saved threshold: {float(threshold):.6f}")
except:
    print("   ⚠ No threshold found, using default 0.006")

print("\n2. Creating Lambda deployment package...")

# Copy lambda handler
import shutil
shutil.copy('src/models/lambda_inference.py', 'models/lambda_export/lambda_function.py')
print("   ✓ Copied lambda handler")

# Create requirements for Lambda layer
lambda_reqs = """tensorflow>=2.13.0
numpy>=1.24.0
"""

with open('models/lambda_export/requirements.txt', 'w') as f:
    f.write(lambda_reqs)

print("   ✓ Created requirements.txt")

print("\n3. Summary:")
print("   Export directory: models/lambda_export/")
print("   - lstm_model_savedmodel/    (TensorFlow SavedModel)")
print("   - lstm_model.tflite         (TensorFlow Lite - ultra lightweight)")
print("   - threshold.npy             (Anomaly detection threshold)")
print("   - lambda_function.py        (Lambda handler)")
print("   - requirements.txt          (Dependencies)")

print("\n✅ Export complete!")
print("\nNext steps:")
print("1. Upload model to S3: aws s3 cp models/lambda_export/ s3://your-bucket/lstm-model/")
print("2. Create Lambda layer with dependencies")
print("3. Deploy lambda_function.py as Lambda function")
print("4. Set MODEL_PATH environment variable to S3 model path")
EOF

echo ""
echo "Export complete! Check models/lambda_export/"
