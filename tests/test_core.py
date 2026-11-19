import unittest

from aiops.core import (RemediationError, SSH_WORLD_IPV4, has_world_ssh_rule,
                        precise_revoke_permissions, revoke_ssh_world_localstack,
                        validate_security_group_id)


class FakeEC2:
    def __init__(self, perms, group_id="sg-0a1b2c3d", fail=False, no_change=False):
        self.perms = list(perms)
        self.group_id = group_id
        self.fail = fail
        self.no_change = no_change
        self.revocations = []

    def describe_security_groups(self, GroupIds):
        assert GroupIds == [self.group_id]
        return {"SecurityGroups": [{"GroupId": self.group_id, "IpPermissions": self.perms}]}

    def revoke_security_group_ingress(self, GroupId, IpPermissions):
        if self.fail:
            raise RuntimeError("simulated provider error")
        self.revocations.append({"GroupId": GroupId, "IpPermissions": IpPermissions})
        if not self.no_change:
            self.perms = [x for x in self.perms if x.get("FromPort") != 22 or x.get("ToPort") != 22]
        return {}


class CoreTests(unittest.TestCase):
    def test_valid_group_ids(self):
        self.assertEqual(validate_security_group_id("sg-0a1b2c3d"), "sg-0a1b2c3d")
        self.assertEqual(validate_security_group_id("sg-0123456789abcdef0"), "sg-0123456789abcdef0")

    def test_rejects_injected_or_invalid_ids(self):
        for candidate in ("prefix sg-0a1b2c3d suffix", "sg-nothex!!", "sg-1234567", "sg-"+"a"*18,
                          "sg-0a1b2c3d\n", "sg-0a1b2c3d; DROP", None, 55, "sg-deadbeef bad"):
            with self.subTest(candidate=candidate), self.assertRaises(RemediationError):
                validate_security_group_id(candidate)

    def test_only_exact_rule_revoke(self):
        other = {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
        self.assertTrue(has_world_ssh_rule([other, SSH_WORLD_IPV4]))
        self.assertEqual(precise_revoke_permissions([other, SSH_WORLD_IPV4]), [SSH_WORLD_IPV4])
        ec2 = FakeEC2([other, SSH_WORLD_IPV4])
        out = revoke_ssh_world_localstack("sg-0a1b2c3d", ec2)
        self.assertTrue(out["verified"])
        self.assertEqual(ec2.revocations[0]["IpPermissions"], [SSH_WORLD_IPV4])
        self.assertIn(other, ec2.perms)

    def test_closed_rule_is_not_modified(self):
        ec2 = FakeEC2([])
        out = revoke_ssh_world_localstack("sg-0a1b2c3d", ec2)
        self.assertEqual(out["status"], "already_secure")
        self.assertEqual(ec2.revocations, [])

    def test_broad_range_fails_closed(self):
        ec2 = FakeEC2([{"IpProtocol": "tcp", "FromPort": 20, "ToPort": 30,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        with self.assertRaisesRegex(RemediationError, "manual review"):
            revoke_ssh_world_localstack("sg-0a1b2c3d", ec2)
        self.assertEqual(ec2.revocations, [])

    def test_failed_cloud_call_does_not_claim_success(self):
        ec2 = FakeEC2([SSH_WORLD_IPV4], fail=True)
        with self.assertRaisesRegex(RemediationError, "failed"):
            revoke_ssh_world_localstack("sg-0a1b2c3d", ec2)

    def test_readback_verification_failure(self):
        ec2 = FakeEC2([SSH_WORLD_IPV4], no_change=True)
        with self.assertRaisesRegex(RemediationError, "verification failed"):
            revoke_ssh_world_localstack("sg-0a1b2c3d", ec2)
