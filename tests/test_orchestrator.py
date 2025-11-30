"""
Tests for orchestrator agent
"""

import pytest
from agents.orchestrator import OrchestratorAgent


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "agents": {
            "orchestrator": {
                "model": "gemini-2.5-flash",
                "temperature": 0.3
            }
        }
    }


def test_orchestrator_initialization(mock_config):
    """Test that orchestrator initializes correctly."""
    orchestrator = OrchestratorAgent(mock_config)

    assert orchestrator is not None
    assert orchestrator.model_name == "gemini-2.5-flash"
    assert orchestrator.temperature == 0.3
    assert orchestrator.active_incidents == {}


@pytest.mark.asyncio
async def test_process_incident(mock_config):
    """Test incident processing."""
    orchestrator = OrchestratorAgent(mock_config)

    incident_data = {
        "alert_id": "TEST-001",
        "severity": "SEV2",
        "message": "Test alert"
    }

    result = await orchestrator.process_incident(incident_data)

    assert "incident_id" in result
    assert "status" in result
    assert result["status"] == "processing"


# TODO: Add more comprehensive tests for:
# - Postmortem generation
# - Knowledge retrieval
# - Error handling
# - Session management
