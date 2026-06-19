"""Connexion PostgreSQL + PostGIS (OPTIONNELLE).

Par défaut USE_DATABASE=False dans config.py → le backend tourne sur CSV.
Pour activer Postgres plus tard :
  1. créer la base et activer PostGIS :  CREATE EXTENSION postgis;
  2. mettre USE_DATABASE=True et ajuster DATABASE_URL dans config.py
  3. lancer init_db() une fois pour créer les tables et charger les données.
"""
from config import USE_DATABASE, DATABASE_URL

engine = None
SessionLocal = None

if USE_DATABASE:
    from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
    from sqlalchemy.orm import declarative_base, sessionmaker

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    Base = declarative_base()

    class Consumption(Base):
        __tablename__ = "consumption"
        id = Column(Integer, primary_key=True)
        timestamp = Column(DateTime, index=True)
        meterid = Column(String, index=True)
        zone = Column(String)
        quartier = Column(String)
        latitude = Column(Float)
        longitude = Column(Float)
        consumptionliters = Column(Float)
        flowratelpm = Column(Float)
        pressurebar = Column(Float)
        anomalylabel = Column(String)
        # Géométrie PostGIS : décommenter après CREATE EXTENSION postgis;
        # from geoalchemy2 import Geometry
        # geom = Column(Geometry("POINT", srid=4326))

    def init_db():
        import pandas as pd
        from config import DATA_FILE
        Base.metadata.create_all(engine)
        df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
        df.columns = df.columns.str.strip().str.lower()
        df.to_sql("consumption", engine, if_exists="append", index=False, chunksize=5000)
        print("✅ Base initialisée et données chargées.")
else:
    def init_db():
        print("ℹ️  USE_DATABASE=False : le backend fonctionne sur CSV (pas de Postgres).")