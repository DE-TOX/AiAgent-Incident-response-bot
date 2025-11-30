"""
Complete Incident Lifecycle Demo - Day 3

Demonstrates the full incident response workflow:
1. Alert → Triage → Report
2. Resolution → Postmortem → Action Items → Tickets
"""

import asyncio
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

import structlog
logger = structlog.get_logger()


async def demo_full_incident_lifecycle():
    """
    Demonstrate complete incident lifecycle from alert to postmortem.
    """
    print("\n" + "="*80)
    print("  🤖 COMPLETE INCIDENT LIFECYCLE DEMO - Day 3")
    print("  Alert → Triage → Report → Resolution → Postmortem → Action Items")
    print("="*80 + "\n")

    # Load configuration
    config = load_config()

    # Configure Gemini API
    print("[1/10] Configuring Gemini API...")
    api_key = os.getenv('GOOGLE_API_KEY') or config.get('google_api_key')
    if not api_key:
        print("  ⚠️  ERROR: GOOGLE_API_KEY not found!")
        return
    genai.configure(api_key=api_key)
    print("  ✅ Gemini API configured\n")

    # Initialize tools
    print("[2/10] Initializing integration tools...")
    monitoring = MonitoringTool()
    slack = SlackTool(mock_mode=True)
    issue_tracker = IssueTrackingTool(mock_mode=True, platform="jira")
    print("  ✅ Slack, Jira, Monitoring tools ready\n")

    # Initialize ALL AI agents
    print("[3/10] Initializing AI agents...")
    triage_agent = TriageAgent(config)
    report_agent = ReportGeneratorAgent(config)
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
    print("  ✅ Orchestrator + 5 AI agents initialized\n")

    # ==== PHASE 1: INCIDENT DETECTION & TRIAGE ====
    print("=" * 80)
    print("  PHASE 1: INCIDENT DETECTION & TRIAGE")
    print("=" * 80 + "\n")

    print("[4/10] Simulating production alert...")
    alert = monitoring.generate_sample_alert(severity="SEV2")
    print(f"  🚨 Alert: {alert['message']}")
    print(f"  📊 Service: {alert['service']}")
    print(f"  📈 Metric: {alert.get('metric')} = {alert.get('current')} (threshold: {alert.get('threshold')})\n")

    print("[5/10] Processing incident through orchestrator...")
    print("  → Routing to Triage Agent...")
    print("  → Generating Initial Report...")
    incident_result = await orchestrator.process_incident(alert)

    if incident_result.get('status') == 'error':
        print(f"\n  ❌ Error: {incident_result.get('message')}")
        return

    incident_id = incident_result['incident_id']
    print(f"\n  ✅ Incident Created: {incident_id}")
    print(f"  🚨 Severity: {incident_result.get('severity')}")
    print(f"  📋 Title: {incident_result.get('title')}\n")

    # Send alert notification
    await slack.send_notification(
        message=f"🚨 {incident_result.get('severity')} Incident: {incident_result.get('title')}",
        channel="#incidents",
        severity=incident_result.get('severity')
    )

    # Show snippet of initial report
    print("  📄 Initial Incident Report (preview):")
    print("  " + "-" * 76)
    report_lines = incident_result.get('report', '').split('\n')[:8]
    for line in report_lines:
        print(f"  {line}")
    print("  ...")
    print("  " + "-" * 76 + "\n")

    # ==== SIMULATE INCIDENT RESOLUTION ====
    print("=" * 80)
    print("  SIMULATING INCIDENT RESOLUTION...")
    print("=" * 80)
    print("  (In production, engineers would investigate and fix the issue)")
    print("  → Investigation: 15 minutes")
    print("  → Root cause identified: Database connection pool exhaustion")
    print("  → Mitigation applied: Scaled connection pool")
    print("  → Incident resolved!\n")

    # ==== PHASE 2: POSTMORTEM GENERATION ====
    print("=" * 80)
    print("  PHASE 2: POSTMORTEM GENERATION & RCA")
    print("=" * 80 + "\n")

    print(f"[6/10] Generating AI-powered postmortem for {incident_id}...")
    print("  → Using Postmortem Writer Agent...")
    print("  → Searching knowledge base for similar incidents...")
    print("  → Performing 5 Whys Root Cause Analysis...")
    print("  → Extracting lessons learned...")

    postmortem_result = await orchestrator.generate_postmortem(incident_id)

    if postmortem_result.get('error'):
        print(f"\n  ⚠️  Postmortem Error: {postmortem_result.get('error')}")
    else:
        print(f"\n  ✅ Postmortem Generated!")

        # Show similar incidents if found
        similar_incidents = postmortem_result.get('similar_incidents', [])
        if similar_incidents:
            print(f"  🔍 Similar Past Incidents Found: {len(similar_incidents)}")
            for idx, similar in enumerate(similar_incidents, 1):
                print(f"      {idx}. {similar.get('incident_id')} - {similar.get('title')[:60]}...")
                print(f"         Similarity: {similar.get('similarity_score', 0):.2f}")
        else:
            print(f"  🔍 No similar past incidents found (knowledge base empty)")

        print(f"  📊 Action Items Identified: {len(postmortem_result.get('action_items', []))}")
        print(f"  💡 Lessons Learned: {len(postmortem_result.get('lessons_learned', []))}")
        print(f"  💾 Incident indexed for future reference\n")

        # Show postmortem preview
        print("  📄 Postmortem Document (preview):")
        print("  " + "-" * 76)
        pm_lines = postmortem_result.get('postmortem', '').split('\n')[:15]
        for line in pm_lines:
            print(f"  {line}")
        print("  ...")
        print("  " + "-" * 76 + "\n")

    # ==== PHASE 3: ACTION ITEM TRACKING ====
    print("=" * 80)
    print("  PHASE 3: ACTION ITEM TRACKING & TICKET CREATION")
    print("=" * 80 + "\n")

    action_items = postmortem_result.get('action_items', [])

    if action_items:
        print(f"[7/10] Creating Jira tickets for {len(action_items)} action items...\n")

        for idx, item in enumerate(action_items[:5], 1):  # Show first 5
            print(f"  {idx}. [{item.get('priority')}] {item.get('description')}")
            if item.get('ticket_id'):
                print(f"     → Ticket: {item.get('ticket_id')}")
                print(f"     → Category: {item.get('category')}")
                print(f"     → Effort: {item.get('estimated_effort')}")

        if len(action_items) > 5:
            print(f"  ... and {len(action_items) - 5} more action items\n")
    else:
        print("[7/10] No action items extracted\n")

    # ==== PHASE 4: LESSONS LEARNED ====
    print("=" * 80)
    print("  PHASE 4: LESSONS LEARNED")
    print("=" * 80 + "\n")

    lessons = postmortem_result.get('lessons_learned', [])
    if lessons:
        print("[8/10] Key Lessons Learned:\n")
        for idx, lesson in enumerate(lessons[:3], 1):
            print(f"  {idx}. {lesson}")
        print()

    # ==== FINAL NOTIFICATIONS ====
    print("[9/10] Sending completion notifications...")
    await slack.send_notification(
        message=f"✅ Postmortem completed for {incident_id}\n"
                f"📊 {len(action_items)} action items created\n"
                f"💡 {len(lessons)} lessons learned",
        channel="#incidents",
        severity="INFO"
    )
    print("  ✅ Team notified\n")

    # ==== SUMMARY ====
    print("[10/10] Incident lifecycle complete!")
    print("\n" + "=" * 80)
    print("  📊 INCIDENT LIFECYCLE SUMMARY")
    print("=" * 80)
    print(f"  Incident ID: {incident_id}")
    print(f"  Severity: {incident_result.get('severity')}")
    print(f"  Status: {postmortem_result.get('status', 'completed')}")
    print(f"  Duration: Simulated (15 min detection + resolution)")
    print(f"  AI Agents Used: 5 (Triage, Report, Postmortem, Action Tracker, Knowledge)")
    print(f"  Documents Generated: 2 (Incident Report + Postmortem)")
    print(f"  Action Items: {len(action_items)}")
    print(f"  Tickets Created: {len(postmortem_result.get('tickets', []))}")
    print(f"  Lessons Learned: {len(lessons)}")
    print(f"  Similar Incidents Retrieved: {len(postmortem_result.get('similar_incidents', []))}")
    print(f"  Knowledge Base Updated: Yes (incident indexed)")
    print("=" * 80 + "\n")

    print("🎯 What Just Happened:")
    print("  1. ✅ Monitoring alert detected and processed")
    print("  2. ✅ AI classified incident severity and impact")
    print("  3. ✅ Comprehensive incident report generated")
    print("  4. ✅ Knowledge base searched for similar incidents")
    print("  5. ✅ Postmortem with RCA created automatically")
    print("  6. ✅ Action items extracted and tracked")
    print("  7. ✅ Jira tickets created for follow-up")
    print("  8. ✅ Lessons learned documented")
    print("  9. ✅ Incident indexed in knowledge base for future learning\n")

    print("💡 Time Saved:")
    print("  Manual Process: ~2-3 hours (triage + report + postmortem + tickets)")
    print("  With AI Agents: ~5-10 seconds")
    print("  Time Saved: ~99% reduction in documentation time!\n")

    print("🧠 Knowledge Base:")
    print(f"  Total incidents indexed: {knowledge_agent.get_incident_count()}")
    print(f"  Learning from past incidents: {'Yes' if postmortem_result.get('similar_incidents') else 'Building history...'}\n")

    print("🚀 Next Steps:")
    print("  1. Run multiple incidents to build knowledge base")
    print("  2. Test similarity search with more diverse incidents")
    print("  3. Deploy to production")
    print("  4. Create demo video for Kaggle submission\n")


async def main():
    """Main entry point."""
    config = load_config()
    setup_logging(config.get('logging', {}))

    logger.info("incident_response_bot_full_demo_starting")

    try:
        await demo_full_incident_lifecycle()
    except Exception as e:
        logger.error("demo_failed", error=str(e), exc_info=True)
        print(f"\n❌ Demo failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())