import json
import tempfile
import unittest
from pathlib import Path

from aiops.core import RemediationError, SSH_WORLD_IPV4
from aiops.service import OperationsService
from tests.test_core import FakeEC2


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = OperationsService()
        self.incident_id = "INC-2401"

    def test_demo_overview_is_explicitly_simulated(self):
        d=self.service.overview()
        self.assertTrue(d["demo_notice"])
        self.assertEqual(d["summary"]["total"], 5)
        self.assertTrue(d["capabilities"]["human_approval"])
        self.assertFalse(d["capabilities"]["real_aws"])

    def test_only_allowlisted_incidents_receive_plans(self):
        with self.assertRaisesRegex(RemediationError, "No approved"):
            self.service.analyze("INC-2402")

    def test_execution_requires_exact_approval(self):
        plan=self.service.analyze(self.incident_id)
        with self.assertRaisesRegex(RemediationError, "[Aa]uthorization"):
            self.service.approve(plan["id"], "REVOKE SSH sg-wrong", True)
        with self.assertRaisesRegex(RemediationError, "[Aa]uthorization"):
            self.service.approve(plan["id"], plan["approval_phrase"], False)
        with self.assertRaisesRegex(RemediationError, "approval"):
            self.service.execute(plan["id"], "wrong")

    def test_one_use_token_and_verified_state(self):
        plan=self.service.analyze(self.incident_id)
        approved=self.service.approve(plan["id"], plan["approval_phrase"], True)
        self.assertEqual(self.service.overview()["summary"]["active"],3)
        out=self.service.execute(plan["id"], approved["approval_token"])
        self.assertTrue(out["simulation"])
        self.assertTrue(out["verified"])
        self.assertEqual(self.service.overview()["summary"]["active"],2)
        self.assertTrue(any(x["action"]=="REMEDIATION_EXECUTED" for x in self.service.overview()["audit"]))
        with self.assertRaises(RemediationError):
            self.service.execute(plan["id"],approved["approval_token"])

    def test_approval_expiration_and_plan_timeout(self):
        clock=[10.0]
        svc=OperationsService(clock=lambda:clock[0]);plan=svc.analyze(self.incident_id)
        approval=svc.approve(plan["id"],plan["approval_phrase"],True)
        clock[0]+=121.0
        with self.assertRaisesRegex(RemediationError,"approval"):
            svc.execute(plan["id"],approval["approval_token"])
        clock[0]+=600.0
        with self.assertRaisesRegex(RemediationError,"expired"):
            svc.approve(plan["id"],plan["approval_phrase"],True)

    def test_reset_invalidates_approvals(self):
        plan=self.service.analyze(self.incident_id)
        approved=self.service.approve(plan["id"],plan["approval_phrase"],True)
        self.service.reset_demo()
        with self.assertRaises(RemediationError):
            self.service.execute(plan["id"],approved["approval_token"])

    def test_localstack_readback_marks_incident_resolved(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"cloud_alert.json"
            path.write_text(json.dumps({"alert_id":"ALT-1","severity":"CRITICAL",
                                        "description":"SSH public access", "affected_resource_id":"sg-0a1b2c3d"}))
            ec2=FakeEC2([SSH_WORLD_IPV4]);svc=OperationsService(mode="localstack",alert_path=path,ec2_factory=lambda:ec2)
            plan=svc.analyze("ALT-1")
            token=svc.approve(plan["id"],plan["approval_phrase"],True)["approval_token"]
            out=svc.execute(plan["id"],token)
            self.assertFalse(out["simulation"])
            self.assertEqual(svc.overview()["summary"]["resolved"],1)
            self.assertEqual(len(ec2.revocations),1)

    def test_invalid_localstack_alert_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"cloud_alert.json"
            path.write_text('{"affected_resource_id":"sg-aaa; dangerous"}')
            svc=OperationsService(mode="localstack",alert_path=path)
            self.assertEqual(svc.overview()["incidents"], [])
