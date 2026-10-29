import sys
from pathlib import Path

# Permet d'importer optionlab et app depuis backend/ quel que soit le dossier de lancement
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
