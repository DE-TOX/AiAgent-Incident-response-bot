"""
Tests for tools
"""

import pytest
from tools.slack_tool import SlackTool
from tools.issue_tracking import IssueTrackingTool
from tools.monitoring_tool import MonitoringTool


@pytest.mark.asyncio
async def test_slack_notification():
    """Test Slack notification in mock mode."""
    slack = SlackTool(mock_mode=True)

    result = await slack.send_notification(
        message="Test notification",
        channel="#test",
        severity="SEV2"
    )

    assert result is True


@pytest.mark.asyncio
async def test_issue_tracking_create_ticket():
    """Test ticket creation in mock mode."""
    tracker = IssueTrackingTool(mock_mode=True)

    ticket = await tracker.create_ticket(
        title="Test ticket",
        description="Test description",
        priority="high",
        labels=["test"]
    )

    assert "id" in ticket
    assert ticket["title"] == "Test ticket"
    assert ticket["priority"] == "high"


def test_monitoring_tool_generate_alert():
    """Test alert generation."""
    monitoring = MonitoringTool()

    alert = monitoring.generate_sample_alert(severity="SEV2")

    assert alert is not None
    assert alert["severity"] == "SEV2"
    assert "alert_id" in alert
    assert "service" in alert
    assert "message" in alert


def test_monitoring_tool_batch_alerts():
    """Test batch alert generation."""
    monitoring = MonitoringTool()

    alerts = monitoring.get_sample_alerts_batch(count=5)

    assert len(alerts) == 5
    for alert in alerts:
        assert "severity" in alert
        assert "alert_id" in alert


# TODO: Add integration tests for real API calls (when not in mock mode)
