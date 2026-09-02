import React, { useState } from 'react';
import { AiClassificationResponse } from '../types/hotspot';

interface AiClassificationCardProps {
  classificationData: AiClassificationResponse | null;
  loading: boolean;
  error: string | null;
}

export const AiClassificationCard: React.FC<AiClassificationCardProps> = ({
  classificationData,
  loading,
  error,
}) => {
  const [showFeatures, setShowFeatures] = useState<boolean>(false);

  if (loading) {
    return (
      <div className="ai-card loading-card">
        <div className="spinner-small" />
        <span>Running Explainable AI Classifier...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-card error-card">
        <span>⚠️ AI Classification Error: {error}</span>
      </div>
    );
  }

  if (!classificationData) return null;

  const {
    classification,
    confidence_percentage,
    model_source,
    model_status,
    supporting_indicators,
    features,
  } = classificationData;

  const getCategoryBadgeClass = (cat: string) => {
    switch (cat) {
      case 'INDUSTRIAL_FIRE_CANDIDATE':
        return 'cat-badge-industrial-fire';
      case 'PERSISTENT_THERMAL_SOURCE':
        return 'cat-badge-persistent';
      case 'AGRICULTURAL_BURNING_CANDIDATE':
        return 'cat-badge-agri';
      case 'WILDFIRE_CANDIDATE':
        return 'cat-badge-wildfire';
      case 'GAS_FLARE_CANDIDATE':
        return 'cat-badge-flare';
      default:
        return 'cat-badge-uncertain';
    }
  };

  const formatCategoryName = (cat: string) => {
    switch (cat) {
      case 'INDUSTRIAL_FIRE_CANDIDATE':
        return '🏭 Industrial Fire Candidate';
      case 'PERSISTENT_THERMAL_SOURCE':
        return '🔴 Persistent Thermal Source';
      case 'AGRICULTURAL_BURNING_CANDIDATE':
        return '🌾 Agricultural Burning Candidate';
      case 'WILDFIRE_CANDIDATE':
        return '🔥 Wildfire Candidate';
      case 'GAS_FLARE_CANDIDATE':
        return '⚡ Gas Flare Candidate';
      default:
        return '❓ Uncertain Classification';
    }
  };

  return (
    <div className="ai-card">
      <div className="ai-card-header">
        <span className="ai-title">🤖 Explainable AI Classification</span>
        <span className="model-version">v{classificationData.model_version}</span>
      </div>

      <div className="ai-card-body">
        {/* Model Status & Source Pill */}
        <div className="model-status-pill">
          {model_source === 'PROTOTYPE_RULE_ENGINE' ? (
            <span className="pill-warning">
              ⚠️ Prototype Rule Engine ({model_status === 'not_trained' ? 'ML model not trained' : 'Fallback'})
            </span>
          ) : (
            <span className="pill-success">
              🤖 Trained Random Forest ML Model
            </span>
          )}
        </div>

        {/* Classification Result Badge */}
        <div className={`ai-result-badge ${getCategoryBadgeClass(classification)}`}>
          {formatCategoryName(classification)}
        </div>

        {/* Confidence Percentage Meter */}
        <div className="confidence-meter">
          <div className="meter-label-row">
            <span>Confidence Level:</span>
            <span className="meter-val">{confidence_percentage}%</span>
          </div>
          <div className="meter-bar-bg">
            <div
              className="meter-bar-fill"
              style={{ width: `${confidence_percentage}%` }}
            />
          </div>
        </div>

        {/* Supporting Indicators (Explainability) */}
        <div className="indicators-section">
          <div className="indicators-title">Supporting Indicators:</div>
          <ul className="indicators-list">
            {supporting_indicators.map((ind, idx) => (
              <li key={`ind-${idx}`} className="indicator-item">
                ✓ {ind}
              </li>
            ))}
          </ul>
        </div>

        {/* Expandable Raw Feature Details Drawer */}
        <div className="features-drawer">
          <button
            className="drawer-toggle-btn"
            onClick={() => setShowFeatures(!showFeatures)}
          >
            {showFeatures ? '▼ Hide Input Features' : '▶ View Input Features (9)'}
          </button>

          {showFeatures && (
            <div className="feature-grid">
              {Object.entries(features).map(([key, val]) => (
                <div key={key} className="feature-grid-item">
                  <span className="feat-key">{key.replace('_', ' ')}:</span>
                  <span className="feat-val">{String(val)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
