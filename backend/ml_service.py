"""Service ML : chargement des modèles entraînés + prévision + détection.

Robuste : si un modèle est absent ou d'un type inattendu, on retombe sur une
baseline (saisonnier-naïf) au lieu de planter.
"""
import numpy as np
import pandas as pd
import joblib
from functools import lru_cache
from config import MODEL_DIR, COL
import data_service as ds

# ── État chargé au démarrage ────────────────────────────────────────────────
_forecaster = None
_forecaster_kind = "none"
_detector = None
_detector_threshold = None
_detector_features = None
_scaler = None


def _try_load(path):
    try:
        return joblib.load(path)
    except Exception:
        return None


def load_models():
    """Charge le meilleur prévisionniste et le meilleur détecteur.

    Réinitialise explicitement l'état (_forecaster, _detector, ...) avant de
    tenter le chargement : sans ça, un appel ultérieur de load_models() (ex.
    rechargement à chaud, ou tests successifs) garderait en mémoire un modèle
    chargé précédemment même si son fichier .pkl a depuis disparu.
    """
    global _forecaster, _forecaster_kind, _detector, _detector_threshold, _detector_features, _scaler

    _forecaster = None
    _detector = None
    _detector_threshold = None
    _detector_features = None
    _scaler = None
    forecast.cache_clear()  # un nouveau modèle invalide les prévisions déjà en cache

    # --- Prévisionniste ---
    fc = _try_load(MODEL_DIR / "best_forecaster.pkl")
    if fc is not None:
        _forecaster = fc
        mod = type(fc).__module__
        if "statsmodels" in mod:
            _forecaster_kind = "sarima"
        elif "prophet" in mod:
            _forecaster_kind = "prophet"
        elif "xgboost" in mod:
            _forecaster_kind = "xgboost"
        else:
            _forecaster_kind = "other"
    else:
        _forecaster_kind = "naive"  # fallback

    # --- Détecteur (Isolation Forest) + config ---
    det = _try_load(MODEL_DIR / "best_detector.pkl")
    cfg = _try_load(MODEL_DIR / "if_config.pkl") or {}
    if det is not None:
        _detector = det
        _detector_threshold = cfg.get("threshold")
        _detector_features = cfg.get("features", [
            COL["value"], COL["flow"], COL["pressure"], COL["temp"],
            "lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"])
        # Le scaler n'est pas sauvegardé dans le notebook → on le ré-ajuste sur
        # l'historique complet (même distribution que l'entraînement).
        from sklearn.preprocessing import StandardScaler
        # léger : on ajuste le scaler sur les 45 derniers jours (rapide et représentatif)
        feats = _build_detection_features(ds.recent(45 * 24))
        _scaler = StandardScaler().fit(feats[_detector_features].values)

    return status()


def status() -> dict:
    return {
        "forecaster_loaded": _forecaster is not None,
        "forecaster_kind": _forecaster_kind,
        "detector_loaded": _detector is not None,
        "detector_threshold": _detector_threshold,
    }


# ── PRÉVISION ────────────────────────────────────────────────────────────────
@lru_cache(maxsize=16)
def forecast(n_hours: int = 48) -> dict:
    """Prévoit la demande horaire du réseau pour les n_hours prochaines heures.
    Le résultat est mis en cache : seul le tout premier appel fait le calcul."""
    series = ds.hourly_series()
    hist_n = min(len(series), 24 * 7)
    history = [{"timestamp": str(t), "value": round(float(v), 1)}
               for t, v in series.tail(hist_n).items()]

    future_index = pd.date_range(series.index[-1] + pd.Timedelta(hours=1),
                                 periods=n_hours, freq="1h")
    try:
        if _forecaster_kind == "sarima":
            # serving léger : SARIMA compact ré-estimé sur les ~2 dernières semaines
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            recent = series.tail(24 * 14)
            m = SARIMAX(recent, order=(2, 1, 2), seasonal_order=(1, 1, 1, 24),
                        enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
            yhat = np.asarray(m.forecast(steps=n_hours))
        elif _forecaster_kind == "prophet":
            fc = _forecaster.predict(pd.DataFrame({"ds": future_index}))
            yhat = fc["yhat"].values
        else:
            yhat = _seasonal_naive(series, n_hours)
    except Exception:
        yhat = _seasonal_naive(series, n_hours)

    yhat = np.clip(yhat, 0, None)
    forecast = [{"timestamp": str(t), "value": round(float(v), 1)}
                for t, v in zip(future_index, yhat)]
    return {"model": _forecaster_kind, "history": history, "forecast": forecast}


def _seasonal_naive(series: pd.Series, n: int) -> np.ndarray:
    """Baseline : reprend le profil de la même heure la semaine précédente."""
    period = 24 * 7
    vals = series.values
    if len(vals) >= period:
        return np.array([vals[-period + (i % period)] for i in range(n)])
    return np.repeat(vals[-1], n)


# ── DÉTECTION D'ANOMALIES ────────────────────────────────────────────────────
def _build_detection_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.sort_values([COL["meter"], COL["ts"]]).copy()
    grp = d.groupby(COL["meter"])[COL["value"]]
    d["lag_1"] = grp.shift(1)
    d["lag_24"] = grp.shift(24)
    d["roll_mean_24"] = grp.transform(lambda x: x.shift(1).rolling(24, min_periods=1).mean())
    d["roll_std_24"] = grp.transform(lambda x: x.shift(1).rolling(24, min_periods=1).std())
    d["deviation_ratio"] = np.where(d["roll_mean_24"] > 0,
                                    (d[COL["value"]] - d["roll_mean_24"]) / d["roll_mean_24"], 0)
    return d.bfill().fillna(0)


def detect(hours: int = 168) -> dict:
    """Détecte les anomalies sur les `hours` dernières heures (données 15 min)."""
    if _detector is None:
        return {"detector": "none", "points": [], "summary": {}}

    # on récupère un peu plus que la fenêtre demandée pour calculer correctement
    # les lags/rolling, puis on ne garde que la fenêtre voulue.
    window = ds.recent(hours + 24)
    feats = _build_detection_features(window)
    cutoff = feats[COL["ts"]].max() - pd.Timedelta(hours=hours)
    feats = feats[feats[COL["ts"]] >= cutoff].reset_index(drop=True)
    X = _scaler.transform(feats[_detector_features].values)
    score = -_detector.score_samples(X)
    thr = _detector_threshold if _detector_threshold is not None \
        else np.percentile(score, 96)
    is_anom = score >= thr

    points = []
    for (_, row), s, a in zip(feats.iterrows(), score, is_anom):
        if a:  # ne renvoyer que les anomalies détectées (allège la réponse)
            points.append({
                "timestamp": str(row[COL["ts"]]),
                "meterid": row[COL["meter"]],
                "zone": row[COL["zone"]],
                "quartier": row.get(COL["quartier"], None),
                "consumption": round(float(row[COL["value"]]), 1),
                "pressure": round(float(row[COL["pressure"]]), 2),
                "score": round(float(s), 3),
            })
    return {
        "detector": "isolation_forest",
        "threshold": round(float(thr), 3),
        "summary": {
            "window_hours": hours,
            "points_scanned": int(len(feats)),
            "anomalies_detected": int(is_anom.sum()),
            "anomaly_rate_pct": round(float(is_anom.mean() * 100), 2),
        },
        "points": points,
    }


def alerts(hours: int = 168, top: int = 20) -> list[dict]:
    """Alertes = anomalies les plus sévères récentes (pour le tableau de bord)."""
    res = detect(hours)
    pts = sorted(res.get("points", []), key=lambda p: p["score"], reverse=True)[:top]
    for p in pts:
        p["severity"] = "élevée" if p["score"] > (res["threshold"] * 1.3) else "moyenne"
        p["type"] = "fuite potentielle" if p["pressure"] < 3.2 else "consommation anormale"
    return pts


# ── COMPARAISON DES MODÈLES ──────────────────────────────────────────────────
def model_results() -> dict:
    """Lit les tableaux de résultats sauvegardés par les notebooks 02 et 03."""
    out = {"forecasting": [], "detection": []}
    files = {"forecasting": "forecasting_results.csv", "detection": "detection_results.csv"}
    for key, fname in files.items():
        path = MODEL_DIR / fname
        if path.exists():
            df = pd.read_csv(path)
            df = df.rename(columns={df.columns[0]: "model"})
            out[key] = df.round(3).to_dict("records")
    return out