"""API FastAPI — Système intelligent de surveillance de l'eau (Grand Agadir).

Lancer :  cd backend && uvicorn main:app --reload
Docs interactives :  http://localhost:8000/docs
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

import data_service as ds
import ml_service as ml
from config import CORS_ORIGINS
from schemas import HealthResponse, ForecastResponse, ZoneStat, MeterGeo, Alert

app = FastAPI(
    title="API — Surveillance Intelligente de l'Eau (Grand Agadir)",
    description="Prévision de la consommation et détection des fuites par IA.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    ds.load_df()        # met le dataset en cache
    ml.load_models()    # charge prévisionniste + détecteur
    try:
        ml.forecast(48)   # pré-calcule la prévision (cache) → 1re requête instantanée
    except Exception:
        pass
    print("🚀 API prête :", ml.status())


@app.get("/", tags=["meta"])
def root():
    return {"message": "API Surveillance Eau Agadir", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health():
    return {"status": "ok", "data": ds.info(), "models": ml.status()}


@app.get("/predict", response_model=ForecastResponse, tags=["prévision"])
def predict(hours: int = Query(48, ge=1, le=336, description="Horizon de prévision (h)")):
    """Prévoit la demande horaire du réseau pour les `hours` prochaines heures."""
    return ml.forecast(hours)


@app.get("/anomalies", tags=["détection"])
def anomalies(hours: int = Query(168, ge=1, le=720, description="Fenêtre d'analyse (h)")):
    """Détecte les anomalies/fuites sur la fenêtre récente."""
    return ml.detect(hours)


@app.get("/alerts", response_model=list[Alert], tags=["détection"])
def get_alerts(hours: int = Query(168, ge=1, le=720), top: int = Query(20, ge=1, le=100)):
    """Liste des alertes les plus sévères (pour le tableau de bord)."""
    return ml.alerts(hours, top)


@app.get("/zones", response_model=list[ZoneStat], tags=["géographie"])
def zones():
    """Statistiques agrégées par zone (heatmap)."""
    return ds.zone_aggregates()


@app.get("/zone-shapes", tags=["géographie"])
def zone_shapes():
    """Contours (polygones) des zones du Grand Agadir, pour affichage sur la carte."""
    return ds.zone_shapes()


@app.get("/meters", response_model=list[MeterGeo], tags=["géographie"])
def meters():
    """Position et statistiques de chaque compteur (marqueurs de carte)."""
    return ds.meter_geo()


@app.get("/models", tags=["modèles"])
def models_compare():
    """Tableaux comparatifs des modèles (lus depuis les résultats des notebooks 02 et 03)."""
    return ml.model_results()