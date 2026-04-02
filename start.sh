#!/bin/bash
# ─── AI POC — Startup Script ──────────────────────────────────────────────────
# Usage: ./start.sh
# Starts both Flask backend (port 5000) and Next.js frontend (port 3000)

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# ─── Cleanup on exit ──────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "🛑 กำลังหยุดเซิร์ฟเวอร์..."
    [ -n "$FLASK_PID" ] && kill "$FLASK_PID" 2>/dev/null || true
    [ -n "$NEXTJS_PID" ] && kill "$NEXTJS_PID" 2>/dev/null || true
    wait 2>/dev/null
    echo "✅ หยุดเซิร์ฟเวอร์ทั้งหมดแล้ว"
    exit 0
}
trap cleanup INT TERM

# ─── Check .env ───────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "❌ ไม่พบไฟล์ .env"
    echo "   กรุณา copy .env.example แล้วใส่ API key:"
    echo "   cp .env.example .env && nano .env"
    exit 1
fi

# ─── Check venv ───────────────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "⚙️  สร้าง virtual environment..."
    python3 -m venv venv
fi

# ─── Activate venv ────────────────────────────────────────────────────────────
source venv/bin/activate

# ─── Install backend dependencies ─────────────────────────────────────────────
echo "📦 ตรวจสอบ backend dependencies..."
pip install -q -r requirements.txt

# ─── Install frontend dependencies ────────────────────────────────────────────
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "📦 ตรวจสอบ frontend dependencies..."
    cd frontend
    npm install --silent
    cd "$PROJECT_DIR"
fi

# ─── Create required directories ──────────────────────────────────────────────
mkdir -p workspace temp

# ─── Start servers ────────────────────────────────────────────────────────────
echo ""
echo "🚀 กำลังเริ่ม AI POC servers..."
echo "   Backend:  http://localhost:5000"
echo "   Frontend: http://localhost:3000"
echo "   หยุดด้วย Ctrl+C"
echo ""

export PYTHONIOENCODING=utf-8

# Start Flask backend in background
./venv/bin/gunicorn --config gunicorn.conf.py "app:app" &
FLASK_PID=$!

# Start Next.js frontend in background (if frontend/ exists)
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    npm run dev &
    NEXTJS_PID=$!
    cd "$PROJECT_DIR"
else
    NEXTJS_PID=""
    echo "⚠️  ไม่พบ frontend/ — รันเฉพาะ backend"
fi

# Wait for both processes
wait
