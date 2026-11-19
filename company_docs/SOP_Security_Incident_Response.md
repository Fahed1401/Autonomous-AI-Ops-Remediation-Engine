# STANDARD OPERATING PROCEDURE (SOP): CLOUD SECURITY INCIDENT RESPONSE

**Document Control Information**
* **Document ID:** SEC-SOP-042
* **Version:** 2.1
* **Effective Date:** March 2026
* **Document Owner:** Cloud Security Operations Center (CSOC)
* **Approved By:** Chief Information Security Officer (CISO)
* **Classification:** INTERNAL / RESTRICTED

---

## 1. Purpose
The purpose of this Standard Operating Procedure (SOP) is to establish a standardized, rapid, and predictable response to unauthorized access attempts and misconfigurations within the enterprise cloud infrastructure (AWS/GCP/Azure). This ensures compliance with organizational security policies and minimizes Mean Time to Resolution (MTTR) during active cyber threats.

## 2. Scope
This procedure applies to all Virtual Private Clouds (VPCs), Security Groups, Network Access Control Lists (NACLs), and compute instances operating within the production and staging environments. It is applicable to human DevOps engineers, Site Reliability Engineers (SREs), and authorized Autonomous AIOps Remediation Agents.

## 3. Roles and Responsibilities
* **L1 Security Analyst / Autonomous Agent:** Responsible for initial alert ingestion, triage, and immediate automated containment (Tier 1 remediation).
* **L2 Cloud Security Engineer:** Responsible for post-incident forensics, root-cause analysis, and handling escalations if automated remediation fails.
* **Incident Commander:** Coordinates response for Sev-1 (Critical) incidents affecting customer data.

## 4. Incident Definition: Unauthorized SSH Access (Port 22)
**Alert Trigger:** Monitoring systems (e.g., AWS CloudWatch, Datadog, GuardDuty) detect repeated failed authentication attempts, or identify a security group configuration where TCP Port 22 (SSH) is exposed to the public internet (`0.0.0.0/0`) or an unauthorized IP address.
**Severity:** CRITICAL (Sev-1)
**SLA for Containment:** < 5 Minutes

## 5. Containment and Remediation Procedure
Upon detection of an unauthorized SSH exposure or brute-force attack, the responding entity (Human Engineer or LangChain Autonomous Agent) MUST execute the following steps strictly in order:

### Step 5.1: Threat Identification and Triage
1. Parse the incoming JSON alert payload.
2. Identify the exact **Attacker IP address** or the exposed CIDR block.
3. Identify the exact **Affected Resource ID** (specifically, the AWS Security Group ID, e.g., `sg-xxxxxxxx`).

### Step 5.2: Immediate Containment (Execution Phase)
To stop the active threat and restore infrastructure compliance, the ingress rule allowing the unauthorized traffic must be immediately destroyed.

* **Authorized Action:** The responding engineer or autonomous agent must use the approved cloud management tools to revoke the ingress rule.
* **Target Protocol:** TCP
* **Target Port:** 22
* **Required Command/Tool:** Execute the `revoke_security_group_ingress` API call (via Boto3 or the AWS CLI) against the affected Security Group ID to permanently block the unauthorized IP range or global `0.0.0.0/0` exposure. 

### Step 5.3: Verification
1. Query the security group state using `describe_security_groups`.
2. Verify that the ingress rule for Port 22 no longer exists.
3. Log the successful remediation in the incident management system (Jira/ServiceNow).

## 6. Escalation Matrix
If the `revoke_security_group_ingress` action fails due to permission errors (`AccessDenied`), or if the resource does not exist (`InvalidGroup.NotFound`), the Autonomous Agent MUST halt execution and escalate the ticket to the L2 Cloud Security Engineer immediately. 

## 7. Revision History
| Version | Date | Author | Description of Change |
|---------|------|--------|-----------------------|
| 1.0 | Jan 2024 | CloudSec Team | Initial draft for manual incident response. |
| 2.0 | Nov 2025 | DevSecOps | Updated to include Boto3 API commands. |
| 2.1 | Mar 2026 | F. Ahmad | Integrated AI Autonomous Agent workflows and HITL requirements. |