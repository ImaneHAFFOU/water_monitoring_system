"""Accès aux données : chargement CSV + agrégations utilisées par l'API.

Le backend fonctionne directement sur le CSV (aucune base de données requise pour démarrer).
Brancher PostgreSQL/PostGIS plus tard se fait dans database.py sans changer l'API.
"""
import pandas as pd
import numpy as np
from functools import lru_cache
from config import DATA_FILE, COL
from agadir_coords import correct_meter, VERIFIED_COORDS


@lru_cache(maxsize=1)
def load_df() -> pd.DataFrame:
    """Charge le dataset une seule fois (mis en cache)."""
    df = pd.read_csv(DATA_FILE, parse_dates=[COL["ts"]])
    df.columns = df.columns.str.strip().str.lower()
    df = df.sort_values([COL["meter"], COL["ts"]]).reset_index(drop=True)
    return df


def info() -> dict:
    df = load_df()
    return {
        "rows": int(len(df)),
        "meters": int(df[COL["meter"]].nunique()),
        "zones": sorted(df[COL["zone"]].unique().tolist()),
        "period_start": str(df[COL["ts"]].min()),
        "period_end": str(df[COL["ts"]].max()),
    }


def hourly_series() -> pd.Series:
    """Demande horaire agrégée du réseau (somme de tous les compteurs)."""
    df = load_df()
    return df.set_index(COL["ts"])[COL["value"]].resample("1h").sum()


def recent(hours: int = 168) -> pd.DataFrame:
    """Les `hours` dernières heures de données 15 min (tous compteurs)."""
    df = load_df()
    cutoff = df[COL["ts"]].max() - pd.Timedelta(hours=hours)
    return df[df[COL["ts"]] >= cutoff].copy()


def zone_aggregates() -> list[dict]:
    """Statistiques par zone + centroïde géographique (pour la heatmap).
    Le centroïde est calculé à partir des coordonnées CORRIGÉES de chaque
    compteur (pas de la moyenne brute du CSV, qui peut être faussée par des
    points aberrants situés en mer)."""
    df = load_df()
    meters = {m["meterid"]: m for m in meter_geo()}
    out = []
    for zone, g in df.groupby(COL["zone"]):
        zone_meters = [m for m in meters.values() if m["zone"] == zone]
        lat = sum(m["latitude"] for m in zone_meters) / len(zone_meters) if zone_meters else float(g[COL["lat"]].mean())
        lon = sum(m["longitude"] for m in zone_meters) / len(zone_meters) if zone_meters else float(g[COL["lon"]].mean())
        out.append({
            "zone": zone,
            "n_meters": int(g[COL["meter"]].nunique()),
            "mean_consumption": round(float(g[COL["value"]].mean()), 1),
            "total_consumption": round(float(g[COL["value"]].sum()), 0),
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "anomaly_rate": round(float((g[COL["label"]] != "normal").mean() * 100), 2),
        })
    return out


def meter_geo() -> list[dict]:
    """Position et stats de chaque compteur (marqueurs de carte).
    Les coordonnées sont corrigées avec une table vérifiée (sur terre) quand
    le compteur est connu, pour éviter les positions aberrantes (ex. en mer)."""
    df = load_df()
    g = df.groupby(COL["meter"]).agg(
        zone=(COL["zone"], "first"),
        quartier=(COL["quartier"], "first"),
        latitude=(COL["lat"], "first"),
        longitude=(COL["lon"], "first"),
        mean_consumption=(COL["value"], "mean"),
        anomaly_rate=(COL["label"], lambda x: (x != "normal").mean() * 100),
    ).reset_index()
    g["mean_consumption"] = g["mean_consumption"].round(1)
    g["anomaly_rate"] = g["anomaly_rate"].round(2)

    fixed_lat, fixed_lon, fixed_q = [], [], []
    for _, row in g.iterrows():
        lat, lon, q = correct_meter(row[COL["meter"]], row["latitude"], row["longitude"], row["quartier"])
        fixed_lat.append(round(float(lat), 5)); fixed_lon.append(round(float(lon), 5)); fixed_q.append(q)
    g["latitude"], g["longitude"], g["quartier"] = fixed_lat, fixed_lon, fixed_q
    return g.to_dict("records")


def zone_shapes() -> dict:
    """Contours (polygones) des zones, pour affichage sur la carte."""
    from agadir_coords import ZONE_POLYGONS
    return {z: [[lat, lon] for lat, lon in pts] for z, pts in ZONE_POLYGONS.items()}