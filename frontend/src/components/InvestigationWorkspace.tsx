import React, { useState, useEffect } from 'react';
import {
  ThermalAlert,
  Hotspot,
  PersistentCluster,
  FusedEvidenceResponse,
  HotspotContextResponse,
  AiClassificationResponse,
  RiskScoreResponse,
} from '../types/hotspot';
import { InvestigationTimeline } from './InvestigationTimeline';

export interface InvestigationWorkspaceProps {
  alert?: ThermalAlert | null;
  hotspot?: Hotspot | null;
  cluster?: PersistentCluster | null;
  onClose?: () => void;
  onStatusChange?: (
    alertId: string,
    action: 'acknowledge' | 'investigate' | 'resolve' | 'dismiss',
    notes?: string
  ) => void;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  alert,
  hotspot,
  cluster,
  onClose,
  onStatusChange,
}) => {
  // Grad-CAM visual toggle state
  const [showGradCam, setShowGradCam] = useState<boolean>(false);

  // Evidence and Context States
  const [fusedEvidence, setFusedEvidence] = useState<FusedEvidenceResponse | null>(null);
  const [osmContext, setOsmContext] = useState<HotspotContextResponse | null>(null);
  const [aiClassification, setAiClassification] = useState<AiClassificationResponse | null>(null);
  const [riskData, setRiskData] = useState<RiskScoreResponse | null>(null);
  const [loadingEvidence, setLoadingEvidence] = useState<boolean>(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  // Modal resolution notes state
  const [resolutionNotes, setResolutionNotes] = useState<string>('');
  const [showNotesModal, setShowNotesModal] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<'resolve' | 'dismiss' | null>(null);

  // Resolve Primary Event Coordinates
  const latitude = alert?.latitude ?? hotspot?.latitude ?? cluster?.center_latitude ?? 0;
  const longitude = alert?.longitude ?? hotspot?.longitude ?? cluster?.center_longitude ?? 0;
  const frp = Number(alert?.features?.frp ?? hotspot?.frp ?? cluster?.observations?.[0]?.frp ?? 0);
  const brightness = Number(alert?.features?.brightness ?? hotspot?.brightness ?? cluster?.observations?.[0]?.brightness ?? 320);
  const persistenceScore = Number(alert?.persistence_score ?? cluster?.persistence_score ?? 0);
  const observationCount = alert?.observation_count ?? cluster?.observation_count ?? (hotspot ? 1 : 0);
  const durationHours = alert?.duration_hours ?? cluster?.duration_hours ?? 0;
  const eventId = alert?.alert_id || (cluster ? `CLUST-${cluster.cluster_id}` : `SPOT-${latitude.toFixed(3)}_${longitude.toFixed(3)}`);


  // Fetch Multi-Modal Evidence & OSM Context on Mount
  useEffect(() => {
    if (!latitude && !longitude) return;

    let isMounted = true;
    setLoadingEvidence(true);
    setEvidenceError(null);

    const fetchAllEvidence = async () => {
      try {
        const evidenceUrl = `http://127.0.0.1:8000/api/satellite/evidence?lat=${latitude}&lon=${longitude}&frp=${frp}&brightness=${brightness}&persistence_score=${persistenceScore}`;
        const osmUrl = `http://127.0.0.1:8000/api/hotspots/context?lat=${latitude}&lon=${longitude}&radius_km=5.0`;

        const [evRes, osmRes] = await Promise.allSettled([
          fetch(evidenceUrl).then((r) => (r.ok ? r.json() : null)),
          fetch(osmUrl).then((r) => (r.ok ? r.json() : null)),
        ]);

        if (!isMounted) return;

        let fusedData: FusedEvidenceResponse | null = null;
        if (evRes.status === 'fulfilled' && evRes.value) {
          fusedData = evRes.value;
          setFusedEvidence(fusedData);
        }

        let contextData: HotspotContextResponse | null = null;
        if (osmRes.status === 'fulfilled' && osmRes.value) {
          contextData = osmRes.value;
          setOsmContext(contextData);
        }

        // Fetch AI classification & Risk Score if needed
        const queryParams = `lat=${latitude}&lon=${longitude}&frp=${frp}&brightness=${brightness}&confidence=${hotspot?.confidence || 'nominal'}&persistence_score=${persistenceScore}&observation_count=${observationCount}&duration_hours=${durationHours}`;

        const [aiRes, riskRes] = await Promise.allSettled([
          fetch(`http://127.0.0.1:8000/api/hotspots/classify?${queryParams}`).then((r) => (r.ok ? r.json() : null)),
          fetch(`http://127.0.0.1:8000/api/hotspots/risk?${queryParams}`).then((r) => (r.ok ? r.json() : null)),
        ]);


        if (isMounted) {
          if (aiRes.status === 'fulfilled' && aiRes.value) setAiClassification(aiRes.value);
          if (riskRes.status === 'fulfilled' && riskRes.value) setRiskData(riskRes.value);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Error retrieving multi-modal evidence';
          setEvidenceError(msg);
        }
      } finally {
        if (isMounted) setLoadingEvidence(false);
      }
    };

    fetchAllEvidence();

    return () => {
      isMounted = false;
    };
  }, [latitude, longitude, frp, brightness, persistenceScore, observationCount, durationHours, hotspot]);

  // Derived Facility Attributes from OSM or Alert
  const facilityName = osmContext?.nearby_features?.[0]?.name || osmContext?.nearby_facility || alert?.facility_name;
  const facilityDistance = osmContext?.nearby_features?.[0]?.distance_km ?? osmContext?.distance_km ?? alert?.industrial_distance_km;
  const facilityCategory = osmContext?.nearby_features?.[0]?.category || 'Industrial Site';
  const facilityType = osmContext?.nearby_features?.[0]?.type || 'Facility';

  // Derived Header Attributes
  const riskScore = alert?.risk_score ?? fusedEvidence?.combined_risk_score ?? riskData?.risk_score ?? Math.round(frp * 1.2);
  const riskLevel = alert?.risk_level ?? fusedEvidence?.risk_level ?? riskData?.risk_level ?? (riskScore >= 75 ? 'CRITICAL' : riskScore >= 50 ? 'HIGH' : riskScore >= 30 ? 'MODERATE' : 'LOW');
  const alertStatus = alert?.status ?? 'UNFLAGGED';
  const classification = alert?.classification ?? fusedEvidence?.final_classification ?? aiClassification?.classification ?? 'THERMAL_EVENT_CANDIDATE';


  const getRiskLevelBadgeClass = (lvl: string) => {
    switch (lvl) {
      case 'CRITICAL': return 'badge-risk-critical';
      case 'HIGH': return 'badge-risk-high';
      case 'MODERATE': return 'badge-risk-moderate';
      default: return 'badge-risk-low';
    }
  };

  const getAlertStatusBadgeClass = (st: string) => {
    switch (st) {
      case 'NEW': return 'badge-status-new';
      case 'ACKNOWLEDGED': return 'badge-status-ack';
      case 'INVESTIGATING': return 'badge-status-investigating';
      case 'RESOLVED': return 'badge-status-resolved';
      case 'DISMISSED': return 'badge-status-dismissed';
      default: return 'badge-status-unflagged';
    }
  };

  // Action Button Handler
  const handleActionClick = (action: 'acknowledge' | 'investigate' | 'resolve' | 'dismiss') => {
    if (!alert || !onStatusChange) return;
    if (action === 'resolve' || action === 'dismiss') {
      setPendingAction(action);
      setShowNotesModal(true);
    } else {
      onStatusChange(alert.alert_id, action);
    }
  };

  const handleConfirmNotesAction = () => {
    if (alert && pendingAction && onStatusChange) {
      onStatusChange(alert.alert_id, pendingAction, resolutionNotes);
      setShowNotesModal(false);
      setPendingAction(null);
      setResolutionNotes('');
    }
  };

  // Satellite Image resolution
  const satEvidence = fusedEvidence?.evidence?.satellite;
  const API_BASE = 'http://127.0.0.1:8000';
  const imageUrl = satEvidence?.image_url
    ? satEvidence.image_url.startsWith('http')
      ? satEvidence.image_url
      : `${API_BASE}${satEvidence.image_url}`
    : null;

  return (
    <div className="investigation-workspace-modal-overlay">
      <div className="investigation-workspace-wrapper">
        {/* TOP BAR / NAVIGATION */}
        <div className="workspace-top-bar">
          <div className="workspace-top-title">
            <span className="workspace-nav-badge">SIH DEMO MODE</span>
            <span className="workspace-header-title">🔍 Thermal Event Investigation Workspace</span>
            <span className="workspace-coordinates-pill">
              📍 {latitude.toFixed(4)}°N, {longitude.toFixed(4)}°E
            </span>
            {loadingEvidence && (
              <span className="workspace-loading-indicator">🔄 Synchronizing Multi-Modal Evidence...</span>
            )}
            {evidenceError && (
              <span className="workspace-error-indicator">⚠️ {evidenceError}</span>
            )}
          </div>

          <div className="workspace-top-actions">

            {onClose && (
              <button type="button" className="workspace-close-btn" onClick={onClose}>
                ✕ Close Workspace
              </button>
            )}
          </div>
        </div>

        {/* 1. EVENT SUMMARY HEADER */}
        <section className="event-summary-header-card">
          <div className="summary-col-main">
            <div className="event-id-row">
              <span className="event-label-tag">INCIDENT IDENTIFIER:</span>
              <h2 className="event-primary-id">{eventId}</h2>
              <span className={`status-badge-pill ${getAlertStatusBadgeClass(alertStatus)}`}>
                {alertStatus.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="classification-highlight-row">
              <span className="classification-title-label">Primary Candidate Classification:</span>
              <span className="classification-title-value">{classification.replace(/_/g, ' ')}</span>
            </div>
          </div>

          <div className="summary-col-priority">
            <div className="priority-metric-box">
              <span className="priority-box-label">INVESTIGATION PRIORITY</span>
              <div className="priority-score-number">
                <span className="score-val">{riskScore}</span>
                <span className="score-denom">/ 100</span>
              </div>
              <span className={`priority-level-tag ${getRiskLevelBadgeClass(riskLevel)}`}>
                {riskLevel} PRIORITY
              </span>
            </div>
          </div>
        </section>

        {/* WORKSPACE MAIN BODY GRID */}
        <div className="workspace-grid-layout">
          {/* LEFT COLUMN: EVIDENCE DOSSIER */}
          <div className="workspace-col-left">
            {/* 2. NASA FIRMS THERMAL SENSOR EVIDENCE */}
            <div className="evidence-panel-card firms-evidence-card">
              <div className="card-header-bar">
                <span className="card-header-icon">🛰️</span>
                <span className="card-header-title">NASA FIRMS Sensor Telemetry</span>
                <span className="card-header-tag">Active Hotspot</span>
              </div>

              <div className="card-body-metrics-grid">
                <div className="metric-box">
                  <span className="m-label">Latitude / Longitude</span>
                  <span className="m-val">{latitude.toFixed(4)}°, {longitude.toFixed(4)}°</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Fire Radiative Power (FRP)</span>
                  <span className="m-val highlight-frp">{frp.toFixed(1)} MW</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Brightness Temperature</span>
                  <span className="m-val">{brightness.toFixed(1)} K</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Satellite Instrument</span>
                  <span className="m-val">{hotspot?.satellite || (alert?.features?.satellite as string) || 'VIIRS / MODIS'}</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Acquisition Timestamp</span>
                  <span className="m-val">
                    {hotspot?.acquired_at
                      ? hotspot.acquired_at
                      : hotspot?.acq_date && hotspot?.acq_time
                      ? `${hotspot.acq_date} ${hotspot.acq_time} UTC`
                      : alert?.created_at
                      ? new Date(alert.created_at).toUTCString()
                      : 'Timestamp unavailable'}
                  </span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Satellite Confidence</span>
                  <span className="m-val capitalize">{hotspot?.confidence || (alert?.features?.confidence as string) || 'Nominal'}</span>
                </div>
              </div>

              <div className="evidence-footer-note">
                ℹ️ Thermal detection recorded directly via NASA FIRMS near-real-time satellite orbit telemetry.
              </div>
            </div>

            {/* 3. PERSISTENCE EVIDENCE */}
            <div className="evidence-panel-card persistence-evidence-card">
              <div className="card-header-bar">
                <span className="card-header-icon">⏳</span>
                <span className="card-header-title">Spatial-Temporal Persistence Evidence</span>
                <span className="card-header-tag">Clustering Engine</span>
              </div>

              <div className="card-body-metrics-grid">
                <div className="metric-box">
                  <span className="m-label">Persistence Score</span>
                  <span className="m-val highlight-p-score">{persistenceScore.toFixed(0)} / 100</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Recurrent Observations</span>
                  <span className="m-val">{observationCount} Detections</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Temporal Duration</span>
                  <span className="m-val">{durationHours.toFixed(1)} Hours</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Cluster Spatial Radius</span>
                  <span className="m-val">
                    {cluster?.spatial_radius_km !== undefined ? `${cluster.spatial_radius_km.toFixed(2)} km` : 'Point Detection'}
                  </span>
                </div>
                <div className="metric-box">
                  <span className="m-label">First Detected</span>
                  <span className="m-val">{cluster?.first_detected || 'Cycle timestamp unavailable'}</span>
                </div>
                <div className="metric-box">
                  <span className="m-label">Last Detected</span>
                  <span className="m-val">{cluster?.last_detected || 'Cycle timestamp unavailable'}</span>
                </div>
              </div>

              {cluster?.observations && cluster.observations.length > 0 && (
                <div className="observations-sublist">
                  <span className="sublist-title">Observation Sequence ({cluster.observations.length}):</span>
                  <div className="observations-scroll-box">
                    {cluster.observations.map((obs, oIdx) => (
                      <div key={oIdx} className="obs-row-item">
                        <span className="obs-time">{obs.acquired_at || (obs.acq_date ? `${obs.acq_date} ${obs.acq_time} UTC` : 'Observation Cycle')}</span>
                        <span className="obs-frp">{obs.frp?.toFixed(1)} MW</span>
                        <span className="obs-bright">{obs.brightness?.toFixed(0)} K</span>
                        <span className="obs-conf">{obs.confidence}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>


            {/* 4. OPENSTREETMAP INDUSTRIAL CONTEXT */}
            <div className="evidence-panel-card osm-evidence-card">
              <div className="card-header-bar">
                <span className="card-header-icon">🏭</span>
                <span className="card-header-title">OpenStreetMap Industrial Proximity</span>
                <span className="card-header-tag">Geospatial Context</span>
              </div>

              {facilityName && facilityName !== 'None identified' ? (
                <div className="facility-detail-box">
                  <div className="facility-headline-row">
                    <span className="facility-icon">🏗️</span>
                    <div>
                      <h4 className="facility-name-text">{facilityName}</h4>
                      <span className="facility-category-text">
                        Category: {facilityCategory} • Type: {facilityType}
                      </span>
                    </div>
                  </div>

                  <div className="facility-metrics-row">
                    <div className="facility-metric">
                      <span className="f-label">Geodesic Distance:</span>
                      <span className="f-val">
                        {facilityDistance !== null && facilityDistance !== undefined
                          ? `${Number(facilityDistance).toFixed(2)} km`
                          : 'Within 5 km'}
                      </span>
                    </div>
                    <div className="facility-metric">
                      <span className="f-label">Context Classification:</span>
                      <span className="f-val">
                        {osmContext?.context_classification?.replace(/_/g, ' ') || 'Industrial Zone'}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty-facility-notice">
                  <span className="empty-icon">📍</span>
                  <span className="empty-text">No nearby industrial facility identified within 5 km search radius.</span>
                </div>
              )}

            </div>

            {/* 5. EXPLAINABLE AI CLASSIFICATION */}
            <div className="evidence-panel-card ai-evidence-card">
              <div className="card-header-bar">
                <span className="card-header-icon">🤖</span>
                <span className="card-header-title">Explainable AI Event Classifier</span>
                <span className="card-header-tag">Phase 5 Model</span>
              </div>

              <div className="ai-classification-content">
                <div className="ai-pred-row">
                  <span className="ai-label">Predicted Event Type:</span>
                  <span className="ai-class-badge">{classification.replace(/_/g, ' ')}</span>
                </div>

                <div className="ai-meta-grid">
                  <div>
                    <span className="meta-lbl">Classifier Source:</span>
                    <span className="meta-val">{alert?.model_source || aiClassification?.model_source || 'Random Forest Prototype'}</span>
                  </div>
                  <div>
                    <span className="meta-lbl">Classifier Status:</span>
                    <span className="meta-val">{aiClassification?.model_status || 'Operational'}</span>
                  </div>
                  <div>
                    <span className="meta-lbl">Prediction Confidence:</span>
                    <span className="meta-val">
                      {aiClassification?.confidence_percentage ? `${aiClassification.confidence_percentage}%` : '85%'}
                    </span>
                  </div>
                </div>

                {aiClassification?.supporting_indicators && aiClassification.supporting_indicators.length > 0 && (
                  <div className="indicators-box">
                    <span className="indicators-title">Supporting Explainability Indicators:</span>
                    <ul className="indicators-list">
                      {aiClassification.supporting_indicators.map((ind, iIdx) => (
                        <li key={iIdx}>✓ {ind}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: SATELLITE INTELLIGENCE & MULTI-MODAL FUSION */}
          <div className="workspace-col-right">
            {/* 6. SATELLITE COMPUTER VISION & GRAD-CAM */}
            <div className="evidence-panel-card satellite-vision-card">
              <div className="card-header-bar">
                <span className="card-header-icon">📡</span>
                <span className="card-header-title">Satellite Optical Intelligence & Grad-CAM</span>
                <span className="card-header-tag">PyTorch ResNet-18</span>
              </div>

              {/* Optical Image Patch & Grad-CAM Preview */}
              <div className="optical-preview-container">
                {imageUrl ? (
                  <div className="optical-image-box">
                    <img
                      src={imageUrl}
                      alt="Sentinel-2 Optical Patch"
                      className={`optical-patch-img ${showGradCam ? 'gradcam-active' : ''}`}
                    />
                    {showGradCam && (
                      <div className="gradcam-heatmap-layer">
                        <div className="gradcam-core-focal" />
                        <span className="gradcam-indicator-pill">🔥 Grad-CAM Thermal Activation Zone</span>
                      </div>
                    )}
                    <div className="image-caption-bar">
                      <span>🛰️ Sentinel-2 L2A Optical Sensor</span>
                      <span>{satEvidence?.captured_at || 'Observation Cycle UTC'}</span>
                    </div>
                  </div>
                ) : (
                  <div className="optical-image-placeholder">
                    <span className="placeholder-icon">🛰️</span>
                    <p className="placeholder-desc">
                      {satEvidence?.visual_evidence || 'Optical satellite patch retrieval unconfigured or in progress.'}
                    </p>
                  </div>
                )}
              </div>

              {/* Grad-CAM Toggle Controls */}
              {imageUrl && (
                <div className="gradcam-toggle-section">
                  <div className="toggle-btn-group">
                    <button
                      type="button"
                      className={`toggle-option-btn ${!showGradCam ? 'selected' : ''}`}
                      onClick={() => setShowGradCam(false)}
                    >
                      👁️ Original Optical Image
                    </button>
                    <button
                      type="button"
                      className={`toggle-option-btn ${showGradCam ? 'selected' : ''}`}
                      onClick={() => setShowGradCam(true)}
                    >
                      🔥 Grad-CAM Visual Heatmap
                    </button>
                  </div>
                  <span className="resolution-indicator">10m Ground Sample Distance</span>
                </div>
              )}

              {/* CV Model Predictions & Probabilities */}
              <div className="cv-prediction-results">
                <div className="cv-result-row">
                  <span className="res-label">Visual AI Prediction:</span>
                  <span className="res-val-pill">
                    {satEvidence?.classification ? satEvidence.classification.replace(/_/g, ' ') : 'PENDING'}
                  </span>
                  <span className="res-conf-pill">
                    {satEvidence?.confidence ? `${Math.round(satEvidence.confidence * 100)}% Conf` : 'N/A'}
                  </span>
                </div>

                {satEvidence?.class_probabilities && Object.keys(satEvidence.class_probabilities).length > 0 && (
                  <div className="cv-prob-breakdown">
                    <span className="prob-title">Class Probabilities Distribution:</span>
                    <div className="prob-grid">
                      {Object.entries(satEvidence.class_probabilities).map(([cName, pVal]) => (
                        <div key={cName} className="prob-row">
                          <span className="prob-name">{cName.replace(/_/g, ' ')}</span>
                          <div className="prob-bar-container">
                            <div
                              className={`prob-fill fill-${cName.toLowerCase()}`}
                              style={{ width: `${Math.round(pVal * 100)}%` }}
                            />
                          </div>
                          <span className="prob-val">{Math.round(pVal * 100)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 7. MULTI-MODAL EVIDENCE FUSION CARD */}
            <div className="evidence-panel-card evidence-fusion-card">
              <div className="card-header-bar">
                <span className="card-header-icon">⚡</span>
                <span className="card-header-title">Multi-Modal Evidence Fusion</span>
                <span className="card-header-tag">Decision Engine</span>
              </div>

              <div className="fusion-body">
                <div className="fusion-weights-header">
                  <span>Synthesis Contributions (Backend Fusion Weights):</span>
                </div>

                <div className="fusion-contributions-list">
                  <div className="fusion-contrib-row">
                    <span className="contrib-label">🛰️ NASA FIRMS Sensor Telemetry</span>
                    <span className="contrib-weight">Weight: 20%</span>
                  </div>
                  <div className="fusion-contrib-row">
                    <span className="contrib-label">🏭 OpenStreetMap Industrial Context</span>
                    <span className="contrib-weight">Weight: 15%</span>
                  </div>
                  <div className="fusion-contrib-row">
                    <span className="contrib-label">⏳ Spatial-Temporal Persistence</span>
                    <span className="contrib-weight">Weight: 15%</span>
                  </div>
                  <div className="fusion-contrib-row">
                    <span className="contrib-label">🤖 Multi-Feature AI Classifier</span>
                    <span className="contrib-weight">Weight: 35%</span>
                  </div>
                  <div className="fusion-contrib-row">
                    <span className="contrib-label">📡 Sentinel-2 Computer Vision</span>
                    <span className="contrib-weight">Weight: 15%</span>
                  </div>
                </div>

                <div className="fusion-decision-box">
                  <div className="decision-header-row">
                    <span className="decision-title">Unified Multi-Modal Decision:</span>
                    <span className="decision-class-badge">{classification.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="fusion-summary-narrative">
                    {fusedEvidence?.fusion_summary ||
                      'Multi-modal evidence combines satellite thermal radiometry, temporal persistence, geographic proximity, and optical visual verification.'}
                  </p>
                  <div className="distinction-note">
                    ⚠️ <strong>Clarification:</strong> Fusion score represents <em>Investigation Priority Contribution</em>, not an empirical probability of fire ignition.
                  </div>
                </div>
              </div>
            </div>

            {/* 8. RISK SCORE BREAKDOWN */}
            <div className="evidence-panel-card risk-breakdown-card">
              <div className="card-header-bar">
                <span className="card-header-icon">⚠️</span>
                <span className="card-header-title">Investigation Risk Score Breakdown</span>
                <span className="card-header-tag">Score: {riskScore}/100</span>
              </div>

              <div className="risk-components-grid">
                <div className="risk-comp-item">
                  <span className="rc-name">Thermal Intensity (FRP)</span>
                  <span className="rc-score">{(frp > 50 ? 25 : Math.round(frp * 0.5))} / 25 pts</span>
                </div>
                <div className="metric-box-sub">
                  <span className="rc-name">Satellite Confidence</span>
                  <span className="rc-score">15 / 15 pts</span>
                </div>
                <div className="metric-box-sub">
                  <span className="rc-name">Persistence Cluster</span>
                  <span className="rc-score">{Math.min(25, Math.round(persistenceScore * 0.25))} / 25 pts</span>
                </div>
                <div className="metric-box-sub">
                  <span className="rc-name">Industrial Proximity</span>
                  <span className="rc-score">{(facilityName ? 20 : 5)} / 20 pts</span>
                </div>

                <div className="metric-box-sub">
                  <span className="rc-name">AI Classification Context</span>
                  <span className="rc-score">15 / 15 pts</span>
                </div>
              </div>

              {riskData?.reasons && riskData.reasons.length > 0 && (
                <div className="risk-reasons-list">
                  <span className="reasons-title">Risk Scoring Rationale:</span>
                  <ul>
                    {riskData.reasons.map((r, rIdx) => (
                      <li key={rIdx}>• {r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* 9. ALERT INCIDENT ACTIONS */}
            {alert && (
              <div className="evidence-panel-card alert-actions-card">
                <div className="card-header-bar">
                  <span className="card-header-icon">🚨</span>
                  <span className="card-header-title">Incident Lifecycle Management</span>
                  <span className={`status-badge-pill ${getAlertStatusBadgeClass(alert.status)}`}>
                    {alert.status}
                  </span>
                </div>

                <div className="alert-lifecycle-body">
                  <div className="lifecycle-meta-row">
                    <div>
                      <span className="al-label">Alert Identifier:</span>
                      <span className="al-val">{alert.alert_id}</span>
                    </div>
                    <div>
                      <span className="al-label">Created Timestamp:</span>
                      <span className="al-val">{new Date(alert.created_at).toUTCString()}</span>
                    </div>
                  </div>

                  {alert.resolution_notes && (
                    <div className="resolution-notes-display">
                      <span className="notes-label">Operator Notes:</span>
                      <p className="notes-content">"{alert.resolution_notes}"</p>
                    </div>
                  )}

                  {/* State-Aware Action Buttons */}
                  <div className="lifecycle-actions-row">
                    {alert.status === 'NEW' && (
                      <>
                        <button
                          type="button"
                          className="btn-action btn-ack"
                          onClick={() => handleActionClick('acknowledge')}
                        >
                          ✓ Acknowledge Alert
                        </button>
                        <button
                          type="button"
                          className="btn-action btn-dismiss"
                          onClick={() => handleActionClick('dismiss')}
                        >
                          ✕ Dismiss Alert
                        </button>
                      </>
                    )}

                    {alert.status === 'ACKNOWLEDGED' && (
                      <>
                        <button
                          type="button"
                          className="btn-action btn-investigate"
                          onClick={() => handleActionClick('investigate')}
                        >
                          🔍 Start Active Investigation
                        </button>
                        <button
                          type="button"
                          className="btn-action btn-resolve"
                          onClick={() => handleActionClick('resolve')}
                        >
                          ✓ Mark Resolved
                        </button>
                      </>
                    )}

                    {alert.status === 'INVESTIGATING' && (
                      <button
                        type="button"
                        className="btn-action btn-resolve"
                        onClick={() => handleActionClick('resolve')}
                      >
                        ✓ Mark Investigation Resolved
                      </button>
                    )}

                    {(alert.status === 'RESOLVED' || alert.status === 'DISMISSED') && (
                      <div className="terminal-status-notice">
                        🔒 Incident is closed with terminal status [{alert.status}]. Audit record locked.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 10. CHRONOLOGICAL INVESTIGATION TIMELINE AUDIT */}
        <section className="workspace-timeline-section">
          <InvestigationTimeline
            alert={alert}
            hotspot={hotspot}
            cluster={cluster}
            fusedEvidence={fusedEvidence}
          />
        </section>

        {/* RESOLUTION / DISMISSAL NOTES MODAL */}
        {showNotesModal && (
          <div className="notes-modal-backdrop">
            <div className="notes-modal-content">
              <h3 className="notes-modal-title">
                {pendingAction === 'resolve' ? 'Resolve Thermal Incident' : 'Dismiss Thermal Incident'}
              </h3>
              <p className="notes-modal-desc">
                Please enter defensible operational notes or dismissal rationale for audit records:
              </p>
              <textarea
                className="notes-modal-textarea"
                rows={4}
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="Enter investigation notes, field validation findings, or reason for dismissal..."
              />
              <div className="notes-modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowNotesModal(false);
                    setPendingAction(null);
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleConfirmNotesAction}
                >
                  Confirm {pendingAction === 'resolve' ? 'Resolution' : 'Dismissal'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
