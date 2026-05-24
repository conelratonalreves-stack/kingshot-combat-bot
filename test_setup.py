#!/usr/bin/env python3
"""
Test script for Kingshot Bot
Verifica que todo esté correctamente configurado antes de ejecutar el bot
"""

import os
import sys
from pathlib import Path

def print_header(text):
    print(f"\n{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}\n")

def check_python_version():
    print_header("Verificando version de Python")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python version: {version}")
    if sys.version_info < (3, 10):
        print("ERROR: Se requiere Python 3.10+")
        return False
    print("OK: Version compatible")
    return True

def check_project_structure():
    print_header("Verificando estructura del proyecto")
    required_files = [
        "main.py",
        "requirements.txt",
        ".env"
    ]
    
    required_dirs = [
        "cogs",
        "models",
        "data",
        "utils"
    ]
    
    all_good = True
    for file in required_files:
        exists = Path(file).exists()
        status = "OK" if exists else "FALTA"
        print(f"  [{status}] {file}")
        if not exists:
            all_good = False
    
    for dir in required_dirs:
        exists = Path(dir).exists()
        status = "OK" if exists else "FALTA"
        print(f"  [{status}] {dir}/")
        if not exists:
            all_good = False
    
    return all_good

def check_env_file():
    print_header("Verificando archivo .env")
    if not Path(".env").exists():
        print("ERROR: Archivo .env no encontrado")
        return False
    
    with open(".env", "r") as f:
        content = f.read()
    
    if "DISCORD_TOKEN" not in content:
        print("ERROR: DISCORD_TOKEN no configurado en .env")
        return False
    
    if content.strip().endswith("="):
        print("ERROR: DISCORD_TOKEN esta vacio")
        return False
    
    print("OK: DISCORD_TOKEN configurado")
    return True

def check_imports():
    print_header("Verificando imports Python")
    
    imports = {
        "discord": "discord.py",
        "dotenv": "python-dotenv",
        "PIL": "Pillow",
        "numpy": "numpy",
        "pytesseract": "pytesseract"
    }
    
    all_good = True
    for module, package in imports.items():
        try:
            __import__(module)
            print(f"  [OK] {package}")
        except ImportError as e:
            print(f"  [ERROR] {package}: {str(e)[:50]}")
            all_good = False
    
    return all_good

def check_model_imports():
    print_header("Verificando modelos locales")
    
    try:
        from models.troop import TroopComposition, TroopStats
        print("  [OK] models.troop")
    except Exception as e:
        print(f"  [ERROR] models.troop: {e}")
        return False
    
    try:
        from models.hero import BattleHeroes, HeroStats
        print("  [OK] models.hero")
    except Exception as e:
        print(f"  [ERROR] models.hero: {e}")
        return False
    
    try:
        from models.battle import BattleCalculator
        print("  [OK] models.battle")
    except Exception as e:
        print(f"  [ERROR] models.battle: {e}")
        return False
    
    try:
        from cogs.commands import BattleCommands
        print("  [OK] cogs.commands")
    except Exception as e:
        print(f"  [ERROR] cogs.commands: {e}")
        return False
    
    return True

def main():
    print("\n" + "="*50)
    print("  KINGSHOT BOT - VERIFICATION TEST")
    print("="*50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Project Structure", check_project_structure),
        ("Environment File", check_env_file),
        ("Python Packages", check_imports),
        ("Model Imports", check_model_imports)
    ]
    
    results = []
    for name, check in checks:
        try:
            result = check()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR en {name}: {e}")
            results.append((name, False))
    
    print_header("Resultado Final")
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {name}")
    
    all_pass = all(result for _, result in results)
    
    if all_pass:
        print("\n" + "="*50)
        print("  [OK] TODO LISTO - BOT LISTO PARA EJECUTAR")
        print("="*50)
        print("\nPara iniciar el bot, ejecuta:")
        print("  python main.py")
        print("\nO si estas en un venv:")
        print("  .venv\\Scripts\\activate     (Windows)")
        print("  source venv/bin/activate  (Linux/Mac)")
        print("  python main.py")
        return 0
    else:
        print("\n" + "="*50)
        print("  [ERROR] FALLOS DETECTADOS - FIX REQUIRED")
        print("="*50)
        return 1

if __name__ == "__main__":
    sys.exit(main())
