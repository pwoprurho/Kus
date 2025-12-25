# services/vanguard.py
def calculate_vanguard_score(user_message: str, has_file: bool, current_score: int = 0) -> int:
    score = current_score
    if has_file: score += 25
    
    tech_keywords = ["latency", "throughput", "siem", "o-ran", "cve", "brute force"]
    if any(word in user_message.lower() for word in tech_keywords):
        score += 15
        
    return min(score, 100)

def get_lead_tier(score: int) -> str:
    if score >= 80: return "WHALE (Tier-1)"
    if score >= 50: return "QUALIFIED (Tier-2)"
    return "CASUAL"