# AquaVeille — Système intelligent de surveillance de la consommation d'eau et de détection des fuites
### Application au Grand Agadir — Projet de Fin d'Études

**Réalisé par :** HAFFOU Imane
**Encadré par :** Dr. EL HAJJAMI Salma
**Établissement :** Université Ibn Zohr — Faculté des Sciences Agadir — Centre d'excellence Software Engineering (IL)

---

## 🎯 Contexte

La région de Souss-Massa fait face à des défis croissants de gestion des ressources hydriques (rareté de l'eau,
pression touristique saisonnière, pertes par fuites non détectées). Ce projet propose une plateforme intelligente
combinant **Machine Learning** et **visualisation géospatiale** pour prédire la consommation d'eau et détecter
automatiquement les fuites dans le réseau du Grand Agadir.

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│  Notebooks  │ ───▶ │   Backend    │ ───▶ │     Frontend     │
│  (modèles)  │      │  (FastAPI)   │      │  (React + Vite)  │
└─────────────┘      └──────────────┘      └─────────────────┘
      │                     │
      ▼                     ▼
  models/*.pkl         data/*.csv
```

- **Données** : dataset de compteurs intelligents simulés pour le Grand Agadir (12 compteurs de secteur,
  approche DMA, 3 zones : résidentiel / touristique / industriel), enrichi de variables climatiques et
  d'événements (saisonnalité touristique, Ramadan, etc.).
- **Modèles IA** : 4 modèles de prévision comparés (SARIMA, Prophet, XGBoost, LSTM) et 3 modèles de détection
  d'anomalies (Isolation Forest, LSTM-Autoencoder, méthode statistique 3-sigma).
- **Backend** : API FastAPI exposant les prédictions et alertes, testée (75 tests, 92 % de couverture).
- **Frontend** : tableau de bord React (AquaVeille) avec carte interactive, prévision et gestion des alertes.

## 📁 Structure du dépôt

```
pfe_eau_agadir/
├── data/                   # Datasets (brut, traité, train/test)
├── models/                 # Modèles entraînés (.pkl, .keras) + résultats comparatifs
├── notebooks/              # 01_eda · 02_prediction · 03_anomaly_detection
├── reports/figures/        # Graphiques générés pour le mémoire
├── backend/                # API FastAPI — voir backend/README.md
│   └── tests/              # Suite de tests (pytest) + tests de charge (Locust)
└── frontend/               # Application React — voir frontend/README.md
```

## 🚀 Démarrage rapide

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload          # http://localhost:8000/docs

# 2. Frontend (autre terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Détails complets : [`backend/README.md`](backend/README.md) · [`frontend/README.md`](frontend/README.md)

## 🧪 Tests

```bash
cd backend
pytest --cov=. --cov-report=term-missing   # tests unitaires + couverture
locust -f locustfile.py --host=http://127.0.0.1:8000 --headless -u 30 -r 5 -t 60s
```

75 tests unitaires/intégration (100 % passants, 92 % de couverture) + tests de charge.

## 🛠️ Stack technique

| Catégorie | Outils |
|---|---|
| Data & ML | Python, Pandas, NumPy, Scikit-learn, Statsmodels, XGBoost, TensorFlow/Keras, Prophet |
| Backend | FastAPI, Uvicorn, Pydantic, pytest, Locust |
| Frontend | React, Vite, Recharts, React-Leaflet |
| Base de données (optionnelle) | PostgreSQL + PostGIS |
| Gestion de projet | Git/GitHub, Jupyter Notebook |

## 📊 Résultats clés

- **Prévision** : SARIMA[24] retenu — MAPE ≈ 10,7 % sur la demande horaire du réseau.
- **Détection** : Isolation Forest retenu — AUC ≈ 0,90, seuil optimisé pour le F1.

## 📄 Licence / Cadre académique

Projet réalisé dans le cadre d'un Projet de Fin d'Études (PFE) — Université Ibn Zohr, Agadir.