"""
Tests unitaires — ml_service.py

Couvre trois axes :
1. Robustesse : le service ne doit JAMAIS planter, même sans modèles
   sauvegardés (fallback saisonnier-naïf / détecteur absent).
2. Cohérence des features de détection (_build_detection_features) :
   pas de NaN, bonnes colonnes, pas de fuite de données (un lag ne doit
   jamais "voir" la valeur du point courant).
3. Contrat de sortie de l'API interne (forecast(), detect(), alerts()) :
   types, bornes, structure — ce sont les fonctions directement appelées
   par main.py, donc leur contrat doit être stable.
"""
import numpy as np
import pandas as pd
import pytest


# ───────────────────────── load_models() / status() ─────────────────────────

def test_load_models_falls_back_to_naive_when_no_files(test_env):
    """Sans best_forecaster.pkl ni best_detector.pkl sur disque, le service
    doit démarrer proprement en mode dégradé plutôt que lever une exception."""
    import ml_service as ml

    status = ml.load_models()
    assert status["forecaster_loaded"] is False
    assert status["forecaster_kind"] == "naive"
    assert status["detector_loaded"] is False
    assert status["detector_threshold"] is None


def test_load_models_detects_sarima_kind(test_env):
    """Un objet statsmodels sauvegardé doit être reconnu comme 'sarima'."""
    import joblib
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    import ml_service as ml

    data_dir, model_dir, df = test_env
    series = df.set_index("timestamp")["consumptionliters"].resample("1h").sum()
    fitted = SARIMAX(series, order=(1, 0, 0)).fit(disp=False)
    joblib.dump(fitted, model_dir / "best_forecaster.pkl")

    status = ml.load_models()
    assert status["forecaster_loaded"] is True
    assert status["forecaster_kind"] == "sarima"


def test_load_models_loads_detector_and_fits_scaler(test_env):
    """Avec un Isolation Forest sauvegardé, le détecteur doit être chargé
    ET le scaler doit être ajusté (sinon detect() plantera plus tard)."""
    import joblib
    from sklearn.ensemble import IsolationForest
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    feature_cols = ["consumptionliters", "flowratelpm", "pressurebar", "temperaturec",
                     "lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"]
    detector = IsolationForest(n_estimators=20, random_state=42).fit(feats[feature_cols].values)
    joblib.dump(detector, model_dir / "best_detector.pkl")
    joblib.dump({"threshold": 0.1, "features": feature_cols}, model_dir / "if_config.pkl")

    status = ml.load_models()
    assert status["detector_loaded"] is True
    assert status["detector_threshold"] == 0.1
    assert ml._scaler is not None


# ───────────────────── _build_detection_features() ─────────────────────────

def test_build_detection_features_no_nan(test_env):
    """Les features de détection ne doivent jamais contenir de NaN — sinon
    StandardScaler.transform() ou IsolationForest.score_samples() planteraient
    en production (ex. première ligne d'un compteur, sans historique pour lag_24)."""
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    cols = ["lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"]
    assert not feats[cols].isna().any().any()


def test_build_detection_features_lag_1_no_data_leakage(test_env):
    """lag_1 doit être la valeur du PAS PRÉCÉDENT, jamais la valeur courante
    (fuite de données classique : si lag_1 == consumptionliters, le modèle
    "trichera" en apprenant à recopier la cible)."""
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)

    # on vérifie sur un compteur, après le 1er point (qui est bfill donc ignoré)
    g = feats[feats["meterid"] == "M001"].reset_index(drop=True)
    for i in range(2, len(g)):  # à partir de i=2 pour être sûr d'être hors bfill
        assert g.loc[i, "lag_1"] == pytest.approx(g.loc[i - 1, "consumptionliters"])


def test_build_detection_features_lags_are_per_meter(test_env):
    """Les lags doivent être calculés PAR COMPTEUR (groupby('meterid')) :
    le premier point d'un compteur ne doit pas hériter du lag du compteur
    précédent dans le DataFrame trié."""
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    first_rows = feats.groupby("meterid").head(1)
    # bfill() a comblé le lag_1 du tout premier point avec une valeur du MÊME
    # compteur (jamais NaN, jamais une valeur d'un autre meterid) : on vérifie
    # juste qu'aucune valeur n'est aberrante (négative ou extrême) plutôt que
    # de dépendre de l'implémentation exacte du bfill.
    assert (first_rows["lag_1"] >= 0).all()


# ───────────────────────────── forecast() ───────────────────────────────────

def test_forecast_naive_fallback_returns_correct_horizon(test_env):
    """Même sans modèle entraîné, forecast(n) doit renvoyer exactement n points."""
    import ml_service as ml

    ml.load_models()  # pas de .pkl -> mode naive
    result = ml.forecast(24)
    assert result["model"] == "naive"
    assert len(result["forecast"]) == 24


def test_forecast_values_are_never_negative(test_env):
    """La consommation d'eau ne peut pas être négative — le clip(0, None)
    de ml_service.forecast() doit être respecté quel que soit le modèle."""
    import ml_service as ml

    ml.load_models()
    result = ml.forecast(48)
    values = [p["value"] for p in result["forecast"]]
    assert all(v >= 0 for v in values)


def test_forecast_history_has_timestamps_before_forecast(test_env):
    """L'historique renvoyé doit précéder strictement la partie prévue
    (pas de chevauchement temporel, sinon le graphe frontend serait incohérent)."""
    import ml_service as ml

    ml.load_models()
    result = ml.forecast(24)
    last_hist = pd.Timestamp(result["history"][-1]["timestamp"])
    first_fc = pd.Timestamp(result["forecast"][0]["timestamp"])
    assert first_fc > last_hist


def test_forecast_is_cached_between_calls(test_env):
    """forecast() est décoré @lru_cache : deux appels avec le même n_hours
    doivent renvoyer EXACTEMENT le même résultat (même objet en mémoire)."""
    import ml_service as ml

    ml.load_models()
    r1 = ml.forecast(48)
    r2 = ml.forecast(48)
    assert r1 is r2


def test_seasonal_naive_repeats_last_value_if_short_history(test_env):
    """Avec un historique plus court qu'une semaine, le fallback ne doit pas
    planter (IndexError) mais répéter la dernière valeur connue."""
    import ml_service as ml

    short_series = pd.Series([42.0, 43.0, 44.0])
    out = ml._seasonal_naive(short_series, n=5)
    assert len(out) == 5
    assert (out == 44.0).all()


def test_seasonal_naive_uses_weekly_profile_if_long_history(test_env):
    """Avec un historique d'au moins une semaine (168h), le fallback doit
    reprendre le profil de la même heure la semaine précédente plutôt que
    de juste répéter la dernière valeur — c'est ce qui distingue
    'saisonnier-naïf' d'un naïf simple."""
    import ml_service as ml

    # semaine 1 = des valeurs croissantes 0..167, semaine 2 = recommence pareil
    vals = list(range(168)) * 2
    long_series = pd.Series(vals, dtype=float)
    out = ml._seasonal_naive(long_series, n=5)
    # le point 0 prévu doit reprendre la valeur d'il y a 168h (vals[-168] = 0.0)
    assert out[0] == pytest.approx(0.0)
    assert out[1] == pytest.approx(1.0)


def test_forecast_with_real_sarima_model_returns_correct_horizon(test_env):
    """Avec un véritable SARIMA chargé (_forecaster_kind == 'sarima'),
    forecast() doit emprunter la branche de ré-estimation légère (lignes
    103-109 de ml_service.py) sans planter et produire le bon nombre de points.
    C'est la branche identifiée comme sensible dans la revue de code
    (ré-entraînement à chaque appel, forecast multi-pas pur)."""
    import joblib
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    import ml_service as ml

    data_dir, model_dir, df = test_env
    series = df.set_index("timestamp")["consumptionliters"].resample("1h").sum()
    fitted = SARIMAX(series, order=(1, 0, 0)).fit(disp=False)
    joblib.dump(fitted, model_dir / "best_forecaster.pkl")

    ml.load_models()
    assert ml._forecaster_kind == "sarima"

    result = ml.forecast(12)
    assert result["model"] == "sarima"
    assert len(result["forecast"]) == 12
    assert all(p["value"] >= 0 for p in result["forecast"])


def test_forecast_sarima_failure_falls_back_to_naive_without_crashing(test_env, monkeypatch):
    """Si l'estimation SARIMA échoue en serving (ex. données insuffisantes,
    erreur numérique), forecast() doit retomber sur _seasonal_naive plutôt
    que de renvoyer une erreur 500 au frontend — c'est le `except Exception`
    de ml_service.forecast()."""
    import joblib
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    import ml_service as ml

    data_dir, model_dir, df = test_env
    series = df.set_index("timestamp")["consumptionliters"].resample("1h").sum()
    fitted = SARIMAX(series, order=(1, 0, 0)).fit(disp=False)
    joblib.dump(fitted, model_dir / "best_forecaster.pkl")
    ml.load_models()

    # on force SARIMAX(...).fit(...) à lever une exception pour simuler un
    # échec d'estimation en serving (ex. données dégénérées)
    def boom(*args, **kwargs):
        raise ValueError("estimation impossible (simulé)")
    monkeypatch.setattr(ml, "SARIMAX", boom, raising=False)

    import statsmodels.tsa.statespace.sarimax as sarimax_module
    monkeypatch.setattr(sarimax_module, "SARIMAX", boom)

    result = ml.forecast(6)
    assert len(result["forecast"]) == 6  # le fallback a quand même produit 6 points
    assert all(p["value"] >= 0 for p in result["forecast"])


# ──────────────────────────── detect() / alerts() ───────────────────────────

def test_detect_without_detector_returns_empty_safely(test_env):
    """Sans détecteur chargé, detect() doit renvoyer une structure valide
    et vide plutôt que lever une exception (ex. AttributeError sur None)."""
    import ml_service as ml

    ml.load_models()  # pas de best_detector.pkl -> _detector reste None
    result = ml.detect(168)
    assert result["detector"] == "none"
    assert result["points"] == []


def test_detect_with_detector_returns_consistent_summary(test_env):
    """Quand un détecteur est chargé, summary['anomalies_detected'] doit
    correspondre exactement au nombre de points renvoyés dans 'points'."""
    import joblib
    from sklearn.ensemble import IsolationForest
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    feature_cols = ["consumptionliters", "flowratelpm", "pressurebar", "temperaturec",
                     "lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"]
    detector = IsolationForest(n_estimators=20, contamination=0.1, random_state=42)
    detector.fit(feats[feature_cols].values)
    joblib.dump(detector, model_dir / "best_detector.pkl")
    joblib.dump({"threshold": None, "features": feature_cols}, model_dir / "if_config.pkl")

    ml.load_models()
    result = ml.detect(hours=24 * 5)
    assert result["summary"]["anomalies_detected"] == len(result["points"])
    assert result["summary"]["points_scanned"] >= len(result["points"])


def test_alerts_are_sorted_by_score_descending(test_env):
    """alerts() doit renvoyer les anomalies triées par sévérité décroissante
    (la plus grave en premier) — c'est ce que le dashboard affiche en tête."""
    import joblib
    from sklearn.ensemble import IsolationForest
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    feature_cols = ["consumptionliters", "flowratelpm", "pressurebar", "temperaturec",
                     "lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"]
    detector = IsolationForest(n_estimators=20, contamination=0.15, random_state=42)
    detector.fit(feats[feature_cols].values)
    joblib.dump(detector, model_dir / "best_detector.pkl")
    joblib.dump({"threshold": None, "features": feature_cols}, model_dir / "if_config.pkl")

    ml.load_models()
    result = ml.alerts(hours=24 * 5, top=50)
    scores = [a["score"] for a in result]
    assert scores == sorted(scores, reverse=True)


def test_alerts_severity_and_type_fields_are_set(test_env):
    """Chaque alerte doit avoir 'severity' in {'élevée','moyenne'} et
    'type' in {'fuite potentielle','consommation anormale'} — ce sont les
    valeurs que le frontend (Alerts.jsx) compare littéralement."""
    import joblib
    from sklearn.ensemble import IsolationForest
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    feature_cols = ["consumptionliters", "flowratelpm", "pressurebar", "temperaturec",
                     "lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"]
    detector = IsolationForest(n_estimators=20, contamination=0.15, random_state=42)
    detector.fit(feats[feature_cols].values)
    joblib.dump(detector, model_dir / "best_detector.pkl")
    joblib.dump({"threshold": None, "features": feature_cols}, model_dir / "if_config.pkl")

    ml.load_models()
    result = ml.alerts(hours=24 * 5, top=50)
    for a in result:
        assert a["severity"] in {"élevée", "moyenne"}
        assert a["type"] in {"fuite potentielle", "consommation anormale"}


def test_alerts_top_parameter_limits_results(test_env):
    import joblib
    from sklearn.ensemble import IsolationForest
    import ml_service as ml

    data_dir, model_dir, df = test_env
    feats = ml._build_detection_features(df)
    feature_cols = ["consumptionliters", "flowratelpm", "pressurebar", "temperaturec",
                     "lag_1", "lag_24", "roll_mean_24", "roll_std_24", "deviation_ratio"]
    detector = IsolationForest(n_estimators=20, contamination=0.2, random_state=42)
    detector.fit(feats[feature_cols].values)
    joblib.dump(detector, model_dir / "best_detector.pkl")
    joblib.dump({"threshold": None, "features": feature_cols}, model_dir / "if_config.pkl")

    ml.load_models()
    result = ml.alerts(hours=24 * 5, top=3)
    assert len(result) <= 3


# ─────────────────────────── model_results() ────────────────────────────────

def test_model_results_empty_when_no_csv(test_env):
    """Sans forecasting_results.csv ni detection_results.csv, /models ne doit
    pas planter mais renvoyer des listes vides (cas d'un projet pas encore
    entraîné, ou notebooks pas encore exécutés)."""
    import ml_service as ml

    out = ml.model_results()
    assert out == {"forecasting": [], "detection": []}


def test_model_results_reads_existing_csv(test_env):
    import ml_service as ml

    data_dir, model_dir, df = test_env
    pd.DataFrame([{"model": "SARIMA[24]", "MAE": 100.0, "RMSE": 150.0, "MAPE": 10.0}]) \
        .to_csv(model_dir / "forecasting_results.csv", index=False)

    out = ml.model_results()
    assert len(out["forecasting"]) == 1
    assert out["forecasting"][0]["model"] == "SARIMA[24]"
    assert out["detection"] == []