import React, { useEffect, useState } from 'react';
import { Hotspot, HotspotContextResponse, AiClassificationResponse, RiskScoreResponse, FusedEvidenceResponse } from '../types/hotspot';
import { AiClassificationCard } from './AiClassificationCard';
import { RiskScoreCard } from './RiskScoreCard';
import { SatelliteEvidenceCard } from './SatelliteEvidenceCard';

interface ContextPanelProps {
  selectedHotspot: Hotspot | null;
  contextData: HotspotContextResponse | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

export const ContextPanel: React.FC<ContextPanelProps> = ({
  selectedHotspot,
  contextData,
  loading,
  error,
  onClose,
}) => {
  const [aiData, setAiData] = useState<AiClassificationResponse | null>(null);
  const [riskData, setRiskData] = useState<RiskScoreResponse | null>(null);
  const [fusedEvidence, setFusedEvidence] = useState<FusedEvidenceResponse | null>(null);
  const [panelLoading, setPanelLoading] = useState<boolean>(false);
  const [panelError, setPanelError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedHotspot) return;

    const fetchAiAndRisk = async () => {
      setPanelLoading(true);
      setPanelError(null);
      try {
        const queryParams = `lat=${selectedHotspot.latitude}&lon=${selectedHotspot.longitude}&frp=${selectedHotspot.frp}&brightness=${selectedHotspot.brightness}&confidence=${selectedHotspot.confidence}`;
        
        const [aiRes, riskRes, satRes] = await Promise.all([
          fetch(`http://127.0.0.1:8000/api/hotspots/classify?${queryParams}`),
          fetch(`http://127.0.0.1:8000/api/hotspots/risk?${queryParams}`),
          fetch(`http://127.0.0.1:8000/api/satellite/evidence?${queryParams}`)
        ]);

        if (!aiRes.ok || !riskRes.ok) {
          throw new Error('API server error');
        }

        const aiJson: AiClassificationResponse = await aiRes.json();
        const riskJson: RiskScoreResponse = await riskRes.json();
        const satJson: FusedEvidenceResponse = satRes.ok ? await satRes.json() : null;

        setAiData(aiJson);
        setRiskData(riskJson);
        setFusedEvidence(satJson);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Unable to fetch evaluation';
        setPanelError(msg);
      } finally {
        setPanelLoading(false);
      }
    };

    fetchAiAndRisk();
  }, [selectedHotspot]);

  if (!selectedHotspot) return null;

  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case 'INDUSTRIAL':
        return <span className="ctx-badge badge-industrial">🏭 INDUSTRIAL ZONE</span>;
      case 'URBAN':
        return <span className="ctx-badge badge-urban">🏠 URBAN AREA</span>;
      case 'RURAL_OR_AGRICULTURAL':
        return <span className="ctx-badge badge-rural">🌾 RURAL / AGRICULTURAL</span>;
      default:
        return <span className="ctx-badge badge-unknown">❓ UNKNOWN CONTEXT</span>;
    }
  };

  const getFeatureIcon = (type: string) => {
    switch (type) {
      case 'industrial':
        return '🏭';
      case 'power':
        return '⚡';
      case 'urban':
        return '🏠';
      case 'road':
        return '🛣';
      default:
        return '📍';
    }
  };

  return (
    <div className="context-panel">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">Location Context</h3>
          <p className="panel-subtitle">OpenStreetMap Proximity & Satellite Intelligence</p>
        </div>
        <button className="panel-close-btn" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="panel-body">
        {/* Hotspot Summary Card */}
        <div className="hotspot-summary-card">
          <div className="summary-row">
            <span className="summary-label">Target Hotspot:</span>
            <span className="summary-val">{selectedHotspot.satellite} ({selectedHotspot.instrument})</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">Coordinates:</span>
            <span className="summary-val">{selectedHotspot.latitude.toFixed(4)}, {selectedHotspot.longitude.toFixed(4)}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">FRP / Brightness:</span>
            <span className="summary-val highlight-frp">{selectedHotspot.frp} MW / {selectedHotspot.brightness} K</span>
          </div>
        </div>

        {/* Phase 8 Satellite Image Evidence */}
        <SatelliteEvidenceCard
          fusedEvidence={fusedEvidence}
          loading={panelLoading}
        />

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

        {/* Loading State */}
        {loading && (
          <div className="panel-loading">
            <div className="spinner-small" />
            <span>Querying OpenStreetMap nearby features...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="panel-error">
            <span>⚠️ {error}</span>
          </div>
        )}

        {/* Context Content */}
        {!loading && !error && contextData && (
          <>
            <div className="classification-section">
              <span className="section-label">Geospatial Context:</span>
              {getClassificationBadge(contextData.context_classification)}
            </div>

            <div className="features-section">
              <div className="section-header">
                <span>Nearby Features ({contextData.search_radius_km} km radius)</span>
                <span className="feature-count">{contextData.facility_count} found</span>
              </div>

              {contextData.nearby_features.length === 0 ? (
                <p className="no-features-text">No major industrial or urban features mapped in OSM within {contextData.search_radius_km} km.</p>
              ) : (
                <div className="features-list">
                  {contextData.nearby_features.map((feature, index) => (
                    <div key={`${feature.osm_id}-${index}`} className={`feature-item feature-type-${feature.type}`}>
                      <div className="feature-icon">{getFeatureIcon(feature.type)}</div>
                      <div className="feature-info">
                        <div className="feature-name">{feature.name}</div>
                        <div className="feature-meta">
                          <span className="feature-cat">{feature.category.replace('_', ' ')}</span>
                          <span className="feature-dist">{feature.distance_km} km away</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
