import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from src.utils.logger import get_logger
from src.utils.config import AIR_QUALITY_FILE, ISOLATION_FOREST_MODEL_DIR

logger = get_logger("isolation_forest_service")

WINDOW = 96
MIN_PERIODS = 24
MAX_GAP_MINUTES = 15
CONTAMINATION = 0.02
RANDOM_STATE = 42
FEATURES = ["value", "deviation", "past_std", "hour_sin", "hour_cos"]


class IsolationForestService:
    def __init__(self, model_dir: Path = ISOLATION_FOREST_MODEL_DIR):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / "isolation_forest_v1.joblib"
        self.metadata_path = self.model_dir / "metadata.json"

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes rolling historical features and cyclic temporal variables without data leakage."""
        clean_df = df[df["parameter"].astype(str).str.lower().eq("pm25")].copy()
        clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"], utc=True, errors="coerce")
        clean_df["value"] = pd.to_numeric(clean_df["value"], errors="coerce")
        clean_df = clean_df.dropna(subset=["station", "timestamp", "value"])
        clean_df = clean_df.sort_values(["station", "timestamp"]).reset_index(drop=True)

        clean_df["gap_minutes"] = clean_df.groupby("station")["timestamp"].diff().dt.total_seconds() / 60
        starts_segment = clean_df["gap_minutes"].isna() | (clean_df["gap_minutes"] > MAX_GAP_MINUTES)
        clean_df["segment_id"] = starts_segment.groupby(clean_df["station"]).cumsum()
        keys = ["station", "segment_id"]

        values = clean_df.groupby(keys, sort=False)["value"]
        clean_df["past_mean"] = values.transform(
            lambda s: s.shift(1).rolling(WINDOW, min_periods=MIN_PERIODS).mean()
        )
        clean_df["past_std"] = values.transform(
            lambda s: s.shift(1).rolling(WINDOW, min_periods=MIN_PERIODS).std()
        )
        clean_df["deviation"] = clean_df["value"] - clean_df["past_mean"]
        clean_df["past_z_score"] = clean_df["deviation"] / clean_df["past_std"].replace(0, np.nan)

        hour = clean_df["timestamp"].dt.hour + clean_df["timestamp"].dt.minute / 60
        clean_df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        clean_df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

        return clean_df

    def train_and_save(self) -> Dict[str, Any]:
        """Trains station-specific or unified Isolation Forest models and serializes artifacts."""
        logger.info("Training Isolation Forest model...")
        if not AIR_QUALITY_FILE.exists():
            raise FileNotFoundError(f"Air quality dataset missing: {AIR_QUALITY_FILE}")

        raw_df = pd.read_parquet(AIR_QUALITY_FILE)
        df = self.prepare_features(raw_df)

        usable = df[FEATURES].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
        X = df.loc[usable, FEATURES].astype(float)

        if len(X) < 50:
            raise ValueError(f"Insufficient training data: only {len(X)} eligible rows.")

        station_models = {}
        station_stats = {}

        for station in df.loc[usable, "station"].unique():
            idx = df.index[usable & df["station"].eq(station)]
            X_st = df.loc[idx, FEATURES].astype(float)
            if len(X_st) < 50:
                continue

            model = IsolationForest(
                n_estimators=300,
                contamination=CONTAMINATION,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            model.fit(X_st)
            station_models[str(station)] = model
            flags = model.predict(X_st) == -1
            station_stats[str(station)] = {
                "trained_samples": int(len(X_st)),
                "anomalies_detected": int(flags.sum()),
                "anomaly_rate_pct": round(float(flags.mean() * 100), 2),
            }

        # Also fit a global fallback model
        global_model = IsolationForest(
            n_estimators=300,
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        global_model.fit(X)

        artifact_payload = {
            "station_models": station_models,
            "global_model": global_model,
            "feature_names": FEATURES,
            "contamination": CONTAMINATION,
            "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
        }

        joblib.dump(artifact_payload, self.model_path)

        metadata = {
            "version": "1.0.0",
            "model_type": "IsolationForest",
            "n_estimators": 300,
            "contamination": CONTAMINATION,
            "random_state": RANDOM_STATE,
            "total_training_samples": int(len(X)),
            "feature_schema": FEATURES,
            "trained_at": artifact_payload["trained_at"],
            "station_summary": station_stats,
            "artifact_file": self.model_path.name,
        }

        self.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.info(f"Model saved to {self.model_path}")
        return metadata

    def load_model(self) -> Dict[str, Any]:
        """Loads serialized model payload."""
        if not self.model_path.exists():
            # Try to train if dataset exists
            logger.warning(f"Model artifact not found at {self.model_path}. Training new model...")
            self.train_and_save()

        return joblib.load(self.model_path)

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executes inference on given DataFrame and returns anomaly scores and flags."""
        payload = self.load_model()
        station_models = payload.get("station_models", {})
        global_model = payload.get("global_model")

        df_feat = self.prepare_features(df)
        usable = df_feat[FEATURES].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)

        df_feat["anomaly_score"] = np.nan
        df_feat["isolation_forest_anomaly"] = False

        for station in df_feat["station"].unique():
            st_mask = df_feat["station"].eq(station) & usable
            if not st_mask.any():
                continue

            idx = df_feat.index[st_mask]
            X_st = df_feat.loc[idx, FEATURES].astype(float)

            if str(station) in station_models:
                m = station_models[str(station)]
            elif global_model is not None:
                m = global_model
            else:
                continue

            scores = -m.decision_function(X_st)
            flags = m.predict(X_st) == -1

            df_feat.loc[idx, "anomaly_score"] = scores
            df_feat.loc[idx, "isolation_forest_anomaly"] = flags

        return df_feat

    def get_status(self) -> Dict[str, Any]:
        """Returns metadata and health of the ML model."""
        if not self.model_path.exists() or not self.metadata_path.exists():
            return {
                "status": "unavailable",
                "model_loaded": False,
                "message": "Model artifact not serialized.",
            }

        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            return {
                "status": "active",
                "model_loaded": True,
                "metadata": metadata,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
