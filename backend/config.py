"""Configuration centrale du backend."""
from pathlib import Path

# Racine du projet (../ par rapport à backend/)
BASE_DIR  = Path(__file__).resolve().parent.parent
DATA_DIR  = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

# Fichier de données principal (sortie de l'EDA)
DATA_FILE = DATA_DIR / "water_consumption_agadir_pfe.csv"

# Noms de colonnes (alignés sur les notebooks)
COL = dict(
    ts="timestamp", meter="meterid", zone="zone", quartier="quartier",
    lat="latitude", lon="longitude", value="consumptionliters",
    flow="flowratelpm", pressure="pressurebar", temp="temperaturec",
    label="anomalylabel",
)

# Base de données (optionnelle — le backend marche sans Postgres, sur CSV).
USE_DATABASE = False
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/agadir_eau"

# CORS : autoriser le frontend React (Vite = 5173, CRA = 3000)
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "*"]