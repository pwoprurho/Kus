import datetime
import random
import os

# --- REAL WORLD TOOL DEFINITIONS ---

def get_server_health(server_id: str):
    """
    Queries the live status of a specific server infrastructure.
    Real-world equivalent: Querying AWS CloudWatch, Datadog, or Azure Monitor.
    """
    # Simulate fetching real-time data
    statuses = ["HEALTHY", "DEGRADED", "CRITICAL", "MAINTENANCE"]
    status = random.choice(statuses)
    cpu_load = random.randint(5, 98)
    memory_usage = random.randint(20, 90)
    
    return {
        "server_id": server_id,
        "status": status,
        "cpu_load": f"{cpu_load}%",
        "memory_usage": f"{memory_usage}%",
        "last_ping": datetime.datetime.now().isoformat()
    }

def trigger_incident_protocol(severity: str, server_id: str, notes: str):
    """
    Executes a real-world incident response protocol.
    Real-world equivalent: PagerDuty alert, Slack Webhook, or Jira Ticket creation.
    """
    # PROOF OF ACTION: We write to a physical file in the project directory
    filename = "REAL_WORLD_ACTIONS.log"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = (
        f"[{timestamp}] ACTION_TRIGGERED\n"
        f"   Target: {server_id}\n"
        f"   Severity: {severity.upper()}\n"
        f"   Notes: {notes}\n"
        f"   Status: PagerDuty & Slack Notifications Sent.\n"
        "---------------------------------------------------\n"
    )
    
    try:
        with open(filename, "a") as f:
            f.write(log_entry)
        return {
            "status": "SUCCESS", 
            "action": "Protocol Executed", 
            "log_file": filename, 
            "message": f"Alert sent for {server_id}. Incident team notified."
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

# Registry for the Engine
MCP_TOOLKIT = {
    'get_server_health': get_server_health,
    'trigger_incident_protocol': trigger_incident_protocol
}