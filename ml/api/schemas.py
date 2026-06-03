"""Pydantic request/response schemas for the TerraShield FastAPI backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    sensor_id: str
    domain:    str                           # 'water' | 'soil' | 'health'
    values:    Dict[str, float]              # {metric: value}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnomalyAlert(BaseModel):
    sensor_id:     str
    domain:        str
    anomaly_score: float                     # 0–1
    is_anomaly:    bool
    severity:      str                       # 'normal' | 'warning' | 'critical'
    timestamp:     datetime


class TrustUpdate(BaseModel):
    sensor_id:    str
    domain:       str
    sensor_trust: float                      # P(healthy) for this sensor
    domain_trust: Dict[str, float]           # domain → aggregate trust


class CorrelationSnapshot(BaseModel):
    water_soil:   float
    water_health: float
    soil_health:  float
    timestamp:    datetime


class ProvenanceStepOut(BaseModel):
    step:        int
    node_id:     str
    domain:      str
    event_type:  str
    title:       str
    confidence:  float
    color:       str                         # hex colour for the React UI node
    description: str
    timestamp:   datetime


class ProvenanceReportOut(BaseModel):
    chain_length:        int
    root_cause:          str
    cascade_duration_h:  Optional[float]
    overall_confidence:  float
    detection_latency_s: float
    steps:               List[ProvenanceStepOut]


class TerraShieldEvent(BaseModel):
    """Envelope for all WebSocket messages."""
    event_type: str   # 'sensor_update' | 'anomaly' | 'trust_update'
                      # | 'correlation' | 'provenance' | 'ping'
    payload:    Dict[str, Any]
    timestamp:  datetime = Field(default_factory=datetime.utcnow)


class StatusResponse(BaseModel):
    domain_trust:       Dict[str, float]
    active_ws_clients:  int
    buffer_sizes:       Dict[str, int]
    uptime_s:           float
    timestamp:          datetime
