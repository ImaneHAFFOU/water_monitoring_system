"""
Tests unitaires — agadir_coords.py

Ce module n'a aucune dépendance externe (pas de CSV, pas de config) :
les tests sont donc de purs tests unitaires, sans fixture test_env.
"""
from agadir_coords import correct_meter, VERIFIED_COORDS, ZONE_POLYGONS


def test_known_meter_returns_verified_coordinates():
    """Pour un compteur connu, on doit récupérer les coordonnées VÉRIFIÉES,
    pas les coordonnées brutes passées en argument."""
    raw_lat, raw_lon = 99.0, 99.0  # coordonnées volontairement absurdes/en mer
    lat, lon, quartier = correct_meter("M001", raw_lat, raw_lon, None)

    expected_lat, expected_lon, expected_q = VERIFIED_COORDS["M001"]
    assert lat == expected_lat
    assert lon == expected_lon
    assert quartier == expected_q


def test_known_meter_keeps_original_quartier_if_provided():
    """Si le CSV fournit déjà un quartier, on ne doit PAS l'écraser avec
    celui de la table vérifiée (seul lat/lon doit être corrigé)."""
    lat, lon, quartier = correct_meter("M001", 0.0, 0.0, "Quartier Original CSV")
    assert quartier == "Quartier Original CSV"


def test_unknown_meter_returns_original_coordinates_unchanged():
    """Un compteur absent de VERIFIED_COORDS doit être renvoyé tel quel
    (pas de correction) plutôt que de planter ou renvoyer des valeurs bidon."""
    lat, lon, quartier = correct_meter("M999_INCONNU", 30.41, -9.60, "MonQuartier")
    assert lat == 30.41
    assert lon == -9.60
    assert quartier == "MonQuartier"


def test_all_verified_coordinates_are_within_agadir_bounding_box():
    """Garde-fou géographique : toutes les coordonnées vérifiées doivent
    rester dans une zone raisonnable autour du Grand Agadir (évite qu'une
    coordonnée mal recopiée envoie un compteur à l'autre bout du Maroc)."""
    LAT_MIN, LAT_MAX = 30.30, 30.50
    LON_MIN, LON_MAX = -9.70, -9.40
    for meterid, (lat, lon, _q) in VERIFIED_COORDS.items():
        assert LAT_MIN <= lat <= LAT_MAX, f"{meterid}: latitude {lat} hors zone Agadir"
        assert LON_MIN <= lon <= LON_MAX, f"{meterid}: longitude {lon} hors zone Agadir"


def test_zone_polygons_have_at_least_three_points():
    """Un polygone géographique valide nécessite au moins 3 sommets."""
    for zone, points in ZONE_POLYGONS.items():
        assert len(points) >= 3, f"Polygone '{zone}' invalide (< 3 points)"


def test_zone_polygons_points_are_lat_lon_pairs():
    for zone, points in ZONE_POLYGONS.items():
        for point in points:
            assert len(point) == 2
            lat, lon = point
            assert 30.0 <= lat <= 31.0
            assert -10.0 <= lon <= -9.0