"""Simulated MCP tools used by the sandbox and agent demos.

This module intentionally contains lightweight, deterministic-ish
simulators for demo and testing. Keep implementations idempotent and
free of side-effects beyond returning structured dicts.
"""
import datetime
import random
import time
from typing import Any, Dict
from typing import Union
try:
    # import calendar helper if present
    from services.calendar_tool import create_calendar_event
    CALENDAR_AVAILABLE = True
except Exception:
    CALENDAR_AVAILABLE = False


def get_server_health(server_id: str) -> Dict[str, Any]:
    """Return a mock health snapshot for a server."""
    statuses = ["HEALTHY", "DEGRADED", "CRITICAL", "MAINTENANCE"]
    return {
        "server_id": server_id,
        "status": random.choice(statuses),
        "cpu_load": f"{random.randint(5, 98)}%",
        "last_ping": datetime.datetime.utcnow().isoformat()
    }


def get_oran_metrics(node_id: str) -> Dict[str, Any]:
    """Return mock O-RAN telemetry for a node."""
    latency = random.randint(10, 150)
    return {
        "node_id": node_id,
        "status": "OPTIMAL" if latency < 100 else "DEGRADED",
        "telemetry": {"latency_ms": latency}
    }


def run_napalm_audit(node_id: str) -> Dict[str, Any]:
    """Simulated network audit run for remediation scenarios."""
    time.sleep(0.2)
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


def trigger_incident_protocol(severity: str, target_id: str, notes: str) -> Dict[str, Any]:
    """Simulate creating an incident ticket and applying a blocking rule."""
    return {
        "status": "SUCCESS",
        "ticket_id": f"INC-{random.randint(10000, 99999)}",
        "action": f"SIEM Rule Created. Target {target_id} blocked at firewall.",
        "severity": severity,
        "notes": notes,
    }


def scan_siem_logs(query_filter: str) -> Dict[str, Any]:
    """Return a shallow response indicating a search was executed."""
    return {"status": "Complete", "matches": f"Simulated results for: {query_filter}"}


def get_attacker_metadata(ip_address: str) -> Dict[str, Any]:
    """Return enriched metadata for a suspicious IP (mock)."""
    # Deep-trace forensic enrichment
    mock_data = {
        "192.168.45.2": {
            "origin": "Eastern Europe",
            "type": "Known Botnet Node",
            "threat_level": "High",
            "first_seen": "2025-12-01T14:22:00Z",
            "last_activity": "2026-01-03T23:59:00Z",
            "attack_methods": ["Brute Force", "SQL Injection"],
            "related_cases": ["INC-10023", "INC-10456"]
        },
        "10.0.0.15": {
            "origin": "Internal VPN",
            "type": "Unauthorized Lateral Movement",
            "threat_level": "Critical",
            "first_seen": "2025-12-28T09:00:00Z",
            "last_activity": "2026-01-04T01:00:00Z",
            "attack_methods": ["Credential Stuffing"],
            "related_cases": ["INC-10999"]
        }
    }
    result = mock_data.get(ip_address, {
        "origin": "Unknown Proxy",
        "type": "Suspicious Probe",
        "threat_level": "Medium",
        "first_seen": None,
        "last_activity": None,
        "attack_methods": [],
        "related_cases": []
    })
    # Tamper-proof log stub (to be encrypted in security.py)
    try:
        from core.security import tamper_proof_log
        tamper_proof_log({"event": "attacker_metadata_lookup", "ip": ip_address, "result": result})
    except Exception:
        pass
    return {
        "ip": ip_address,
        "metadata": result,
        "action_recommendation": "Initiate Quarantine" if result["threat_level"] in ["Critical", "High"] else "Monitor"
    }


def quarantine_compute_node(node_id: str) -> Dict[str, Any]:
    """Simulate isolating a compute node from the network fabric."""
    time.sleep(0.3)
    # Tamper-proof log stub (to be encrypted in security.py)
    try:
        from core.security import tamper_proof_log
        tamper_proof_log({"event": "quarantine_node", "node_id": node_id, "ts": datetime.datetime.utcnow().isoformat()})
    except Exception:
        pass
    return {
        "status": "SUCCESS",
        "action": f"Node {node_id} isolated from O-RAN Fabric.",
        "firewall_rule": "DENY ALL INBOUND/OUTBOUND",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


def get_robot_vision_feed(camera_id: str) -> Dict[str, Any]:
    """Return a simulated visual-analysis result for a camera feed."""
    time.sleep(0.25)
    scenarios = [
        {
            "status": "SECURE",
            "objects": ["Server Rack", "Cooling Unit"],
            "anomaly_score": 0.05,
            "frame_hash": "a1b2c3d4"
        },
        {
            "status": "CRITICAL",
            "objects": ["Open Chassis", "Unverified USB Device", "Human Hand"],
            "anomaly_score": 0.98,
            "frame_hash": "e5f6g7h8"
        }
    ]
    result = random.choice(scenarios)
    # Tamper-proof log stub (to be encrypted in security.py)
    try:
        from core.security import tamper_proof_log
        tamper_proof_log({"event": "robot_vision_feed", "camera_id": camera_id, "result": result})
    except Exception:
        pass
    return {
        "camera_id": camera_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "visual_analysis": result,
        "action_required": "Physical Intervention" if result["anomaly_score"] > 0.8 else "None"
    }


def execute_arc_payment(amount_usdc: float, recipient: str) -> Dict[str, Any]:
    """
    Simulate a USDC payment on Arc L1 using Circle's x402 standard.
    Returns a transaction dict with status, x402 header, tx hash, and timestamp.
    """
    import hashlib
    import datetime
    # Simulate transaction hash
    tx_input = f"{amount_usdc}:{recipient}:{random.random()}:{datetime.datetime.utcnow().isoformat()}"
    tx_hash = hashlib.sha256(tx_input.encode()).hexdigest()
    # Simulate status
    status = random.choice(["PENDING", "CONFIRMED", "FAILED"])
    x402_header = f"Circle-USDC amount={amount_usdc}; address={recipient}; x402=arc-l1"
    return {
        "status": status,
        "x402_header": x402_header,
        "tx_hash": tx_hash,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": (
            "Transaction confirmed and audit report released."
            if status == "CONFIRMED" else
            "Transaction pending. Awaiting confirmation."
            if status == "PENDING" else
            "Transaction failed. Please retry."
        )
    }


def perform_self_heal(target_system: str) -> Dict[str, Any]:
    """Execute a short, deterministic self-heal simulation and return actions."""
    actions = []
    # Step 1: Restart critical services
    actions.append({
        "action": "restart_services",
        "detail": f"Restarted {target_system}-core services",
        "status": "SUCCESS"
    })
    time.sleep(0.15)

    # Step 2: Reconcile firewall and routing rules
    actions.append({
        "action": "reconcile_firewall",
        "detail": "Applied hardened firewall rules; removed suspicious entries",
        "status": "SUCCESS"
    })
    time.sleep(0.12)

    # Step 3: Post-heal verification
    verification = random.choice(["PASS", "PASS", "WARN"])
    actions.append({
        "action": "post_heal_verification",
        "detail": f"Verification result: {verification}",
        "status": "PASS" if verification == "PASS" else "WARN"
    })

    return {
        "status": "COMPLETED" if verification == "PASS" else "COMPLETED_WITH_WARNINGS",
        "actions": actions,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


# Public registry of tools available for controlled invocation in the sandbox
MCP_TOOLKIT = {
    "get_server_health": get_server_health,
    "get_oran_metrics": get_oran_metrics,
    "run_napalm_audit": run_napalm_audit,
    "scan_siem_logs": scan_siem_logs,
    "trigger_incident_protocol": trigger_incident_protocol,
    "get_attacker_metadata": get_attacker_metadata,
    "quarantine_compute_node": quarantine_compute_node,
    "get_robot_vision_feed": get_robot_vision_feed,
    "execute_arc_payment": execute_arc_payment,
    "perform_self_heal": perform_self_heal,
    "create_calendar_event": (create_calendar_event if CALENDAR_AVAILABLE else None),
}
