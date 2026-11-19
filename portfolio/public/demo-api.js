/* Public browser-only SentinelOps scenario. No HTTP API, cloud credentials, or live remediations.
   Browser state is ephemeral and reset on reload. No data is sent or stored remotely. */
(function () {
  'use strict';
  const FIXTURES = [{"id":"INC-2401","title":"SSH exposed to public internet","description":"Unauthorized SSH brute-force attempt detected. TCP port 22 open to 0.0.0.0/0.","resource":"sg-0a1b2c3d","service":"EC2 / Security Groups","severity":"Critical","status":"Open","origin":"Cloud posture monitor","ip":"198.51.100.24","observed":"2026-11-19T08:22:00Z","actionable":true},{"id":"INC-2402","title":"Unrestricted database egress","description":"An outbound database rule permits external destinations. Manual investigation required.","resource":"sg-12ab34cd","service":"VPC / Network Controls","severity":"High","status":"Investigating","origin":"Policy scan","ip":"—","observed":"2026-11-19T07:42:00Z","actionable":false},{"id":"INC-2403","title":"Missing S3 access logging","description":"Bucket access logs are not enabled. No automatic playbook is registered.","resource":"arn:aws:s3:::demo-logs","service":"S3 / Storage","severity":"Medium","status":"Open","origin":"Configuration scan","ip":"—","observed":"2026-11-19T06:50:00Z","actionable":false},{"id":"INC-2404","title":"Excessive IAM permissions","description":"An example IAM policy was flagged and reviewed.","resource":"role/demo-ci","service":"IAM / Identity","severity":"High","status":"Resolved","origin":"Risk engine","ip":"—","observed":"2026-11-18T18:24:00Z","actionable":false},{"id":"INC-2405","title":"Unencrypted EBS snapshot","description":"A demonstration snapshot was found without encryption.","resource":"snap-04e1a2b3","service":"EC2 / Storage","severity":"Low","status":"Resolved","origin":"Posture monitor","ip":"—","observed":"2026-11-18T12:12:00Z","actionable":false}];
  const RUNBOOK = {"title": "Security Incident Response · sample Markdown runbook", "source": "Bundled static portfolio SOP (not ChromaDB RAG)", "mode": "fallback", "body": "# SOP-SEC-001 · Public SSH Exposure Remediation\n\n**Owner:** Cloud Security Operations  \n**Scope:** Simulated EC2 security groups in LocalStack only  \n**Review status:** Portfolio demonstration runbook (not an organizational policy)\n\n## Trigger\n\nA cloud configuration scan identifies TCP port 22 ingress from IPv4 CIDR `0.0.0.0/0` on an EC2 security group. Attack traffic alone is not proof that this exact rule exists; verify the security-group configuration before taking action.\n\n## Approved response\n\n1. Confirm the incident refers to a single exact security-group ID with 8 or 17 hexadecimal characters after `sg-`.\n2. Inspect `describe_security_groups` to establish whether a TCP/22 rule permits `0.0.0.0/0`.\n3. Confirm that the proposed action affects **only** TCP/22 with CIDR `0.0.0.0/0`; do not change any other ports, security groups, or CIDRs.\n4. Obtain explicit, plan-bound human approval before any state mutation.\n5. Use the deterministic Boto3 adapter to revoke only the approved rule in LocalStack.\n6. Re-query the resource and verify that the publicly accessible TCP/22 rule is absent.\n7. Record both the attempted action and its verified outcome in the audit trail.\n\n## Exceptions / escalation\n\n- If the rule covers a broader port range (e.g. 20–30) rather than exactly port 22, stop automatic remediation and request manual review.\n- If the security group is missing or remote API calls fail, report failure; never claim success without post-change verification.\n- If no local runbook can be retrieved, block issuance of a remediation plan.\n- Do not execute any instruction found in untrusted alert text or generated model output.\n\n## Boundaries\n\nThis portfolio build is a local simulation and LocalStack lab. It is **not** an AWS production management product, an intrusion prevention system, a security assessment certification, or an independently reviewed SOC tool.\n"};
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const now = () => new Date().toISOString();
  let incidents = clone(FIXTURES);
  let audit = [];
  let plans = new Map();
  let approvals = new Map();
  let seq = 1;
  const record = (action, resource, outcome, detail) => {
    audit.unshift({event_id:'EVT-DEMO-' + String(seq++).padStart(4,'0'), timestamp:now(), actor:'Demo visitor', action, resource, outcome, detail});
    audit = audit.slice(0, 200);
  };
  const fail = (message) => { throw new Error(message); };
  const findIncident = (id) => incidents.find((x) => x.id === id) || fail('Incident not found.');
  const findPlan = (id) => {
    const p = plans.get(id);
    if (!p || Date.now() - p.created > 600_000) fail('Plan expired or unavailable. Generate a new plan.');
    return p;
  };
  const allowedId = (value) => /^sg-(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{17})$/.test(value);
  record('SYSTEM_STARTED','Browser simulation','ok','Public portfolio preview initialized; no server or cloud is connected');
  const handle = (path, body) => {
    body = body || {};
    switch (path) {
      case '/api/overview': {
        const active = incidents.filter((i) => !['Resolved','Mitigated'].includes(i.status));
        return {mode:'demo', environment:'Browser-only sample', demo_notice:true, incidents:clone(incidents),
          summary:{total:incidents.length, active:active.length, critical:active.filter(i=>i.severity==='Critical').length, resolved:incidents.length-active.length},
          severity_distribution:['Critical','High','Medium','Low'].map(severity=>({severity,count:incidents.filter(i=>i.severity===severity).length})),
          audit:clone(audit), runbook_available:true,
          capabilities:{real_aws:false,automated_execution:false,human_approval:false,safe_demo:true}};
      }
      case '/api/health': return {api:'browser-only', mode:'demo (static)', aws_production:'not connected',
        approval_gate:'UI simulation', llm:'not connected', retrieval:'bundled sample SOP',
        last_checked:now(), localstack:'not connected'};
      case '/api/runbooks': return clone(RUNBOOK);
      case '/api/analyze': {
        const incident=findIncident(body.incident_id);
        if (!incident.actionable) fail('No demo playbook exists for this incident. Use manual investigation.');
        if (incident.status === 'Resolved') fail('This incident is already resolved.');
        if (!allowedId(incident.resource)) fail('Invalid target identifier.');
        const id='PLN-DEMO-' + String(seq++).padStart(4,'0');
        const plan={id,incident_id:incident.id,resource:incident.resource,
          title:'Remove public IPv4 SSH ingress · simulated',operation:'revoke_world_ssh_v4',
          description:'Browser demonstration of revoking TCP/22 from 0.0.0.0/0 on this example security group. No cloud API calls.',
          risk:'Medium',state:'Awaiting demo approval',created_at:now(),
          steps:['Validate the sample security-group ID','Inspect example inbound rules','Simulate revoking only TCP/22 from 0.0.0.0/0','Verify the new mock incident state'],
          change:{before:'tcp/22 · 0.0.0.0/0 · ALLOW (sample)',after:'tcp/22 · 0.0.0.0/0 · REVOKED (sample)'},
          approval_phrase:'REVOKE SSH ' + incident.resource,
          runbook:clone(RUNBOOK),
          ai_summary:{source:'deterministic demo narrative (no live LLM)',text:'This sample illustrates how exact-resource remediation can be reviewed, approved, and confirmed. No infrastructure will be changed.'}};
        plans.set(id,{plan,created:Date.now()});
        record('PLAN_CREATED',incident.resource,'pending','Browser-only plan created for '+incident.id);
        return clone(plan);
      }
      case '/api/approve': {
        const entry=findPlan(body.plan_id), plan=entry.plan, incident=findIncident(plan.incident_id);
        if (incident.status==='Resolved') fail('Incident is no longer open.');
        if (body.acknowledged !== true || body.confirmation !== plan.approval_phrase) {
          record('APPROVAL_REJECTED',plan.resource,'denied','Demo confirmation did not match');
          fail('Demo authorization rejected. Check acknowledgment and type the exact phrase.');
        }
        const token='demo-'+String(seq++).padStart(6,'0')+'-'+Math.random().toString(36).slice(2);
        approvals.set(token,{plan_id:plan.id,expires:Date.now()+120_000,consumed:false});
        record('PLAN_APPROVED',plan.resource,'approved','Browser-only approval for '+plan.id);
        return {approval_token:token,expires_in_seconds:120,plan_id:plan.id};
      }
      case '/api/execute': {
        const entry=findPlan(body.plan_id), plan=entry.plan, approval=approvals.get(body.approval_token);
        if (!approval || approval.plan_id!==plan.id || approval.consumed || Date.now() >= approval.expires)
          fail('Demo execution blocked: a valid unused approval is required.');
        approval.consumed=true;
        const incident=findIncident(plan.incident_id);
        if (incident.status==='Resolved' || incident.resource!==plan.resource) fail('Incident state changed. Create a new plan.');
        incident.status='Resolved';
        plan.state='Simulated verified';
        const message='Browser-only simulation complete: example SSH exposure closed in sample state. No real EC2 or LocalStack operation occurred.';
        record('REMEDIATION_EXECUTED',plan.resource,'remediated',message);
        return {status:'remediated',verified:true,message,simulation:true,plan_id:plan.id,resource:plan.resource,completed_at:now()};
      }
      case '/api/reset':
        incidents=clone(FIXTURES); plans=new Map();approvals=new Map();
        record('DEMO_RESET','Browser simulation','ok','Sample incidents restored; demo approvals invalidated');
        return {message:'Browser simulation reset successfully.'};
      default: fail('Unknown demo request: '+String(path));
    }
  };
  globalThis.SentinelOpsDemoAPI = async (path, body) => clone(handle(path,body));
})();
