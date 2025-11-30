"""
Postmortem Writer Agent - Creates detailed postmortem documents

This agent generates comprehensive postmortems including:
- Incident timeline and root cause analysis
- What went well / What went wrong
- Action items and preventive measures
- Lessons learned
"""

import structlog
from typing import Dict, Any, List
import google.generativeai as genai
from datetime import datetime

logger = structlog.get_logger()


class PostmortemWriterAgent:
    """
    Specialized agent for writing incident postmortems.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the postmortem writer agent.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.model_name = config.get("agents", {}).get("postmortem_writer", {}).get("model", "gemini-2.5-flash")
        self.temperature = config.get("agents", {}).get("postmortem_writer", {}).get("temperature", 0.5)

        self.model = genai.GenerativeModel(self.model_name)

        logger.info("postmortem_writer_initialized", model=self.model_name)

    async def write_postmortem(
        self,
        incident_data: Dict[str, Any],
        similar_incidents: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive postmortem document.

        Args:
            incident_data: Complete incident information
            similar_incidents: Related past incidents for context

        Returns:
            Dict with postmortem content and extracted action items
        """
        logger.info("writing_postmortem", incident_id=incident_data.get("incident_id"))

        try:
            # Build comprehensive postmortem prompt
            prompt = self._build_postmortem_prompt(incident_data, similar_incidents)

            # Generate postmortem with Gemini
            response = self.model.generate_content(prompt)

            # Parse response to extract action items and lessons
            parsed_result = self._parse_postmortem_response(response.text, incident_data)

            # Format final postmortem document
            postmortem = self._format_postmortem(incident_data, parsed_result['content'])

            logger.info("postmortem_generated",
                       incident_id=incident_data.get("incident_id"),
                       action_items_count=len(parsed_result['action_items']))

            return {
                "postmortem": postmortem,
                "action_items": parsed_result['action_items'],
                "lessons_learned": parsed_result['lessons_learned']
            }

        except Exception as e:
            logger.error("postmortem_generation_failed",
                        error=str(e),
                        incident_id=incident_data.get("incident_id"))
            # Fallback to template-based postmortem
            return self._fallback_postmortem(incident_data)

    def _build_postmortem_prompt(self, incident_data: Dict[str, Any], similar_incidents: List[Dict[str, Any]] = None) -> str:
        """Build comprehensive prompt for postmortem generation."""

        # Build context from similar incidents if provided
        similar_context = ""
        if similar_incidents:
            similar_context = "\n\nSIMILAR PAST INCIDENTS:\n"
            for inc in similar_incidents[:3]:
                similar_context += f"- {inc.get('title', 'Unknown')}: {inc.get('resolution', 'N/A')}\n"

        prompt = f"""You are an expert SRE writing a detailed incident postmortem. Create a comprehensive, blameless postmortem following industry best practices.

INCIDENT DETAILS:
- Incident ID: {incident_data.get('incident_id', 'N/A')}
- Title: {incident_data.get('title', 'Unknown')}
- Severity: {incident_data.get('severity', 'Unknown')}
- Status: {incident_data.get('status', 'resolved')}
- Affected Services: {', '.join(incident_data.get('affected_services', []))}
- Error Messages: {', '.join(incident_data.get('error_messages', []))}
- Actions Taken: {', '.join(incident_data.get('recommended_actions', []))}
{similar_context}

Create a BLAMELESS postmortem with these sections:

## Executive Summary
[2-3 sentences: What happened, impact, resolution, key learnings]

## Timeline of Events
[Detailed timeline from detection to resolution:
- HH:MM - Alert triggered
- HH:MM - Investigation began
- HH:MM - Root cause identified
- HH:MM - Mitigation applied
- HH:MM - Incident resolved]

## Root Cause Analysis
[Use the 5 Whys technique:
1. Why did the incident occur?
2. Why did that happen?
3. Why wasn't it caught earlier?
4. Why didn't our systems prevent this?
5. Why was the impact so significant?

Then provide the ROOT CAUSE in one clear sentence.]

## What Went Well ✅
[List 3-5 things that worked well:
- Detection and alerting
- Team response
- Communication
- Mitigation speed
- Tools and processes that helped]

## What Went Wrong ❌
[List 3-5 things that didn't go well:
- Gaps in monitoring
- Process failures
- Technical debt
- Documentation issues
- Areas for improvement]

## Action Items
[List specific, actionable items with priority:
Format: [PRIORITY] Action description
- [HIGH] Example: Implement automated rollback for service X
- [MEDIUM] Example: Add monitoring for metric Y
- [LOW] Example: Update runbook for scenario Z]

## Lessons Learned
[3-5 key takeaways that will prevent future incidents]

## Preventive Measures
[Specific steps to prevent recurrence]

Keep it professional, blameless, and actionable. Focus on systems and processes, not individuals."""

        return prompt

    def _parse_postmortem_response(self, response_text: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse postmortem response to extract structured data."""

        # Extract action items from the response
        action_items = []
        lessons_learned = []

        lines = response_text.split('\n')
        in_action_section = False
        in_lessons_section = False

        for line in lines:
            line_stripped = line.strip()

            # Detect sections
            if '## Action Items' in line_stripped or '##Action Items' in line_stripped:
                in_action_section = True
                in_lessons_section = False
                continue
            elif '## Lessons Learned' in line_stripped or '##Lessons Learned' in line_stripped:
                in_lessons_section = True
                in_action_section = False
                continue
            elif line_stripped.startswith('##'):
                in_action_section = False
                in_lessons_section = False
                continue

            # Extract action items
            if in_action_section and line_stripped.startswith('-'):
                # Parse priority and description
                action_text = line_stripped[1:].strip()
                priority = "MEDIUM"  # default

                if '[HIGH]' in action_text or '[CRITICAL]' in action_text:
                    priority = "HIGH"
                    action_text = action_text.replace('[HIGH]', '').replace('[CRITICAL]', '').strip()
                elif '[LOW]' in action_text:
                    priority = "LOW"
                    action_text = action_text.replace('[LOW]', '').strip()
                elif '[MEDIUM]' in action_text:
                    action_text = action_text.replace('[MEDIUM]', '').strip()

                if action_text:
                    action_items.append({
                        "description": action_text,
                        "priority": priority,
                        "incident_id": incident_data.get('incident_id')
                    })

            # Extract lessons learned
            if in_lessons_section and line_stripped.startswith('-'):
                lesson = line_stripped[1:].strip()
                if lesson:
                    lessons_learned.append(lesson)

        return {
            "content": response_text,
            "action_items": action_items,
            "lessons_learned": lessons_learned
        }

    def _format_postmortem(self, incident_data: Dict[str, Any], ai_content: str) -> str:
        """Format the complete postmortem document with metadata."""

        return f"""# Postmortem: {incident_data.get('title', 'Unknown')}

**Incident ID:** {incident_data.get('incident_id', 'N/A')}
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Severity:** {incident_data.get('severity', 'Unknown')}
**Status:** {incident_data.get('status', 'Resolved')}
**Author:** Incident Response Bot (AI-Generated)

---

{ai_content}

---

**Postmortem Completed:** {datetime.now().isoformat()}
**Generated by:** Incident Response Bot powered by Gemini
"""

    def _fallback_postmortem(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic postmortem if Gemini fails."""

        postmortem = f"""# Postmortem: {incident_data.get('title', 'Unknown')}

**Incident ID:** {incident_data.get('incident_id', 'N/A')}
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Severity:** {incident_data.get('severity', 'Unknown')}
**Author:** Incident Response Bot

## Executive Summary
Incident {incident_data.get('incident_id')} affecting {', '.join(incident_data.get('affected_services', ['unknown services']))} was detected and resolved.

## Timeline
- Alert triggered for {incident_data.get('title', 'incident')}
- Investigation initiated
- Issue mitigated
- Incident resolved

## Root Cause
To be determined through manual investigation.

## Impact
Services affected: {', '.join(incident_data.get('affected_services', ['unknown']))}
Error messages: {', '.join(incident_data.get('error_messages', ['none recorded']))}

## Action Items
- Investigate root cause in detail
- Implement monitoring improvements
- Update runbooks

## Lessons Learned
- Postmortem requires manual completion
- AI generation unavailable

---

*Template postmortem - Gemini unavailable. Manual review required.*
"""

        return {
            "postmortem": postmortem,
            "action_items": [{
                "description": "Complete full postmortem analysis",
                "priority": "HIGH",
                "incident_id": incident_data.get('incident_id')
            }],
            "lessons_learned": ["AI postmortem generation failed - requires manual intervention"]
        }

            