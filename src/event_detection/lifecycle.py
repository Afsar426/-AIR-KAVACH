"""
AIR KAVACH - Event Lifecycle & Temporal Status Policy
Scientifically classifies pollution events based on observation timestamps,
station continuous monitoring history, and temporal proximity to current time.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
import pandas as pd


class EventLifecycleState(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    RECENT = "recent"
    HISTORICAL = "historical"
    INSUFFICIENT_DATA = "insufficient_data"


class EventLifecycleManager:
    """
    Computes rigorous temporal lifecycle classification for detected pollution events.
    Guarantees that historical events are NEVER classified as active.
    """

    @classmethod
    def evaluate_lifecycle(
        cls,
        start_time: Any,
        end_time: Any,
        latest_observation: Optional[Any] = None,
        reference_time: Optional[datetime] = None,
        reading_count: int = 4,
    ) -> tuple[str, Dict[str, Any]]:
        """Convenience evaluation returning (state_str, metadata_dict)."""
        meta = cls.classify_event(
            start_time=start_time,
            end_time=end_time,
            latest_station_obs_time=latest_observation,
            reference_time=reference_time,
            readings_count=reading_count,
        )
        # Add hours_since_end for convenience
        ref_dt = reference_time or datetime.now(timezone.utc)
        try:
            end_dt = pd.to_datetime(end_time, utc=True)
            meta["hours_since_end"] = (ref_dt - end_dt).total_seconds() / 3600.0
        except Exception:
            meta["hours_since_end"] = 0.0
        meta["reading_count"] = reading_count
        return meta["temporal_status"], meta

    @staticmethod
    def classify_event(
        start_time: Any,
        end_time: Any,
        latest_station_obs_time: Optional[Any] = None,
        reference_time: Optional[datetime] = None,
        readings_count: int = 4,
    ) -> Dict[str, Any]:
        """
        Classifies an event into one of five definitive temporal states:
        - 'active': ongoing elevation where end_time matches newest reading and reading is fresh (<= 6h).
        - 'resolved': ended within last 72 hours, with subsequent baseline observations recorded.
        - 'recent': ended between 72 hours and 30 days ago.
        - 'historical': ended more than 30 days ago (or part of an archival dataset).
        - 'insufficient_data': incomplete event boundaries or fewer than 4 readings.
        """
        now = reference_time or datetime.now(timezone.utc)

        # Parse timestamps safely
        try:
            start_dt = pd.to_datetime(start_time, utc=True)
            end_dt = pd.to_datetime(end_time, utc=True)
        except Exception:
            return {
                "temporal_status": "insufficient_data",
                "lifecycle_label": "Invalid or unparseable event timestamp boundaries",
                "is_active": False,
                "latest_station_observation": None,
                "observation_age_hours": None,
            }

        latest_obs_dt = pd.to_datetime(latest_station_obs_time, utc=True) if latest_station_obs_time else end_dt
        obs_age_hours = round((now - latest_obs_dt).total_seconds() / 3600.0, 1)
        event_age_hours = (now - end_dt).total_seconds() / 3600.0

        # Insufficient data check
        if readings_count < 4 or pd.isna(start_dt) or pd.isna(end_dt) or end_dt < start_dt:
            return {
                "temporal_status": "insufficient_data",
                "lifecycle_label": "Insufficient readings (< 4) to confirm continuous episode",
                "is_active": False,
                "latest_station_observation": latest_obs_dt.isoformat(),
                "observation_age_hours": obs_age_hours,
                "hours_since_end": round(event_age_hours, 1) if pd.notna(event_age_hours) else None,
            }

        # Active check: event must have concluded within last 6 hours AND latest reading is not after event end
        if event_age_hours <= 6.0 and latest_obs_dt <= end_dt:
            return {
                "temporal_status": "active",
                "lifecycle_label": f"Active Ongoing Elevation (Latest reading: {latest_obs_dt.strftime('%Y-%m-%d %H:%M UTC')})",
                "is_active": True,
                "latest_station_observation": latest_obs_dt.isoformat(),
                "observation_age_hours": obs_age_hours,
                "hours_since_end": round(event_age_hours, 1),
            }

        # Resolved check: event ended within last 72 hours AND newer normal readings have been received
        if event_age_hours <= 72.0:
            return {
                "temporal_status": "resolved",
                "lifecycle_label": f"Recently Resolved ({obs_age_hours:.1f}h ago; subsequent normal baseline observed)",
                "is_active": False,
                "latest_station_observation": latest_obs_dt.isoformat(),
                "observation_age_hours": obs_age_hours,
                "hours_since_end": round(event_age_hours, 1),
            }

        # Recent operational window: between 3 days and 30 days
        if event_age_hours <= 720.0:  # 30 days
            days_ago = round(event_age_hours / 24.0, 1)
            return {
                "temporal_status": "recent",
                "lifecycle_label": f"Recent Episode ({days_ago} days ago)",
                "is_active": False,
                "latest_station_observation": latest_obs_dt.isoformat(),
                "observation_age_hours": obs_age_hours,
                "hours_since_end": round(event_age_hours, 1),
            }

        # Historical event: older than 30 days
        days_ago = round(event_age_hours / 24.0, 1)
        return {
            "temporal_status": "historical",
            "lifecycle_label": f"Historical Validation Event (Concluded {end_dt.strftime('%Y-%m-%d')}, {days_ago} days ago)",
            "is_active": False,
            "latest_station_observation": latest_obs_dt.isoformat(),
            "observation_age_hours": obs_age_hours,
            "hours_since_end": round(event_age_hours, 1),
        }
