import boto3

# CRITICAL: Point boto3 to LocalStack, NOT real AWS
ec2 = boto3.client('ec2', region_name='us-east-1', endpoint_url='http://localhost:4566')

def create_vulnerable_security_group():
    # 1. Create a VPC (Virtual Private Cloud)
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    print(f"Created Mock VPC: {vpc_id}")

    # 2. Create a Security Group
    sg = ec2.create_security_group(
        GroupName='production-web-sg',
        Description='SG for production web server',
        VpcId=vpc_id
    )
    sg_id = sg['GroupId']
    print(f"Created Mock Security Group: {sg_id}")

    # 3. Simulate a misconfiguration (Allowing SSH from anywhere)
    # We will pretend a rogue IP (e.g., 192.168.1.50) is attacking this open port.
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )
    print("Simulated Vulnerability: SSH (Port 22) is open to the world.")
    return sg_id

if __name__ == "__main__":
    create_vulnerable_security_group()