#!/bin/bash
# ─── AI POC — WSL Startup Script ──────────────────────────────────────────────
# Usage: ./start.sh
# รัน Flask app บน WSL ด้วย virtual environment

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Check .env exists
if [ ! -f ".env" ]; then
    echo "❌ ไม่พบไฟล์ .env"
    echo "   กรุณา copy .env.example แล้วใส่ API key:"
    echo "   cp .env.example .env && nano .env"
    exit 1
fi

# Check venv exists
if [ ! -d "venv" ]; then
    echo "⚙️  สร้าง virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install/update dependencies
echo "📦 ตรวจสอบ dependencies..."
pip install -q -r requirements.txt

# Create required directories
mkdir -p workspace temp

echo "🚀 กำลังเริ่ม AI POC server..."
echo "   URL: http://localhost:5000"
echo "   หยุดด้วย Ctrl+C"
echo ""

# Run via gunicorn + gevent (production-safe, SSE-compatible)
export PYTHONIOENCODING=utf-8
./venv/bin/gunicorn --config gunicorn.conf.py "app:app"
