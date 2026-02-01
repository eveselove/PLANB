#!/bin/bash
# Запуск дашборда План 2026

cd "$(dirname "$0")"

echo "🚀 Запуск дашборда..."
echo "📊 Откройте в браузере: http://localhost:8501"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

streamlit run app.py --server.port 8501 --server.headless true
