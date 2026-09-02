import React, { useState } from 'react';
import { ThermalAlert } from '../types/hotspot';

interface AlertHistoryProps {
  alerts: ThermalAlert[];
  loading: boolean;
  onSelectAlert: (alert: ThermalAlert) => void;
}

export const AlertHistory: React.FC<AlertHistoryProps> = ({
  alerts,
  loading,
  onSelectAlert,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filtered = alerts.filter((a) => {
    if (a.status !== 'RESOLVED' && a.status !== 'DISMISSED') return false;
    if (statusFilter !== 'ALL' && a.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="alert-dashboard-card history-card">
      <div className="table-card-header">
        <div>
          <h3 className="table-card-title">📜 Resolved & Dismissed Incident Audit History</h3>
          <p className="table-card-subtitle">Archived historical alert records with resolution notes</p>
        </div>

        <div className="filter-group">
          <label className="filter-label">Filter Status:</label>
          <select
            className="filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All Archived (Resolved & Dismissed)</option>
            <option value="RESOLVED">Resolved Only</option>
            <option value="DISMISSED">Dismissed Only</option>
          </select>
        </div>
      </div>

      <div className="table-card-body">
        {loading ? (
          <div className="table-loading">
            <div className="spinner-small" />
            <span>Loading alert history...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="table-empty">No archived incident records match the filter.</div>
        ) : (
          <div className="table-wrapper">
            <table className="ranking-table alert-table">
              <thead>
                <tr>
                  <th>Alert ID</th>
                  <th>Risk Score</th>
                  <th>Classification</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Resolved At</th>
                  <th>Operator</th>
                  <th>Resolution Notes</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((alt) => (
                  <tr key={alt.alert_id} onClick={() => onSelectAlert(alt)}>
                    <td className="loc-id">{alt.alert_id}</td>
                    <td className="score-cell font-bold">{alt.risk_score} / 100</td>
                    <td className="cat-cell">{alt.classification.replace('_', ' ')}</td>
                    <td className="loc-coords">{alt.latitude.toFixed(3)}, {alt.longitude.toFixed(3)}</td>
                    <td>
                      <span className={`alert-status-badge status-badge-${alt.status.toLowerCase()}`}>
                        {alt.status}
                      </span>
                    </td>
                    <td className="time-cell">{alt.resolved_at || alt.updated_at}</td>
                    <td>{alt.resolved_by || 'Operator'}</td>
                    <td className="notes-cell">{alt.resolution_notes || 'None'}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button className="btn btn-secondary btn-sm" onClick={() => onSelectAlert(alt)}>
                        🔍 View Audit
                      </button>
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
