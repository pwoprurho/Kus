import datetime
import random
import time
import os

# --- INFRASTRUCTURE TOOLS ---
def get_server_health(server_id: str):
    """Queries live status of specific server infrastructure."""
    statuses = ["HEALTHY", "DEGRADED", "CRITICAL", "MAINTENANCE"]
    return {
        "server_id": server_id,
        "status": random.choice(statuses),
        "cpu_load": f"{random.randint(5, 98)}%",
        "last_ping": datetime.datetime.now().isoformat()
    }

# --- SENTINEL TOOLS ---
def get_oran_metrics(node_id: str):
    """Fetches real-time O-RAN telemetry."""
    latency = random.randint(10, 150)
    return {
        "node_id": node_id,
        "status": "OPTIMAL" if latency < 100 else "DEGRADED",
        "telemetry": {"latency_ms": latency}
    }

def run_napalm_audit(node_id: str):
    """
    PROACTIVE TOOL: Called automatically by Sentinel during critical events.
    """
    time.sleep(1) # Simulation delay
    return {
        "tool": "NAPALM_DRIVER_V2",
        "target": node_id,
        "status": "COMPROMISED",
        "diagnostics": {
            "interface_opt0": "DOWN (Signal Loss)",
            "action": "Traffic Rerouted to Backup Gateway",
            "result": "Connectivity Restored (Latency: 142ms)"
        }
    }

def trigger_incident_protocol(severity: str, target_id: str, notes: str):
    """Logs a critical action and simulates an alert."""
    return {
        "status": "SUCCESS", 
        "ticket_id": f"INC-{random.randint(10000, 99999)}", 
        "action": f"SIEM Rule Created. Target {target_id} blocked at firewall."
    }

def scan_siem_logs(query_filter: str):
    return {"status": "Complete", "matches": "See live logs for details."}

# --- TOOL REGISTRY ---
MCP_TOOLKIT = {
    'get_server_health': get_server_health,
    'get_oran_metrics': get_oran_metrics,
    'run_napalm_audit': run_napalm_audit,
    'scan_siem_logs': scan_siem_logs,
    'trigger_incident_protocol': trigger_incident_protocol
}