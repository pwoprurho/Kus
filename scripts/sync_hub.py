# scripts/sync_hub.py
import os
import subprocess
import sys

def sync_hub(hub_path):
    print(f"--- Synchronizing Kusmus Hub: {hub_path} ---")
    
    if not os.path.exists(hub_path):
        print(f"Error: Hub path {hub_path} does not exist.")
        return False
        
    try:
        # 1. Git Pull
        print("Pulling updates from upstream registry...")
        result = subprocess.run(["git", "-C", hub_path, "pull", "origin", "main"], capture_output=True, text=True)
        print(result.stdout)
        
        # 2. Run Audit
        print("Starting post-sync security audit...")
        audit_script = os.path.join(os.path.dirname(__file__), "audit_skills.py")
        audit_result = subprocess.run([sys.executable, audit_script, hub_path], capture_output=True, text=True)
        print(audit_result.stdout)
        
        if audit_result.returncode != 0:
            print("[!] SECURITY ALERT: New vulnerabilities detected in updated skills.")
            return False
            
        print("--- Hub Synchronization Successful ---")
        return True
        
    except Exception as e:
        print(f"Synchronization Error: {e}")
        return False

if __name__ == "__main__":
    hub_path = "C:\\Users\\Administrator\\kus\\kushub"
    success = sync_hub(hub_path)
    sys.exit(0 if success else 1)
