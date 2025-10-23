#!/bin/bash

echo "========================================"
echo "Financial Market Data Streaming System"
echo "Installation Verification Script"
echo "========================================"
echo ""

ERRORS=0

# Check Python
echo "✓ Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "  Found: $PYTHON_VERSION"
else
    echo "  ✗ Python 3 not found!"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check Docker
echo "✓ Checking Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "  Found: $DOCKER_VERSION"
else
    echo "  ✗ Docker not found!"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check Docker Compose
echo "✓ Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo "  Found: $COMPOSE_VERSION"
else
    echo "  ✗ Docker Compose not found!"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check .env file
echo "✓ Checking environment configuration..."
if [ -f .env ]; then
    echo "  Found: .env file"

    if grep -q "POLYGON_API_KEY=" .env || \
       grep -q "FINAGE_API_KEY=" .env || \
       grep -q "ALPHA_VANTAGE_API_KEY=" .env; then
        echo "  ✓ API key(s) configured"
    else
        echo "  ⚠ No API keys found in .env"
        echo "    Please add at least one API key"
    fi
else
    echo "  ⚠ .env file not found"
    echo "    Run: cp .env.example .env"
    echo "    Then add your API keys"
fi
echo ""

# Check project structure
echo "✓ Checking project structure..."
REQUIRED_DIRS=("src/producers" "src/consumers" "src/analytics" "src/api" "src/storage" "src/dashboard" "src/monitoring" "config" "data" "logs")
MISSING=0

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "  ✗ Missing directory: $dir"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -eq 0 ]; then
    echo "  ✓ All required directories present"
else
    echo "  ✗ Missing $MISSING directories"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check Python files
echo "✓ Checking Python modules..."
PYTHON_FILES=(
    "src/producers/market_api_streamer.py"
    "src/consumers/stream_processor.py"
    "src/analytics/technical_indicators.py"
    "src/analytics/price_predictor.py"
    "src/api/rest_api.py"
    "src/api/websocket_server.py"
    "src/storage/timescaledb_connector.py"
    "src/storage/influxdb_handler.py"
    "src/storage/redis_cache.py"
    "src/dashboard/realtime_dashboard.py"
    "src/monitoring/anomaly_detector.py"
    "src/monitoring/alerting.py"
    "src/monitoring/metrics_collector.py"
)

MISSING_FILES=0
for file in "${PYTHON_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  ✗ Missing file: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -eq 0 ]; then
    echo "  ✓ All core Python modules present (${#PYTHON_FILES[@]} files)"
else
    echo "  ✗ Missing $MISSING_FILES Python files"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check configuration files
echo "✓ Checking configuration files..."
CONFIG_FILES=("docker-compose.yml" "requirements.txt" "config/api_config.yaml" "Makefile")
MISSING_CONFIGS=0

for file in "${CONFIG_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  ✗ Missing: $file"
        MISSING_CONFIGS=$((MISSING_CONFIGS + 1))
    fi
done

if [ $MISSING_CONFIGS -eq 0 ]; then
    echo "  ✓ All configuration files present"
else
    echo "  ✗ Missing $MISSING_CONFIGS configuration files"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check documentation
echo "✓ Checking documentation..."
DOC_FILES=("README.md" "QUICKSTART.md" "ARCHITECTURE.md" "PROJECT_SUMMARY.md")
for file in "${DOC_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ Missing: $file"
    fi
done
echo ""

# Check if requirements can be imported
echo "✓ Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo "  Testing key imports..."
    python3 -c "import kafka; import pyspark; import fastapi; import dash; import redis" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✓ Core dependencies installed"
    else
        echo "  ⚠ Some dependencies missing"
        echo "    Run: pip install -r requirements.txt"
    fi
else
    echo "  ✗ requirements.txt not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Summary
echo "========================================"
echo "Verification Summary"
echo "========================================"

if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed!"
    echo ""
    echo "Your system is ready. Next steps:"
    echo "  1. Ensure API keys are set in .env"
    echo "  2. Install dependencies: pip install -r requirements.txt"
    echo "  3. Start the system: ./start_all.sh"
    echo "  4. Access dashboard: http://localhost:8050"
    echo ""
    echo "For detailed instructions, see QUICKSTART.md"
    exit 0
else
    echo "⚠ Found $ERRORS errors"
    echo ""
    echo "Please fix the errors above before continuing."
    echo "Refer to README.md for setup instructions."
    exit 1
fi
