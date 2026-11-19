"""Validated actions and narrowly scoped remediation primitives."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

SG_PATTERN = re.compile(r"sg-(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{17})\Z")
SSH_WORLD_IPV4 = {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                  "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}


class RemediationError(Exception):
    """An expected validation or remediation failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_security_group_id(value: Any) -> str:
    if not isinstance(value, str) or not SG_PATTERN.fullmatch(value):
        raise RemediationError("Invalid security-group ID: expected sg- followed by 8 or 17 hexadecimal characters.")
    return value.lower()


def has_world_ssh_rule(permissions: list[dict[str, Any]]) -> bool:
    """Only the exact TCP/22 IPv4 world rule is eligible for this playbook."""
    for perm in permissions:
        protocol = str(perm.get("IpProtocol", "")).lower()
        lo, hi = perm.get("FromPort"), perm.get("ToPort")
        if protocol in ("tcp", "6") and isinstance(lo, int) and isinstance(hi, int) and lo <= 22 <= hi:
            if any(block.get("CidrIp") == "0.0.0.0/0" for block in perm.get("IpRanges", [])):
                return True
    return False


def precise_revoke_permissions(permissions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select matching broad ranges without revoking any unrelated CIDRs/ports.

    A broad port interval (e.g. 20-30) is deliberately NOT auto-remediated:
    changing it would require splitting the existing rule and carries additional risk.
    """
    out: list[dict[str, Any]] = []
    for perm in permissions:
        if (str(perm.get("IpProtocol", "")).lower() in ("tcp", "6")
            and perm.get("FromPort") == 22 and perm.get("ToPort") == 22
            and any(block.get("CidrIp") == "0.0.0.0/0" for block in perm.get("IpRanges", []))):
            out.append(SSH_WORLD_IPV4.copy())
    return out


def revoke_ssh_world_localstack(group_id: str, ec2: Any) -> dict[str, Any]:
    """Execute only a known defensive playbook against the caller's LocalStack EC2 client."""
    group_id = validate_security_group_id(group_id)
    try:
        response = ec2.describe_security_groups(GroupIds=[group_id])
        groups = response.get("SecurityGroups", [])
        if len(groups) != 1 or groups[0].get("GroupId", "").lower() != group_id:
            raise RemediationError("Target security group was not found or did not match the approved resource.")
        before = groups[0].get("IpPermissions", [])
        if not has_world_ssh_rule(before):
            return {"status": "already_secure", "verified": True,
                    "message": "No public TCP/22 IPv4 rule remains; nothing was changed."}
        precise = precise_revoke_permissions(before)
        if not precise:
            raise RemediationError("Broad SSH port-range rule requires manual review; no changes were made.")
        ec2.revoke_security_group_ingress(GroupId=group_id, IpPermissions=precise)
        after_response = ec2.describe_security_groups(GroupIds=[group_id])
        after_groups = after_response.get("SecurityGroups", [])
        if len(after_groups) != 1 or after_groups[0].get("GroupId", "").lower() != group_id:
            raise RemediationError("Could not verify the target resource following remediation.")
        verified = not has_world_ssh_rule(after_groups[0].get("IpPermissions", []))
        if not verified:
            raise RemediationError("The revoke API returned, but verification failed: SSH is still publicly accessible.")
        return {"status": "remediated", "verified": True,
                "message": "Public TCP/22 IPv4 ingress revoked and verified with a fresh EC2 read."}
    except RemediationError:
        raise
    except Exception as exc:
        # Never treat a provider exception as success, including InvalidPermission.NotFound.
        raise RemediationError(f"Cloud operation failed ({type(exc).__name__}); no success was claimed.") from exc
