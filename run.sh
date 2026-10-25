#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv --system-site-packages venv
fi

. venv/bin/activate

python -m pip install --upgrade pip >/dev/null 2>&1 || true

if [ -f "requirements-pi.txt" ]; then
  python -m pip install -r requirements-pi.txt >/dev/null 2>&1 || true
else
  python -m pip install -r requirements.txt >/dev/null 2>&1 || true
fi

echo "🍓 Starting FreshScan AI 2.0 on Raspberry Pi 5 (USB Camera + Gemini AI Pro) on Port 8000..."
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
