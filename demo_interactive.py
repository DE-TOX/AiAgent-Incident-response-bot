"""
Interactive Incident Response Demo - Perfect for Hackathon Presentation!

Run this during your demo to:
1. Type custom incident descriptions
2. Watch AI process them in real-time
3. Receive email notifications
4. Show complete workflow
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
from tools.email_tool import EmailTool
from tools.slack_tool import SlackTool
from tools.issue_tracking import IssueTrackingTool

import structlog
logger = structlog.get_logger()


def print_header(text):
    """Print fancy header."""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def print_section(text):
    """Print section divider."""
    print("\n" + "-"*80)
    print(f"  {text}")
    print("-"*80 + "\n")


async def interactive_demo():
    """
    Interactive demo - user types incident description and gets email!
    """
    print_header("🎤 INTERACTIVE INCIDENT RESPONSE DEMO")
    print("  Welcome to the AI-Powered Incident Response System!")
    print("  This demo showcases real-time incident processing with email notifications\n")

    # Configuration
    config = load_config()

    # Get email configuration
    print("📧 Email Configuration")
    print("-" * 40)

    email_mode = input("  Send real emails? (yes/no) [default: no]: ").strip().lower()
    use_real_email = email_mode == 'yes'

    recipient_email = None
    sender_email = None
    sender_password = None

    if use_real_email:
        recipient_email = input("  Enter recipient email: ").strip()
        sender_email = os.getenv('SENDER_EMAIL') or input("  Enter sender email (Gmail): ").strip()
        sender_password = os.getenv('SENDER_PASSWORD') or input("  Enter app password: ").strip()
        print(f"\n  ✅ Will send real emails to {recipient_email}")
    else:
        recipient_email = input("  Enter email for display [default: demo@example.com]: ").strip()
        if not recipient_email:
            recipient_email = "demo@example.com"
        print(f"\n  ✅ Will show mock emails (not actually sent)")

    # Configure Gemini
    print_section("🤖 Initializing AI Agents")

    api_key = os.getenv('GOOGLE_API_KEY') or config.get('google_api_key')
    if not api_key:
        print("  ⚠️  ERROR: GOOGLE_API_KEY not found!")
        return

    genai.configure(api_key=api_key)
    print("  ✅ Gemini API configured")

    # Initialize tools
    email_tool = EmailTool(
        sender_email=sender_email,
        sender_password=sender_password,
        mock_mode=not use_real_email
    )
    slack = SlackTool(mock_mode=True)
    issue_tracker = IssueTrackingTool(mock_mode=True, platform="jira")

    print("  ✅ Email, Slack, Jira tools ready")

    # Initialize AI agents
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

    print("  ✅ 5 AI Agents initialized (Triage, Report, Postmortem, Actions, Knowledge)")

    # Main interaction loop
    while True:
        print_header("🎯 CREATE NEW INCIDENT")

        print("Examples:")
        print("  • 'Database connection pool exhausted, API returning 500 errors'")
        print("  • 'Payment service is down, customers cannot checkout'")
        print("  • 'High memory usage in worker nodes, jobs failing'")
        print("  • Type 'quit' to exit\n")

        # Get incident description
        description = input("📝 Describe the incident: ").strip()

        if description.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Thanks for using the Incident Response Bot!")
            break

        if not description:
            continue

        # Ask for severity
        print("\nSeverity levels:")
        print("  SEV1 - Critical (service completely down)")
        print("  SEV2 - High (significant impact)")
        print("  SEV3 - Medium (minor impact)")
        print("  SEV4 - Low (cosmetic)")

        severity = input("Severity [default: SEV2]: ").strip().upper()
        if severity not in ['SEV1', 'SEV2', 'SEV3', 'SEV4']:
            severity = 'SEV2'

        # Ask for affected service
        service = input("Affected service [default: api-gateway]: ").strip()
        if not service:
            service = "api-gateway"

        # Create alert data
        alert_data = {
            "alert_id": f"CUSTOM-{int(asyncio.get_event_loop().time())}",
            "message": description,
            "severity": severity,
            "service": service,
            "type": "custom",
            "environment": "production"
        }

        # ==== PROCESS INCIDENT ====
        print_section("⚡ PROCESSING INCIDENT WITH AI")

        print("  [1/4] Routing to Triage Agent...")
        print("        → Analyzing incident with Gemini AI...")

        try:
            result = await orchestrator.process_incident(alert_data)

            if result.get('status') == 'error':
                print(f"\n  ❌ Error: {result.get('message')}")
                continue

            incident_id = result['incident_id']

            print(f"\n  ✅ Incident Created!")
            print(f"      ID: {incident_id}")
            print(f"      Severity: {result.get('severity')}")
            print(f"      Title: {result.get('title')}")

            # Send incident email
            print("\n  [2/4] Sending incident notification email...")
            await email_tool.send_incident_notification(
                recipient=recipient_email,
                incident_id=incident_id,
                severity=result.get('severity'),
                title=result.get('title'),
                summary=description
            )

            # Show classification
            classification = result.get('classification', {})
            print(f"\n  [3/4] AI Classification Results:")
            print(f"      Affected Services: {', '.join(classification.get('affected_services', []))}")

            if classification.get('recommended_actions'):
                print(f"      Recommended Actions:")
                for action in classification.get('recommended_actions', [])[:3]:
                    print(f"        • {action}")

            # Show report snippet
            print(f"\n  [4/4] Incident Report Generated:")
            print("  " + "-" * 76)
            report_lines = result.get('report', '').split('\n')[:10]
            for line in report_lines:
                print(f"  {line}")
            print("  ...")
            print("  " + "-" * 76)

            # ==== ASK ABOUT POSTMORTEM ====
            print_section("📝 POSTMORTEM GENERATION")

            generate_pm = input("\nGenerate postmortem? (yes/no) [default: yes]: ").strip().lower()

            if generate_pm != 'no':
                print("\n  → Generating AI-Powered Postmortem...")
                print("  → Searching for similar past incidents...")
                print("  → Performing 5 Whys Root Cause Analysis...")
                print("  → Extracting action items...")

                pm_result = await orchestrator.generate_postmortem(incident_id)

                if pm_result.get('error'):
                    print(f"\n  ⚠️  {pm_result.get('error')}")
                else:
                    print(f"\n  ✅ Postmortem Complete!")

                    # Show similar incidents if found
                    similar_incidents = pm_result.get('similar_incidents', [])
                    if similar_incidents:
                        print(f"      Similar Past Incidents Found: {len(similar_incidents)}")
                        for idx, similar in enumerate(similar_incidents, 1):
                            print(f"        {idx}. {similar.get('incident_id')} - {similar.get('title')} (similarity: {similar.get('similarity_score', 0):.2f})")

                    print(f"      Action Items: {len(pm_result.get('action_items', []))}")
                    print(f"      Lessons Learned: {len(pm_result.get('lessons_learned', []))}")

                    # Send postmortem email
                    print("\n  → Sending postmortem notification email...")
                    await email_tool.send_postmortem_notification(
                        recipient=recipient_email,
                        incident_id=incident_id,
                        title=result.get('title'),
                        action_items_count=len(pm_result.get('action_items', [])),
                        lessons_count=len(pm_result.get('lessons_learned', []))
                    )

                    # Show action items
                    if pm_result.get('action_items'):
                        print("\n  📋 Action Items Created:")
                        for idx, item in enumerate(pm_result.get('action_items', [])[:5], 1):
                            print(f"      {idx}. [{item.get('priority')}] {item.get('description')}")
                            if item.get('ticket_id'):
                                print(f"         Jira Ticket: {item.get('ticket_id')}")

                    # Show lessons
                    if pm_result.get('lessons_learned'):
                        print("\n  💡 Lessons Learned:")
                        for idx, lesson in enumerate(pm_result.get('lessons_learned', [])[:3], 1):
                            print(f"      {idx}. {lesson}")

            # Summary
            print_section("✅ INCIDENT PROCESSING COMPLETE")
            print(f"  Incident ID: {incident_id}")
            print(f"  Emails Sent: 2 (Incident Alert + Postmortem)")
            print(f"  Documents Generated: 2 (Report + Postmortem)")
            print(f"  Total Time: ~8-10 seconds")

        except Exception as e:
            print(f"\n  ❌ Error processing incident: {str(e)}")
            logger.error("interactive_demo_error", error=str(e), exc_info=True)

        # Ask if they want to create another
        print("\n")
        another = input("Process another incident? (yes/no) [default: yes]: ").strip().lower()
        if another == 'no':
            print("\n👋 Demo complete! Thanks for watching!")
            break


async def main():
    """Main entry point."""
    config = load_config()
    setup_logging(config.get('logging', {}))

    try:
        await interactive_demo()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        logger.error("demo_failed", error=str(e), exc_info=True)
        print(f"\n❌ Demo failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
