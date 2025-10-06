#!/bin/bash
# Helper script to run real model integration tests

# Check if API credentials are set
if [ -z "$VLLM_API_KEY" ] || [ -z "$VLLM_API_BASE" ]; then
    echo "Error: Please set VLLM_API_KEY and VLLM_API_BASE environment variables"
    echo ""
    echo "Example:"
    echo "  export VLLM_API_KEY='your-key'"
    echo "  export VLLM_API_BASE='http://localhost:8000/v1'"
    echo "  ./run_real_test.sh"
    exit 1
fi

# Set project root in PYTHONPATH
export PYTHONPATH="$(cd "$(dirname "$0")/../.." && pwd)"

echo "====================================="
echo "Running Real Model Integration Tests"
echo "====================================="
echo "Model endpoint: $VLLM_API_BASE"
echo "Project root: $PYTHONPATH"
echo ""

# Activate virtual environment if it exists
if [ -d "$PYTHONPATH/venv" ]; then
    source "$PYTHONPATH/venv/bin/activate"
    echo "Virtual environment activated"
    echo ""
fi

# Run the tests
pytest sweagent/test/test_real_model.py -s -v "$@"

