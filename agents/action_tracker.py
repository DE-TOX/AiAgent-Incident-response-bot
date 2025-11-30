"""
Action Tracker Agent - Manages incident action items

This agent:
- Extracts action items from incidents and postmortems
- Creates tickets in issue tracking systems (Jira/GitHub)
- Tracks completion status
- Sends reminders for overdue items
"""

import structlog
from typing import Dict, Any, List
import google.generativeai as genai
from datetime import datetime, timedelta

logger = structlog.get_logger()


class ActionTrackerAgent:
    """
    Specialized agent for tracking incident action items.
    """

    def __init__(self, config: Dict[str, Any], issue_tracker=None):
        """
        Initialize the action tracker agent.

        Args:
            config: Configuration dictionary
            issue_tracker: IssueTrackingTool instance (optional)
        """
        self.config = config
        self.model_name = config.get("agents", {}).get("action_tracker", {}).get("model", "gemini-2.5-flash")
        self.temperature = config.get("agents", {}).get("action_tracker", {}).get("temperature", 0.2)

        self.model = genai.GenerativeModel(self.model_name)

        # Issue tracking tool
        self.issue_tracker = issue_tracker

        # Track action items
        self.action_items: Dict[str, List[Dict[str, Any]]] = {}

        logger.info("action_tracker_initialized", model=self.model_name)

    async def extract_action_items(self, text: str, incident_id: str) -> List[Dict[str, Any]]:
        """
        Extract action items from postmortem or incident notes using Gemini.

        Args:
            text: Postmortem or incident text
            incident_id: Associated incident ID

        Returns:
            List of structured action items
        """
        logger.info("extracting_action_items", incident_id=incident_id)

        try:
            # Build prompt for action item extraction
            prompt = self._build_extraction_prompt(text, incident_id)

            # Extract with Gemini
            response = self.model.generate_content(prompt)

            # Parse response
            action_items = self._parse_action_items(response.text, incident_id)

            logger.info("action_items_extracted",
                       incident_id=incident_id,
                       count=len(action_items))

            return action_items

        except Exception as e:
            logger.error("action_extraction_failed",
                        error=str(e),
                        incident_id=incident_id)
            return []

    def _build_extraction_prompt(self, text: str, incident_id: str) -> str:
        """Build prompt for extracting action items."""

        prompt = f"""You are an expert SRE analyzing an incident postmortem to extract actionable items.

POSTMORTEM TEXT:
{text[:2000]}

TASK: Extract ALL action items, improvements, and follow-up tasks from this text.

For each action item, provide in this EXACT format:
ACTION: [description of the action]
PRIORITY: [HIGH|MEDIUM|LOW]
CATEGORY: [monitoring|process|documentation|technical|other]
ESTIMATED_EFFORT: [hours or story points estimate]

Example format:
ACTION: Implement automated rollback for payment service
PRIORITY: HIGH
CATEGORY: technical
ESTIMATED_EFFORT: 8 hours

ACTION: Update runbook with new troubleshooting steps
PRIORITY: MEDIUM
CATEGORY: documentation
ESTIMATED_EFFORT: 2 hours

Extract all action items you can find. Be thorough and specific."""

        return prompt

    def _parse_action_items(self, response_text: str, incident_id: str) -> List[Dict[str, Any]]:
        """Parse action items from Gemini response."""

        action_items = []
        lines = response_text.split('\n')

        current_action = {}

        for line in lines:
            line = line.strip()

            if line.startswith('ACTION:'):
                # Save previous action if exists
                if current_action.get('description'):
                    current_action['incident_id'] = incident_id
                    current_action['created_at'] = datetime.now().isoformat()
                    current_action['status'] = 'open'
                    action_items.append(current_action)

                # Start new action
                current_action = {
                    'description': line.replace('ACTION:', '').strip(),
                    'priority': 'MEDIUM',  # default
                    'category': 'other',
                    'estimated_effort': 'TBD'
                }

            elif line.startswith('PRIORITY:'):
                priority = line.replace('PRIORITY:', '').strip().upper()
                if priority in ['HIGH', 'MEDIUM', 'LOW']:
                    current_action['priority'] = priority

            elif line.startswith('CATEGORY:'):
                category = line.replace('CATEGORY:', '').strip().lower()
                current_action['category'] = category

            elif line.startswith('ESTIMATED_EFFORT:'):
                effort = line.replace('ESTIMATED_EFFORT:', '').strip()
                current_action['estimated_effort'] = effort

        # Don't forget the last action
        if current_action.get('description'):
            current_action['incident_id'] = incident_id
            current_action['created_at'] = datetime.now().isoformat()
            current_action['status'] = 'open'
            action_items.append(current_action)

        return action_items

    async def create_tickets(self, action_items: List[Dict[str, Any]], incident_id: str) -> List[Dict[str, Any]]:
        """
        Create tickets in issue tracking system for action items.

        Args:
            action_items: List of action items to create tickets for
            incident_id: Associated incident ID

        Returns:
            List of created tickets with IDs
        """
        logger.info("creating_tickets", incident_id=incident_id, count=len(action_items))

        created_tickets = []

        if not self.issue_tracker:
            logger.warning("no_issue_tracker_configured")
            return []

        for item in action_items:
            try:
                # Create ticket using issue tracking tool
                ticket = await self.issue_tracker.create_ticket(
                    title=f"[{item.get('priority')}] {item.get('description', 'Action Item')[:80]}",
                    description=self._format_ticket_description(item, incident_id),
                    priority=item.get('priority', 'medium').lower(),
                    labels=[
                        f"incident-{incident_id}",
                        f"priority-{item.get('priority', 'medium').lower()}",
                        f"category-{item.get('category', 'other')}"
                    ],
                    incident_id=incident_id
                )

                created_tickets.append({
                    **item,
                    'ticket_id': ticket.get('id'),
                    'ticket_url': ticket.get('url')
                })

                logger.info("ticket_created",
                           ticket_id=ticket.get('id'),
                           action=item.get('description')[:50])

            except Exception as e:
                logger.error("ticket_creation_failed",
                            error=str(e),
                            action=item.get('description'))

        # Store action items
        if incident_id not in self.action_items:
            self.action_items[incident_id] = []
        self.action_items[incident_id].extend(created_tickets)

        return created_tickets

    def _format_ticket_description(self, action_item: Dict[str, Any], incident_id: str) -> str:
        """Format ticket description with action item details."""

        description = f"""# Action Item from Incident {incident_id}

## Description
{action_item.get('description', 'No description')}

## Details
- **Priority:** {action_item.get('priority', 'MEDIUM')}
- **Category:** {action_item.get('category', 'other')}
- **Estimated Effort:** {action_item.get('estimated_effort', 'TBD')}
- **Incident:** {incident_id}
- **Created:** {action_item.get('created_at', datetime.now().isoformat())}

## Context
This action item was identified during the postmortem analysis of incident {incident_id}.

## Acceptance Criteria
- [ ] Action completed and validated
- [ ] Documentation updated (if applicable)
- [ ] Changes deployed and verified
- [ ] Incident tagged as resolved

---

*Auto-generated by Incident Response Bot*
"""

        return description

    async def check_overdue_items(self) -> List[Dict[str, Any]]:
        """
        Check for overdue action items.

        Returns:
            List of overdue action items
        """
        logger.info("checking_overdue_items")

        overdue = []
        current_time = datetime.now()

        for incident_id, items in self.action_items.items():
            for item in items:
                # Check if item is still open and past due date
                if item.get('status') == 'open' and item.get('due_date'):
                    try:
                        due_date = datetime.fromisoformat(item['due_date'])
                        if current_time > due_date:
                            overdue.append(item)
                    except (ValueError, TypeError):
                        pass

        logger.info("overdue_check_complete", overdue_count=len(overdue))
        return overdue

    def get_action_items_for_incident(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get all action items for a specific incident."""
        return self.action_items.get(incident_id, [])

    def get_all_action_items(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all action items across all incidents."""
        return self.action_items
