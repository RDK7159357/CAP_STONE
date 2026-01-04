#!/bin/bash
# Enable execute permissions for pipeline scripts

chmod +x export_for_lambda.sh
chmod +x train_pipeline.sh

echo "✓ Pipeline scripts ready"
echo ""
echo "To train the model, run:"
echo "  bash train_pipeline.sh"
