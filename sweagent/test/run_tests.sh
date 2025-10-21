#!/bin/bash

# Test runner script for SWE-agent tests
# This script runs all tests in the sweagent/test directory

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory (parent of sweagent directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}SWE-agent Test Runner${NC}"
echo "=================================="
echo "Project root: $PROJECT_ROOT"
echo "Test directory: $TEST_DIR"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Use conda environment's Python directly
if [[ -n "$CONDA_PREFIX" ]]; then
    PYTHON_CMD="$CONDA_PREFIX/bin/python"
    echo "Using Python from: $PYTHON_CMD"
    echo "Python version: $($PYTHON_CMD --version)"
else
    echo -e "${RED}Error: No conda environment active!${NC}"
    echo "Please run: conda activate sweagent"
    exit 1
fi
echo ""

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo -e "${YELLOW}Running tests...${NC}"
echo ""

# Test 1: Minimal real response test (standalone script)
echo -e "${YELLOW}1. Running minimal real response test...${NC}"
if $PYTHON_CMD "$TEST_DIR/test_minimal_real_response.py"; then
    echo -e "${GREEN}✓ Minimal real response test passed${NC}"
else
    echo -e "${RED}✗ Minimal real response test failed${NC}"
    exit 1
fi
echo ""

# Test 2: MCP integration tests (pytest)
echo -e "${YELLOW}2. Running MCP integration tests...${NC}"
if $PYTHON_CMD -m pytest "$TEST_DIR/test_mcp_integration.py" -v; then
    echo -e "${GREEN}✓ MCP integration tests passed${NC}"
else
    echo -e "${RED}✗ MCP integration tests failed${NC}"
    exit 1
fi
echo ""

# Test 3: Commands tests (pytest)
echo -e "${YELLOW}3. Running commands tests...${NC}"
if $PYTHON_CMD -m pytest "$TEST_DIR/test_commands.py" -v; then
    echo -e "${GREEN}✓ Commands tests passed${NC}"
else
    echo -e "${RED}✗ Commands tests failed${NC}"
    exit 1
fi
echo ""

# Test 4: Workspace tests (pytest)
echo -e "${YELLOW}4. Running workspace tests...${NC}"
if $PYTHON_CMD -m pytest "$TEST_DIR/test_workspace.py" -v; then
    echo -e "${GREEN}✓ Workspace tests passed${NC}"
else
    echo -e "${RED}✗ Workspace tests failed${NC}"
    exit 1
fi
echo ""

# Test 5: Real MCP execution tests (requires Apptainer images)
echo -e "${YELLOW}5. Running real MCP execution tests...${NC}"
if $PYTHON_CMD -m pytest "$TEST_DIR/test_mcp_real_execution.py" -v --tb=short; then
    echo -e "${GREEN}✓ Real MCP execution tests passed${NC}"
else
    echo -e "${RED}✗ Real MCP execution tests failed${NC}"
    echo -e "${YELLOW}Note: These tests require Apptainer images to be available${NC}"
    # Don't exit on failure for this test as it requires external dependencies
fi
echo ""

# Test 6: Run all pytest tests together
echo -e "${YELLOW}6. Running all pytest tests together...${NC}"
if $PYTHON_CMD -m pytest "$TEST_DIR" -v --tb=short; then
    echo -e "${GREEN}✓ All pytest tests passed${NC}"
else
    echo -e "${RED}✗ Some pytest tests failed${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}🎉 All tests completed successfully!${NC}"
echo ""
echo "Test Summary:"
echo "- Minimal real response test: ✓"
echo "- MCP integration tests: ✓"
echo "- Commands tests: ✓"
echo "- Workspace tests: ✓"
echo "- Real MCP execution tests: ✓"
echo "- All pytest tests: ✓"