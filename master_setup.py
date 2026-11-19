import boto3
import json
import time

def setup_synced_scenario():
    print("🛠️  Step 1: Building vulnerable infrastructure in LocalStack...")
    
    # Connect to LocalStack
    ec2 = boto3.client('ec2', region_name='us-east-1', endpoint_url='http://localhost:4566')
    
    # Create VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    
    # Create Security Group with a unique name
    unique_sg_name = f'production-web-sg-{int(time.time())}'
    sg = ec2.create_security_group(
        GroupName=unique_sg_name,
        Description='SG for production web server',
        VpcId=vpc_id
    )
    sg_id = sg['GroupId']
    print(f"✅ Created Mock Security Group: {sg_id}")
    
    # Simulate the vulnerability (Open Port 22)
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )
    print("⚠️  Simulated Vulnerability: SSH (Port 22) is open to the world.\n")

    print("🚨 Step 2: Generating CloudWatch Alert...")
    
    # Generate the JSON Alert automatically using the exact sg_id
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
        
    print("✅ Alert generated and synced successfully: cloud_alert.json")
    print("\n🚀 You are perfectly synced! Go to your Streamlit dashboard and Launch the Agent.")

if __name__ == "__main__":
    setup_synced_scenario()