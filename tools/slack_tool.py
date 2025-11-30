"""
Slack Integration Tool - Send notifications to Slack channels

Supports both mock mode (for demo) and real webhook integration.
"""

import structlog
from typing import Dict, Any, Optional
import httpx
import json

logger = structlog.get_logger()


class SlackTool:
    """
    Tool for sending notifications to Slack.
    """

    def __init__(self, webhook_url: Optional[str] = None, mock_mode: bool = True):
        """
        Initialize Slack tool.

        Args:
            webhook_url: Slack webhook URL (required if not in mock mode)
            mock_mode: If True, simulate notifications without actually sending
        """
        self.webhook_url = webhook_url
        self.mock_mode = mock_mode

        logger.info("slack_tool_initialized", mock_mode=mock_mode)

    async def send_notification(
        self,
        message: str,
        channel: Optional[str] = None,
        severity: Optional[str] = None
    ) -> bool:
        """
        Send a notification to Slack.

        Args:
            message: Message content
            channel: Target channel (optional)
            severity: Incident severity for formatting

        Returns:
            Success status
        """
        # Format message with severity color
        color = self._get_severity_color(severity)

        payload = {
            "text": message,
            "attachments": [{
                "color": color,
                "text": message,
                "footer": "Incident Response Bot"
            }]
        }

        if channel:
            payload["channel"] = channel

        if self.mock_mode:
            logger.info("slack_notification_mock", payload=payload)
            print(f"\n[MOCK SLACK] Sending to {channel or 'default'}:")
            print(f"  {message}")
            return True

        # Real webhook mode
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()

            logger.info("slack_notification_sent", channel=channel)
            return True

        except Exception as e:
            logger.error("slack_notification_failed", error=str(e))
            return False

    def _get_severity_color(self, severity: Optional[str]) -> str:
        """Get color code for severity level."""
        colors = {
            "SEV1": "#d9534f",  # Red
            "SEV2": "#f0ad4e",  # Orange
            "SEV3": "#5bc0de",  # Blue
            "SEV4": "#5cb85c",  # Green
        }
        return colors.get(severity, "#777777")