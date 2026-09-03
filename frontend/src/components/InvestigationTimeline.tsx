import React from 'react';
import { ThermalAlert, Hotspot, PersistentCluster, FusedEvidenceResponse } from '../types/hotspot';

interface InvestigationTimelineProps {
  alert?: ThermalAlert | null;
  hotspot?: Hotspot | null;
  cluster?: PersistentCluster | null;
  fusedEvidence?: FusedEvidenceResponse | null;
}

interface TimelineItem {
  title: string;
  stage: string;
  timestamp: string;
  status: 'completed' | 'active' | 'pending';
  icon: string;
  description: string;
  badge?: string;
}

export const InvestigationTimeline: React.FC<InvestigationTimelineProps> = ({
  alert,
  hotspot,
  cluster,
  fusedEvidence,
}) => {
  const items: TimelineItem[] = [];

  // Milestone 1: Satellite Thermal Detection (NASA FIRMS)
  const obsTime = hotspot?.acquired_at
    ? hotspot.acquired_at
    : hotspot?.acq_date && hotspot?.acq_time
    ? `${hotspot.acq_date} ${hotspot.acq_time} UTC`
    : alert?.created_at
    ? new Date(alert.created_at).toUTCString()
    : 'Timestamp unavailable';


  const satelliteInstrument = hotspot?.satellite || (alert?.features?.satellite as string) || 'VIIRS / MODIS';
  const frpVal = hotspot?.frp ?? (alert?.features?.frp as number) ?? 0;
  const brightVal = hotspot?.brightness ?? (alert?.features?.brightness as number) ?? 0;

  items.push({
    title: 'Satellite Thermal Anomaly Detection',
    stage: 'NASA FIRMS Sensor Ingestion',
    timestamp: obsTime,
    status: 'completed',
    icon: '🛰️',
    description: `Thermal radiative anomaly captured by ${satelliteInstrument} sensor. Brightness: ${brightVal ? `${brightVal} K` : 'N/A'}, FRP: ${frpVal ? `${frpVal} MW` : 'N/A'}.`,
    badge: 'NASA FIRMS',
  });

  // Milestone 2: Spatial-Temporal Persistence Analysis
  if (cluster || (alert && alert.persistence_score > 0)) {
    const obsCount = cluster?.observation_count ?? alert?.observation_count ?? 1;
    const durHours = cluster?.duration_hours ?? alert?.duration_hours ?? 0;
    const pScore = cluster?.persistence_score ?? alert?.persistence_score ?? 0;
    const pTime = cluster?.first_detected ? `${cluster.first_detected} UTC` : 'Observation cycle timestamp unavailable';

    items.push({
      title: 'Spatial-Temporal Persistence Detection',
      stage: 'Spatiotemporal Clustering Engine',
      timestamp: pTime,
      status: 'completed',
      icon: '⏳',
      description: `Cluster identified across ${obsCount} recurrent satellite observations spanning ${durHours.toFixed(1)} hours. Persistence Score: ${pScore}/100.`,
      badge: 'Persistence Engine',
    });
  }

  // Milestone 3: OpenStreetMap Industrial Proximity
  const facilityName = alert?.facility_name || fusedEvidence?.evidence?.osm?.nearby_facility;
  const distanceKm = alert?.industrial_distance_km ?? fusedEvidence?.evidence?.osm?.distance_km;
  const osmContext = fusedEvidence?.evidence?.osm?.context;

  items.push({
    title: 'OpenStreetMap Industrial Infrastructure Query',
    stage: 'Geospatial Context Discovery',
    timestamp: 'Query completed upon ingestion',
    status: 'completed',
    icon: '🏭',
    description: facilityName && facilityName !== 'None identified'
      ? `Identified nearby industrial asset: "${facilityName}" located ${distanceKm !== null && distanceKm !== undefined ? `${distanceKm.toFixed(2)} km` : 'within 5 km'} from thermal epicenter (${osmContext || 'Industrial Zone'}).`
      : 'Geospatial search within 5 km radius: No registered heavy industrial facility found.',
    badge: 'OpenStreetMap',
  });

  // Milestone 4: Explainable AI Event Classification
  const aiClass = alert?.classification || fusedEvidence?.final_classification || 'UNKNOWN';
  const modelSrc = alert?.model_source || 'ML_MODEL';
  items.push({
    title: 'Explainable AI Classification',
    stage: 'Multi-Feature Random Forest Classifier',
    timestamp: 'Evaluated upon feature extraction',
    status: 'completed',
    icon: '🤖',
    description: `Classified candidate event as "${aiClass.replace(/_/g, ' ')}" using ${modelSrc === 'ML_MODEL' ? 'Random Forest model' : 'Prototype Rule Engine fallback'}.`,
    badge: modelSrc,
  });

  // Milestone 5: Sentinel-2 Satellite Optical Verification & Computer Vision
  const satEvidence = fusedEvidence?.evidence?.satellite;
  if (satEvidence) {
    items.push({
      title: 'Sentinel-2 Optical Patch & PyTorch CV Analysis',
      stage: 'Satellite Computer Vision & Grad-CAM',
      timestamp: satEvidence.captured_at ? `${satEvidence.captured_at} UTC` : 'Timestamp unavailable',
      status: satEvidence.image_available ? 'completed' : 'pending',
      icon: '📡',
      description: satEvidence.image_available
        ? `Optical patch analyzed with PyTorch vision model (${satEvidence.model || 'ResNet-18'}). Predicted visual signature: ${satEvidence.classification.replace(/_/g, ' ')} (${Math.round((satEvidence.confidence || 0) * 100)}% confidence). Grad-CAM visual explanation generated.`
        : 'Optical imagery retrieval not configured or unavailable for this coordinate.',
      badge: satEvidence.model || 'CV Model',
    });
  }

  // Milestone 6: Multi-Modal Decision Fusion & Investigation Prioritization
  const riskScore = alert?.risk_score ?? fusedEvidence?.combined_risk_score ?? 0;
  const riskLevel = alert?.risk_level ?? fusedEvidence?.risk_level ?? 'LOW';
  items.push({
    title: 'Multi-Modal Evidence Fusion & Risk Calculation',
    stage: 'Decision Prioritization Engine',
    timestamp: alert?.created_at ? new Date(alert.created_at).toUTCString() : 'Real-time calculation',
    status: 'completed',
    icon: '⚡',
    description: `Synthesized FIRMS (20%), OSM (15%), Persistence (15%), Base AI (35%), and Satellite CV (15%). Total Investigation Priority Score: ${riskScore} / 100 (${riskLevel}).`,
    badge: `${riskLevel} PRIORITY`,
  });

  // Milestone 7: Alert Incident Lifecycle (If alert exists)
  if (alert) {
    items.push({
      title: `Incident Alert Created (${alert.alert_id})`,
      stage: 'Incident Management Lifecycle',
      timestamp: alert.created_at ? new Date(alert.created_at).toUTCString() : 'Timestamp unavailable',
      status: 'completed',
      icon: '🚨',
      description: `High-priority incident record registered with initial status [NEW]. Priority Level: ${alert.risk_level}.`,
      badge: 'Alert Service',
    });

    if (alert.acknowledged_at || alert.status === 'ACKNOWLEDGED' || alert.status === 'INVESTIGATING' || alert.status === 'RESOLVED' || alert.status === 'DISMISSED') {
      items.push({
        title: 'Incident Acknowledged by Operator',
        stage: 'Incident Management Lifecycle',
        timestamp: alert.acknowledged_at ? new Date(alert.acknowledged_at).toUTCString() : 'Timestamp unavailable',
        status: 'completed',
        icon: '👁️',
        description: `Alert acknowledged by operator (${alert.acknowledged_by || 'Control Room Operator'}). Dispatched for active investigation.`,
        badge: 'ACKNOWLEDGED',
      });
    }

    if (alert.status === 'INVESTIGATING' || alert.status === 'RESOLVED') {
      items.push({
        title: 'Active Investigation Protocol Initiated',
        stage: 'Incident Management Lifecycle',
        timestamp: alert.updated_at ? new Date(alert.updated_at).toUTCString() : 'Timestamp unavailable',
        status: alert.status === 'INVESTIGATING' ? 'active' : 'completed',
        icon: '🔍',
        description: 'Ground team / facility operator coordination underway. Analyzing cross-sensor visual and thermal telemetry.',
        badge: 'INVESTIGATING',
      });
    }

    if (alert.status === 'RESOLVED') {
      items.push({
        title: 'Incident Resolved & Closed',
        stage: 'Incident Management Lifecycle',
        timestamp: alert.resolved_at ? new Date(alert.resolved_at).toUTCString() : alert.updated_at ? new Date(alert.updated_at).toUTCString() : 'Timestamp unavailable',
        status: 'completed',
        icon: '✅',
        description: `Incident investigation concluded. Operator notes: "${alert.resolution_notes || 'Confirmed and addressed in accordance with standard operating procedure.'}"`,
        badge: 'RESOLVED',
      });
    } else if (alert.status === 'DISMISSED') {
      items.push({
        title: 'Incident Dismissed / Non-Actionable',
        stage: 'Incident Management Lifecycle',
        timestamp: alert.resolved_at ? new Date(alert.resolved_at).toUTCString() : alert.updated_at ? new Date(alert.updated_at).toUTCString() : 'Timestamp unavailable',
        status: 'completed',
        icon: '⚪',
        description: `Incident marked non-actionable. Reason: "${alert.resolution_notes || 'Dismissed by operator following visual and spatial validation.'}"`,
        badge: 'DISMISSED',
      });
    }
  }

  return (
    <div className="investigation-timeline-component">
      <div className="timeline-header">
        <span className="timeline-title">📜 Chronological Investigation Audit Trail</span>
        <span className="timeline-subtitle">Defensible end-to-end provenance from satellite telemetry to resolution</span>
      </div>

      <div className="timeline-container">
        {items.map((item, idx) => (
          <div key={idx} className={`timeline-step-item status-${item.status}`}>
            <div className="timeline-left-marker">
              <div className="timeline-icon-circle">{item.icon}</div>
              {idx < items.length - 1 && <div className="timeline-line-connector" />}
            </div>

            <div className="timeline-step-content">
              <div className="step-header-row">
                <span className="step-title">{item.title}</span>
                {item.badge && <span className="step-badge">{item.badge}</span>}
              </div>

              <div className="step-meta-row">
                <span className="step-stage">{item.stage}</span>
                <span className="step-timestamp">⏱️ {item.timestamp}</span>
              </div>

              <p className="step-description">{item.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
