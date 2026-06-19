"""
Tests unitaires — data_service.py

Couvre : chargement du CSV, agrégations par zone, géolocalisation des
compteurs, et la correction des coordonnées GPS (agadir_coords.py).
"""
import pandas as pd
import pytest


def test_load_df_returns_expected_shape_and_columns(test_env):
    """Le CSV est chargé avec les bonnes colonnes et sans perte de lignes."""
    import data_service as ds

    df = ds.load_df()
    assert len(df) == 4 * 96 * 5  # 4 compteurs * 96 pts/jour * 5 jours
    assert "timestamp" in df.columns
    assert "consumptionliters" in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])


def test_load_df_is_cached(test_env):
    """load_df() est décoré @lru_cache : deux appels renvoient le même objet."""
    import data_service as ds

    df1 = ds.load_df()
    df2 = ds.load_df()
    assert df1 is df2


def test_load_df_sorted_by_meter_then_time(test_env):
    """Les données doivent être triées (meterid, timestamp) — précondition
    indispensable pour que les lags/rolling calculés ailleurs soient corrects."""
    import data_service as ds

    df = ds.load_df()
    for mid, g in df.groupby("meterid"):
        assert g["timestamp"].is_monotonic_increasing


def test_info_matches_dataset(test_env):
    """info() doit refléter fidèlement le dataset chargé (pas de valeurs en dur)."""
    import data_service as ds

    data_dir, model_dir, raw_df = test_env
    info = ds.info()
    assert info["rows"] == len(raw_df)
    assert info["meters"] == raw_df["meterid"].nunique()
    assert set(info["zones"]) == set(raw_df["zone"].unique())


def test_hourly_series_aggregates_all_meters(test_env):
    """hourly_series() doit sommer TOUS les compteurs par heure, pas seulement
    un sous-ensemble (sinon la demande réseau prédite serait sous-estimée)."""
    import data_service as ds

    series = ds.hourly_series()
    raw_total = ds.load_df()["consumptionliters"].sum()
    assert series.sum() == pytest.approx(raw_total, rel=1e-6)


def test_hourly_series_is_hourly_indexed(test_env):
    import data_service as ds

    series = ds.hourly_series()
    diffs = series.index.to_series().diff().dropna().unique()
    assert len(diffs) == 1
    assert diffs[0] == pd.Timedelta(hours=1)


def test_recent_respects_window(test_env):
    """recent(hours) ne doit retourner que les données dans la fenêtre demandée."""
    import data_service as ds

    df = ds.load_df()
    window = ds.recent(hours=24)
    cutoff = df["timestamp"].max() - pd.Timedelta(hours=24)
    assert (window["timestamp"] >= cutoff).all()
    assert len(window) < len(df)  # la fenêtre est bien un sous-ensemble


def test_recent_full_window_returns_everything(test_env):
    """Avec une fenêtre plus grande que tout l'historique, on récupère tout."""
    import data_service as ds

    df = ds.load_df()
    window = ds.recent(hours=24 * 365)
    assert len(window) == len(df)


def test_zone_aggregates_n_meters_sums_to_total(test_env):
    """La somme des n_meters par zone doit égaler le nombre total de compteurs
    (sinon un compteur serait compté deux fois ou oublié)."""
    import data_service as ds

    df = ds.load_df()
    zones = ds.zone_aggregates()
    total_meters_in_zones = sum(z["n_meters"] for z in zones)
    assert total_meters_in_zones == df["meterid"].nunique()


def test_zone_aggregates_anomaly_rate_between_0_and_100(test_env):
    import data_service as ds

    for z in ds.zone_aggregates():
        assert 0.0 <= z["anomaly_rate"] <= 100.0


def test_meter_geo_returns_one_row_per_meter(test_env):
    import data_service as ds

    df = ds.load_df()
    meters = ds.meter_geo()
    assert len(meters) == df["meterid"].nunique()
    assert {m["meterid"] for m in meters} == set(df["meterid"].unique())


def test_meter_geo_uses_verified_coordinates(test_env):
    """Les coordonnées exposées par l'API doivent être celles de la table
    VERIFIED_COORDS (sur terre), pas les coordonnées brutes du CSV — c'est
    le but même de agadir_coords.correct_meter()."""
    import data_service as ds
    from agadir_coords import VERIFIED_COORDS

    meters = {m["meterid"]: m for m in ds.meter_geo()}
    for mid, (vlat, vlon, vquartier) in VERIFIED_COORDS.items():
        if mid in meters:
            assert meters[mid]["latitude"] == pytest.approx(vlat, abs=1e-4)
            assert meters[mid]["longitude"] == pytest.approx(vlon, abs=1e-4)


def test_zone_shapes_returns_known_zones(test_env):
    import data_service as ds

    shapes = ds.zone_shapes()
    assert set(shapes.keys()) == {"residential", "tourist", "industrial"}
    for zone, polygon in shapes.items():
        assert len(polygon) >= 3  # un polygone valide a au moins 3 points
        for point in polygon:
            assert len(point) == 2  # [lat, lon]