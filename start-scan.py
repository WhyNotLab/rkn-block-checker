"""
Быстрый запуск RKN Block Checker.
Использование: python start-scan.py [--white] [--black] [--json]
"""
import sys
import io

# Принудительно UTF-8 для Windows-терминалов (cp1252/cp866)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rkn_checker.cli import main

sys.exit(main(sys.argv[1:]))
