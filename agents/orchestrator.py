"""
Orchestrator Agent - Main coordinator for the incident response system

This agent manages the overall workflow and coordinates between specialized sub-agents:
- Receives incoming incidents
- Routes to appropriate sub-agents based on task
- Maintains incident state and context
- Ensures proper workflow execution
"""

import structlog
from typing import Dict, Any, Optional
from datetime import datetime
import google.generativeai as genai

logger = structlog.get_logger()


class OrchestratorAgent:
    """
    Main orchestrator agent that coordinates all incident response activities.

    Uses Gemini to intelligently route tasks to specialized sub-agents and
    maintain incident context throughout the response lifecycle.
    """

    def __init__(self, config: Dict[str, Any], triage_agent=None, report_agent=None, postmortem_agent=None, action_tracker=None, knowledge_agent=None):
        """
        Initialize the orchestrator agent.

        Args:
            config: Configuration dictionary containing model settings
            triage_agent: TriageAgent instance (optional)
            report_agent: ReportGeneratorAgent instance (optional)
            postmortem_agent: PostmortemWriterAgent instance (optional)
            action_tracker: ActionTrackerAgent instance (optional)
            knowledge_agent: KnowledgeRetrievalAgent instance (optional)
        """
        self.config = config
        self.model_name = config.get("agents", {}).get("orchestrator", {}).get("model", "gemini-2.5-flash")
        self.temperature = config.get("agents", {}).get("orchestrator", {}).get("temperature", 0.3)

        # Initialize Gemini model
        self.model = genai.GenerativeModel(self.model_name)

        # Sub-agents
        self.triage_agent = triage_agent
        self.report_agent = report_agent
        self.postmortem_agent = postmortem_agent
        self.action_tracker = action_tracker
        self.knowledge_agent = knowledge_agent

        # Track active incidents
        self.active_incidents: Dict[str, Dict[str, Any]] = {}
        self.incident_counter = 1

        logger.info("orchestrator_initialized", model=self.model_name)

    async def process_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming incident through the full workflow.

        Args:
            incident_data: Raw incident information

        Returns:
            Dict containing incident ID, classification, and initial report
        """
        logger.info("orchestrator_processing_incident", alert_id=incident_data.get("alert_id"))

        # Generate incident ID
        incident_id = self._generate_incident_id()

        try:
            # Step 1: Triage - Classify the incident
            logger.info("orchestrator_step_triage", incident_id=incident_id)
            classification = await self.triage_agent.classify_incident(incident_data)

            # Build full incident object
            incident = {
                "incident_id": incident_id,
                "alert_id": incident_data.get("alert_id"),
                "timestamp": datetime.now().isoformat(),
                "status": "active",
                **classification  # Merge classification results
            }

            # Step 2: Generate initial incident report
            logger.info("orchestrator_step_report", incident_id=incident_id)
            report = await self.report_agent.generate_report(incident)

            # Store incident
            self.active_incidents[incident_id] = {
                **incident,
                "report": report,
                "created_at": datetime.now().isoformat()
            }

            logger.info("orchestrator_incident_processed",
                       incident_id=incident_id,
                       severity=classification.get("severity"))

            return {
                "incident_id": incident_id,
                "severity": classification.get("severity"),
                "title": classification.get("title"),
                "status": "active",
                "report": report,
                "classification": classification,
                "message": f"Incident {incident_id} created and processed"
            }

        except Exception as e:
            logger.error("orchestrator_processing_failed",
                        incident_id=incident_id,
                        error=str(e),
                        exc_info=True)

            return {
                "incident_id": incident_id,
                "status": "error",
                "message": f"Failed to process incident: {str(e)}"
            }

    def _generate_incident_id(self) -> str:
        """Generate a unique incident ID."""
        timestamp = datetime.now().strftime("%Y%m%d")
        incident_id = f"INC-{timestamp}-{self.incident_counter:03d}"
        self.incident_counter += 1
        return incident_id

    async def generate_postmortem(self, incident_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive postmortem for a resolved incident.

        Args:
            incident_id: Unique incident identifier

        Returns:
            Dict containing postmortem content, action items, similar incidents, and tickets
        """
        logger.info("orchestrator_generating_postmortem", incident_id=incident_id)

        # Retrieve incident data
        incident = self.active_incidents.get(incident_id)

        if not incident:
            logger.error("incident_not_found", incident_id=incident_id)
            return {
                "error": f"Incident {incident_id} not found",
                "incident_id": incident_id
            }

        if not self.postmortem_agent:
            logger.error("postmortem_agent_not_configured")
            return {
                "error": "Postmortem agent not configured",
                "incident_id": incident_id
            }

        try:
            # Mark incident as resolved (for postmortem context)
            incident['status'] = 'resolved'
            incident['resolved_at'] = datetime.now().isoformat()

            # Step 1: Search for similar past incidents (if knowledge agent available)
            similar_incidents = []
            if self.knowledge_agent:
                logger.info("orchestrator_step_knowledge_retrieval", incident_id=incident_id)
                try:
                    query = f"{incident.get('title', '')} {' '.join(incident.get('error_messages', []))}"
                    similar_incidents = await self.knowledge_agent.search_similar_incidents(
                        query=query,
                        limit=3
                    )

                    if similar_incidents:
                        logger.info("similar_incidents_found", count=len(similar_incidents))
                except Exception as e:
                    logger.warning("knowledge_retrieval_failed", error=str(e))

            # Step 2: Generate postmortem with AI (include similar incidents for context)
            logger.info("orchestrator_step_postmortem_write", incident_id=incident_id)
            postmortem_result = await self.postmortem_agent.write_postmortem(
                incident_data=incident,
                similar_incidents=similar_incidents
            )

            # Step 3: Create tickets for action items (if action tracker available)
            created_tickets = []
            if self.action_tracker and postmortem_result.get('action_items'):
                logger.info("orchestrator_step_create_tickets",
                           incident_id=incident_id,
                           action_count=len(postmortem_result['action_items']))

                created_tickets = await self.action_tracker.create_tickets(
                    action_items=postmortem_result['action_items'],
                    incident_id=incident_id
                )

            # Step 4: Index this incident in knowledge base for future reference
            if self.knowledge_agent:
                logger.info("orchestrator_step_index_incident", incident_id=incident_id)
                try:
                    # Prepare incident data with postmortem for indexing
                    incident_to_index = {
                        **incident,
                        'postmortem': postmortem_result['postmortem'],
                        'action_items': postmortem_result['action_items'],
                        'lessons_learned': postmortem_result['lessons_learned']
                    }
                    await self.knowledge_agent.index_incident(incident_to_index)
                    logger.info("incident_indexed_successfully", incident_id=incident_id)
                except Exception as e:
                    logger.warning("incident_indexing_failed", error=str(e))

            # Update incident with postmortem data
            self.active_incidents[incident_id].update({
                'postmortem': postmortem_result['postmortem'],
                'action_items': postmortem_result['action_items'],
                'lessons_learned': postmortem_result['lessons_learned'],
                'similar_incidents': similar_incidents,
                'tickets': created_tickets,
                'status': 'closed',
                'closed_at': datetime.now().isoformat()
            })

            logger.info("orchestrator_postmortem_complete",
                       incident_id=incident_id,
                       action_items=len(postmortem_result['action_items']),
                       tickets_created=len(created_tickets),
                       similar_found=len(similar_incidents))

            return {
                "incident_id": incident_id,
                "postmortem": postmortem_result['postmortem'],
                "action_items": postmortem_result['action_items'],
                "lessons_learned": postmortem_result['lessons_learned'],
                "similar_incidents": similar_incidents,
                "tickets": created_tickets,
                "status": "completed"
            }

        except Exception as e:
            logger.error("orchestrator_postmortem_failed",
                        incident_id=incident_id,
                        error=str(e),
                        exc_info=True)

            return {
                "incident_id": incident_id,
                "error": f"Postmortem generation failed: {str(e)}",
                "status": "failed"
            }

    async def query_knowledge(self, query: str) -> Dict[str, Any]:
        """
        Query past incidents for similar issues.

        Args:
            query: Search query or description

        Returns:
            Dict containing relevant past incidents
        """
        logger.info("querying_knowledge", query=query)

        # TODO: Implement knowledge retrieval
        # Call knowledge retrieval agent with query

        return {
            "query": query,
            "results": [],
            "count": 0
        }