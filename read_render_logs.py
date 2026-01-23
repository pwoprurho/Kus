import urllib.request
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("RENDER_API_KEY")

if not API_KEY:
    print("Error: RENDER_API_KEY environment variable is not set.")
    print("Please set it temporarily in the terminal using `$env:RENDER_API_KEY='rnd_...'` (PowerShell) or `export RENDER_API_KEY='rnd_...'` (Bash).")
    sys.exit(1)

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

BASE_URL = "https://api.render.com/v1"

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
            else:
                print(f"Error: Status {response.status}")
                return None
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        print(e.read().decode())
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    # 1. List Services
    print("Fetching services...")
    services = get_json(f"{BASE_URL}/services?limit=20")
    if not services:
        return

    service_list = services if isinstance(services, list) else services.get("items", []) # Handle pagination wrapper if present
    
    if not service_list: # Check if list is empty after extraction
         # The API doc says returns list of service objects, but usually it's wrapped in list or dict with cursor
         # Example in docs showed response [ { "service": ... } ]
         # Let's handle both
         pass
    
    # Render API usually returns a list of objects like [ {"service": {...}}, ... ]
    
    target_service = None
    print(f"Found {len(service_list)} services.")
    
    for item in service_list:
        svc = item.get("service", {})
        name = svc.get("name")
        s_id = svc.get("id")
        updated = svc.get("updatedAt")
        print(f"- {name} ({s_id}) - Last Updated: {updated}")
        
        # Heuristic: Pick the one that seems most relevant or asks user (but we are automated)
        # Let's pick the first one for now or look for "krag"
        if "krag" in name.lower() or "bot" in name.lower():
            target_service = svc
        
    if not target_service and service_list:
        target_service = service_list[0].get("service")

    if not target_service:
        print("No services found.")
        return

    print(f"\nSelected Service: {target_service.get('name')} ({target_service.get('id')})")
    
    # 2. List Deploys
    print(f"Fetching deploys for {target_service.get('name')}...")
    deploys_url = f"{BASE_URL}/services/{target_service.get('id')}/deploys?limit=5"
    deploys = get_json(deploys_url)
    
    if not deploys:
        return
        
    # Deploys response: [ {"deploy": ...}, ... ]
    
    latest_deploy = None
    for item in deploys:
        d = item.get("deploy", {})
        status = d.get("status")
        created = d.get("createdAt")
        print(f"- Deploy {d.get('id')}: {status} at {created}")
        
        if not latest_deploy:
            latest_deploy = d
            
    if latest_deploy:
        print("\n--- Latest Deploy Object Inspection ---")
        print(json.dumps(latest_deploy, indent=2))
        print("---------------------------------------")

        print(f"\nFetching logs for latest deploy: {latest_deploy.get('id')} ({latest_deploy.get('status')})")
        
        # The 'List logs' doc says GET /v1/logs with serviceId param
        print("\nAttempting to fetch logs via global endpoint with filters...")
        
        # Note: serviceId is an array in docs, so we pass it as query param
        # &serviceId[]=srv-xyz or just &serviceId=srv-xyz depending on parser. Standard is repeat key or []
        
        logs_url = f"{BASE_URL}/logs?serviceId={target_service.get('id')}&limit=100"
        print(f"URL: {logs_url}")
        
        logs_resp = get_json(logs_url)
        if logs_resp:
            # It returns a list of log objects, usually with 'text' and 'timestamp'
            # Check structure
            if isinstance(logs_resp, list):
                print(f"Retrieved {len(logs_resp)} log entries.")
                for entry in logs_resp:
                     ts = entry.get("timestamp", "")
                     msg = entry.get("message", "") # or 'text'
                     print(f"[{ts}] {msg}")
            else:
                print("Logs response structure unexpected:")
                print(json.dumps(logs_resp, indent=2))
        else:
             print("Failed to retrieve logs from global endpoint.")


if __name__ == "__main__":
    main()
