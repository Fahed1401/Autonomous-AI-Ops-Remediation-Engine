import json
import time

def generate_security_alert(sg_id):
    alert_data = {
        "alert_id": f"ALT-{int(time.time())}",
        "severity": "CRITICAL",
        "description": "Unauthorized SSH brute-force attempt detected.",
        "affected_resource_id": sg_id, 
        "attacker_ip": "192.168.1.50",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    with open('cloud_alert.json', 'w') as f:
        json.dump(alert_data, f, indent=4)
        
    print("🚨 Alert generated: cloud_alert.json")

# Replace 'sg-xx' with the ID printed after running setup_mock_cloud.py
generate_security_alert("sg-929cfa34438451d4e") # Example SG ID, replace with your actual SG ID from the previous step.