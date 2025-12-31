# PowerShell скрипт для запуску нічної обробки всіх НПА
# Використання: .\run_overnight.ps1

# Перейти в директорію проекту
Set-Location $PSScriptRoot\..

# Активація віртуального середовища (якщо використовується)
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
}

# Запуск скрипта
python scripts\process_all_npa_overnight.py

