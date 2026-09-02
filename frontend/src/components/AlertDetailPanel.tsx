import React, { useState, useEffect } from 'react';
import { ThermalAlert, FusedEvidenceResponse } from '../types/hotspot';
import { SatelliteEvidenceCard } from './SatelliteEvidenceCard';

interface AlertDetailPanelProps {
  alert: ThermalAlert | null;
  onClose: () => void;
  onStatusChange: (alertId: string, action: 'acknowledge' | 'investigate' | 'resolve' | 'dismiss', notes?: string) => void;
}

export const AlertDetailPanel: React.FC<AlertDetailPanelProps> = ({
  alert,
  onClose,
  onStatusChange,
}) => {
  const [resolutionNotes, setResolutionNotes] = useState<string>('');
  const [showNotesInput, setShowNotesInput] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<'resolve' | 'dismiss' | null>(null);
  
  const [fusedEvidence, setFusedEvidence] = useState<FusedEvidenceResponse | null>(null);
  const [loadingSatellite, setLoadingSatellite] = useState<boolean>(false);

  useEffect(() => {
    if (alert) {
      setLoadingSatellite(true);
      const frp = Number(alert.features?.frp || 0);
      const brightness = Number(alert.features?.brightness || 320);
      const url = `http://127.0.0.1:8000/api/satellite/evidence?lat=${alert.latitude}&lon=${alert.longitude}&frp=${frp}&brightness=${brightness}&persistence_score=${alert.persistence_score}`;

      fetch(url)
        .then((res) => res.json())
        .then((data) => {
          setFusedEvidence(data);
          setLoadingSatellite(false);
        })
        .catch(() => {
          setFusedEvidence(null);
          setLoadingSatellite(false);
        });
    } else {
      setFusedEvidence(null);
    }
  }, [alert]);

  if (!alert) return null;

  const getStatusBadgeClass = (st: string) => {
    switch (st) {
      case 'NEW':
        return 'status-badge-new';
      case 'ACKNOWLEDGED':
        return 'status-badge-ack';
      case 'INVESTIGATING':
        return 'status-badge-investigating';
      case 'RESOLVED':
        return 'status-badge-resolved';
      case 'DISMISSED':
        return 'status-badge-dismissed';
      default:
        return '';
    }
  };

  const getRiskBadgeClass = (lvl: string) => {
    switch (lvl) {
      case 'CRITICAL':
        return 'risk-badge-critical';
      case 'HIGH':
        return 'risk-badge-high';
      case 'MODERATE':
        return 'risk-badge-medium';
      default:
        return 'risk-badge-low';
    }
  };

  const handleActionClick = (action: 'acknowledge' | 'investigate' | 'resolve' | 'dismiss') => {
    if (action === 'resolve' || action === 'dismiss') {
      setPendingAction(action);
      setShowNotesInput(true);
    } else {
      onStatusChange(alert.alert_id, action);
    }
  };

  const handleConfirmNotesAction = () => {
    if (pendingAction) {
      onStatusChange(alert.alert_id, pendingAction, resolutionNotes);
      setShowNotesInput(false);
      setPendingAction(null);
      setResolutionNotes('');
    }
  };

  return (
    <div className="context-panel alert-detail-panel">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">Thermal Event Alert Details</h3>
          <p className="panel-subtitle">ID: {alert.alert_id}</p>
        </div>
        <button className="panel-close-btn" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="panel-body">
        {/* Status Header & Risk Gauge */}
        <div className="alert-meta-card">
          <div className="alert-status-row">
            <span className="summary-label">Alert Status:</span>
            <span className={`alert-status-badge ${getStatusBadgeClass(alert.status)}`}>
              {alert.status}
            </span>
          </div>

          <div className="alert-risk-row">
            <span className="summary-label">Investigation Risk Priority:</span>
            <span className={`risk-level-badge ${getRiskBadgeClass(alert.risk_level)}`}>
              {alert.risk_score} / 100 ({alert.risk_level})
            </span>
          </div>
        </div>

        {/* Phase 8 Satellite Image Evidence Card */}
        <SatelliteEvidenceCard
          fusedEvidence={fusedEvidence}
          loading={loadingSatellite}
        />

        {/* Classification Card */}
        <div className="alert-section-box">
          <div className="box-title">🤖 AI Candidate Classification</div>
          <div className="box-content">
            <div className="highlight-text">{alert.classification.replace(/_/g, ' ')}</div>
            <div className="small-meta">Model Source: {alert.model_source}</div>
          </div>
        </div>

        {/* Location & Facility Context */}
        <div className="alert-section-box">
          <div className="box-title">📍 Location & Infrastructure Proximity</div>
          <div className="box-content">
            <div className="meta-row">
              <span>Coordinates:</span>
              <span className="font-bold">{alert.latitude.toFixed(4)}, {alert.longitude.toFixed(4)}</span>
            </div>
            <div className="meta-row">
              <span>Industrial Facility:</span>
              <span className="font-bold">{alert.facility_name || 'None mapped'}</span>
            </div>
            <div className="meta-row">
              <span>Distance to Infrastructure:</span>
              <span className="font-bold highlight-frp">
                {alert.industrial_distance_km !== null ? `${alert.industrial_distance_km} km` : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Persistence Metrics */}
        <div className="alert-section-box">
          <div className="box-title">🕐 Spatial-Temporal Persistence</div>
          <div className="box-content">
            <div className="meta-row">
              <span>Persistence Score:</span>
              <span className="font-bold">{alert.persistence_score} / 100</span>
            </div>
            <div className="meta-row">
              <span>Satellite Observations:</span>
              <span className="font-bold">{alert.observation_count} passes</span>
            </div>
            <div className="meta-row">
              <span>Thermal Duration:</span>
              <span className="font-bold">{alert.duration_hours} hours</span>
            </div>
          </div>
        </div>

        {/* Supporting Evidence List */}
        <div className="alert-section-box">
          <div className="box-title">📋 Supporting Evidence Rationale</div>
          <ul className="alert-evidence-list">
            {alert.evidence.map((ev, idx) => (
              <li key={`ev-${idx}`} className="evidence-item">
                ✓ {ev}
              </li>
            ))}
          </ul>
        </div>

        {/* Action Controls based on State Machine */}
        <div className="alert-actions-section">
          <div className="actions-title">Operator Incident Actions:</div>

          {showNotesInput ? (
            <div className="notes-input-container">
              <label className="filter-label">Enter Notes for {pendingAction?.toUpperCase()}:</label>
              <textarea
                className="filter-input"
                rows={2}
                placeholder="Optional incident notes..."
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
              />
              <div className="action-btn-row">
                <button className="btn btn-primary btn-sm" onClick={handleConfirmNotesAction}>
                  Confirm {pendingAction?.toUpperCase()}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => setShowNotesInput(false)}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="action-btn-row">
              {alert.status === 'NEW' && (
                <>
                  <button className="btn btn-primary" onClick={() => handleActionClick('acknowledge')}>
                    ✓ Acknowledge Alert
                  </button>
                  <button className="btn btn-secondary" onClick={() => handleActionClick('dismiss')}>
                    ✕ Dismiss
                  </button>
                </>
              )}

              {alert.status === 'ACKNOWLEDGED' && (
                <>
                  <button className="btn btn-primary" onClick={() => handleActionClick('investigate')}>
                    🔍 Start Investigation
                  </button>
                  <button className="btn btn-secondary" onClick={() => handleActionClick('resolve')}>
                    ✅ Resolve Alert
                  </button>
                  <button className="btn btn-secondary" onClick={() => handleActionClick('dismiss')}>
                    ✕ Dismiss
                  </button>
                </>
              )}

              {alert.status === 'INVESTIGATING' && (
                <>
                  <button className="btn btn-primary" onClick={() => handleActionClick('resolve')}>
                    ✅ Mark as Resolved
                  </button>
                  <button className="btn btn-secondary" onClick={() => handleActionClick('dismiss')}>
                    ✕ Dismiss
                  </button>
                </>
              )}

              {(alert.status === 'RESOLVED' || alert.status === 'DISMISSED') && (
                <div className="terminal-state-text">
                  Incident is {alert.status}. Resolved by {alert.resolved_by || 'Operator'} at {alert.resolved_at}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
