import pandas as pd
import numpy as np

INPUT_FILE = "data/water_consumption_agadir.csv"
OUTPUT_FILE = "data/water_consumption_agadir_pfe.csv"

START_DATE = "2025-02-01"
END_DATE = "2025-09-30"

METERS_PER_ZONE = 4
TARGET_ZONES = ["residential", "tourist", "industrial"]

df = pd.read_csv(INPUT_FILE, parse_dates=["timestamp"])

df = df.rename(columns={
    "meter_id": "meterid",
    "zone_type": "zone",
    "consumption_liters": "consumptionliters",
    "flow_rate": "flowratelpm",
    "pressure": "pressurebar",
    "temperature": "temperaturec",
    "day_of_week": "dayofweek",
    "is_weekend": "isweekend",
    "anomaly_label": "anomalylabel"
})

required_cols = ["timestamp", "meterid", "zone", "consumptionliters"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Colonnes obligatoires manquantes : {missing}")

df["zone"] = df["zone"].astype(str).str.strip().str.lower()
df = df[(df["timestamp"] >= START_DATE) & (df["timestamp"] <= END_DATE)].copy()

selected_meters = []

for z in TARGET_ZONES:
    zdf = df[df["zone"] == z]
    meter_counts = zdf.groupby("meterid").size().sort_values(ascending=False)
    chosen = meter_counts.head(METERS_PER_ZONE).index.tolist()
    selected_meters.extend(chosen)
    print(f"{z}: {len(chosen)} compteurs sélectionnés -> {chosen}")

df_pfe = df[df["meterid"].isin(selected_meters)].copy()
df_pfe = df_pfe.sort_values(["meterid", "timestamp"]).reset_index(drop=True)

print("\n===== RÉSUMÉ DATASET PFE =====")
print("Shape:", df_pfe.shape)
print("Période:", df_pfe["timestamp"].min(), "->", df_pfe["timestamp"].max())
print("Nb compteurs:", df_pfe["meterid"].nunique())
print("Zones:")
print(df_pfe["zone"].value_counts())

df_pfe.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
print(f"\nDataset sauvegardé : {OUTPUT_FILE}")


# import pandas as pd
# df = pd.read_csv("data/water_consumption_agadir_pfe.csv")
# print(df.groupby("zone")["consumptionliters"].describe())
# print(df["anomalylabel"].value_counts(normalize=True))
# print(df["event_type"].value_counts())