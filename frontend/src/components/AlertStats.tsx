import React from 'react';
import { AlertStats as AlertStatsType } from '../types/hotspot';

interface AlertStatsProps {
  stats: AlertStatsType | null;
  loading: boolean;
}

export const AlertStats: React.FC<AlertStatsProps> = ({ stats, loading }) => {
  if (loading || !stats) {
    return (
      <div className="alert-stats-bar">
        <div className="stat-pill loading-pill">Syncing Alert Metrics...</div>
      </div>
    );
  }

  return (
    <div className="alert-stats-bar">
      <div className="stat-pill pill-active">
        <span className="stat-label">Active Alerts:</span>
        <span className="stat-num">{stats.active_alerts}</span>
      </div>

      <div className="stat-pill pill-critical">
        <span className="stat-label">🔴 Critical:</span>
        <span className="stat-num">{stats.critical_alerts}</span>
      </div>

      <div className="stat-pill pill-high">
        <span className="stat-label">🟠 High:</span>
        <span className="stat-num">{stats.high_alerts}</span>
      </div>

      <div className="stat-pill pill-ack">
        <span className="stat-label">Acknowledged:</span>
        <span className="stat-num">{stats.acknowledged_alerts}</span>
      </div>

      <div className="stat-pill pill-investigating">
        <span className="stat-label">Investigating:</span>
        <span className="stat-num">{stats.investigating_alerts}</span>
      </div>

      <div className="stat-pill pill-resolved">
        <span className="stat-label">Resolved Today:</span>
        <span className="stat-num">{stats.resolved_today}</span>
      </div>
    </div>
  );
};
