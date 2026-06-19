"""
Fixtures pytest partagées par toute la suite de tests backend.

Stratégie d'isolation :
- On NE TOUCHE JAMAIS au vrai data/water_consumption_agadir_pfe.csv ni aux
  vrais modèles dans models/. Chaque test utilise un dossier temporaire avec
  un petit dataset synthétique généré à la volée.
- On redirige config.DATA_FILE / config.MODEL_DIR via monkeypatch pour que
  data_service.py et ml_service.py lisent ces fichiers temporaires.
- ds.load_df.cache_clear() est appelé avant/après chaque test car load_df()
  utilise @lru_cache(maxsize=1) — sans ça, le 2e test verrait les données du 1er.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Permet `import config`, `import data_service`, etc. comme le fait main.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


COLUMNS_ORDER = [
    "timestamp", "meterid", "zone", "quartier", "latitude", "longitude",
    "consumptionliters", "flowratelpm", "pressurebar", "temperaturec",
    "rainfall", "hour", "dayofweek", "month", "isweekend", "season",
    "household_size", "event_type", "anomalylabel",
]


def make_synthetic_df(n_days: int = 5, seed: int = 42) -> pd.DataFrame:
    """Génère un dataset 15 minutes minimal mais structurellement identique
    au vrai CSV (mêmes colonnes, mêmes types, mêmes valeurs catégorielles).
    n_days=5 suffit pour calculer lags/rolling(24) et reste très rapide."""
    rng = np.random.default_rng(seed)
    meters = {
        "M001": ("residential", "Talborjt", 30.4255, -9.5975),
        "M002": ("residential", "Talborjt", 30.4230, -9.5945),
        "M003": ("tourist", "Founty Nord", 30.3970, -9.5910),
        "M004": ("industrial", "Anza", 30.4530, -9.6050),
    }
    timestamps = pd.date_range("2025-03-01", periods=96 * n_days, freq="15min")

    rows = []
    for mid, (zone, quartier, lat, lon) in meters.items():
        base = {"residential": 80, "tourist": 150, "industrial": 300}[zone]
        for ts in timestamps:
            factor = 1.5 if 7 <= ts.hour <= 9 or 18 <= ts.hour <= 21 else 1.0
            conso = max(0.0, rng.normal(base * factor, base * 0.2))
            label = "normal"
            pressure = max(0.5, rng.normal(2.5, 0.2))
            if rng.random() < 0.03:
                label = "leak"
                conso *= 3
                pressure = max(0.3, rng.normal(2.0, 0.3))
            elif rng.random() < 0.03:
                label = "anomaly"
                conso *= 2
            rows.append({
                "timestamp": ts, "meterid": mid, "zone": zone, "quartier": quartier,
                "latitude": lat, "longitude": lon,
                "consumptionliters": round(conso, 1),
                "flowratelpm": round(conso / 15, 2),
                "pressurebar": round(pressure, 2),
                "temperaturec": round(rng.normal(21, 4), 1),
                "rainfall": 0.0,
                "hour": ts.hour, "dayofweek": ts.dayofweek, "month": ts.month,
                "isweekend": int(ts.dayofweek >= 5),
                "season": "spring",
                "household_size": int(rng.integers(1, 5)),
                "event_type": "normal",
                "anomalylabel": label,
            })
    df = pd.DataFrame(rows)[COLUMNS_ORDER]
    return df.sort_values(["meterid", "timestamp"]).reset_index(drop=True)


@pytest.fixture
def synthetic_df():
    """Le DataFrame de test brut, sans toucher au disque ni à config."""
    return make_synthetic_df()


@pytest.fixture
def test_env(tmp_path, monkeypatch, synthetic_df):
    """
    Environnement de test complet et isolé :
    - écrit le CSV synthétique dans un dossier temporaire
    - redirige config.DATA_FILE et config.MODEL_DIR vers ce dossier
    - vide le cache de data_service.load_df() avant/après le test

    Retourne (data_dir, model_dir, df) pour que le test puisse, si besoin,
    écrire d'autres fichiers (modèles factices, résultats CSV...).
    """
    import config
    import data_service as ds
    import ml_service as ml

    data_dir = tmp_path / "data"
    model_dir = tmp_path / "models"
    data_dir.mkdir()
    model_dir.mkdir()

    csv_path = data_dir / "water_consumption_agadir_pfe.csv"
    synthetic_df.to_csv(csv_path, index=False)

    # IMPORTANT : data_service.py et ml_service.py font
    # `from config import DATA_FILE, MODEL_DIR` (import PAR VALEUR).
    # Patcher uniquement config.DATA_FILE ne suffit donc pas : il faut aussi
    # patcher la copie locale déjà importée dans chaque module qui l'utilise.
    monkeypatch.setattr(config, "DATA_FILE", csv_path)
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "MODEL_DIR", model_dir)
    monkeypatch.setattr(ds, "DATA_FILE", csv_path)
    monkeypatch.setattr(ml, "MODEL_DIR", model_dir)

    ds.load_df.cache_clear()
    ml.forecast.cache_clear()
    yield data_dir, model_dir, synthetic_df
    ds.load_df.cache_clear()
    ml.forecast.cache_clear()