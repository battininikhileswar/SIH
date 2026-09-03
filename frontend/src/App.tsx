import { useEffect, useState, useCallback } from 'react';
import { FireMap } from './components/FireMap';
import { FilterBar } from './components/FilterBar';
import { ContextPanel } from './components/ContextPanel';
import { PersistencePanel } from './components/PersistencePanel';
import { PriorityTable } from './components/PriorityTable';
import { AlertStats } from './components/AlertStats';
import { AlertDashboard } from './components/AlertDashboard';
import { AlertDetailPanel } from './components/AlertDetailPanel';
import { AlertHistory } from './components/AlertHistory';
import { InvestigationWorkspace } from './components/InvestigationWorkspace';
import {
  Hotspot,
  HotspotsApiResponse,
  HotspotContextResponse,
  PersistentCluster,
  PersistentClustersApiResponse,
  PriorityRankingItem,
  ThermalAlert,
  AlertStats as AlertStatsType,
} from './types/hotspot';

export function App() {
  const [region, setRegion] = useState<string>('india');
  const [customBbox, setCustomBbox] = useState<string>('');
  const [viewMode, setViewMode] = useState<'hotspots' | 'clusters'>('hotspots');
  const [activeTab, setActiveTab] = useState<'active_alerts' | 'investigation' | 'priority_queue' | 'alert_history'>('active_alerts');

  // Single Hotspots State
  const [hotspotsData, setHotspotsData] = useState<HotspotsApiResponse | null>(null);
  const [loadingHotspots, setLoadingHotspots] = useState<boolean>(false);
  const [hotspotsError, setHotspotsError] = useState<string | null>(null);
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);

  // Persistent Clusters State
  const [clustersData, setClustersData] = useState<PersistentClustersApiResponse | null>(null);
  const [loadingClusters, setLoadingClusters] = useState<boolean>(false);
  const [selectedCluster, setSelectedCluster] = useState<PersistentCluster | null>(null);

  // Priority Ranking State (Phase 6)
  const [priorityItems, setPriorityItems] = useState<PriorityRankingItem[]>([]);
  const [loadingPriority, setLoadingPriority] = useState<boolean>(false);

  // Alert State (Phase 7)
  const [alerts, setAlerts] = useState<ThermalAlert[]>([]);
  const [alertStats, setAlertStats] = useState<AlertStatsType | null>(null);
  const [loadingAlerts, setLoadingAlerts] = useState<boolean>(false);
  const [selectedAlert, setSelectedAlert] = useState<ThermalAlert | null>(null);

  // OSM Context State
  const [contextData, setContextData] = useState<HotspotContextResponse | null>(null);
  const [loadingContext, setLoadingContext] = useState<boolean>(false);
  const [contextError, setContextError] = useState<string | null>(null);

  // Phase 10: Investigation Workspace & SIH Demo State
  const [investigationEvent, setInvestigationEvent] = useState<{
    alert?: ThermalAlert | null;
    hotspot?: Hotspot | null;
    cluster?: PersistentCluster | null;
  } | null>(null);
  const [demoNotice, setDemoNotice] = useState<string | null>(null);

  // Map viewport state
  const [mapCenter, setMapCenter] = useState<[number, number]>([20.5937, 78.9629]); // India center
  const [mapZoom, setMapZoom] = useState<number>(5);

  // Fetch FIRMS Hotspots
  const loadHotspots = useCallback(async (selectedRegion: string, bboxStr: string) => {
    setLoadingHotspots(true);
    setHotspotsError(null);
    try {
      let url = `http://127.0.0.1:8000/api/hotspots?region=${selectedRegion}`;
      if (selectedRegion === 'custom' && bboxStr) {
        url += `&bbox=${encodeURIComponent(bboxStr)}`;
      }
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
      const data: HotspotsApiResponse = await response.json();
      setHotspotsData(data);

      if (data.hotspots.length > 0 && selectedRegion === 'andhra_pradesh') {
        setMapCenter([15.9129, 79.74]);
        setMapZoom(7);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unable to connect to backend';
      setHotspotsError(message);
    } finally {
      setLoadingHotspots(false);
    }
  }, []);

  // Fetch Persistent Clusters
  const loadClusters = useCallback(async (selectedRegion: string, bboxStr: string) => {
    setLoadingClusters(true);
    try {
      let url = `http://127.0.0.1:8000/api/persistent-hotspots?region=${selectedRegion}`;
      if (selectedRegion === 'custom' && bboxStr) {
        url += `&bbox=${encodeURIComponent(bboxStr)}`;
      }
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
      const data: PersistentClustersApiResponse = await response.json();
      setClustersData(data);
    } catch {
      // Ignore cluster fetch error in background
    } finally {
      setLoadingClusters(false);
    }
  }, []);

  // Fetch Priority Ranking Leaderboard
  const loadPriorityRanking = useCallback(async (selectedRegion: string) => {
    setLoadingPriority(true);
    try {
      const url = `http://127.0.0.1:8000/api/hotspots/priority-ranking?region=${selectedRegion}&limit=10`;
      const response = await fetch(url);
      if (response.ok) {
        const json = await response.json();
        setPriorityItems(json.priority_events || []);
      }
    } catch {
      // Ignore background priority loading errors
    } finally {
      setLoadingPriority(false);
    }
  }, []);

  // Fetch & Evaluate Alerts (Phase 7)
  const loadAlertsAndStats = useCallback(async (selectedRegion: string) => {
    setLoadingAlerts(true);
    try {
      // Step 1: Trigger background evaluation
      await fetch(`http://127.0.0.1:8000/api/alerts/evaluate?region=${selectedRegion}`, { method: 'POST' });

      // Step 2: Fetch all alerts & stats
      const [alertsRes, statsRes] = await Promise.all([
        fetch(`http://127.0.0.1:8000/api/alerts?limit=100`),
        fetch(`http://127.0.0.1:8000/api/alerts/stats`)
      ]);

      if (alertsRes.ok && statsRes.ok) {
        const alertsJson = await alertsRes.json();
        const statsJson = await statsRes.json();
        setAlerts(alertsJson.alerts || []);
        setAlertStats(statsJson);
      }
    } catch {
      // Ignore alert sync background errors
    } finally {
      setLoadingAlerts(false);
    }
  }, []);

  // Initial Load & On Filter Changes
  useEffect(() => {
    loadHotspots(region, customBbox);
    loadClusters(region, customBbox);
    loadPriorityRanking(region);
    loadAlertsAndStats(region);
  }, [region, customBbox, loadHotspots, loadClusters, loadPriorityRanking, loadAlertsAndStats]);

  // Handle Alert Status Change Action (Phase 7 & 10)
  const handleAlertStatusChange = async (
    alertId: string,
    action: 'acknowledge' | 'investigate' | 'resolve' | 'dismiss',
    notes?: string
  ) => {
    try {
      let url = `http://127.0.0.1:8000/api/alerts/${alertId}/${action}`;
      if (notes) {
        url += `?notes=${encodeURIComponent(notes)}`;
      }
      const res = await fetch(url, { method: 'POST' });
      if (res.ok) {
        const updatedAlert: ThermalAlert = await res.json();
        // Update local alerts list
        setAlerts((prev) => prev.map((a) => (a.alert_id === alertId ? updatedAlert : a)));
        if (selectedAlert && selectedAlert.alert_id === alertId) {
          setSelectedAlert(updatedAlert);
        }
        if (investigationEvent && investigationEvent.alert?.alert_id === alertId) {
          setInvestigationEvent({ ...investigationEvent, alert: updatedAlert });
        }
        // Refresh stats
        const statsRes = await fetch(`http://127.0.0.1:8000/api/alerts/stats`);
        if (statsRes.ok) {
          setAlertStats(await statsRes.json());
        }
      }
    } catch {
      // Handle alert action failure
    }
  };

  // Handle Hotspot Click (OSM Context)
  const handleSelectHotspot = async (hotspot: Hotspot) => {
    setSelectedHotspot(hotspot);
    setSelectedCluster(null);
    setSelectedAlert(null);
    setInvestigationEvent({ hotspot });
    setContextData(null);
    setContextError(null);
    setLoadingContext(true);
    setMapCenter([hotspot.latitude, hotspot.longitude]);
    setMapZoom(11);

    try {
      const url = `http://127.0.0.1:8000/api/hotspots/context?lat=${hotspot.latitude}&lon=${hotspot.longitude}&radius_km=5.0`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
      const data: HotspotContextResponse = await response.json();
      setContextData(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to retrieve OSM context';
      setContextError(message);
    } finally {
      setLoadingContext(false);
    }
  };

  // Handle Cluster Click
  const handleSelectCluster = (cluster: PersistentCluster) => {
    setSelectedCluster(cluster);
    setSelectedHotspot(null);
    setSelectedAlert(null);
    setInvestigationEvent({ cluster });
    setContextData(null);
    setMapCenter([cluster.center_latitude, cluster.center_longitude]);
    setMapZoom(12);
  };

  // Handle Alert Click
  const handleSelectAlert = (alert: ThermalAlert) => {
    setSelectedAlert(alert);
    setSelectedHotspot(null);
    setSelectedCluster(null);
    setInvestigationEvent({ alert });
    setContextData(null);
    setMapCenter([alert.latitude, alert.longitude]);
    setMapZoom(12);
  };

  // Handle Priority Table Row Click
  const handleSelectPriorityEvent = (item: PriorityRankingItem) => {
    setViewMode('clusters');
    setMapCenter([item.latitude, item.longitude]);
    setMapZoom(12);

    if (clustersData) {
      const targetCluster = clustersData.clusters.find((c) => c.cluster_id === item.cluster_id);
      if (targetCluster) {
        setSelectedCluster(targetCluster);
        setSelectedHotspot(null);
        setInvestigationEvent({ cluster: targetCluster });
      }
    }
  };

  // Phase 10: Seamless Transition to Investigation Workspace
  const handleOpenInvestigation = (event: {
    alert?: ThermalAlert | null;
    hotspot?: Hotspot | null;
    cluster?: PersistentCluster | null;
  }) => {
    setInvestigationEvent(event);
    setActiveTab('investigation');

    const lat = event.alert?.latitude ?? event.hotspot?.latitude ?? event.cluster?.center_latitude;
    const lon = event.alert?.longitude ?? event.hotspot?.longitude ?? event.cluster?.center_longitude;
    if (lat !== undefined && lon !== undefined) {
      setMapCenter([lat, lon]);
      setMapZoom(12);
    }
  };

  // Phase 10: SIH Demo Mode Trigger
  const handleDemoInvestigation = async () => {
    // 1. Prioritize a critical or high-risk active alert from state
    let targetAlert =
      alerts.find((a) => a.risk_level === 'CRITICAL' || a.risk_score >= 60) || alerts[0];

    // If state is still loading, fetch alerts directly
    if (!targetAlert) {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/alerts?limit=10');
        if (res.ok) {
          const json = await res.json();
          const fetchedAlerts: ThermalAlert[] = json.alerts || [];
          if (fetchedAlerts.length > 0) {
            targetAlert =
              fetchedAlerts.find((a) => a.risk_level === 'CRITICAL' || a.risk_score >= 60) ||
              fetchedAlerts[0];
            setAlerts(fetchedAlerts);
          }
        }
      } catch {
        // Fallback to clusters
      }
    }

    if (targetAlert) {
      setSelectedAlert(targetAlert);
      setSelectedHotspot(null);
      setSelectedCluster(null);
      handleOpenInvestigation({ alert: targetAlert });
      return;
    }

    // 2. Next check for persistent cluster
    if (clustersData && clustersData.clusters.length > 0) {
      const targetCluster = [...clustersData.clusters].sort(
        (a, b) => b.persistence_score - a.persistence_score
      )[0];
      setSelectedCluster(targetCluster);
      setSelectedAlert(null);
      setSelectedHotspot(null);
      handleOpenInvestigation({ cluster: targetCluster });
      return;
    }

    // 3. Next check for highest FRP hotspot
    if (hotspotsData && hotspotsData.hotspots.length > 0) {
      const targetSpot = [...hotspotsData.hotspots].sort((a, b) => b.frp - a.frp)[0];
      setSelectedHotspot(targetSpot);
      setSelectedAlert(null);
      setSelectedCluster(null);
      handleOpenInvestigation({ hotspot: targetSpot });
      return;
    }

    // Fallback notice if no data exists
    setDemoNotice('No suitable live investigation event currently available.');
    setTimeout(() => setDemoNotice(null), 4500);
  };


  const handleRefresh = () => {
    loadHotspots(region, customBbox);
    loadClusters(region, customBbox);
    loadPriorityRanking(region);
    loadAlertsAndStats(region);
  };

  const activeUnresolvedAlerts = alerts.filter(
    (a) => a.status === 'NEW' || a.status === 'ACKNOWLEDGED' || a.status === 'INVESTIGATING'
  );

  return (
    <div className="app-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-brand">
          <span className="logo-badge">SIH 26162</span>
          <h1 className="main-title">Industrial Fire & Persistent Thermal Source Intelligence</h1>
          <p className="subtitle">
            Real-Time NASA FIRMS Satellite Observations • OSM Geospatial Context • Persistence • Risk Scoring • Alert Incident Management • Sentinel-2 CV
          </p>
        </div>

        <div className="header-controls-group">
          {/* SIH Demo Investigation Button */}
          <button
            type="button"
            className="btn-demo-investigation"
            onClick={handleDemoInvestigation}
            title="Launch SIH demo walkthrough using an actual high-risk thermal event"
          >
            ⚡ Demo Investigation
          </button>

          <div className="status-card">
            <div className={`status-dot ${loadingHotspots ? 'checking' : hotspotsError ? 'offline' : 'online'}`} />
            <div className="status-info">
              <span className="status-title">Backend API:</span>
              <span className="status-val">{loadingHotspots ? 'Syncing...' : hotspotsError ? 'Disconnected' : 'Online'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Demo Notice Notification Banner if triggered without data */}
      {demoNotice && (
        <div className="demo-notice-banner">
          <span>⚠️ {demoNotice}</span>
        </div>
      )}

      {/* Main Content */}
      <main className="dashboard-content">
        {/* Alert Summary Stats Bar (Phase 7) */}
        <AlertStats stats={alertStats} loading={loadingAlerts} />

        {/* Filter Controls Bar */}
        <FilterBar
          viewMode={viewMode}
          onViewModeChange={(mode) => {
            setViewMode(mode);
            setSelectedHotspot(null);
            setSelectedCluster(null);
          }}
          region={region}
          onRegionChange={setRegion}
          customBbox={customBbox}
          onCustomBboxChange={setCustomBbox}
          onApplyCustomBbox={handleRefresh}
          onRefresh={handleRefresh}
          loading={loadingHotspots || loadingClusters}
          count={viewMode === 'hotspots' ? (hotspotsData?.count || 0) : (clustersData?.persistent_cluster_count || 0)}
        />

        {/* Workspace Layout */}
        <div className="main-workspace">
          {/* Map Component */}
          <div className="map-section">
            <FireMap
              viewMode={viewMode}
              hotspots={hotspotsData?.hotspots || []}
              clusters={clustersData?.clusters || []}
              activeAlerts={activeUnresolvedAlerts}
              center={mapCenter}
              zoom={mapZoom}
              selectedHotspot={selectedHotspot}
              onSelectHotspot={handleSelectHotspot}
              selectedCluster={selectedCluster}
              onSelectCluster={handleSelectCluster}
              selectedAlert={selectedAlert}
              onSelectAlert={handleSelectAlert}
              nearbyFeatures={contextData?.nearby_features || []}
            />
          </div>

          {/* Context Panel (Single Hotspot) */}
          {selectedHotspot && (
            <ContextPanel
              selectedHotspot={selectedHotspot}
              contextData={contextData}
              loading={loadingContext}
              error={contextError}
              onClose={() => setSelectedHotspot(null)}
              onOpenInvestigation={(spot) => handleOpenInvestigation({ hotspot: spot })}
            />
          )}

          {/* Persistence Panel (Cluster) */}
          {selectedCluster && (
            <PersistencePanel
              cluster={selectedCluster}
              onClose={() => setSelectedCluster(null)}
              onOpenInvestigation={(cl) => handleOpenInvestigation({ cluster: cl })}
            />
          )}

          {/* Alert Detail Panel (Phase 7) */}
          {selectedAlert && (
            <AlertDetailPanel
              alert={selectedAlert}
              onClose={() => setSelectedAlert(null)}
              onStatusChange={handleAlertStatusChange}
              onOpenInvestigation={(alt) => handleOpenInvestigation({ alert: alt })}
            />
          )}
        </div>

        {/* Dashboard Navigation Tabs (Phase 7 & Phase 10) */}
        <div className="dashboard-tabs">
          <button
            className={`tab-btn ${activeTab === 'active_alerts' ? 'active-tab' : ''}`}
            onClick={() => setActiveTab('active_alerts')}
          >
            🚨 Active Incident Queue ({activeUnresolvedAlerts.length})
          </button>
          <button
            className={`tab-btn ${activeTab === 'investigation' ? 'active-tab highlight-investigation' : ''}`}
            onClick={() => setActiveTab('investigation')}
          >
            🔍 Investigation Workspace {investigationEvent ? '●' : ''}
          </button>
          <button
            className={`tab-btn ${activeTab === 'priority_queue' ? 'active-tab' : ''}`}
            onClick={() => setActiveTab('priority_queue')}
          >
            🏆 Highest Risk Priority Leaderboard ({priorityItems.length})
          </button>
          <button
            className={`tab-btn ${activeTab === 'alert_history' ? 'active-tab' : ''}`}
            onClick={() => setActiveTab('alert_history')}
          >
            📜 Alert Audit History ({alerts.length - activeUnresolvedAlerts.length})
          </button>
        </div>

        {/* Tab 1: Active Alert Incident Queue */}
        {activeTab === 'active_alerts' && (
          <AlertDashboard
            alerts={activeUnresolvedAlerts}
            loading={loadingAlerts}
            onSelectAlert={(alt) => {
              handleSelectAlert(alt);
            }}
            onStatusChange={handleAlertStatusChange}
          />
        )}

        {/* Tab 2: Phase 10 Unified Investigation Workspace */}
        {activeTab === 'investigation' && (
          <div className="investigation-tab-wrapper">
            {investigationEvent ? (
              <InvestigationWorkspace
                alert={investigationEvent.alert}
                hotspot={investigationEvent.hotspot}
                cluster={investigationEvent.cluster}
                onStatusChange={handleAlertStatusChange}
                onClose={() => setActiveTab('active_alerts')}
              />
            ) : (
              <div className="empty-investigation-notice">
                <span className="notice-icon">🔍</span>
                <h3>No Thermal Event Currently Selected for Investigation</h3>
                <p>
                  Select an active incident from the queue, a persistent cluster from the map, or launch demo mode:
                </p>
                <button
                  type="button"
                  className="btn-demo-investigation"
                  onClick={handleDemoInvestigation}
                >
                  ⚡ Launch Demo Investigation
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Highest Risk Thermal Events Priority Leaderboard (Phase 6) */}
        {activeTab === 'priority_queue' && (
          <PriorityTable
            items={priorityItems}
            loading={loadingPriority}
            onSelectEvent={handleSelectPriorityEvent}
          />
        )}

        {/* Tab 4: Alert Audit History (Phase 7) */}
        {activeTab === 'alert_history' && (
          <AlertHistory
            alerts={alerts}
            loading={loadingAlerts}
            onSelectAlert={handleSelectAlert}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="dashboard-footer">
        <p>
          SIH Problem Statement 26162 • NASA FIRMS • OpenStreetMap • Spatial-Temporal Persistence • Explainable AI Risk Prioritization • Incident Alert Management • Sentinel-2 Computer Vision
        </p>
      </footer>
    </div>
  );
}

export default App;
