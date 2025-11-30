"""
Triage Agent - Classifies and prioritizes incoming incidents

This agent analyzes incoming alerts and messages to:
- Determine incident severity (SEV1-SEV4)
- Extract key information (affected services, error messages, etc.)
- Assign initial priority and routing
"""

import structlog
from typing import Dict, Any
import google.generativeai as genai

logger = structlog.get_logger()


class TriageAgent:
    """
    Specialized agent for incident classification and triage.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the triage agent.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.model_name = config.get("agents", {}).get("triage", {}).get("model", "gemini-2.5-flash")
        self.temperature = config.get("agents", {}).get("triage", {}).get("temperature", 0.2)

        self.model = genai.GenerativeModel(self.model_name)

        logger.info("triage_agent_initialized", model=self.model_name)

    async def classify_incident(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify incident severity and extract key information.

        Args:
            alert_data: Raw alert/notification data

        Returns:
            Dict with severity, title, affected_services, etc.
        """
        logger.info("classifying_incident", alert_data=alert_data)

        # Build classification prompt with severity guidelines
        prompt = self._build_classification_prompt(alert_data)

        try:
            # Call Gemini for classification
            response = self.model.generate_content(prompt)

            # Parse the response
            result = self._parse_classification_response(response.text, alert_data)

            logger.info("incident_classified", severity=result.get("severity"), title=result.get("title"))
            return result

        except Exception as e:
            logger.error("classification_failed", error=str(e), alert_data=alert_data)
            # Fallback to basic classification
            return self._fallback_classification(alert_data)

    def _build_classification_prompt(self, alert_data: Dict[str, Any]) -> str:
        """Build the prompt for incident classification."""

        prompt = f"""You are an expert SRE analyzing a production incident alert.

SEVERITY CLASSIFICATION GUIDELINES:
- SEV1 (Critical): Complete service outage, major revenue impact, all customers affected
- SEV2 (High): Partial service degradation, significant customer impact, workaround exists
- SEV3 (Medium): Minor service impact, limited customers affected, low urgency
- SEV4 (Low): Cosmetic issues, monitoring alerts, no customer impact

ALERT DATA:
Service: {alert_data.get('service', 'Unknown')}
Message: {alert_data.get('message', 'No message')}
Metric: {alert_data.get('metric', 'N/A')}
Current Value: {alert_data.get('current', 'N/A')}
Threshold: {alert_data.get('threshold', 'N/A')}
Environment: {alert_data.get('environment', 'production')}

TASK:
Analyze this alert and provide a structured classification in this EXACT format:

SEVERITY: [SEV1|SEV2|SEV3|SEV4]
TITLE: [concise incident title in 5-10 words]
AFFECTED_SERVICES: [comma-separated list of affected services]
SYMPTOMS: [key symptoms and error messages]
IMMEDIATE_ACTIONS: [recommended first steps to investigate or mitigate]

Be precise and actionable."""

        return prompt

    def _parse_classification_response(self, response_text: str, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gemini's classification response."""

        result = {
            "severity": "SEV3",  # Default
            "title": alert_data.get('message', 'Incident'),
            "affected_services": [alert_data.get('service', 'unknown')],
            "error_messages": [alert_data.get('message', '')],
            "recommended_actions": []
        }

        # Parse the structured response
        lines = response_text.strip().split('\n')

        for line in lines:
            line = line.strip()

            if line.startswith('SEVERITY:'):
                severity = line.split(':', 1)[1].strip()
                if severity in ['SEV1', 'SEV2', 'SEV3', 'SEV4']:
                    result['severity'] = severity

            elif line.startswith('TITLE:'):
                result['title'] = line.split(':', 1)[1].strip()

            elif line.startswith('AFFECTED_SERVICES:'):
                services_str = line.split(':', 1)[1].strip()
                if services_str and services_str.lower() != 'none':
                    result['affected_services'] = [s.strip() for s in services_str.split(',')]

            elif line.startswith('SYMPTOMS:'):
                symptoms = line.split(':', 1)[1].strip()
                if symptoms:
                    result['error_messages'] = [symptoms]

            elif line.startswith('IMMEDIATE_ACTIONS:'):
                actions = line.split(':', 1)[1].strip()
                if actions:
                    result['recommended_actions'] = [a.strip() for a in actions.split(',')]

        return result

    def _fallback_classification(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback classification if Gemini fails."""

        # Simple rule-based classification
        message = alert_data.get('message', '').lower()
        service = alert_data.get('service', 'unknown')

        # Determine severity based on keywords
        severity = 'SEV3'
        if any(word in message for word in ['down', 'outage', 'critical', 'failed']):
            severity = 'SEV1'
        elif any(word in message for word in ['high', 'degraded', 'timeout', 'error']):
            severity = 'SEV2'
        elif any(word in message for word in ['warning', 'elevated']):
            severity = 'SEV3'
        else:
            severity = 'SEV4'

        return {
            "severity": severity,
            "title": f"{severity}: {alert_data.get('message', 'Incident')[:50]}",
            "affected_services": [service],
            "error_messages": [alert_data.get('message', '')],
            "recommended_actions": ["Investigate alert", "Check service health", "Review recent changes"]
        }