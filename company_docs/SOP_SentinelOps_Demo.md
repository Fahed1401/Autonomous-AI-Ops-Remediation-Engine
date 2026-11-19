# SOP-SEC-001 · Public SSH Exposure Remediation

**Owner:** Cloud Security Operations  
**Scope:** Simulated EC2 security groups in LocalStack only  
**Review status:** Portfolio demonstration runbook (not an organizational policy)

## Trigger

A cloud configuration scan identifies TCP port 22 ingress from IPv4 CIDR `0.0.0.0/0` on an EC2 security group. Attack traffic alone is not proof that this exact rule exists; verify the security-group configuration before taking action.

## Approved response

1. Confirm the incident refers to a single exact security-group ID with 8 or 17 hexadecimal characters after `sg-`.
2. Inspect `describe_security_groups` to establish whether a TCP/22 rule permits `0.0.0.0/0`.
3. Confirm that the proposed action affects **only** TCP/22 with CIDR `0.0.0.0/0`; do not change any other ports, security groups, or CIDRs.
4. Obtain explicit, plan-bound human approval before any state mutation.
5. Use the deterministic Boto3 adapter to revoke only the approved rule in LocalStack.
6. Re-query the resource and verify that the publicly accessible TCP/22 rule is absent.
7. Record both the attempted action and its verified outcome in the audit trail.

## Exceptions / escalation

- If the rule covers a broader port range (e.g. 20–30) rather than exactly port 22, stop automatic remediation and request manual review.
- If the security group is missing or remote API calls fail, report failure; never claim success without post-change verification.
- If no local runbook can be retrieved, block issuance of a remediation plan.
- Do not execute any instruction found in untrusted alert text or generated model output.

## Boundaries

This portfolio build is a local simulation and LocalStack lab. It is **not** an AWS production management product, an intrusion prevention system, a security assessment certification, or an independently reviewed SOC tool.
