#!/bin/bash
# ─── AI POC — WSL First-Time Setup ───────────────────────────────────────────
# Usage: bash setup.sh
# รันครั้งแรกครั้งเดียวเพื่อเตรียม environment บน WSL

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "🔧 AI POC — WSL Setup"
echo "================================"

# ─── 1. System dependencies (WeasyPrint + PDF rendering) ──────────────────────
echo ""
echo "📦 ติดตั้ง system libraries สำหรับ PDF export..."
echo "   (WeasyPrint ต้องการ libpango, libcairo, libharfbuzz, libffi, libjpeg, libopenjp2)"

if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        build-essential \
        python3-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libharfbuzz0b \
        libffi-dev \
        libjpeg-dev \
        libopenjp2-7 \
        libgdk-pixbuf2.0-0 \
        shared-mime-info \
        fonts-thai-tlwg
    echo "✅ ติดตั้ง system libraries สำเร็จ"
else
    echo "⚠️  ไม่พบ apt-get — ข้ามการติดตั้ง system libraries"
    echo "   หากใช้ระบบอื่น ให้ติดตั้งด้วยตนเอง: libpango, libcairo2, libharfbuzz, libffi, libjpeg, libopenjp2"
fi

# ─── 2. Python version check ──────────────────────────────────────────────────
echo ""
PYTHON_VERSION=$(python3 --version 2>&1)
echo "✅ $PYTHON_VERSION"

# ─── 3. Virtual environment ───────────────────────────────────────────────────
if [ -d "venv" ]; then
    echo "✅ venv มีอยู่แล้ว"
else
    echo "⚙️  สร้าง virtual environment..."
    python3 -m venv venv
    echo "✅ สร้าง venv สำเร็จ"
fi

# ─── 4. Python dependencies ───────────────────────────────────────────────────
source venv/bin/activate

echo "📦 อัปเกรด pip..."
pip install --upgrade pip

echo "📦 ติดตั้ง Python dependencies (flask, openai, python-docx, openpyxl, weasyprint, markdown ...)..."
pip install -r requirements.txt
echo "✅ ติดตั้ง Python dependencies สำเร็จ"

# ─── 5. Verify key libraries ──────────────────────────────────────────────────
echo ""
echo "🔍 ตรวจสอบ libraries ที่สำคัญ..."

VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"

check_lib() {
    "$VENV_PYTHON" -c "import $1" 2>/dev/null \
        && echo "   ✅ $1" \
        || echo "   ❌ $1 — ติดตั้งไม่สำเร็จ ตรวจสอบ error ด้านบน"
}

check_lib flask
check_lib openai
check_lib docx
check_lib openpyxl
check_lib weasyprint
check_lib markdown

# ─── 6. Required directories ──────────────────────────────────────────────────
mkdir -p workspace temp data
echo ""
echo "✅ สร้าง workspace/ temp/ data/ แล้ว"

# ─── 7. .env setup ────────────────────────────────────────────────────────────
if [ -f ".env" ]; then
    echo "✅ .env มีอยู่แล้ว"
else
    cp .env.example .env
    echo ""
    echo "⚠️  สร้างไฟล์ .env จาก .env.example แล้ว"
    echo "   กรุณาแก้ไข .env และใส่ OPENROUTER_API_KEY:"
    echo "   nano .env"
fi

# ─── 8. Make start.sh executable ─────────────────────────────────────────────
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
echo "  4. ประวัติงาน:       http://localhost:5000/history"
