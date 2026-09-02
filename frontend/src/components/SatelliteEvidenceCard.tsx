import React from 'react';
import { FusedEvidenceResponse, SatelliteEvidence } from '../types/hotspot';

interface SatelliteEvidenceCardProps {
  fusedEvidence: FusedEvidenceResponse | null;
  satelliteData?: SatelliteEvidence | null;
  loading?: boolean;
}

export const SatelliteEvidenceCard: React.FC<SatelliteEvidenceCardProps> = ({
  fusedEvidence,
  satelliteData,
  loading = false,
}) => {
  const sat: SatelliteEvidence | undefined = fusedEvidence?.evidence?.satellite || satelliteData || undefined;
  const isAvailable = sat?.image_available ?? false;

  if (loading) {
    return (
      <div className="satellite-card loading-skeleton">
        <div className="skeleton-title">🔍 Retrieving Satellite Optical Patch...</div>
      </div>
    );
  }

  const getClassificationBadgeClass = (cls: string) => {
    switch (cls) {
      case 'INDUSTRIAL_FIRE':
      case 'INDUSTRIAL_FIRE_CANDIDATE':
        return 'badge-industrial-fire';
      case 'NATURAL_FIRE':
      case 'WILDFIRE_CANDIDATE':
        return 'badge-wildfire';
      case 'PERSISTENT_THERMAL_SOURCE':
        return 'badge-persistent';
      case 'NON_FIRE':
        return 'badge-non-fire';
      default:
        return 'badge-unknown';
    }
  };

  const API_BASE = 'http://127.0.0.1:8000';
  const imageUrl = sat?.image_url ? (sat.image_url.startsWith('http') ? sat.image_url : `${API_BASE}${sat.image_url}`) : null;

  return (
    <div className="satellite-evidence-card">
      <div className="card-header-row">
        <div className="card-title-text">
          <span>📡 Satellite Image Intelligence</span>
          <span className="source-tag">{sat?.source || 'Sentinel-2 L2A'}</span>
        </div>
        {isAvailable ? (
          <span className="status-tag status-available">✓ VERIFIED OPTICAL PATCH</span>
        ) : (
          <span className="status-tag status-unconfigured">⚠️ IMAGERY UNCONFIGURED</span>
        )}
      </div>

      {/* Image Patch Preview Container */}
      <div className="satellite-patch-container">
        {imageUrl ? (
          <div className="patch-image-wrapper">
            <img src={imageUrl} alt="Satellite Thermal Patch" className="satellite-patch-img" />
            <div className="patch-overlay-caption">
              <span>{sat?.source || 'Sentinel-2'}</span>
              <span>{sat?.captured_at || 'Observation UTC'}</span>
            </div>
          </div>
        ) : (
          <div className="satellite-patch-placeholder">
            <div className="placeholder-icon">🛰️</div>
            <div className="placeholder-text">
              {sat?.visual_evidence || 'Satellite credentials missing (SATELLITE_API_KEY).'}
            </div>
          </div>
        )}
      </div>

      {/* AI Visual Classification Results */}
      <div className="satellite-analysis-box">
        <div className="analysis-row">
          <span className="label-text">Visual AI Classification:</span>
          <span className={`classification-badge ${getClassificationBadgeClass(sat?.classification || 'UNKNOWN')}`}>
            {(sat?.classification || 'UNKNOWN').replace(/_/g, ' ')}
          </span>
        </div>

        <div className="analysis-row">
          <span className="label-text">Visual AI Confidence:</span>
          <div className="confidence-meter-container">
            <div
              className="confidence-bar-fill"
              style={{ width: `${Math.round((sat?.confidence || 0) * 100)}%` }}
            ></div>
            <span className="confidence-text">{Math.round((sat?.confidence || 0) * 100)}%</span>
          </div>
        </div>

        <div className="visual-evidence-description">
          <strong>Visual Evidence Rationale:</strong>
          <p>{sat?.visual_evidence || 'Multi-spectral satellite optical patch supports thermal anomaly verification.'}</p>
        </div>

        {/* Multi-Modal Fusion Rationale Summary if available */}
        {fusedEvidence && (
          <div className="fusion-summary-box">
            <div className="fusion-header">
              ⚡ Multi-Modal Decision Fusion (FIRMS + OSM + Persistence + Satellite)
            </div>
            <div className="fusion-decision-row">
              <span>Combined AI Decision: <strong>{fusedEvidence.final_classification.replace(/_/g, ' ')}</strong></span>
              <span className="fusion-conf-pill">{fusedEvidence.combined_confidence_percentage}% Confidence</span>
            </div>
            <p className="fusion-summary-text">{fusedEvidence.fusion_summary}</p>
          </div>
        )}
      </div>
    </div>
  );
};
