"""Schémas de réponse (Pydantic) — documentent l'API et valident les sorties."""
from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    data: dict
    models: dict


class Point(BaseModel):
    timestamp: str
    value: float


class ForecastResponse(BaseModel):
    model: str
    history: list[Point]
    forecast: list[Point]


class ZoneStat(BaseModel):
    zone: str
    n_meters: int
    mean_consumption: float
    total_consumption: float
    latitude: float
    longitude: float
    anomaly_rate: float


class MeterGeo(BaseModel):
    meterid: str
    zone: str
    quartier: Optional[str] = None
    latitude: float
    longitude: float
    mean_consumption: float
    anomaly_rate: float


class Alert(BaseModel):
    timestamp: str
    meterid: str
    zone: str
    quartier: Optional[str] = None
    consumption: float
    pressure: float
    score: float
    severity: str
    type: str