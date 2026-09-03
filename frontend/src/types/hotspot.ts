export interface Hotspot {
  latitude: number;
  longitude: number;
  brightness: number;
  confidence: string | number;
  frp: number;
  acquired_at: string;
  acq_date?: string;
  acq_time?: string;
  satellite: string;
  instrument: string;
  source: string;
}

export interface HotspotsApiResponse {
  source: string;
  region: string;
  bbox: number[];
  count: number;
  hotspots: Hotspot[];
  fetched_at: string;
}

export interface OsmFeature {
  name: string;
  type: 'industrial' | 'power' | 'urban' | 'road';
  category: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  osm_id: string;
}

export interface HotspotContextResponse {
  hotspot: {
    latitude: number;
    longitude: number;
  };
  search_radius_km: number;
  context_classification: 'INDUSTRIAL' | 'URBAN' | 'RURAL_OR_AGRICULTURAL' | 'UNKNOWN';
  facility_count: number;
  nearby_features: OsmFeature[];
  nearby_facility?: string | null;
  distance_km?: number | null;
  fetched_at: string;
}


export interface PersistentCluster {
  cluster_id: string;
  center_latitude: number;
  center_longitude: number;
  observation_count: number;
  first_detected: string;
  last_detected: string;
  duration_hours: number;
  spatial_radius_km: number;
  persistence_score: number;
  classification: 'TEMPORARY' | 'SUSPICIOUS' | 'PERSISTENT' | 'HIGHLY PERSISTENT';
  observations: Hotspot[];
  industrial_context?: {
    context_classification: string;
    nearby_facility: string | null;
    facility_type: string | null;
    facility_category: string | null;
    distance_km: number | null;
  } | null;
  has_sufficient_history: boolean;
}

export interface PersistentClustersApiResponse {
  source: string;
  region: string;
  total_clusters: number;
  persistent_cluster_count: number;
  spatial_threshold_km: number;
  clusters: PersistentCluster[];
  status: string;
  message?: string;
  fetched_at: string;
}

export interface AiClassificationResponse {
  classification: string;
  confidence_percentage: number;
  model_source: 'ML_MODEL' | 'PROTOTYPE_RULE_ENGINE';
  model_status: 'trained' | 'not_trained';
  model_version: string;
  supporting_indicators: string[];
  features: Record<string, number | string>;
}

export interface RiskScoreResponse {
  risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  model_source: 'ML_MODEL' | 'PROTOTYPE_RULE_ENGINE';
  classification: string;
  components: {
    thermal_intensity: number;
    satellite_confidence: number;
    persistence: number;
    industrial_proximity: number;
    classification_context: number;
  };
  max_component_weights: {
    thermal_intensity: number;
    satellite_confidence: number;
    persistence: number;
    industrial_proximity: number;
    classification_context: number;
  };
  normalized_scores_100: Record<string, number>;
  reasons: string[];
  features: Record<string, number | string>;
  fetched_at: string;
}

export interface PriorityRankingItem {
  rank: number;
  cluster_id: string;
  latitude: number;
  longitude: number;
  risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  classification: string;
  industrial_facility: string;
  industrial_distance_km: number | null;
  persistence_score: number;
  observation_count: number;
  duration_hours: number;
  reasons: string[];
}

export interface ThermalAlert {
  alert_id: string;
  cluster_id: string;
  latitude: number;
  longitude: number;
  risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  classification: string;
  model_source: 'ML_MODEL' | 'PROTOTYPE_RULE_ENGINE';
  persistence_score: number;
  observation_count: number;
  duration_hours: number;
  industrial_distance_km: number | null;
  facility_name: string | null;
  status: 'NEW' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED' | 'DISMISSED';
  evidence: string[];
  features: Record<string, number | string>;
  created_at: string;
  updated_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
  resolution_notes?: string | null;
}

export interface AlertStats {
  total_alerts: number;
  active_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  acknowledged_alerts: number;
  investigating_alerts: number;
  resolved_today: number;
  fetched_at: string;
}

export interface SatelliteEvidence {
  image_available: boolean;
  classification: 'INDUSTRIAL_FIRE' | 'NATURAL_FIRE' | 'PERSISTENT_THERMAL_SOURCE' | 'NON_FIRE' | 'UNKNOWN';
  confidence: number;
  source: string;
  model?: string;
  model_type?: string;
  model_version?: string;
  captured_at?: string;
  image_url?: string;
  visual_evidence: string;
  class_probabilities?: Record<string, number>;
  gradcam_overlay_path?: string;
  gradcam_region?: string;
}


export interface FusedEvidenceResponse {
  final_classification: string;
  combined_confidence: number;
  combined_confidence_percentage: number;
  combined_risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  fusion_summary: string;
  evidence: {
    firms: {
      frp_mw: number;
      brightness_k: number;
      confidence: string;
      summary: string;
    };
    osm: {
      context: string;
      nearby_facility: string;
      distance_km: number | null;
      summary: string;
    };
    persistence: {
      persistence_score: number;
      observation_count: number;
      duration_hours: number;
      summary: string;
    };
    satellite: SatelliteEvidence;
  };
}
