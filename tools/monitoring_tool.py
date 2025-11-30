"""
Monitoring Tool - Simulates monitoring system alerts

Generates mock alerts for testing the incident response system.
"""

import structlog
from typing import Dict, Any, List
from datetime import datetime
import random

logger = structlog.get_logger()


class MonitoringTool:
    """
    Tool for simulating monitoring system alerts.
    """

    def __init__(self):
        """Initialize monitoring tool."""
        logger.info("monitoring_tool_initialized")

    def generate_sample_alert(self, severity: str = "SEV2") -> Dict[str, Any]:
        """
        Generate a sample monitoring alert.

        Args:
            severity: Desired severity level

        Returns:
            Dict with alert data
        """
        alert_types = [
            {
                "type": "high_error_rate",
                "service": "api-gateway",
                "metric": "error_rate",
                "threshold": 5.0,
                "current": 12.3,
                "message": "Error rate exceeded threshold: 12.3% (threshold: 5.0%)"
            },
            {
                "type": "high_latency",
                "service": "database",
                "metric": "query_latency_p99",
                "threshold": 1000,
                "current": 3500,
                "message": "Database query latency P99 at 3500ms (threshold: 1000ms)"
            },
            {
                "type": "service_down",
                "service": "payment-processor",
                "metric": "health_check",
                "threshold": 1,
                "current": 0,
                "message": "Payment processor service health check failing"
            },
            {
                "type": "high_cpu",
                "service": "worker-pool",
                "metric": "cpu_usage",
                "threshold": 80,
                "current": 95,
                "message": "Worker pool CPU usage at 95% (threshold: 80%)"
            },
            {
                "type": "memory_leak",
                "service": "cache-service",
                "metric": "memory_usage",
                "threshold": 85,
                "current": 92,
                "message": "Cache service memory usage at 92% and rising"
            }
        ]

        alert_data = random.choice(alert_types)

        return {
            "alert_id": f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            **alert_data,
            "source": "monitoring-system",
            "environment": "production",
            "runbook_url": f"https://runbooks.example.com/{alert_data['type']}"
        }

    def get_sample_alerts_batch(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Generate multiple sample alerts for testing.

        Args:
            count: Number of alerts to generate

        Returns:
            List of alert dictionaries
        """
        severities = ["SEV1", "SEV2", "SEV3", "SEV4"]
        weights = [0.1, 0.3, 0.4, 0.2]  # Distribution of severities

        alerts = []
        for _ in range(count):
            severity = random.choices(severities, weights=weights)[0]
            alerts.append(self.generate_sample_alert(severity))

        logger.info("generated_sample_alerts", count=count)
        return alerts
