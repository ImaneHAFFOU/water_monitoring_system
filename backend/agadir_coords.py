"""Coordonnées GPS vérifiées (sur terre) pour les compteurs du Grand Agadir.

Source : relevé manuel par quartier (carte de zonage fournie), pour éviter que
des coordonnées générées aléatoirement dans le dataset ne tombent en mer.
Utilisé par data_service.py pour corriger lat/lon avant de les exposer à l'API.
"""

# meterid -> (latitude, longitude, quartier)
VERIFIED_COORDS = {
    # ── Résidentiel ──
    "M001": (30.4255, -9.5975, "Talborjt"), "M002": (30.4230, -9.5945, "Talborjt"),
    "M003": (30.4210, -9.5960, "Talborjt"), "M004": (30.4270, -9.5920, "Talborjt"),
    "M005": (30.4290, -9.5960, "Talborjt"), "M006": (30.4245, -9.6010, "Talborjt"),
    "M007": (30.4310, -9.5990, "Talborjt"),
    "M008": (30.4400, -9.5780, "Hay Mohammadi"), "M009": (30.4430, -9.5720, "Hay Mohammadi"),
    "M010": (30.4370, -9.5750, "Hay Mohammadi"), "M011": (30.4420, -9.5820, "Hay Mohammadi"),
    "M012": (30.4450, -9.5770, "Hay Mohammadi"), "M013": (30.4380, -9.5700, "Hay Mohammadi"),
    "M014": (30.4460, -9.5840, "Hay Mohammadi"),
    "M015": (30.4200, -9.5750, "Dakhla"), "M016": (30.4230, -9.5700, "Dakhla"),
    "M017": (30.4170, -9.5700, "Hay Salam"), "M018": (30.4280, -9.5750, "Dakhla"),
    "M019": (30.4320, -9.5720, "Bensergao N."), "M020": (30.4150, -9.5750, "Hay Salam"),
    "M021": (30.4250, -9.5800, "Dakhla"),
    "M022": (30.4130, -9.5820, "Tikiouine"), "M023": (30.4100, -9.5750, "Tikiouine"),
    "M024": (30.4160, -9.5850, "Tikiouine"), "M025": (30.4080, -9.5820, "Tilila"),
    "M026": (30.4110, -9.5900, "Tilila"), "M027": (30.4060, -9.5880, "Tilila"),
    "M028": (30.4140, -9.5970, "Tikiouine O."), "M029": (30.4090, -9.5960, "Tilila"),
    "M030": (30.4070, -9.5700, "Tilila S."),
    # ── Touristique ──
    # Coordonnées recalées sur un repère réel vérifié (résidence Founty Bay :
    # 30.40118, -9.58706) — les valeurs précédentes tombaient sur la plage/l'eau.
    "M031": (30.4012, -9.5870, "Founty — Hôtel"), "M032": (30.3970, -9.5910, "Founty Nord"),
    "M033": (30.3940, -9.5860, "Founty Sud"), "M034": (30.4090, -9.5930, "Marina d'Agadir"),
    "M035": (30.4000, -9.5920, "Bord de mer"), "M036": (30.4040, -9.5900, "Promenade"),
    "M037": (30.4060, -9.5880, "Founty N."), "M038": (30.4075, -9.5910, "Founty N."),
    "M039": (30.4100, -9.5900, "Haut Founty"), "M040": (30.4120, -9.5920, "Haut Founty"),
    "M041": (30.4150, -9.5940, "Marina"), "M042": (30.4170, -9.5920, "Marina"),
    "M043": (30.4190, -9.5900, "Marina N."), "M044": (30.4230, -9.5910, "Front de Mer"),
    "M045": (30.4270, -9.5920, "Corniche"),
    # ── Industriel ──
    "M046": (30.4530, -9.6050, "Anza"), "M047": (30.4570, -9.6100, "Anza"),
    "M048": (30.4550, -9.6180, "Z.I. Anza"), "M049": (30.4600, -9.6050, "Anza N."),
    "M050": (30.4510, -9.5900, "Z.I. Agadir"),
    "M051": (30.3850, -9.5600, "Bensergao S."), "M052": (30.3780, -9.5520, "Inezgane N."),
    "M053": (30.3700, -9.5480, "Inezgane"), "M054": (30.3620, -9.5450, "Inezgane S."),
    "M055": (30.3560, -9.5380, "Inezgane"),
    "M056": (30.3780, -9.5280, "Dcheira"), "M057": (30.3700, -9.5200, "Dcheira"),
    "M058": (30.3620, -9.5150, "Aït Melloul"), "M059": (30.3510, -9.5050, "Aït Melloul"),
    "M060": (30.3420, -9.5000, "Aït Melloul S."),
}

# Polygones de zones (lat, lon) — pour l'affichage des contours sur la carte.
ZONE_POLYGONS = {
    "residential": [
        (30.4460, -9.6050), (30.4480, -9.5830), (30.4490, -9.5630), (30.4350, -9.5500),
        (30.4180, -9.5480), (30.4050, -9.5580), (30.4080, -9.5820), (30.4130, -9.6050),
        (30.4280, -9.6120), (30.4400, -9.6100),
    ],
    "tourist": [
        # Contour resserré vers l'intérieur des terres (les sommets côté mer ont
        # été ramenés vers l'est) pour ne plus chevaucher l'océan sur la carte.
        (30.4440, -9.6050), (30.4280, -9.6070), (30.4130, -9.6020), (30.4080, -9.5850),
        (30.3980, -9.5920), (30.3880, -9.6000), (30.3850, -9.5980), (30.3870, -9.6080),
        (30.3950, -9.6090), (30.4060, -9.6090), (30.4160, -9.6080), (30.4300, -9.6050),
        (30.4430, -9.6000),
    ],
    "industrial": [
        # Anza (nord) + cluster sud (Inezgane / Aït Melloul / Dcheira), simplifié en une enveloppe
        (30.4460, -9.6050), (30.4430, -9.6240), (30.4520, -9.6320), (30.4620, -9.6200),
        (30.4650, -9.5980), (30.4600, -9.5780), (30.4490, -9.5630),
    ],
}


def correct_meter(meterid: str, lat: float, lon: float, quartier):
    """Retourne (lat, lon, quartier) vérifiés si connus, sinon les valeurs d'origine."""
    if meterid in VERIFIED_COORDS:
        vlat, vlon, vquartier = VERIFIED_COORDS[meterid]
        return vlat, vlon, (quartier or vquartier)
    return lat, lon, quartier