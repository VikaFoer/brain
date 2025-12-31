"""
Python скрипт для автоматичного завантаження на GitHub
"""
import os
import subprocess
import sys
from pathlib import Path

# Налаштування кодування для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def find_git():
    """Знайти git в системі"""
    possible_paths = [
        "git",  # В PATH
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Programs\Git\cmd\git.exe"),
    ]
    
    # Перевірити GitHub Desktop
    local_appdata = os.environ.get('LOCALAPPDATA', '')
    if local_appdata:
        github_desktop = Path(local_appdata) / "GitHubDesktop"
        if github_desktop.exists():
            for app_dir in github_desktop.glob("app-*"):
                git_path = app_dir / "resources" / "app" / "git" / "cmd" / "git.exe"
                if git_path.exists():
                    possible_paths.append(str(git_path))
    
    for git_path in possible_paths:
        try:
            result = subprocess.run(
                [git_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ Знайдено Git: {git_path}")
                return git_path
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            continue
    
    return None

def run_git(git_exe, *args):
    """Виконати git команду"""
    try:
        result = subprocess.run(
            [git_exe] + list(args),
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(f"⚠️  {result.stderr}", file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Помилка: {e}", file=sys.stderr)
        return False

def main():
    print("🔍 Пошук Git...")
    git_exe = find_git()
    
    if not git_exe:
        print("❌ Git не знайдено!")
        print("\n📥 Будь ласка, встановіть Git:")
        print("   https://git-scm.com/download/win")
        print("\nАбо використайте GitHub Desktop:")
        print("   https://desktop.github.com/")
        return False
    
    print("\n🚀 Початок завантаження на GitHub...\n")
    
    # Перевірити чи ініціалізовано репозиторій
    if not Path(".git").exists():
        print("📦 Ініціалізація git репозиторію...")
        if not run_git(git_exe, "init"):
            return False
    
    # Перевірити remote
    result = subprocess.run(
        [git_exe, "remote", "get-url", "origin"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("🔗 Додавання remote репозиторію...")
        if not run_git(git_exe, "remote", "add", "origin", "https://github.com/VikaFoer/brain.git"):
            print("⚠️  Remote вже може існувати, продовжую...")
    else:
        print(f"✅ Remote вже налаштовано: {result.stdout.strip()}")
    
    # Додати файли
    print("\n📝 Додавання файлів...")
    if not run_git(git_exe, "add", "."):
        return False
    
    # Перевірити чи є зміни
    result = subprocess.run(
        [git_exe, "status", "--porcelain"],
        capture_output=True,
        text=True
    )
    
    if not result.stdout.strip():
        print("ℹ️  Немає змін для commit")
        # Спробувати pull якщо репозиторій вже існує
        print("📥 Спробую отримати зміни з GitHub...")
        run_git(git_exe, "pull", "origin", "main", "--allow-unrelated-histories")
        return True
    
    # Створити commit
    print("\n💾 Створення commit...")
    commit_message = """Initial commit: Legal Graph System - система аналізу нормативно-правових актів

- Backend на FastAPI з підтримкою PostgreSQL та Neo4j
- Frontend з візуалізацією графів (D3.js)
- Інтеграція з API Ради України
- Виділення елементів множини через OpenAI
- GraphRAG для аналізу зв'язків
- Чат-аналітика з OpenAI"""
    
    if not run_git(git_exe, "commit", "-m", commit_message):
        return False
    
    # Встановити гілку main
    print("\n🌿 Встановлення гілки main...")
    run_git(git_exe, "branch", "-M", "main")
    
    # Push
    print("\n📤 Завантаження на GitHub...")
    print("⚠️  Може знадобитися автентифікація (Personal Access Token)")
    if run_git(git_exe, "push", "-u", "origin", "main"):
        print("\n✅ Успішно завантажено на GitHub!")
        print("📚 Репозиторій: https://github.com/VikaFoer/brain")
        return True
    else:
        print("\n⚠️  Помилка при завантаженні.")
        print("Можливі причини:")
        print("1. Потрібна автентифікація (Personal Access Token)")
        print("2. Репозиторій вже існує і має інші файли")
        print("\nСпробуйте:")
        print("  git pull origin main --allow-unrelated-histories")
        print("  git push -u origin main")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
