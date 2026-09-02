import React, { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { Hotspot, OsmFeature, PersistentCluster, ThermalAlert } from '../types/hotspot';
import { Legend } from './Legend';

interface FireMapProps {
  viewMode: 'hotspots' | 'clusters';
  hotspots: Hotspot[];
  clusters: PersistentCluster[];
  activeAlerts: ThermalAlert[];
  center: [number, number];
  zoom: number;
  selectedHotspot: Hotspot | null;
  onSelectHotspot: (hotspot: Hotspot) => void;
  selectedCluster: PersistentCluster | null;
  onSelectCluster: (cluster: PersistentCluster) => void;
  selectedAlert: ThermalAlert | null;
  onSelectAlert: (alert: ThermalAlert) => void;
  nearbyFeatures: OsmFeature[];
}

const MapViewController: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
};

export const FireMap: React.FC<FireMapProps> = ({
  viewMode,
  hotspots,
  clusters,
  activeAlerts,
  center,
  zoom,
  selectedHotspot,
  onSelectHotspot,
  selectedCluster,
  onSelectCluster,
  selectedAlert,
  onSelectAlert,
  nearbyFeatures,
}) => {
  const getHotspotColor = (frp: number): string => {
    if (frp > 20) return '#ef4444';
    if (frp >= 5) return '#f97316';
    return '#eab308';
  };

  const getClusterColor = (score: number): string => {
    if (score >= 81) return '#ef4444'; // Red
    if (score >= 61) return '#a855f7'; // Purple
    if (score >= 31) return '#f97316'; // Orange
    return '#eab308';                  // Yellow
  };

  const getOsmMarkerColor = (type: string): string => {
    switch (type) {
      case 'industrial':
        return '#a855f7';
      case 'power':
        return '#eab308';
      case 'urban':
        return '#06b6d4';
      case 'road':
        return '#64748b';
      default:
        return '#3b82f6';
    }
  };

  return (
    <div className="map-wrapper">
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        className="leaflet-container"
      >
        <MapViewController center={center} zoom={zoom} />

        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Satellite: NASA FIRMS / Sentinel-2'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* ACTIVE ALERTS MARKERS OVERLAY (Phase 7 & 8) */}
        {activeAlerts.map((alt) => {
          const isSelected = selectedAlert && selectedAlert.alert_id === alt.alert_id;
          const color = alt.risk_level === 'CRITICAL' ? '#ef4444' : '#f97316';
          const radius = isSelected ? 22 : 16;

          return (
            <CircleMarker
              key={`alert-${alt.alert_id}`}
              center={[alt.latitude, alt.longitude]}
              radius={radius}
              eventHandlers={{
                click: () => onSelectAlert(alt),
              }}
              pathOptions={{
                color: '#ffffff',
                fillColor: color,
                fillOpacity: 0.95,
                weight: isSelected ? 4 : 2.5,
              }}
            >
              <Popup className="custom-popup">
                <div className="popup-container">
                  <div className="popup-header" style={{ color: color }}>
                    🚨 ACTIVE INCIDENT ALERT ({alt.alert_id})
                  </div>
                  <div className="popup-body">
                    <div className="popup-row">
                      <span className="popup-label">Risk Priority:</span>
                      <span className="popup-val highlight-frp">{alt.risk_score} / 100 ({alt.risk_level})</span>
                    </div>
                    <div className="popup-row">
                      <span className="popup-label">Classification:</span>
                      <span className="popup-val">{alt.classification.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="popup-row">
                      <span className="popup-label">Status:</span>
                      <span className="popup-val">{alt.status}</span>
                    </div>
                    <div className="popup-row">
                      <span className="popup-label">Facility:</span>
                      <span className="popup-val">{alt.facility_name || 'None'}</span>
                    </div>
                    <div className="popup-row">
                      <span className="popup-label">Satellite Imagery:</span>
                      <span className="popup-val" style={{ color: '#10b981', fontWeight: 600 }}>📡 Sentinel-2 Patch Ready</span>
                    </div>
                    <button
                      className="btn btn-primary btn-sm"
                      style={{ marginTop: '0.5rem', width: '100%' }}
                      onClick={() => onSelectAlert(alt)}
                    >
                      📡 Inspect Satellite & Incident Evidence
                    </button>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

        {/* MODE 1: Single Hotspots View */}
        {viewMode === 'hotspots' &&
          hotspots.map((spot, index) => {
            const color = getHotspotColor(spot.frp);
            const isSelected =
              selectedHotspot &&
              selectedHotspot.latitude === spot.latitude &&
              selectedHotspot.longitude === spot.longitude;
            const radius = isSelected ? 18 : Math.min(Math.max(spot.frp / 4, 6), 14);

            return (
              <CircleMarker
                key={`spot-${spot.latitude}-${spot.longitude}-${index}`}
                center={[spot.latitude, spot.longitude]}
                radius={radius}
                eventHandlers={{
                  click: () => onSelectHotspot(spot),
                }}
                pathOptions={{
                  color: isSelected ? '#ffffff' : color,
                  fillColor: color,
                  fillOpacity: isSelected ? 0.95 : 0.8,
                  weight: isSelected ? 3 : 1.5,
                }}
              >
                <Popup className="custom-popup">
                  <div className="popup-container">
                    <div className="popup-header">🔥 FIRMS HOTSPOT</div>
                    <div className="popup-body">
                      <div className="popup-row">
                        <span className="popup-label">Satellite:</span>
                        <span className="popup-val">{spot.satellite}</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Instrument:</span>
                        <span className="popup-val">{spot.instrument}</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Acquired:</span>
                        <span className="popup-val">{spot.acquired_at}</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Brightness:</span>
                        <span className="popup-val">{spot.brightness} K</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">FRP:</span>
                        <span className="popup-val highlight-frp">{spot.frp} MW</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Optical Evidence:</span>
                        <span className="popup-val" style={{ color: '#38bdf8' }}>📡 Sentinel-2 Evidence</span>
                      </div>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ marginTop: '0.5rem', width: '100%' }}
                        onClick={() => onSelectHotspot(spot)}
                      >
                        📡 Inspect Satellite & Risk Context
                      </button>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

        {/* MODE 2: Persistent Thermal Clusters View */}
        {viewMode === 'clusters' &&
          clusters.map((cluster, index) => {
            const color = getClusterColor(cluster.persistence_score);
            const isSelected =
              selectedCluster && selectedCluster.cluster_id === cluster.cluster_id;
            const radius = isSelected ? 20 : Math.min(Math.max(cluster.observation_count * 2.5, 10), 22);

            return (
              <CircleMarker
                key={`cluster-${cluster.cluster_id}-${index}`}
                center={[cluster.center_latitude, cluster.center_longitude]}
                radius={radius}
                eventHandlers={{
                  click: () => onSelectCluster(cluster),
                }}
                pathOptions={{
                  color: isSelected ? '#ffffff' : color,
                  fillColor: color,
                  fillOpacity: isSelected ? 0.95 : 0.85,
                  weight: isSelected ? 3.5 : 2,
                }}
              >
                <Popup className="custom-popup">
                  <div className="popup-container">
                    <div className="popup-header" style={{ color: color }}>
                      🔴 PERSISTENT THERMAL SOURCE
                    </div>
                    <div className="popup-body">
                      <div className="popup-row">
                        <span className="popup-label">Cluster ID:</span>
                        <span className="popup-val">{cluster.cluster_id}</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Persistence Score:</span>
                        <span className="popup-val highlight-frp">{cluster.persistence_score} / 100</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Classification:</span>
                        <span className="popup-val">{cluster.classification}</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Observations:</span>
                        <span className="popup-val">{cluster.observation_count}</span>
                      </div>
                      <div className="popup-row">
                        <span className="popup-label">Duration:</span>
                        <span className="popup-val">{cluster.duration_hours} hrs</span>
                      </div>
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ marginTop: '0.5rem', width: '100%' }}
                        onClick={() => onSelectCluster(cluster)}
                      >
                        📊 View Satellite & Priority Timeline
                      </button>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

        {/* Nearby OSM Facilities */}
        {nearbyFeatures.map((feat, idx) => {
          const color = getOsmMarkerColor(feat.type);
          return (
            <CircleMarker
              key={`osm-${feat.osm_id}-${idx}`}
              center={[feat.latitude, feat.longitude]}
              radius={8}
              pathOptions={{
                color: '#ffffff',
                fillColor: color,
                fillOpacity: 0.9,
                weight: 1.5,
              }}
            >
              <Popup className="custom-popup">
                <div className="popup-container">
                  <div className="popup-header" style={{ color: color }}>
                    📍 OSM NEARBY FEATURE
                  </div>
                  <div className="popup-body">
                    <div className="popup-row">
                      <span className="popup-label">Name:</span>
                      <span className="popup-val">{feat.name}</span>
                    </div>
                    <div className="popup-row">
                      <span className="popup-label">Category:</span>
                      <span className="popup-val">{feat.type} ({feat.category})</span>
                    </div>
                    <div className="popup-row">
                      <span className="popup-label">Distance:</span>
                      <span className="popup-val highlight-frp">{feat.distance_km} km</span>
                    </div>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>

      <Legend viewMode={viewMode} />
    </div>
  );
};
