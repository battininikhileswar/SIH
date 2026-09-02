import React from 'react';
import { ThermalAlert } from '../types/hotspot';

interface AlertDashboardProps {
  alerts: ThermalAlert[];
  loading: boolean;
  onSelectAlert: (alert: ThermalAlert) => void;
  onStatusChange: (alertId: string, action: 'acknowledge' | 'investigate' | 'resolve' | 'dismiss') => void;
}

export const AlertDashboard: React.FC<AlertDashboardProps> = ({
  alerts,
  loading,
  onSelectAlert,
  onStatusChange,
}) => {
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
      default:
        return 'status-badge-dismissed';
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

  return (
    <div className="alert-dashboard-card">
      <div className="table-card-header">
        <div>
          <h3 className="table-card-title">🚨 Active Thermal Event Incident Queue</h3>
          <p className="table-card-subtitle">Auto-triggered alerts sorted by priority (CRITICAL first, highest risk score first)</p>
        </div>
        <span className="event-count-badge">{alerts.length} Unresolved Incidents</span>
      </div>

      <div className="table-card-body">
        {loading ? (
          <div className="table-loading">
            <div className="spinner-small" />
            <span>Syncing active incident queue...</span>
          </div>
        ) : alerts.length === 0 ? (
          <div className="table-empty">No active thermal event alerts pending operator action.</div>
        ) : (
          <div className="table-wrapper">
            <table className="ranking-table alert-table">
              <thead>
                <tr>
                  <th>Alert ID</th>
                  <th>Risk Score</th>
                  <th>Priority Level</th>
                  <th>AI Candidate</th>
                  <th>Location</th>
                  <th>Industrial Facility</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th>Incident Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alt) => (
                  <tr key={alt.alert_id} onClick={() => onSelectAlert(alt)}>
                    <td className="loc-id">{alt.alert_id}</td>
                    <td className="score-cell font-bold">{alt.risk_score} / 100</td>
                    <td>
                      <span className={`risk-level-badge ${getRiskBadgeClass(alt.risk_level)}`}>
                        {alt.risk_level}
                      </span>
                    </td>
                    <td className="cat-cell">{alt.classification.replace('_', ' ')}</td>
                    <td className="loc-coords">
                      {alt.latitude.toFixed(3)}, {alt.longitude.toFixed(3)}
                    </td>
                    <td className="facility-cell">
                      {alt.facility_name ? `${alt.facility_name} (${alt.industrial_distance_km} km)` : 'None'}
                    </td>
                    <td>
                      <span className={`alert-status-badge ${getStatusBadgeClass(alt.status)}`}>
                        {alt.status}
                      </span>
                    </td>
                    <td className="time-cell">{alt.created_at.split(' ')[1]}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <div className="table-btn-row">
                        {alt.status === 'NEW' && (
                          <button className="btn btn-primary btn-sm" onClick={() => onStatusChange(alt.alert_id, 'acknowledge')}>
                            ✓ Ack
                          </button>
                        )}
                        {alt.status === 'ACKNOWLEDGED' && (
                          <button className="btn btn-primary btn-sm" onClick={() => onStatusChange(alt.alert_id, 'investigate')}>
                            🔍 Investigate
                          </button>
                        )}
                        {alt.status === 'INVESTIGATING' && (
                          <button className="btn btn-secondary btn-sm" onClick={() => onStatusChange(alt.alert_id, 'resolve')}>
                            ✅ Resolve
                          </button>
                        )}
                        <button className="btn btn-secondary btn-sm" onClick={() => onSelectAlert(alt)}>
                          📋 Details
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
