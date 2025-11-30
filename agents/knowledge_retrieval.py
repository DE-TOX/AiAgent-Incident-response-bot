"""
Knowledge Retrieval Agent - Searches and retrieves past incident information

This agent:
- Maintains embeddings of past incidents
- Performs semantic search for similar incidents
- Provides relevant context from incident history
- Suggests solutions based on past resolutions
"""

import structlog
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
import json
from datetime import datetime
import os

logger = structlog.get_logger()


class KnowledgeRetrievalAgent:
    """
    Specialized agent for retrieving knowledge from past incidents.
    Uses embeddings and semantic search for intelligent retrieval.
    """

    def __init__(self, config: Dict[str, Any], db_path: str = "./data/chroma_db"):
        """
        Initialize the knowledge retrieval agent.

        Args:
            config: Configuration dictionary
            db_path: Path to ChromaDB storage
        """
        self.config = config
        self.model_name = config.get("agents", {}).get("knowledge_retrieval", {}).get("model", "gemini-2.5-flash")
        self.temperature = config.get("agents", {}).get("knowledge_retrieval", {}).get("temperature", 0.1)

        self.model = genai.GenerativeModel(self.model_name)

        # Initialize ChromaDB
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)

        try:
            self.chroma_client = chromadb.PersistentClient(path=db_path)
            self.collection = self.chroma_client.get_or_create_collection(
                name="incidents",
                metadata={"description": "Past incident embeddings for similarity search"}
            )
            logger.info("chromadb_initialized", path=db_path)
        except Exception as e:
            logger.warning("chromadb_init_failed", error=str(e))
            self.chroma_client = None
            self.collection = None

        logger.info("knowledge_retrieval_initialized", model=self.model_name)

    async def index_incident(self, incident_data: Dict[str, Any]) -> bool:
        """
        Index a resolved incident in the knowledge base.

        Args:
            incident_data: Complete incident information including postmortem

        Returns:
            Success status
        """
        incident_id = incident_data.get("incident_id")
        logger.info("indexing_incident", incident_id=incident_id)

        if not self.collection:
            logger.warning("chromadb_not_available")
            return False

        try:
            # Build searchable text from incident
            searchable_text = self._build_searchable_text(incident_data)

            # Generate embedding using Gemini
            embedding = await self._generate_embedding(searchable_text)

            # Prepare metadata
            metadata = {
                "incident_id": incident_id,
                "title": incident_data.get("title", "")[:500],
                "severity": incident_data.get("severity", ""),
                "status": incident_data.get("status", ""),
                "created_at": incident_data.get("created_at", ""),
                "services": ",".join(incident_data.get("affected_services", []))[:500]
            }

            # Store in ChromaDB
            self.collection.add(
                ids=[incident_id],
                embeddings=[embedding],
                documents=[searchable_text],
                metadatas=[metadata]
            )

            logger.info("incident_indexed", incident_id=incident_id)
            return True

        except Exception as e:
            logger.error("indexing_failed", incident_id=incident_id, error=str(e))
            return False

    async def search_similar_incidents(
        self,
        query: str,
        limit: int = 5,
        severity_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar past incidents using semantic search.

        Args:
            query: Search query (symptoms, error messages, etc.)
            limit: Maximum number of results
            severity_filter: Optional filter by severity level

        Returns:
            List of similar incidents with relevance scores
        """
        logger.info("searching_similar_incidents", query=query, limit=limit)

        if not self.collection:
            logger.warning("chromadb_not_available")
            return []

        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)

            # Build filter if needed
            where_filter = None
            if severity_filter:
                where_filter = {"severity": severity_filter}

            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter
            )

            # Format results
            similar_incidents = []

            if results and results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    incident = {
                        "incident_id": results['ids'][0][i],
                        "title": results['metadatas'][0][i].get('title', ''),
                        "severity": results['metadatas'][0][i].get('severity', ''),
                        "services": results['metadatas'][0][i].get('services', '').split(','),
                        "similarity_score": 1 - results['distances'][0][i],  # Convert distance to similarity
                        "summary": results['documents'][0][i][:200] + "..."
                    }
                    similar_incidents.append(incident)

            logger.info("similar_incidents_found", count=len(similar_incidents))
            return similar_incidents

        except Exception as e:
            logger.error("search_failed", error=str(e), exc_info=True)
            return []

    async def suggest_solutions(self, current_incident: Dict[str, Any]) -> List[str]:
        """
        Suggest solutions based on similar past incidents.

        Args:
            current_incident: Current incident data

        Returns:
            List of suggested solutions/actions
        """
        incident_id = current_incident.get("incident_id")
        logger.info("suggesting_solutions", incident_id=incident_id)

        try:
            # Search for similar incidents
            query = f"{current_incident.get('title', '')} {' '.join(current_incident.get('error_messages', []))}"
            similar = await self.search_similar_incidents(query, limit=3)

            if not similar:
                logger.info("no_similar_incidents_found")
                return []

            # Build prompt for solution synthesis
            prompt = self._build_solution_prompt(current_incident, similar)

            # Use Gemini to synthesize solutions
            response = self.model.generate_content(prompt)

            # Parse solutions
            solutions = self._parse_solutions(response.text)

            logger.info("solutions_suggested", count=len(solutions))
            return solutions

        except Exception as e:
            logger.error("solution_suggestion_failed", error=str(e))
            return []

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Gemini."""
        try:
            # Use Gemini's embedding API
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Return zero vector as fallback
            return [0.0] * 768

    def _build_searchable_text(self, incident_data: Dict[str, Any]) -> str:
        """Build searchable text from incident data."""

        parts = [
            f"Title: {incident_data.get('title', '')}",
            f"Severity: {incident_data.get('severity', '')}",
            f"Services: {', '.join(incident_data.get('affected_services', []))}",
            f"Errors: {' '.join(incident_data.get('error_messages', []))}",
        ]

        # Add postmortem if available
        if incident_data.get('postmortem'):
            pm = incident_data['postmortem']
            # Extract key sections
            parts.append(f"Postmortem: {pm[:1000]}")

        # Add lessons learned
        if incident_data.get('lessons_learned'):
            parts.append(f"Lessons: {' '.join(incident_data['lessons_learned'])}")

        return " ".join(parts)

    def _build_solution_prompt(self, current: Dict[str, Any], similar: List[Dict[str, Any]]) -> str:
        """Build prompt for solution synthesis."""

        similar_text = "\n".join([
            f"- {inc['title']} (Similarity: {inc['similarity_score']:.2f})"
            for inc in similar
        ])

        prompt = f"""You are an expert SRE analyzing similar past incidents to suggest solutions.

CURRENT INCIDENT:
- Title: {current.get('title', 'Unknown')}
- Severity: {current.get('severity', 'Unknown')}
- Services: {', '.join(current.get('affected_services', []))}
- Errors: {', '.join(current.get('error_messages', []))}

SIMILAR PAST INCIDENTS:
{similar_text}

TASK: Based on these similar incidents, suggest 3-5 specific solutions or actions that might help resolve the current incident.

Format each solution as:
- [Action description in one sentence]

Be specific and actionable. Focus on immediate steps that worked for similar incidents."""

        return prompt

    def _parse_solutions(self, response_text: str) -> List[str]:
        """Parse solutions from AI response."""

        solutions = []
        lines = response_text.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                solution = line[1:].strip()
                if solution and len(solution) > 10:
                    solutions.append(solution)

        return solutions[:5]  # Limit to top 5

    def get_incident_count(self) -> int:
        """Get total number of incidents in knowledge base."""
        if not self.collection:
            return 0
        try:
            return self.collection.count()
        except:
            return 0

    def clear_knowledge_base(self):
        """Clear all incidents from knowledge base (use with caution)."""
        if self.collection:
            try:
                self.chroma_client.delete_collection(name="incidents")
                self.collection = self.chroma_client.create_collection(name="incidents")
                logger.info("knowledge_base_cleared")
            except Exception as e:
                logger.error("clear_failed", error=str(e))
