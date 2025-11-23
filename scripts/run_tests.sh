#!/bin/bash
# テスト実行スクリプト

set -e

echo "=================================="
echo "  LangGraph Training - Test Suite"
echo "=================================="
echo ""

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 引数の解析
TEST_TYPE="${1:-all}"  # all, unit, integration
COVERAGE="${2:-true}"   # true, false

echo "Test Type: $TEST_TYPE"
echo "Coverage: $COVERAGE"
echo ""

# テストコマンドの構築
PYTEST_ARGS="-v --tb=short"

if [ "$COVERAGE" = "true" ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml"
fi

# テストタイプに応じて実行
case "$TEST_TYPE" in
    unit)
        echo -e "${YELLOW}Running unit tests...${NC}"
        pytest tests/ -m "not integration" $PYTEST_ARGS
        ;;
    integration)
        echo -e "${YELLOW}Running integration tests...${NC}"
        pytest tests/integration/ -m integration $PYTEST_ARGS
        ;;
    all)
        echo -e "${YELLOW}Running all tests...${NC}"
        pytest tests/ $PYTEST_ARGS
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: $0 [all|unit|integration] [true|false]"
        exit 1
        ;;
esac

# テスト結果の確認
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=================================="
    echo "  ✅ All tests passed!"
    echo -e "==================================${NC}"
    echo ""
    
    if [ "$COVERAGE" = "true" ]; then
        echo "Coverage report generated:"
        echo "  - HTML: htmlcov/index.html"
        echo "  - XML: coverage.xml"
        echo ""
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}=================================="
    echo "  ❌ Tests failed!"
    echo -e "==================================${NC}"
    echo ""
    exit 1
fi

