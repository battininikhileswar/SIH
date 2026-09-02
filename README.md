# SIH 26162 — Industrial Fire & Persistent Thermal Source Intelligence

Welcome to **SIH Problem Statement 26162**! This project provides an AI-powered platform for detecting, classifying, and monitoring industrial fires and persistent thermal sources using satellite fire observations, geospatial information, temporal analysis, machine learning, explainable risk scoring, and incident alert management.

---

## 📌 Project Overview & Final System Goals

Industrial facilities (e.g., refineries, chemical plants, steel mills, power plants) frequently produce persistent thermal signatures or controlled flaring. Distinguishing between normal industrial high-heat operations and dangerous, uncontrolled industrial fires requires satellite observations and AI-driven spatial-temporal analytics.

When completed, the final system will support:
- 🛰️ **NASA FIRMS Integration**: Real-time hotspot data from MODIS & VIIRS satellites.
- 🗺️ **OpenStreetMap & Geospatial Context**: Spatial mapping of industrial zones, facilities, and proximity analysis.
- 🏭 **Industrial Facility Detection**: Spatial matching of thermal hotspots against industrial infrastructure.
- 📊 **Hotspot Clustering**: Grouping localized thermal anomalies.
- 🔥 **Persistent Thermal Source Detection**: Tracking long-term heat signatures over time.
- 🤖 **AI/ML Classification**: Differentiating routine flaring/heat operations from active fire incidents.
- ⚠️ **Risk Scoring & Prioritization**: Automated priority scoring ($0 - 100$) and investigation queue ranking.
- 🚨 **Alert & Incident Management**: Deduplicated alert triggering, incident status lifecycles, and audit history.
- 🌐 **Interactive Web Map**: Real-time Leaflet visualization map.
- 📈 **Analytics Dashboard**: Comprehensive spatial-temporal reporting.

---

## 🎯 Current Status: Phase 7 Completed (Alert Detection & Incident Management)

We have successfully completed **Phases 1 through 7**:

- **Phase 1**: Initial project architecture, FastAPI backend structure, React + Vite + TypeScript frontend starter.
- **Phase 2**: Real **NASA FIRMS active fire satellite data** integration (`GET /api/hotspots`), regional bounding box filters (India, Andhra Pradesh, Custom BBox), TTL in-memory caching, and interactive Leaflet map rendering.
- **Phase 3**: **OpenStreetMap (OSM) Industrial Context Engine** (`GET /api/hotspots/context`), on-demand facility lookups, geodesic **Haversine distance calculation**, rule-based context classification (`INDUSTRIAL`, `URBAN`, `RURAL_OR_AGRICULTURAL`, `UNKNOWN`), and nearby facility Leaflet visualization.
- **Phase 4**: **Persistent Thermal Source Detection Engine** (`GET /api/persistent-hotspots`), spatial clustering within $1.0 \text{ km}$, temporal duration analysis, transparent persistence scoring ($0-100$), timeline visualization, and industrial context integration.
- **Phase 5**: **Explainable AI Classification Layer** (`GET /api/hotspots/classify`), 9 tabular feature extractors, `scikit-learn` `RandomForestClassifier` training pipeline, safe `ModelManager` loader, `PROTOTYPE_RULE_ENGINE` fallback, supporting indicators, and raw feature drawer.
- **Phase 6**: **Explainable Thermal Event Risk Scoring Engine** (`GET /api/hotspots/risk`, `GET /api/hotspots/priority-ranking`), 5 weighted components ($0 - 100$ total), prototype risk priority levels (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), map visualization, and "Highest Risk Thermal Events" investigation leaderboard.
- **Phase 7**: **Thermal Event Alert & Incident Management System** (`GET /api/alerts`, `POST /api/alerts/evaluate`, status transition endpoints), spatial-temporal deduplication ($1.0 \text{ km}$ / $12 \text{ hrs}$), persistent JSON storage (`data/processed/alerts.json`), state machine lifecycle (`NEW` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `RESOLVED` / `DISMISSED`), Alert Dashboard, Stats Bar, Details Panel, and History view.

---

## 🚨 Alert Detection & Incident Management Architecture

> [!IMPORTANT]
> The alert system is an **internal decision-support and investigation-prioritization system**. It does **NOT** automatically contact emergency services or send external SMS/email notifications.

### 1. Configuration Parameters (`backend/app/config.py`)
- `ALERT_CRITICAL_THRESHOLD = 75.0`: Risk scores $\ge 75$ trigger CRITICAL alerts.
- `ALERT_HIGH_THRESHOLD = 50.0`: Risk scores $\ge 50$ trigger HIGH alerts.
- `ALERT_DEDUP_RADIUS_KM = 1.0`: Spatial radius threshold for deduplication ($1.0 \text{ km}$).
- `ALERT_COOLDOWN_HOURS = 12.0`: Cooldown window for deduplicating recurring satellite passes ($12.0 \text{ hrs}$).

### 2. Deduplication Strategy
- When an active thermal event/cluster is evaluated:
  - If an existing unresolved alert (`NEW`, `ACKNOWLEDGED`, `INVESTIGATING`) is found within $1.0 \text{ km}$ created within the last $12.0 \text{ hours}$:
    - **No duplicate alert record is created.**
    - The existing alert record is updated with the latest risk score, classification, satellite pass details, and evidence rationale (`updated_at`).
  - If no matching unresolved alert exists and risk score $\ge 50$:
    - A new alert record is created with a unique ID (e.g. `ALT-20260901-0001`) and initial status `NEW`.

### 3. Alert Lifecycle State Machine
$$\text{NEW} \xrightarrow{\text{Acknowledge}} \text{ACKNOWLEDGED} \xrightarrow{\text{Investigate}} \text{INVESTIGATING} \xrightarrow{\text{Resolve}} \text{RESOLVED}$$

$$\text{NEW / ACKNOWLEDGED / INVESTIGATING} \xrightarrow{\text{Dismiss}} \text{DISMISSED}$$

- State transitions are strictly controlled via API POST endpoints:
  - `POST /api/alerts/{id}/acknowledge`
  - `POST /api/alerts/{id}/investigate`
  - `POST /api/alerts/{id}/resolve`
  - `POST /api/alerts/{id}/dismiss`
- Invalid transitions return HTTP 400 Bad Request.

### 4. Persistent JSON Storage
Alert records are saved atomically to `data/processed/alerts.json`. Alerts survive backend server restarts and maintain audit timestamps (`created_at`, `updated_at`, `acknowledged_at`, `resolved_at`, `resolved_by`, `resolution_notes`).

---

## 🏗️ Project Architecture

```text
SIH-26162/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                  # Centralized alert thresholds, deduplication math & storage paths
│   │   ├── main.py                    # FastAPI server with health check, hotspots, OSM, persistence, AI, risk & alert APIs
│   │   ├── services/
│   │   │   ├── firms_service.py       # Real NASA FIRMS satellite data parser & caching
│   │   │   ├── osm_service.py         # OpenStreetMap engine, Haversine math & context classifier
│   │   │   ├── persistence_service.py # Spatial clustering engine & persistence scoring
│   │   │   ├── risk_service.py        # Explainable 5-component risk scoring engine & priority rationale
│   │   │   └── alert_service.py       # Alert state machine, deduplication, JSON storage & statistics
│   │   └── ml/
│   │       ├── feature_engineering.py # 9-feature tabular vector extractor & normalizer
│   │       ├── model_manager.py       # Safe joblib model artifact loader/saver
│   │       └── classifier.py          # AI classification engine & explainability generator
│   ├── requirements.txt               # Python dependencies (fastapi, uvicorn, httpx, scikit-learn, joblib)
│   └── .env.example                   # Environment configuration template
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FireMap.tsx            # Leaflet map rendering hotspots, clusters, OSM facilities & active alert markers
│   │   │   ├── FilterBar.tsx          # View mode switch (Hotspots vs Clusters) & region selector
│   │   │   ├── ContextPanel.tsx       # Location context sidebar with AiClassificationCard & RiskScoreCard
│   │   │   ├── PersistencePanel.tsx   # Persistent cluster sidebar with AiClassificationCard & RiskScoreCard
│   │   │   ├── AiClassificationCard.tsx# Explainable AI card, confidence meter & feature drawer
│   │   │   ├── RiskScoreCard.tsx      # Risk priority score, breakdown table & priority reasons
│   │   │   ├── PriorityTable.tsx      # Highest risk thermal events leaderboard table
│   │   │   ├── AlertStats.tsx         # Active alert summary metrics bar
│   │   │   ├── AlertDashboard.tsx     # Active incident queue table with operator action controls
│   │   │   ├── AlertDetailPanel.tsx   # Alert detail sidebar with state machine transition buttons
│   │   │   ├── AlertHistory.tsx       # Archived resolved & dismissed alert audit history
│   │   │   └── Legend.tsx             # Map legend for FRP intensity, persistence scores & risk levels
│   │   ├── types/
│   │   │   └── hotspot.ts             # TypeScript interfaces for Hotspot, OsmFeature, Cluster, AI, Risk & Alert schemas
│   │   ├── App.tsx                    # Main dashboard container & state manager
│   │   ├── index.css                  # Dark-themed dashboard styling
│   │   └── main.tsx                   # React root initializer
│   ├── package.json                   # React 18, Vite, TypeScript, Leaflet dependencies
│   └── vite.config.ts                 # Vite bundler configuration
│
├── data/
│   ├── raw/                           # Unprocessed satellite / OSM data files
│   └── processed/
│       └── alerts.json                # Persistent JSON storage file for alert records
│
├── ml/
│   ├── datasets/
│   │   └── thermal_events_dataset.csv # Labeled training dataset template
│   ├── preprocessing/
│   │   └── prepare_dataset.py         # Dataset creation script
│   ├── training/
│   │   └── train.py                   # RandomForest model training script
│   └── models/                        # Exported ML model artifacts (.pkl)
│
├── .gitignore
└── README.md
```

---

## 🚀 Beginner-Friendly Setup Guide (Windows)

### Step 1: Backend Setup (FastAPI)

1. Open PowerShell or Terminal and navigate to `backend`:
   ```powershell
   cd C:\Users\DELL\OneDrive\Desktop\SIH-26162\backend
   ```

2. Activate Virtual Environment (if created):
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install Backend Dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. Start FastAPI Server:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

5. Verify Backend Endpoints in your Browser:
   - Health Check: `http://127.0.0.1:8000/api/health`
   - Active Hotspots API: `http://127.0.0.1:8000/api/hotspots?region=india`
   - OSM Context API: `http://127.0.0.1:8000/api/hotspots/context?lat=17.6868&lon=83.2185`
   - Persistent Hotspots API: `http://127.0.0.1:8000/api/persistent-hotspots?region=india`
   - AI Classification API: `http://127.0.0.1:8000/api/hotspots/classify?lat=17.6868&lon=83.2185&frp=45.2&brightness=342.7`
   - Risk Priority Scoring API: `http://127.0.0.1:8000/api/hotspots/risk?lat=17.6868&lon=83.2185&frp=52.4&brightness=345.2`
   - Active Alerts List API: `http://127.0.0.1:8000/api/alerts`
   - Alert Dashboard Stats API: `http://127.0.0.1:8000/api/alerts/stats`
   - Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

---

### Step 2: Frontend Setup (React + Vite + TypeScript)

1. Open a **new** PowerShell tab and navigate to `frontend`:
   ```powershell
   cd C:\Users\DELL\OneDrive\Desktop\SIH-26162\frontend
   ```

2. Install Frontend Dependencies:
   ```powershell
   npm install --legacy-peer-deps
   ```

3. Start Vite Development Server:
   ```powershell
   npm run dev
   ```

4. Open Dashboard in Web Browser:
   Navigate to `http://localhost:5173`. Switch between tabs (**🚨 Active Incident Queue**, **🏆 Highest Risk Priority Leaderboard**, **📜 Alert Audit History**) and inspect alert markers on the Leaflet map.

---

## 🧪 Testing & Verification Summary

During Phase 7 testing:
- [x] Threshold check verified: risk score $\ge 50$ triggers alert creation.
- [x] Deduplication verified: re-evaluating recurring satellite passes updates existing unresolved alert without creating duplicate records.
- [x] State machine transitions verified (`NEW` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `RESOLVED` / `DISMISSED`).
- [x] Invalid state transitions return HTTP 400 Bad Request error.
- [x] Persistent JSON storage verified at `data/processed/alerts.json` (alerts survive backend server restarts).
- [x] `AlertDashboard.tsx`, `AlertStats.tsx`, `AlertDetailPanel.tsx`, `AlertHistory.tsx`, and `FireMap.tsx` overlay verified.
- [x] Frontend production build (`npm run build`) completed cleanly with 0 errors.

---

## 📋 Next Steps

Phase 7 is complete! All core Phase 1–7 foundational modules are built and verified.
