import os
import sys
from pathlib import Path

# Permet d'importer optionlab et app depuis backend/ quel que soit le dossier de lancement
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Les tests n'écrivent jamais dans la vraie base : SQLite en mémoire
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
