"""Deterministic pass/fail. No model anywhere near this."""
import sys
import json
import os
from datetime import datetime
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_data():
    with open(os.path.join(DATA_DIR, 'complaints.json'), 'r') as f:
        complaints = json.load(f)
    with open(os.path.join(DATA_DIR, 'closures.json'), 'r') as f:
        closures = json.load(f)
    return complaints, closures

def is_invalid_closure(complaint, closure, all_complaints, all_closures):
    if not closure.get("evidence"):
        return True
    
    assigned_at_str = complaint.get("assigned_at")
    if assigned_at_str:
        assigned_at = datetime.strptime(assigned_at_str, "%Y-%m-%dT%H:%M:%SZ")
        closed_at = datetime.strptime(closure["closed_at"], "%Y-%m-%dT%H:%M:%SZ")
        if (closed_at - assigned_at).total_seconds() < 5 * 60:
            return True
            
    c_lat = complaint["location"]["lat"]
    c_lon = complaint["location"]["lon"]
    has_valid_photo = False
    for ev in closure.get("evidence", []):
        if ev.get("type") == "photo_after":
            e_lat = ev.get("lat")
            e_lon = ev.get("lon")
            if e_lat is not None and e_lon is not None:
                dist = math.sqrt((c_lat - e_lat)**2 + (c_lon - e_lon)**2)
                if dist > 0.005: 
                    return True
                else:
                    has_valid_photo = True
    
    if not has_valid_photo and any(e.get("type") == "photo_after" for e in closure.get("evidence", [])):
        return True
        
    asset_id = complaint.get("asset_id")
    if asset_id:
        closed_complaint_ids = {c["complaint_id"] for c in all_closures}
        for other in all_complaints:
            if other["id"] != complaint["id"] and other.get("asset_id") == asset_id:
                if other["id"] not in closed_complaint_ids:
                    other_reported = datetime.strptime(other["reported_at"], "%Y-%m-%dT%H:%M:%SZ")
                    closure_time = datetime.strptime(closure["closed_at"], "%Y-%m-%dT%H:%M:%SZ")
                    if other_reported < closure_time:
                        return True
                        
    return False

def check():
    complaints, closures = load_data()
    closure_map = {c["complaint_id"]: c for c in closures}
    
    asset_history = {}
    for c in complaints:
        aid = c.get("asset_id")
        if aid:
            dt = datetime.strptime(c["reported_at"], "%Y-%m-%dT%H:%M:%SZ")
            asset_history.setdefault(aid, []).append((c["id"], dt))
            
    reopened = []
    closed_count = 0
    for comp in complaints:
        closure = closure_map.get(comp["id"])
        if closure:
            invalid = is_invalid_closure(comp, closure, complaints, closures)
            
            is_reopened = False
            if invalid:
                aid = comp.get("asset_id")
                comp_dt = datetime.strptime(comp["reported_at"], "%Y-%m-%dT%H:%M:%SZ")
                for other_id, other_dt in asset_history.get(aid, []):
                    if other_dt > comp_dt:
                        is_reopened = True
                        break
                        
            if is_reopened:
                reopened.append(comp["id"])
            else:
                closed_count += 1
                
    return reopened, closed_count

try:
    bad, count = check()
    assert not bad, f"{len(bad)} closed complaints came back: {bad[:3]}"
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
print(f"PASS: {count} closures, none reopened")
