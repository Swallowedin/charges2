import os
import sys

# Ajouter le répertoire courant au chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importer et exécuter la fonction main
from app import main

if __name__ == "__main__":
    main()
