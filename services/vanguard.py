# services/vanguard.py
import random

def calculate_log_stability(context_logs: list) -> int:
    """
    Calculates stability (0-40) based on forensic log integrity.
    """
    if not context_logs:
        return 40 
    
    recent_logs = context_logs[-15:]
    threat_keywords = ["CRITICAL", "ATTACK", "SQL Injection", "RCE", "XSS"]
    threat_hits = sum(1 for log in recent_logs if any(k in log for k in threat_keywords))
    
    return max(0, 40 - (threat_hits * 8))

def calculate_vanguard_score(current_score: int = 100, context_logs: list = None, is_mitigated: bool = False) -> int:
    """
    SELF-HEALING LOGIC ADDED:
    1. Active Healing: +5 points if 'is_mitigated' is True.
    2. Passive Healing: +5 points if last 5 logs are clean (stability).
    """
    score = current_score
    
    # --- 1. PENALTY PHASE ---
    if context_logs:
        # Analyze only the very latest activity for immediate impact
        recent_logs = context_logs[-5:]
        penalty = 0
        for log in recent_logs:
            if "CRITICAL" in log: penalty += 15
            elif "WARNING" in log: penalty += 5
        score -= penalty

    # --- 2. ACTIVE HEALING (Mitigation Bonus) ---
    if is_mitigated:
        score += 5

    # --- 3. PASSIVE HEALING (Stability Check) ---
    # If the last 5 logs have NO critical issues, regenerate integrity
    if context_logs and not any("CRITICAL" in log for log in context_logs[-5:]):
        score += 5

    # --- 4. BASELINE STABILITY ---
    stability_impact = calculate_log_stability(context_logs)
    score = (score * 0.7) + (stability_impact * 0.75) # Weighted blend
    return min(100, max(0, int(score)))


def get_threat_level(score: int = 100, context_logs: list = None) -> str:
    """
    Derive a textual threat level from recent logs and the numeric vanguard score.
    Returns one of: 'low', 'medium', 'high', 'critical'
    """
    if context_logs is None:
        context_logs = []

    recent = context_logs[-10:]
    critical_hits = sum(1 for l in recent if 'CRITICAL' in l or 'ATTACK' in l or 'RCE' in l)
    warning_hits = sum(1 for l in recent if 'WARNING' in l or 'XSS' in l or 'SQL Injection' in l)

    # Immediate critical if explicit critical markers present
    if critical_hits > 0:
        return 'critical'

    # Use weighted heuristic combining hits and score
    threat_score = (critical_hits * 3) + (warning_hits * 1)

    if score < 40 or threat_score >= 4:
        return 'high'
    if threat_score >= 1 or score < 70:
        return 'medium'
    return 'low'

def get_latency_metrics(context_logs: list) -> str:
    """
    Generates a dynamic latency score based on system stress.
    High Threat = High Latency.
    """
    if not context_logs:
        return "12ms"
    
    # Check specifically for active attacks in the last 3 logs
    is_under_attack = any("CRITICAL" in log for log in context_logs[-3:])
    
    if is_under_attack:
        # Spike latency between 120ms and 450ms during attacks
        return f"{random.randint(120, 450)}ms"
    else:
        # Stable latency between 8ms and 24ms
        return f"{random.randint(8, 24)}ms"

def get_security_posture(score: int) -> str:
    if score >= 90: return "SECURED: Optimal Integrity"
    if score >= 70: return "STABLE: Monitoring Active"
    if score >= 40: return "DEGRADED: Latency Spikes"
    return "COMPROMISED: Immediate Action"