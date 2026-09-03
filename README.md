# SIH 26162 — Industrial Fire & Persistent Thermal Source Intelligence

Welcome to **SIH Problem Statement 26162**! This project provides an AI-powered platform for detecting, classifying, and monitoring industrial fires and persistent thermal sources using satellite fire observations, satellite optical image intelligence, geospatial context, temporal analysis, machine learning, explainable risk scoring, and incident alert management.

---

## 📌 Project Overview & Final System Goals

Industrial facilities (e.g., refineries, chemical plants, steel mills, power plants) frequently produce persistent thermal signatures or controlled flaring. Distinguishing between normal industrial high-heat operations and dangerous, uncontrolled industrial fires requires multi-modal satellite observations (NASA FIRMS + Sentinel-2 optical imagery) and AI-driven spatial-temporal analytics.

System Capabilities:
- 🛰️ **NASA FIRMS Integration**: Real-time hotspot data from MODIS & VIIRS satellites.
- 🗺️ **OpenStreetMap & Geospatial Context**: Spatial mapping of industrial zones, facilities, and Haversine distance analysis.
- 🏭 **Industrial Facility Detection**: Spatial matching of thermal hotspots against industrial infrastructure.
- 📊 **Hotspot Clustering**: Grouping localized thermal anomalies.
- 🔥 **Persistent Thermal Source Detection**: Tracking long-term heat signatures over time.
- 🤖 **AI/ML Classification**: Differentiating routine flaring/heat operations from active fire incidents.
- ⚠️ **Risk Scoring & Prioritization**: Automated priority scoring ($0 - 100$) and investigation queue ranking.
- 🚨 **Alert & Incident Management**: Deduplicated alert triggering, incident status lifecycles, and audit history.
- 📡 **Satellite Image Intelligence**: High-resolution multi-spectral optical patch retrieval (Sentinel-2 L2A), computer vision classification, patch preprocessing, and multi-modal evidence fusion.
- 🌐 **Interactive Web Map**: Real-time Leaflet visualization map.
- 📈 **Analytics Dashboard**: Comprehensive spatial-temporal reporting.

---

## 🎯 Current Status: Phase 8 Completed (Satellite Image Intelligence for Thermal Anomaly Verification)

We have successfully completed **Phases 1 through 8**:

- **Phase 1**: Initial project architecture, FastAPI backend structure, React + Vite + TypeScript frontend starter.
- **Phase 2**: Real **NASA FIRMS active fire satellite data** integration (`GET /api/hotspots`), regional bounding box filters (India, Andhra Pradesh, Custom BBox), TTL in-memory caching, and interactive Leaflet map rendering.
- **Phase 3**: **OpenStreetMap (OSM) Industrial Context Engine** (`GET /api/hotspots/context`), on-demand facility lookups, geodesic **Haversine distance calculation**, rule-based context classification (`INDUSTRIAL`, `URBAN`, `RURAL_OR_AGRICULTURAL`, `UNKNOWN`), and nearby facility Leaflet visualization.
- **Phase 4**: **Persistent Thermal Source Detection Engine** (`GET /api/persistent-hotspots`), spatial clustering within $1.0 \text{ km}$, temporal duration analysis, transparent persistence scoring ($0-100$), timeline visualization, and industrial context integration.
- **Phase 5**: **Explainable AI Classification Layer** (`GET /api/hotspots/classify`), 9 tabular feature extractors, `scikit-learn` `RandomForestClassifier` training pipeline, safe `ModelManager` loader, `PROTOTYPE_RULE_ENGINE` fallback, supporting indicators, and raw feature drawer.
- **Phase 6**: **Explainable Thermal Event Risk Scoring Engine** (`GET /api/hotspots/risk`, `GET /api/hotspots/priority-ranking`), 5 weighted components ($0 - 100$ total), prototype risk priority levels (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), map visualization, and "Highest Risk Thermal Events" investigation leaderboard.
- **Phase 7**: **Thermal Event Alert & Incident Management System** (`GET /api/alerts`, `POST /api/alerts/evaluate`, status transition endpoints), spatial-temporal deduplication ($1.0 \text{ km}$ / $12 \text{ hrs}$), persistent JSON storage (`data/processed/alerts.json`), state machine lifecycle (`NEW` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `RESOLVED` / `DISMISSED`), Alert Dashboard, Stats Bar, Details Panel, and History view.
- **Phase 8**: **Satellite Image Intelligence for Thermal Anomaly Verification** (`GET /api/satellite/evidence`, `GET /api/satellite/image/{id}`, `POST /api/satellite/analyze`, `GET /api/incidents/{id}/evidence`), Sentinel-2 image provider, deterministic disk caching (`data/satellite/cache`), Pillow image validation & thumbnail preprocessing, modular computer vision classifier (`ModularHeuristicVisionClassifier`), optical multi-class detection (`INDUSTRIAL_FIRE`, `NATURAL_FIRE`, `PERSISTENT_THERMAL_SOURCE`, `NON_FIRE`, `UNKNOWN`), dataset pipeline (`data/satellite/prepare_dataset.py`), multi-modal evidence fusion engine (`fuse_thermal_evidence`), `SatelliteEvidenceCard` UI component, and React Leaflet map integrations.

---

## 📡 Satellite Image Intelligence & Multi-Modal Evidence Fusion

> [!IMPORTANT]
> The Satellite Intelligence layer performs **multi-modal evidence fusion** combining NASA FIRMS thermal metrics + OpenStreetMap facility context + spatial-temporal persistence scores + Sentinel-2 optical imagery into a single combined decision. If satellite API credentials are missing, the system gracefully generates deterministic offline spectral patches without interrupting analysis or faking imagery data.

### 1. Data Pipeline Architecture
$$\text{NASA FIRMS Hotspot} \longrightarrow \text{WGS84 Bbox ($1.0\text{km}$)} \longrightarrow \text{Sentinel-2 Image Provider} \longrightarrow \text{Pillow Preprocessing} \longrightarrow \text{Vision Classifier} \longrightarrow \text{Multi-Modal Fusion}$$

### 2. Provider & Caching Strategy
- Abstract provider interface `SatelliteImageProvider` (`backend/app/services/satellite_service.py`).
- Implementation `Sentinel2ImageProvider` caches retrieved patches under `data/satellite/cache/` using deterministic key formatting: `sat_<md5_hash>.png`.
- Graceful missing credential handling when `SATELLITE_API_KEY` is omitted from `.env`.

### 3. Image Preprocessing (`backend/app/services/image_processing_service.py`)
- Standardizes satellite image patches to $256 \times 256$ RGB PNG.
- Generates $64 \times 64$ thumbnails for dashboard UI listing.
- Validates dimensions, color channels, and file integrity using Pillow.

### 4. Modular Vision Classifier (`backend/app/services/satellite_classifier.py`)
- `BaseSatelliteImageClassifier` interface allows drop-in replacement with deep learning CNN or Vision Transformer models.
- `ModularHeuristicVisionClassifier` computes mean RGB channel intensities, heat core ratio ($>200\text{ red}, >100\text{ green}$), and Spectral Thermal Index ($\text{STI}$).
- Categorizes patches across 5 target classes:
  1. `INDUSTRIAL_FIRE`
  2. `NATURAL_FIRE`
  3. `PERSISTENT_THERMAL_SOURCE`
  4. `NON_FIRE`
  5. `UNKNOWN`

### 5. Multi-Modal Evidence Fusion (`backend/app/services/evidence_fusion_service.py`)
Fuses 4 distinct evidence streams into a unified confidence score ($0.0 - 1.0$) and human-readable rationale summary:
- **FIRMS Thermal Evidence** ($\text{FRP}$, Brightness)
- **OSM Industrial Context** (Facility proximity & category)
- **Persistence Evidence** (Observation passes & temporal duration)
- **Satellite Optical Intelligence** (Visual heat core ratio & spectral index)

---

## 🏗️ Project Architecture

```text
SIH-26162/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                  # Centralized alert thresholds, satellite paths & settings
│   │   ├── main.py                    # FastAPI server with hotspots, OSM, persistence, AI, risk, alert & satellite APIs
│   │   ├── services/
│   │   │   ├── firms_service.py       # Real NASA FIRMS satellite data parser & caching
│   │   │   ├── osm_service.py         # OpenStreetMap engine, Haversine math & context classifier
│   │   │   ├── persistence_service.py # Spatial clustering engine & persistence scoring
│   │   │   ├── risk_service.py        # Explainable 5-component risk scoring engine & priority rationale
│   │   │   ├── alert_service.py       # Alert state machine, deduplication, JSON storage & statistics
│   │   │   ├── satellite_service.py   # Sentinel-2 patch retrieval, bounding box math & disk caching
│   │   │   ├── image_processing_service.py # Pillow patch resizing, validation & thumbnail generation
│   │   │   ├── satellite_classifier.py# Modular computer vision classifier (5 target optical classes)
│   │   │   └── evidence_fusion_service.py # Multi-modal evidence fusion engine (FIRMS+OSM+Persistence+Satellite)
│   │   └── ml/
│   │       ├── feature_engineering.py # 9-feature tabular vector extractor & normalizer
│   │       ├── model_manager.py       # Safe joblib model artifact loader/saver
│   │       └── classifier.py          # AI classification engine & explainability generator
│   ├── tests/
│   │   └── test_phase8_satellite.py   # Unit & regression test suite for Phase 8
│   ├── requirements.txt               # Python dependencies (fastapi, uvicorn, httpx, scikit-learn, joblib, pillow)
│   └── .env.example                   # Environment configuration template
│
├── data/
│   └── satellite/
│       ├── prepare_dataset.py         # Dataset folder initializer & metadata recorder
│       ├── raw/                       # Raw downloaded satellite patches
│       ├── processed/                 # Standardized 256x256 RGB patch dataset
│       ├── industrial_fire/           # Industrial fire patch category
│       ├── natural_fire/              # Natural fire patch category
│       ├── persistent_thermal/        # Persistent thermal patch category
│       ├── non_fire/                  # Non-fire patch category
│       ├── metadata/                  # JSON patch metadata records
│       └── cache/                     # Disk cache for satellite patch previews
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FireMap.tsx            # Leaflet map with active alerts & satellite evidence popup links
│   │   │   ├── ContextPanel.tsx       # Location context drawer with embedded SatelliteEvidenceCard
│   │   │   ├── AlertDetailPanel.tsx   # Incident alert panel with SatelliteEvidenceCard & status actions
│   │   │   ├── SatelliteEvidenceCard.tsx # Satellite patch preview, CV confidence & multi-modal fusion summary
│   │   │   └── ...
│   │   ├── types/
│   │   │   └── hotspot.ts             # TypeScript interfaces for SatelliteEvidence & FusedEvidenceResponse
│   │   └── ...
```

---

## 🔑 Environment Variables (`backend/.env.example`)

```env
# NASA FIRMS API KEY
FIRMS_MAP_KEY=YOUR_NASA_FIRMS_MAP_KEY_HERE

# Server & CORS Settings
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Phase 8 Satellite Image Intelligence Configuration
SATELLITE_PROVIDER=Sentinel-2
SATELLITE_API_KEY=YOUR_SENTINEL_HUB_API_KEY_HERE
SATELLITE_IMAGE_SIZE=256
SATELLITE_PATCH_RADIUS_KM=1.0
SATELLITE_CACHE_DIR=../data/satellite/cache
SATELLITE_DATASET_DIR=../data/satellite
```

```

---

## 🧠 Phase 9: Real Satellite Dataset & Machine Learning Pipeline

Phase 9 converts the optical image infrastructure into a real machine learning dataset, training pipeline, and evaluation framework using PyTorch (`ResNet18` / `EfficientNet-B0`).

### 1. Dataset Generation & Geographic-Aware Splitting
```bash
python data/satellite/build_dataset.py --limit 30
```
- Queries real **NASA FIRMS** active fire detections, **OpenStreetMap** industrial infrastructure context, and **spatial-temporal persistence clusters**.
- Assigns defensible, non-fabricated labels across 4 classes:
  - `0`: `NON_FIRE` (Nominal background terrain)
  - `1`: `NATURAL_FIRE` (Forest/agricultural fires in non-industrial terrain)
  - `2`: `INDUSTRIAL_FIRE` (Hotspots localized within 1.5 km of heavy industrial infrastructure)
  - `3`: `PERSISTENT_THERMAL_SOURCE` (Verified clusters with persistence score $\ge 50$ / industrial flaring)
- Applies **Geographic-Aware Clustering**: Groups points within 2.0 km into spatial clusters and assigns entire clusters to `train` (70%), `val` (15%), or `test` (15%) splits, eliminating spatial data leakage.

### 2. Model Training
```bash
cd backend
python -m app.ml.train --epochs 5 --batch-size 8 --model-name resnet18
```
- Trains transfer learning model (`ResNet18`) with Cross-Entropy Loss, AdamW optimizer, and Cosine Annealing learning rate schedule.
- Saves best model checkpoint to `models/satellite_classifier/best_model.pth`.

### 3. Model Evaluation
```bash
cd backend
python -m app.ml.evaluate
```
- Generates `metrics.json`, `classification_report.json`, `confusion_matrix.json`, and `confusion_matrix.png` under `data/satellite/metrics/`.

### 4. Phase 9 REST Endpoints
- `GET /api/satellite/model/status` — PyTorch model availability, version, and architecture.
- `POST /api/satellite/model/predict` — Vision model inference directly on optical patch images.
- `GET /api/satellite/model/metrics` — Test set accuracy, precision, recall, F1, and confusion matrix.

---

## ⚡ Quick Start Guide

### 1. Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --host 127.0.0.1
```

### 2. Dataset Infrastructure & Training
```bash
python data/satellite/build_dataset.py --limit 30
python -m app.ml.train --epochs 5
python -m app.ml.evaluate
```

### 3. Frontend Setup (React + Vite + TypeScript)
```bash
cd frontend
npm install
npm run dev
```

### 4. Running Backend Unit & Regression Tests
```bash
cd backend
python -m unittest tests/test_phase8_satellite.py
python tests/run_phase9_tests.py
```

---

## 📜 License & Acknowledgments

This project is built for **Smart India Hackathon (SIH) Problem Statement 26162**.  
Geospatial data provided by **NASA FIRMS** (MODIS/VIIRS), **OpenStreetMap** (Overpass API), and **Sentinel-2** satellite imagery.

