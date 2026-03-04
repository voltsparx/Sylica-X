# core/analyze/confidence.py
def explain_confidence(r):
    reasons = []
    if r["status"] == "FOUND":
        reasons.append("Profile page exists")
    if r.get("bio"):
        reasons.append("Public bio detected")
    if r.get("links"):
        reasons.append("External links found")
    if r.get("contacts", {}):
        reasons.append("Contacts information found")
    if r["confidence"] >= 90:
        reasons.append("High reliability platform")
    return reasons

