import React from 'react';

interface FilterBarProps {
  viewMode: 'hotspots' | 'clusters';
  onViewModeChange: (mode: 'hotspots' | 'clusters') => void;
  region: string;
  onRegionChange: (newRegion: string) => void;
  customBbox: string;
  onCustomBboxChange: (bboxStr: string) => void;
  onApplyCustomBbox: () => void;
  onRefresh: () => void;
  loading: boolean;
  count: number;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  viewMode,
  onViewModeChange,
  region,
  onRegionChange,
  customBbox,
  onCustomBboxChange,
  onApplyCustomBbox,
  onRefresh,
  loading,
  count,
}) => {
  return (
    <div className="filter-bar">
      {/* View Mode Switch */}
      <div className="filter-group mode-switch-group">
        <button
          className={`btn mode-btn ${viewMode === 'hotspots' ? 'active-mode' : 'inactive-mode'}`}
          onClick={() => onViewModeChange('hotspots')}
        >
          🔥 Single Hotspots View
        </button>
        <button
          className={`btn mode-btn ${viewMode === 'clusters' ? 'active-mode' : 'inactive-mode'}`}
          onClick={() => onViewModeChange('clusters')}
        >
          🔴 Persistent Clusters View
        </button>
      </div>

      <div className="filter-group">
        <label className="filter-label">Region:</label>
        <select
          className="filter-select"
          value={region}
          onChange={(e) => onRegionChange(e.target.value)}
          disabled={loading}
        >
          <option value="india">India (National)</option>
          <option value="andhra_pradesh">Andhra Pradesh</option>
          <option value="custom">Custom Bounding Box</option>
        </select>
      </div>

      {region === 'custom' && (
        <div className="filter-group custom-bbox-group">
          <input
            type="text"
            className="filter-input"
            placeholder="min_lon,min_lat,max_lon,max_lat"
            value={customBbox}
            onChange={(e) => onCustomBboxChange(e.target.value)}
          />
          <button
            className="btn btn-secondary"
            onClick={onApplyCustomBbox}
            disabled={loading}
          >
            Apply BBox
          </button>
        </div>
      )}

      <div className="filter-actions">
        <button className="btn btn-primary" onClick={onRefresh} disabled={loading}>
          {loading ? 'Syncing...' : '🔄 Refresh Data'}
        </button>

        <div className="count-badge">
          <span className="count-label">
            {viewMode === 'hotspots' ? 'Active Hotspots:' : 'Thermal Clusters:'}
          </span>
          <span className="count-value">{count}</span>
        </div>
      </div>
    </div>
  );
};
