"""
Test de charge — API AquaVeille (Locust)

Simule plusieurs profils d'utilisateurs réalistes du dashboard React, plutôt
que de bombarder un seul endpoint : c'est ce qui se passe vraiment quand
plusieurs agents ONEP/ONEE consultent le système en même temps.

Lancer :
  - Interface web (recommandé pour la soutenance, graphiques en direct) :
        locust -f locustfile.py --host=http://127.0.0.1:8000
    puis ouvrir http://localhost:8089 et configurer le nombre d'utilisateurs.

  - Mode headless (ligne de commande, pour un rapport automatisé / CI) :
        locust -f locustfile.py --host=http://127.0.0.1:8000 \
               --headless -u 20 -r 5 -t 60s --csv=results/load_test

    -u 20   : 20 utilisateurs simultanés simulés
    -r 5    : 5 nouveaux utilisateurs démarrés par seconde (montée en charge)
    -t 60s  : durée du test
    --csv   : exporte des CSV (résumé, par endpoint, historique) — pratique
              pour générer un graphique à mettre dans le mémoire.

IMPORTANT : le serveur (uvicorn main:app) doit déjà tourner séparément ;
Locust ne le démarre pas lui-même, il envoie de vraies requêtes HTTP dessus.
"""
import random

from locust import HttpUser, task, between


class DashboardViewer(HttpUser):
    """Profil 1 — un agent qui ouvre le tableau de bord et le laisse affiché,
    en le rafraîchissant de temps en temps (comportement réel observé sur
    Dashboard.jsx : un seul useEffect au montage, pas de polling automatique
    actuellement, donc on simule un rafraîchissement manuel périodique)."""

    weight = 3  # le profil le plus fréquent : la plupart des utilisateurs consultent juste le dashboard
    wait_time = between(5, 15)  # temps "humain" entre deux rafraîchissements de page

    @task
    def load_dashboard(self):
        """Reproduit exactement le Promise.all() de Dashboard.jsx :
        health + forecast(48) + zones + alerts(168, 6) quasi simultanément."""
        self.client.get("/health", name="/health")
        self.client.get("/predict?hours=48", name="/predict [dashboard]")
        self.client.get("/zones", name="/zones")
        self.client.get("/alerts?hours=168&top=6", name="/alerts [dashboard]")


class MapExplorer(HttpUser):
    """Profil 2 — un agent terrain qui consulte la carte interactive pour
    localiser des fuites (MapView.jsx : getMeters + getAlerts + getZoneShapes)."""

    weight = 2
    wait_time = between(3, 10)

    @task
    def load_map(self):
        self.client.get("/meters", name="/meters")
        self.client.get("/alerts?hours=168&top=100", name="/alerts [carte]")
        self.client.get("/zone-shapes", name="/zone-shapes")


class ForecastAnalyst(HttpUser):
    """Profil 3 — un analyste qui change l'horizon de prévision plusieurs
    fois de suite (Forecast.jsx : boutons 24h/48h/3j/7j) — c'est le scénario
    le plus coûteux identifié dans la revue de code si SARIMA est chargé
    (ré-entraînement à chaque appel non mis en cache pour un nouvel horizon)."""

    weight = 1
    wait_time = between(2, 6)

    @task
    def change_forecast_horizon(self):
        hours = random.choice([24, 48, 72, 168])
        self.client.get(f"/predict?hours={hours}", name="/predict [horizon variable]")


class AlertsMonitor(HttpUser):
    """Profil 4 — un opérateur qui garde la page Alertes ouverte et change
    de fenêtre temporelle (Alerts.jsx : boutons 7j/14j/30j + filtres)."""

    weight = 1
    wait_time = between(4, 12)

    @task(3)
    def view_alerts(self):
        hours = random.choice([168, 336, 720])
        self.client.get(f"/alerts?hours={hours}&top=100", name="/alerts [monitor]")

    @task(1)
    def view_model_comparison(self):
        self.client.get("/models", name="/models")