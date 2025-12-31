#!/bin/bash
# Скрипт для запуску нічної обробки всіх НПА
# Використання: ./run_overnight.sh

# Перейти в директорію проекту
cd "$(dirname "$0")/.."

# Активація віртуального середовища (якщо використовується)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Запуск скрипта
python scripts/process_all_npa_overnight.py

