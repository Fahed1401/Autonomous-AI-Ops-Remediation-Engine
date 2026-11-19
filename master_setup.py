"""Provision a single intentionally vulnerable demo security group in LOCALSTACK.

WARNING: This script intentionally opens SSH globally, ONLY in LocalStack.
Never use this fixture against a real AWS endpoint.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from aiops.core import SSH_WORLD_IPV4, utc_now
from aiops.integrations import ROOT, localstack_client


def setup_synced_scenario(ec2=None, output=None):
    ec2 = ec2 or localstack_client()  # Adapter pins endpoint to localhost:4566.
    output = Path(output or ROOT / "cloud_alert.json")
    vpc_id = ec2.create_vpc(CidrBlock="10.41.0.0/16")["Vpc"]["VpcId"]
    group_id = ec2.create_security_group(GroupName=f"sentinelops-demo-{time.time_ns()}",
                                          Description="Deliberately vulnerable LOCALSTACK demo resource",
                                          VpcId=vpc_id)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[SSH_WORLD_IPV4])
    record = {"alert_id": f"ALT-{int(time.time())}", "severity": "CRITICAL",
              "description": "Unsafe public SSH ingress: TCP port 22 allowed from 0.0.0.0/0.",
              "affected_resource_id": group_id, "attacker_ip": "198.51.100.24", "timestamp": utc_now()}
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Created LocalStack VPC {vpc_id}, vulnerable SG {group_id}. Alert saved: {output}")
    return record


if __name__ == "__main__":
    setup_synced_scenario()
