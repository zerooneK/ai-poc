#!/bin/bash
# ─── AI POC — WSL First-Time Setup ───────────────────────────────────────────
# Usage: bash setup.sh
# รันครั้งแรกครั้งเดียวเพื่อเตรียม environment บน WSL

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "🔧 AI POC — WSL Setup"
echo "================================"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo "✅ $PYTHON_VERSION"

# Create venv if not exists
if [ -d "venv" ]; then
    echo "✅ venv มีอยู่แล้ว"
else
    echo "⚙️  สร้าง virtual environment..."
    python3 -m venv venv
    echo "✅ สร้าง venv สำเร็จ"
fi

# Activate and install deps
source venv/bin/activate
echo "📦 ติดตั้ง dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ ติดตั้ง dependencies สำเร็จ"

# Create required directories
mkdir -p workspace temp
echo "✅ สร้าง workspace/ และ temp/ แล้ว"

# Setup .env if not exists
if [ -f ".env" ]; then
    echo "✅ .env มีอยู่แล้ว"
else
    cp .env.example .env
    echo ""
    echo "⚠️  สร้างไฟล์ .env จาก .env.example แล้ว"
    echo "   กรุณาแก้ไข .env และใส่ OPENROUTER_API_KEY:"
    echo "   nano .env"
fi

# Make start.sh executable
chmod +x start.sh
echo "✅ start.sh พร้อมใช้งาน"

echo ""
echo "================================"
echo "✅ Setup เสร็จแล้ว!"
echo ""
echo "ขั้นตอนต่อไป:"
echo "  1. แก้ไข .env ใส่ OPENROUTER_API_KEY"
echo "  2. รัน: ./start.sh"
echo "  3. เปิดเบราว์เซอร์: http://localhost:5000"
