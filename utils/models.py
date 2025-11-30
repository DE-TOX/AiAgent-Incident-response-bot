"""
Data models for incident response system

Pydantic models for type safety and validation.
"""

from pydantic import BaseModel, Field

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SeverityLevel(str, Enum):
    """Incident severity levels."""
    SEV1 = "SEV1"  # Critical
    SEV2 = "SEV2"  # High
    SEV3 = "SEV3"  # Medium
    SEV4 = "SEV4"  # Low


class IncidentStatus(str, Enum):
    """Incident status values."""
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"
    CLOSED = "closed"


class ActionItemPriority(str, Enum):
    """Action item priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Incident(BaseModel):
    """Incident data model."""
    incident_id: str
    title: str
    description: str
    severity: SeverityLevel
    status: IncidentStatus = IncidentStatus.ACTIVE
    affected_services: List[str] = Field(default_factory=list)
    error_messages: List[str] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class IncidentReport(BaseModel):
    """Incident report model."""
    incident_id: str
    report_type: str = "status_update"  # status_update, final_report, postmortem
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "IncidentResponseBot"


class ActionItem(BaseModel):
    """Action item model."""
    action_id: str
    incident_id: str
    description: str
    priority: ActionItemPriority
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = "open"  # open, in_progress, completed
    ticket_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class Postmortem(BaseModel):
    """Postmortem document model."""
    incident_id: str
    title: str
    summary: str
    timeline: List[Dict[str, Any]]
    root_cause: str
    what_went_well: List[str]
    what_went_wrong: List[str]
    action_items: List[ActionItem]
    lessons_learned: List[str]
    created_at: datetime = Field(default_factory=datetime.now)
    author: str = "IncidentResponseBot"


class AlertData(BaseModel):
    """Monitoring alert data model."""
    alert_id: str
    timestamp: datetime
    severity: SeverityLevel
    service: str
    metric: str
    message: str
    threshold: Optional[float] = None
    current: Optional[float] = None
    source: str = "monitoring-system"
    environment: str = "production"
    runbook_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
