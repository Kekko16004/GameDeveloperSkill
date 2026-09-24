#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameDeveloperSkill - Sistema di Verifica Completo
Controlla tutti i componenti, percorsi, moduli e configurazioni
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Fix encoding per Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Colori per output (disabilitati su Windows per compatibilità)
USE_COLORS = sys.platform != 'win32'

class Colors:
    GREEN = '\033[92m' if USE_COLORS else ''
    RED = '\033[91m' if USE_COLORS else ''
    YELLOW = '\033[93m' if USE_COLORS else ''
    BLUE = '\033[94m' if USE_COLORS else ''
    CYAN = '\033[96m' if USE_COLORS else ''
    BOLD = '\033[1m' if USE_COLORS else ''
    END = '\033[0m' if USE_COLORS else ''

def print_header(text: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text:^60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.END}\n")

def print_ok(text: str):
    print(f"{Colors.GREEN}[OK]{Colors.END} {text}")

def print_error(text: str):
    print(f"{Colors.RED}[ERR]{Colors.END} {text}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {text}")

def print_info(text: str):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {text}")

def check_file_exists(path: Path, description: str) -> bool:
    """Controlla se un file esiste"""
    if path.exists():
        print_ok(f"{description}: {path}")
        return True
    else:
        print_error(f"{description} MANCANTE: {path}")
        return False

def check_directory_exists(path: Path, description: str) -> bool:
    """Controlla se una directory esiste"""
    if path.exists() and path.is_dir():
        count = len(list(path.rglob('*')))
        print_ok(f"{description}: {path} ({count} files)")
        return True
    else:
        print_error(f"{description} MANCANTE: {path}")
        return False

def check_config() -> Tuple[bool, Dict]:
    """Verifica configurazione principale"""
    print_header("CONFIGURAZIONE")

    config_path = Path("game-developer/config.json")
    defaults_path = Path("game-developer/config/defaults.json")

    if not config_path.exists():
        print_warning("config.json non trovato, uso defaults.json")
        config_path = defaults_path

    if not config_path.exists():
        print_error("Nessun file di configurazione trovato!")
        return False, {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print_ok(f"Config caricato: v{config.get('version', '?')}")
        return True, config
    except Exception as e:
        print_error(f"Errore nel leggere config: {e}")
        return False, {}

def check_structure() -> int:
    """Verifica struttura directories"""
    print_header("STRUTTURA DIRECTORIES")

    required_dirs = [
        ("game-developer", "Root principale"),
        ("game-developer/core", "Core modules"),
        ("game-developer/engines", "Engine integrations"),
        ("game-developer/modules", "Skill modules"),
        ("game-developer/templates", "Templates"),
        ("game-developer/tools", "Tools & utilities"),
        ("game-developer/config", "Configurazioni"),
        ("game-developer/scripts", "Scripts automazione"),
    ]

    score = 0
    for dir_path, description in required_dirs:
        if check_directory_exists(Path(dir_path), description):
            score += 1

    return score

def check_core_files() -> int:
    """Verifica file core essenziali"""
    print_header("FILE CORE")

    core_files = [
        ("game-developer/config.json", "Configurazione principale"),
        ("game-developer/config/defaults.json", "Defaults"),
        ("README.md", "Documentazione principale"),
        ("QUICK_START.md", "Quick start guide"),
    ]

    score = 0
    for file_path, description in core_files:
        if check_file_exists(Path(file_path), description):
            score += 1

    return score

def check_modules(config: Dict) -> int:
    """Verifica moduli abilitati"""
    print_header("MODULI ABILITATI")

    modules = config.get("modules", {})
    enabled = [k for k, v in modules.items() if v]
    disabled = [k for k, v in modules.items() if not v]

    print_info(f"Moduli attivi: {len(enabled)}/{len(modules)}")

    for module in enabled:
        print_ok(f"  {module}")

    if disabled:
        print_info(f"\nModuli disabilitati: {len(disabled)}")
        for module in disabled:
            print_warning(f"  {module}")

    return len(enabled)

def check_paths(config: Dict) -> int:
    """Verifica percorsi configurati"""
    print_header("PERCORSI CONFIGURATI")

    paths = config.get("paths", {})
    valid = 0

    for key, path_str in paths.items():
        if not path_str or path_str == "":
            print_warning(f"{key}: NON CONFIGURATO")
        else:
            path = Path(path_str)
            if path.exists():
                print_ok(f"{key}: {path_str}")
                valid += 1
            else:
                print_error(f"{key}: PATH INVALIDO - {path_str}")

    return valid

def check_dashboard() -> bool:
    """Verifica la console al posto della vecchia dashboard web."""
    print_header("CONSOLE")

    dashboard_files = [
        Path("game-developer/tools/tui/gds_tui.py"),
        Path("start-dashboard.bat"),
        Path("start-dashboard.ps1"),
    ]

    all_ok = True
    for file in dashboard_files:
        if not check_file_exists(file, file.name):
            all_ok = False

    return all_ok

def check_scripts() -> int:
    """Verifica scripts disponibili"""
    print_header("SCRIPTS AUTOMAZIONE")

    scripts_dir = Path("game-developer/scripts")
    if not scripts_dir.exists():
        print_error("Directory scripts non trovata!")
        return 0

    scripts = list(scripts_dir.glob("*.ps1")) + list(scripts_dir.glob("*.py"))

    print_info(f"Scripts trovati: {len(scripts)}")
    for script in sorted(scripts):
        print_ok(f"  {script.name}")

    return len(scripts)

def check_templates() -> int:
    """Verifica templates disponibili"""
    print_header("TEMPLATES")

    templates_dir = Path("game-developer/templates")
    if not templates_dir.exists():
        print_error("Directory templates non trovata!")
        return 0

    # Conta subdirectories
    subdirs = [d for d in templates_dir.iterdir() if d.is_dir()]

    print_info(f"Categorie template: {len(subdirs)}")
    for subdir in sorted(subdirs):
        files = list(subdir.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        print_ok(f"  {subdir.name}: {file_count} files")

    return len(subdirs)

def check_engines(config: Dict) -> bool:
    """Verifica configurazione engine"""
    print_header("ENGINE CONFIGURATION")

    engines = config.get("engines", {})
    unity = config.get("unity", {})

    print_info(f"Engine default: {engines.get('default', 'unity')}")
    print_info(f"Godot abilitato: {engines.get('godotEnabled', False)}")

    if unity:
        packages = unity.get("packages", [])
        print_ok(f"Unity packages configurati: {len(packages)}")
        for pkg in packages[:5]:  # Primi 5
            print(f"    • {pkg}")
        if len(packages) > 5:
            print(f"    ... e altri {len(packages) - 5}")

    return True

def generate_report(results: Dict):
    """Genera report finale"""
    print_header("REPORT FINALE")

    total_score = sum([
        results['structure'],
        results['core_files'],
        results['modules'],
        results['paths'],
        results['scripts'],
        results['templates'],
        (10 if results['dashboard'] else 0),
        (5 if results['engines'] else 0),
    ])

    max_score = 100  # Punteggio massimo stimato
    percentage = (total_score / max_score) * 100

    print(f"\n{Colors.BOLD}Punteggio Totale: {total_score}/{max_score} ({percentage:.1f}%){Colors.END}\n")

    # Status per categoria
    print("Dettaglio:")
    print(f"  Struttura directories: {results['structure']}")
    print(f"  File core: {results['core_files']}")
    print(f"  Moduli attivi: {results['modules']}")
    print(f"  Percorsi validi: {results['paths']}")
    print(f"  Scripts: {results['scripts']}")
    print(f"  Template categories: {results['templates']}")
    print(f"  Console: {'✓ OK' if results['dashboard'] else '✗ MANCANTE'}")
    print(f"  Engine config: {'✓ OK' if results['engines'] else '✗ PROBLEMI'}")

    # Valutazione finale
    print()
    if percentage >= 90:
        print(f"{Colors.GREEN}{Colors.BOLD}[OK] SKILL OTTIMA - Tutto funzionante!{Colors.END}")
    elif percentage >= 70:
        print(f"{Colors.YELLOW}{Colors.BOLD}[WARN] SKILL BUONA - Alcuni componenti mancanti{Colors.END}")
    elif percentage >= 50:
        print(f"{Colors.YELLOW}{Colors.BOLD}[WARN] SKILL FUNZIONANTE - Richiede configurazione{Colors.END}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}[ERR] SKILL INCOMPLETA - Richiede setup{Colors.END}")

    print()

def main():
    """Main check routine"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 60)
    print("   GameDeveloperSkill - Sistema di Verifica v2.0")
    print("=" * 60)
    print(f"{Colors.END}")

    # Esegui tutti i check
    results = {}

    config_ok, config = check_config()
    results['config'] = config_ok

    results['structure'] = check_structure()
    results['core_files'] = check_core_files()

    if config:
        results['modules'] = check_modules(config)
        results['paths'] = check_paths(config)
        results['engines'] = check_engines(config)
    else:
        results['modules'] = 0
        results['paths'] = 0
        results['engines'] = False

    results['dashboard'] = check_dashboard()
    results['scripts'] = check_scripts()
    results['templates'] = check_templates()

    # Report finale
    generate_report(results)

    # Suggerimenti
    print_header("PROSSIMI PASSI")

    if not results['dashboard']:
        print_info("1. Manca la console: game-developer/tools/tui/gds_tui.py")
    else:
        print_ok("1. Console pronta - avviala con: start-dashboard.bat")

    if results['paths'] < 3:
        print_info("2. I percorsi si leggono in config.json (la console non li gestisce tutti)")
    else:
        print_ok("2. Percorsi configurati correttamente")

    if results['modules'] < 5:
        print_info("3. Abilita i moduli che ti servono")
    else:
        print_ok("3. Moduli attivi e funzionanti")

    print()
    print(f"{Colors.BOLD}Per ulteriori info: README.md e QUICK_START.md{Colors.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Verifica interrotta dall'utente{Colors.END}\n")
    except Exception as e:
        print(f"\n{Colors.RED}Errore durante la verifica: {e}{Colors.END}\n")
