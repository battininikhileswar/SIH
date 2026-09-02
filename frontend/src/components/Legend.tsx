import React from 'react';

interface LegendProps {
  viewMode: 'hotspots' | 'clusters';
}

export const Legend: React.FC<LegendProps> = ({ viewMode }) => {
  return (
    <div className="map-legend">
      {viewMode === 'hotspots' ? (
        <div className="legend-section">
          <div className="legend-title">FRP Intensity (MW)</div>
          <div className="legend-item">
            <span className="legend-color high" />
            <span>High Intensity (&gt; 20 MW)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color medium" />
            <span>Moderate (5 - 20 MW)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color low" />
            <span>Low (&lt; 5 MW)</span>
          </div>
        </div>
      ) : (
        <div className="legend-section">
          <div className="legend-title">Persistence Score</div>
          <div className="legend-item">
            <span className="legend-color high-persistent" />
            <span>Highly Persistent (81 - 100)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color persistent" />
            <span>Persistent (61 - 80)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color suspicious" />
            <span>Suspicious (31 - 60)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color temporary" />
            <span>Temporary (0 - 30)</span>
          </div>
        </div>
      )}

      <div className="legend-divider" />

      {/* Investigation Risk Priority Legend */}
      <div className="legend-section">
        <div className="legend-title">Investigation Risk Level</div>
        <div className="legend-item">
          <span className="legend-color high-persistent" />
          <span>🔴 CRITICAL (75 - 100)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color suspicious" />
          <span>🟠 HIGH (50 - 74)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color temporary" />
          <span>🟡 MODERATE (25 - 49)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#22c55e' }} />
          <span>🟢 LOW (0 - 24)</span>
        </div>
      </div>

      <div className="legend-divider" />

      <div className="legend-section">
        <div className="legend-title">OSM Features</div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#a855f7' }} />
          <span>Industrial Site</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#06b6d4' }} />
          <span>Urban / Residential</span>
        </div>
      </div>
    </div>
  );
};
