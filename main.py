"""
Incident Response Bot - Main entry point

Run incident response scenarios and demonstrations.
"""

import asyncio
import structlog
import os
import google.generativeai as genai
from utils.config import load_config
from utils.logging_config import setup_logging
from agents.orchestrator import OrchestratorAgent
from agents.triage_agent import TriageAgent
from agents.report_generator import ReportGeneratorAgent
from agents.postmortem_writer import PostmortemWriterAgent
from agents.action_tracker import ActionTrackerAgent
from agents.knowledge_retrieval import KnowledgeRetrievalAgent
from tools.monitoring_tool import MonitoringTool
from tools.slack_tool import SlackTool
from tools.issue_tracking import IssueTrackingTool

logger = structlog.get_logger()


async def demo_incident_response():
    """
    Demonstrate the incident response workflow with a simulated incident.
    """
    print("\n" + "="*70)
    print("  🤖 Incident Response Bot - Live Demo with Gemini")
    print("="*70 + "\n")

    # Load configuration
    config = load_config()

    # Configure Gemini API
    print("[1/7] Configuring Gemini API...")
    api_key = os.getenv('GOOGLE_API_KEY') or config.get('google_api_key')

    if not api_key:
        print("  ⚠️  WARNING: GOOGLE_API_KEY not found in environment!")
        print("  Please set it in .env file or environment variables.")
        print("  Get your key at: https://aistudio.google.com/app/apikey")
        return

    genai.configure(api_key=api_key)
    print("  ✅ Gemini API configured")

    # Initialize tools
    print("\n[2/7] Initializing integration tools...")
    monitoring = MonitoringTool()
    slack = SlackTool(mock_mode=True)
    issue_tracker = IssueTrackingTool(mock_mode=True)
    print("  ✅ Tools initialized (mock mode)")

    # Initialize AI agents
    print("\n[3/7] Initializing AI agents with Gemini...")
    triage_agent = TriageAgent(config)
    report_agent = ReportGeneratorAgent(config)
    orchestrator = OrchestratorAgent(config, triage_agent, report_agent)
    postmortem_agent = PostmortemWriterAgent(config)
    action_tracker = ActionTrackerAgent(config, issue_tracker=issue_tracker)
    knowledge_agent = KnowledgeRetrievalAgent(config)

    orchestrator = OrchestratorAgent(
        config,
        triage_agent=triage_agent,
        report_agent=report_agent,
        postmortem_agent=postmortem_agent,
        action_tracker=action_tracker,
        knowledge_agent=knowledge_agent
    )
    print("  ✅ Orchestrator + 5 sub-agents ready")

    # Generate sample alert
    print("\n[4/7] Simulating monitoring alert...")
    alert = monitoring.generate_sample_alert(severity="SEV2")
    print(f"  📊 Alert Type: {alert.get('type', 'N/A')}")
    print(f"  🔴 Service: {alert['service']}")
    print(f"  ⚠️  Message: {alert['message']}")
    print(f"  📈 Metric: {alert.get('metric')} = {alert.get('current')} (threshold: {alert.get('threshold')})")

    # Process incident through orchestrator
    print("\n[5/7] Processing incident through AI agents...")
    print("  → Orchestrator routing to Triage Agent...")
    result = await orchestrator.process_incident(alert)

    if result.get('status') == 'error':
        print(f"\n  ❌ Error: {result.get('message')}")
        return

    print(f"\n  ✅ Incident Created: {result['incident_id']}")
    print(f"  📋 Title: {result.get('title', 'N/A')}")
    print(f"  🚨 Severity: {result.get('severity', 'N/A')}")

    # Show classification details
    classification = result.get('classification', {})
    print(f"\n  🎯 Triage Agent Classification:")
    print(f"     - Affected Services: {', '.join(classification.get('affected_services', []))}")
    if classification.get('recommended_actions'):
        print(f"     - Recommended Actions:")
        for action in classification.get('recommended_actions', [])[:3]:
            print(f"       • {action}")

    # Send notifications
    print("\n[6/7] Sending notifications...")
    await slack.send_notification(
        message=f"🚨 {result.get('severity')} Incident: {result.get('title')}",
        channel="#incidents",
        severity=result.get('severity')
    )

    # Show generated report (first 500 chars)
    print("\n[7/7] Generated Incident Report:")
    print("  " + "-" * 66)
    report_preview = result.get('report', '')[:500]
    for line in report_preview.split('\n')[:10]:
        print(f"  {line}")
    print("  ...")
    print("  " + "-" * 66)

    print("\n" + "="*70)
    print("  ✅ Demo completed successfully!")
    print("="*70 + "\n")

    print("📊 Results Summary:")
    print(f"  • Incident ID: {result['incident_id']}")
    print(f"  • Severity: {result.get('severity')}")
    print(f"  • AI Agents Used: Triage → Report Generator")
    print(f"  • Time to Process: ~3-5 seconds")
    print(f"  • Report Length: {len(result.get('report', ''))} characters\n")

    print("🎯 Next Steps:")
    print("  1. Generate postmortem with RCA (use demo_full_lifecycle.py)")
    print("  2. Test knowledge retrieval with multiple incidents")
    print("  3. Deploy to production")
    print("  4. Submit to Kaggle by Dec 1, 2025\n")


async def main():
    """Main entry point."""
    # Setup logging
    config = load_config()
    setup_logging(config.get('logging', {}))

    logger.info("incident_response_bot_starting")

    try:
        await demo_incident_response()
    except Exception as e:
        logger.error("demo_failed", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())