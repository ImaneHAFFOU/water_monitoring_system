# AquaVeille — Frontend (React + Vite)

Tableau de bord de surveillance de l'eau du Grand Agadir. Consomme l'API du dossier `backend/`.

## Prérequis
- Node.js 18+ (vérifie avec `node --version`)
- Le **backend doit tourner** (sinon les pages afficheront un message d'erreur explicite) :
  ```bash
  cd backend && uvicorn main:app --reload
  ```

## Installation & lancement
```bash
cd frontend
npm install
npm run dev
```
Ouvre ensuite **http://localhost:5173**.

> Si ton backend n'est pas sur `http://localhost:8000`, crée un fichier `.env` à la racine de
> `frontend/` avec :  `VITE_API_URL=http://adresse:port`

## Ce qui est livré (Étape 1)
- La coquille de l'application : menu latéral + navigation entre 4 pages.
- La page **Tableau de bord**, complète et connectée à l'API :
  - 4 cartes de KPI (consommation totale, compteurs, alertes actives, taux d'anomalie)
  - courbe de prévision (historique + 48 h prévues, modèle SARIMA)
  - consommation par zone + alertes récentes
- Les pages Carte / Prévision / Alertes sont des espaces réservés (étapes 2 à 4).

## Design
Identité « salle de contrôle hydraulique » : teal profond (l'eau, la surveillance) +
accent sable/ocre (la côte d'Agadir). Chiffres en Space Grotesk pour un rendu d'instrument.
Responsive (jusqu'au mobile) et focus clavier visibles.

## Structure
```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx          point d'entrée
    ├── App.jsx           coquille + routes
    ├── api.js            appels à l'API backend
    ├── styles.css        design system
    ├── components/
    │   ├── Sidebar.jsx
    │   └── ui.jsx        KpiCard, Loader, ErrorBox, EmptyState
    └── pages/
        ├── Dashboard.jsx  ✅ (étape 1)
        ├── MapView.jsx    → étape 2
        ├── Forecast.jsx   → étape 3
        └── Alerts.jsx     → étape 4
```
