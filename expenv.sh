#!/bin/bash
echo "Export the conda environment..."
conda env export --no-builds | grep -v "^prefix: " > environment.yml

echo "Export the pip environment..."
pip freeze > requirements.txt

echo "Environment export completed."
