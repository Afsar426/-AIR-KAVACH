import React, { useEffect, useState } from 'react';
import { fetchModelStatus, triggerModelTraining } from '../api';
import { Cpu, RefreshCw, CheckCircle2, AlertTriangle, Layers } from 'lucide-react';

export default function ModelMonitoringPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetchModelStatus();
      setStatus(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTrain = async () => {
    try {
      setTraining(true);
      await triggerModelTraining();
      await loadData();
    } catch (err) {
      alert("Error training model: " + err.message);
    } finally {
      setTraining(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <RefreshCw size={24} className="spin" /> Loading Isolation Forest Model Lifecycle Status...
      </div>
    );
  }

  const meta = status?.metadata;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      <div className="page-header">
        <div>
          <h2 className="page-title">Machine Learning Model Lifecycle</h2>
          <p className="page-subtitle">
            Station-specific Isolation Forest model artifacts (<code>isolation_forest_v1.joblib</code>), rolling feature schemas, and unsupervised anomaly scoring.
          </p>
        </div>

        <button onClick={handleTrain} disabled={training} className="btn-primary">
          <Cpu size={16} /> {training ? "Training Joblib Artifact..." : "Retrain Isolation Forest"}
        </button>
      </div>

      {/* Explanatory banner */}
      <div className="alert-callout alert-callout-info">
        <Layers size={20} color="var(--accent)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '0.85rem', lineHeight: '1.5' }}>
          <strong>Unsupervised Anomaly Model:</strong> Station-level Isolation Forest models are trained on past rolling observations. They compute multidimensional anomaly scores to complement statistical Z-score detection ($Z \ge 2.0\sigma$) without requiring ground-truth industrial labels.
        </div>
      </div>

      <div className="grid-cols-3">
        <div className="card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, letterSpacing: '0.04em' }}>MODEL ARTIFACT STATUS</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--success)', margin: '0.4rem 0' }}>
            {status?.status?.toUpperCase() || 'TRAINED'}
          </div>
          <span className="badge badge-success">Serialized on Disk</span>
        </div>

        <div className="card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, letterSpacing: '0.04em' }}>ARCHITECTURE & ENSEMBLE</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary)', margin: '0.4rem 0' }}>
            {meta?.model_type || 'IsolationForest'}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            {meta?.n_estimators || 300} Trees &bull; Contamination: {meta?.contamination || 0.02}
          </div>
        </div>

        <div className="card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, letterSpacing: '0.04em' }}>TRAINING SAMPLES & RECENCY</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary)', margin: '0.4rem 0' }}>
            {meta?.total_training_samples?.toLocaleString() || 'N/A'}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Trained: {meta?.trained_at ? new Date(meta.trained_at).toLocaleString() : 'N/A'}
          </div>
        </div>
      </div>

      {/* Feature Schema */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: 'var(--primary)', margin: 0 }}>Input Feature Schema</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
              Normalized feature vector fed into the isolation trees during offline scoring and inference.
            </p>
          </div>
          <span className="badge badge-neutral">{meta?.feature_schema?.length || 0} Features</span>
        </div>
        <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
          {meta?.feature_schema?.map((f) => (
            <span key={f} className="badge badge-info" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
              <code>{f}</code>
            </span>
          ))}
        </div>
      </div>

    </div>
  );
}
