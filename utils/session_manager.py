"""
Session management for incident response bot

Handles incident state persistence and memory management.
"""

import json
import structlog
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from utils.models import Incident, IncidentStatus
from utils.config import get_incidents_dir

logger = structlog.get_logger()


class SessionManager:
    """
    Manages incident sessions and state persistence.
    """

    def __init__(self):
        """Initialize session manager."""
        self.active_sessions: Dict[str, Incident] = {}
        self.incidents_dir = get_incidents_dir()

        logger.info("session_manager_initialized", incidents_dir=str(self.incidents_dir))

    def create_session(self, incident_data: Dict[str, Any]) -> Incident:
        """
        Create a new incident session.

        Args:
            incident_data: Initial incident data

        Returns:
            Incident object
        """
        incident = Incident(**incident_data)
        self.active_sessions[incident.incident_id] = incident

        # Persist to disk
        self._save_incident(incident)

        logger.info("session_created", incident_id=incident.incident_id)
        return incident

    def get_session(self, incident_id: str) -> Optional[Incident]:
        """
        Get an active session or load from disk.

        Args:
            incident_id: Incident identifier

        Returns:
            Incident object or None
        """
        # Check active sessions first
        if incident_id in self.active_sessions:
            return self.active_sessions[incident_id]

        # Try to load from disk
        incident = self._load_incident(incident_id)
        if incident:
            self.active_sessions[incident_id] = incident

        return incident

    def update_session(self, incident_id: str, updates: Dict[str, Any]) -> Optional[Incident]:
        """
        Update an incident session.

        Args:
            incident_id: Incident identifier
            updates: Dictionary of fields to update

        Returns:
            Updated incident object or None
        """
        incident = self.get_session(incident_id)
        if not incident:
            logger.warning("session_not_found", incident_id=incident_id)
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(incident, key):
                setattr(incident, key, value)

        incident.updated_at = datetime.now()

        # Persist changes
        self._save_incident(incident)

        logger.info("session_updated", incident_id=incident_id)
        return incident

    def close_session(self, incident_id: str) -> bool:
        """
        Close an incident session.

        Args:
            incident_id: Incident identifier

        Returns:
            Success status
        """
        incident = self.get_session(incident_id)
        if not incident:
            return False

        incident.status = IncidentStatus.CLOSED
        incident.resolved_at = datetime.now()

        self._save_incident(incident)

        # Remove from active sessions
        self.active_sessions.pop(incident_id, None)

        logger.info("session_closed", incident_id=incident_id)
        return True

    def list_active_sessions(self) -> list:
        """List all active incident sessions."""
        return list(self.active_sessions.values())

    def _save_incident(self, incident: Incident):
        """Save incident to disk."""
        incident_file = self.incidents_dir / f"{incident.incident_id}.json"

        with open(incident_file, 'w') as f:
            json.dump(incident.model_dump(mode='json'), f, indent=2, default=str)

        logger.debug("incident_saved", incident_id=incident.incident_id)

    def _load_incident(self, incident_id: str) -> Optional[Incident]:
        """Load incident from disk."""
        incident_file = self.incidents_dir / f"{incident_id}.json"

        if not incident_file.exists():
            return None

        try:
            with open(incident_file, 'r') as f:
                data = json.load(f)

            incident = Incident(**data)
            logger.debug("incident_loaded", incident_id=incident_id)
            return incident

        except Exception as e:
            logger.error("incident_load_failed", incident_id=incident_id, error=str(e))
            return None