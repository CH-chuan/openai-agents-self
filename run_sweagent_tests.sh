#!/bin/bash

# Simple test runner for SWE-agent tests
# This script runs the main test runner from the project root

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the test script
"$SCRIPT_DIR/sweagent/test/run_tests.sh"
