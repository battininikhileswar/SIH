import React from 'react';
import { PriorityRankingItem } from '../types/hotspot';

interface PriorityTableProps {
  items: PriorityRankingItem[];
  loading: boolean;
  onSelectEvent: (item: PriorityRankingItem) => void;
}

export const PriorityTable: React.FC<PriorityTableProps> = ({
  items,
  loading,
  onSelectEvent,
}) => {
  const getRiskBadgeClass = (level: string) => {
    switch (level) {
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
    <div className="priority-table-card">
      <div className="table-card-header">
        <div>
          <h3 className="table-card-title">Highest Risk Thermal Events</h3>
          <p className="table-card-subtitle">Prioritized investigation queue sorted by Risk Score (0 - 100)</p>
        </div>
        <span className="event-count-badge">{items.length} High Priority Events</span>
      </div>

      <div className="table-card-body">
        {loading ? (
          <div className="table-loading">
            <div className="spinner-small" />
            <span>Ranking thermal events by investigation priority...</span>
          </div>
        ) : items.length === 0 ? (
          <div className="table-empty">No high priority thermal events detected.</div>
        ) : (
          <div className="table-wrapper">
            <table className="ranking-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Location / ID</th>
                  <th>Risk Score</th>
                  <th>Priority Level</th>
                  <th>AI Classification</th>
                  <th>Industrial Facility</th>
                  <th>Proximity</th>
                  <th>Persistence</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.cluster_id} onClick={() => onSelectEvent(item)}>
                    <td className="rank-cell">#{item.rank}</td>
                    <td className="location-cell">
                      <div className="loc-id">{item.cluster_id}</div>
                      <div className="loc-coords">
                        {item.latitude.toFixed(3)}, {item.longitude.toFixed(3)}
                      </div>
                    </td>
                    <td className="score-cell font-bold">{item.risk_score} / 100</td>
                    <td>
                      <span className={`risk-level-badge ${getRiskBadgeClass(item.risk_level)}`}>
                        {item.risk_level}
                      </span>
                    </td>
                    <td className="cat-cell">{item.classification.replace('_', ' ')}</td>
                    <td className="facility-cell">{item.industrial_facility}</td>
                    <td>{item.industrial_distance_km ? `${item.industrial_distance_km} km` : 'N/A'}</td>
                    <td>{item.persistence_score} / 100</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); onSelectEvent(item); }}>
                        🔍 Inspect
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
