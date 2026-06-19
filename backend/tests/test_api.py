"""
Tests d'intégration — API FastAPI (main.py)

Utilise le TestClient de FastAPI : démarre vraiment l'application (y compris
l'événement @app.on_event("startup")) sur l'environnement de test isolé fourni
par la fixture test_env, puis exerce chaque endpoint comme le ferait le
frontend React.
"""
import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(test_env):
    """Un TestClient connecté à l'app, avec les modèles déjà rechargés sur
    l'environnement de test isolé. Le `with` déclenche les events
    startup/shutdown de FastAPI."""
    import ml_service as ml
    import data_service as ds

    ds.load_df.cache_clear()
    ml.forecast.cache_clear()

    from main import app
    with TestClient(app) as c:
        yield c


# ───────────────────────────────── /, /health ────────────────────────────────

def test_root_returns_welcome_message(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_health_status_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "data" in body and "models" in body


def test_health_matches_schema_fields(client):
    """Vérifie que /health respecte bien HealthResponse (champs attendus
    par le frontend Dashboard.jsx : health.data.meters, period_start, etc.)"""
    body = client.get("/health").json()
    assert "meters" in body["data"]
    assert "period_start" in body["data"]
    assert "period_end" in body["data"]
    assert "forecaster_kind" in body["models"]


# ───────────────────────────────── /predict ──────────────────────────────────

def test_predict_default_horizon(client):
    r = client.get("/predict")
    assert r.status_code == 200
    body = r.json()
    assert len(body["forecast"]) == 48  # valeur par défaut de Query(48, ...)


def test_predict_custom_horizon(client):
    r = client.get("/predict", params={"hours": 72})
    assert r.status_code == 200
    assert len(r.json()["forecast"]) == 72


def test_predict_rejects_horizon_above_max(client):
    """La borne le=336 du Query doit être appliquée : FastAPI doit renvoyer
    422 (Unprocessable Entity) plutôt que de planter ou tronquer en silence."""
    r = client.get("/predict", params={"hours": 1000})
    assert r.status_code == 422


def test_predict_rejects_horizon_below_min(client):
    r = client.get("/predict", params={"hours": 0})
    assert r.status_code == 422


def test_predict_forecast_values_are_non_negative(client):
    body = client.get("/predict", params={"hours": 48}).json()
    assert all(p["value"] >= 0 for p in body["forecast"])


def test_predict_response_matches_forecast_schema(client):
    """Chaque point doit avoir exactement 'timestamp' (str) et 'value' (float),
    comme défini dans schemas.Point — sinon le frontend recharts plante."""
    body = client.get("/predict", params={"hours": 24}).json()
    for p in body["forecast"] + body["history"]:
        assert isinstance(p["timestamp"], str)
        assert isinstance(p["value"], (int, float))


# ───────────────────────────────── /anomalies ────────────────────────────────

def test_anomalies_default_window(client):
    r = client.get("/anomalies")
    assert r.status_code == 200
    assert "summary" in r.json()


def test_anomalies_rejects_window_above_max(client):
    r = client.get("/anomalies", params={"hours": 10000})
    assert r.status_code == 422


def test_anomalies_without_detector_returns_empty_list(client):
    """Sur l'environnement de test, aucun best_detector.pkl n'existe par
    défaut (sauf si le test l'ajoute) : l'API doit rester disponible."""
    body = client.get("/anomalies").json()
    assert body["points"] == []


# ───────────────────────────────── /alerts ───────────────────────────────────

def test_alerts_returns_list(client):
    r = client.get("/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_alerts_top_parameter_is_respected(client):
    r = client.get("/alerts", params={"top": 5})
    assert r.status_code == 200
    assert len(r.json()) <= 5


def test_alerts_rejects_top_above_max(client):
    r = client.get("/alerts", params={"top": 1000})
    assert r.status_code == 422


def test_alerts_with_real_detector_matches_alert_schema(test_env):
    """Avec un détecteur réellement entraîné, chaque alerte renvoyée doit
    respecter exactement schemas.Alert (les champs lus par Alerts.jsx /
    MapView.jsx côté frontend : meterid, zone, pressure, score, severity, type)."""
    import ml_service as ml
    import data_service as ds
    from sklearn.ensemble import IsolationForest

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    feature_cols = ["consumptionliters", "flowratelpm", "pressurebar", "temperaturec",
                     "lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"]
    detector = IsolationForest(n_estimators=20, contamination=0.15, random_state=42)
    detector.fit(feats[feature_cols].values)
    joblib.dump(detector, model_dir / "best_detector.pkl")
    joblib.dump({"threshold": None, "features": feature_cols}, model_dir / "if_config.pkl")

    ds.load_df.cache_clear()
    ml.forecast.cache_clear()
    from main import app
    with TestClient(app) as client:
        r = client.get("/alerts", params={"hours": 24 * 5, "top": 50})
        assert r.status_code == 200
        for alert in r.json():
            assert set(alert.keys()) >= {
                "timestamp", "meterid", "zone", "consumption",
                "pressure", "score", "severity", "type",
            }


# ───────────────────────────────── /zones, /meters ───────────────────────────

def test_zones_returns_one_entry_per_zone(client):
    body = client.get("/zones").json()
    assert {z["zone"] for z in body} == {"residential", "tourist", "industrial"}


def test_zone_shapes_returns_polygons(client):
    body = client.get("/zone-shapes").json()
    assert set(body.keys()) == {"residential", "tourist", "industrial"}


def test_meters_returns_geo_data(client):
    body = client.get("/meters").json()
    assert len(body) == 4  # 4 compteurs dans le dataset synthétique
    for m in body:
        assert -90 <= m["latitude"] <= 90
        assert -180 <= m["longitude"] <= 180


def test_meters_matches_meter_geo_schema(client):
    body = client.get("/meters").json()
    for m in body:
        assert set(m.keys()) >= {
            "meterid", "zone", "latitude", "longitude",
            "mean_consumption", "anomaly_rate",
        }


# ───────────────────────────────── /models ───────────────────────────────────

def test_models_empty_when_no_results_csv(client):
    body = client.get("/models").json()
    assert body == {"forecasting": [], "detection": []}


def test_models_returns_csv_content(test_env):
    import ml_service as ml
    import data_service as ds

    data_dir, model_dir, df = test_env
    pd.DataFrame([{"model": "SARIMA[24]", "MAE": 100.0, "RMSE": 150.0, "MAPE": 10.0}]) \
        .to_csv(model_dir / "forecasting_results.csv", index=False)

    ds.load_df.cache_clear()
    ml.forecast.cache_clear()
    from main import app
    with TestClient(app) as client:
        body = client.get("/models").json()
        assert len(body["forecasting"]) == 1
        assert body["forecasting"][0]["model"] == "SARIMA[24]"