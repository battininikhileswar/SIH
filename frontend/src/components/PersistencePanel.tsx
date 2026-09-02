import React, { useEffect, useState } from 'react';
import { PersistentCluster, AiClassificationResponse, RiskScoreResponse } from '../types/hotspot';
import { AiClassificationCard } from './AiClassificationCard';
import { RiskScoreCard } from './RiskScoreCard';

interface PersistencePanelProps {
  cluster: PersistentCluster | null;
  onClose: () => void;
}

export const PersistencePanel: React.FC<PersistencePanelProps> = ({ cluster, onClose }) => {
  const [aiData, setAiData] = useState<AiClassificationResponse | null>(null);
  const [riskData, setRiskData] = useState<RiskScoreResponse | null>(null);
  const [panelLoading, setPanelLoading] = useState<boolean>(false);
  const [panelError, setPanelError] = useState<string | null>(null);

  useEffect(() => {
    if (!cluster) return;

    const fetchAiAndRisk = async () => {
      setPanelLoading(true);
      setPanelError(null);
      try {
        const topObs = cluster.observations[0] || {};
        const queryParams = `lat=${cluster.center_latitude}&lon=${cluster.center_longitude}&frp=${topObs.frp || 0}&brightness=${topObs.brightness || 320}&confidence=${topObs.confidence || 'nominal'}&observation_count=${cluster.observation_count}&duration_hours=${cluster.duration_hours}&spatial_radius_km=${cluster.spatial_radius_km}&persistence_score=${cluster.persistence_score}`;

        const [aiRes, riskRes] = await Promise.all([
          fetch(`http://127.0.0.1:8000/api/hotspots/classify?${queryParams}`),
          fetch(`http://127.0.0.1:8000/api/hotspots/risk?${queryParams}`)
        ]);

        if (!aiRes.ok || !riskRes.ok) {
          throw new Error('API server error');
        }

        const aiJson: AiClassificationResponse = await aiRes.json();
        const riskJson: RiskScoreResponse = await riskRes.json();

        setAiData(aiJson);
        setRiskData(riskJson);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Unable to fetch evaluation';
        setPanelError(msg);
      } finally {
        setPanelLoading(false);
      }
    };

    fetchAiAndRisk();
  }, [cluster]);

  if (!cluster) return null;

  const getScoreBadgeClass = (score: number) => {
    if (score >= 81) return 'score-badge-critical';
    if (score >= 61) return 'score-badge-high';
    if (score >= 31) return 'score-badge-medium';
    return 'score-badge-low';
  };

  return (
    <div className="context-panel persistence-panel">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">Persistent Thermal Source</h3>
          <p className="panel-subtitle">Spatial-Temporal Satellite Cluster Analysis</p>
        </div>
        <button className="panel-close-btn" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="panel-body">
        {/* Cluster ID & Persistence Score Card */}
        <div className="cluster-score-card">
          <div className="cluster-id-row">
            <span className="cluster-id-label">Cluster ID:</span>
            <span className="cluster-id-val">{cluster.cluster_id}</span>
          </div>

          <div className="score-meter-container">
            <div className="score-meter-header">
              <span className="score-label">Persistence Score</span>
              <span className={`score-badge ${getScoreBadgeClass(cluster.persistence_score)}`}>
                {cluster.persistence_score} / 100
              </span>
            </div>
            <div className="score-bar-bg">
              <div
                className={`score-bar-fill ${getScoreBadgeClass(cluster.persistence_score)}`}
                style={{ width: `${cluster.persistence_score}%` }}
              />
            </div>
            <div className="classification-pill">{cluster.classification}</div>
          </div>
        </div>

        {/* Risk Priority Score Card */}
        <RiskScoreCard
          riskData={riskData}
          loading={panelLoading}
          error={panelError}
        />

        {/* Explainable AI Classification Card */}
        <AiClassificationCard
          classificationData={aiData}
          loading={panelLoading}
          error={panelError}
        />

        {/* Insufficient History Warning */}
        {!cluster.has_sufficient_history && (
          <div className="panel-warning">
            ⚠️ <strong>Data Limitation Notice:</strong> Insufficient historical FIRMS observations available in the current window for temporal persistence analysis.
          </div>
        )}

        {/* Spatial & Temporal Metrics Grid */}
        <div className="metrics-grid">
          <div className="metric-box">
            <span className="metric-title">Observations</span>
            <span className="metric-value">{cluster.observation_count}</span>
          </div>
          <div className="metric-box">
            <span className="metric-title">Duration</span>
            <span className="metric-value">{cluster.duration_hours} hrs</span>
          </div>
          <div className="metric-box">
            <span className="metric-title">Cluster Radius</span>
            <span className="metric-value">{cluster.spatial_radius_km} km</span>
          </div>
          <div className="metric-box">
            <span className="metric-title">Center Lat/Lon</span>
            <span className="metric-value">{cluster.center_latitude.toFixed(3)}, {cluster.center_longitude.toFixed(3)}</span>
          </div>
        </div>

        {/* Nearby Industrial Context Integration */}
        {cluster.industrial_context && cluster.industrial_context.nearby_facility && (
          <div className="facility-context-card">
            <div className="facility-card-header">🏭 NEARBY INDUSTRIAL FACILITY</div>
            <div className="facility-card-body">
              <div className="facility-name">{cluster.industrial_context.nearby_facility}</div>
              <div className="facility-meta">
                <span>Category: {cluster.industrial_context.facility_category?.replace('_', ' ')}</span>
                <span className="highlight-frp">Distance: {cluster.industrial_context.distance_km} km</span>
              </div>
            </div>
          </div>
        )}

        {/* Observation Timeline Widget */}
        <div className="timeline-section">
          <div className="section-header">
            <span>Observation Timeline ({cluster.observations.length})</span>
            <span className="timeline-span">
              {cluster.first_detected.split(' ')[1]} - {cluster.last_detected.split(' ')[1]}
            </span>
          </div>

          <div className="timeline-list">
            {cluster.observations.map((obs, idx) => (
              <div key={`obs-${idx}`} className="timeline-item">
                <div className="timeline-dot">🔥</div>
                <div className="timeline-content">
                  <div className="timeline-time">{obs.acquired_at}</div>
                  <div className="timeline-details">
                    <span>{obs.satellite} ({obs.instrument})</span>
                    <span className="highlight-frp">{obs.frp} MW / {obs.brightness} K</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
