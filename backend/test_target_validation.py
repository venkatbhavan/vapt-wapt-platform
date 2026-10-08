import unittest
from pydantic import ValidationError

from app.schemas.assessment import AssessmentCreate
from app.worker.scanners.nmap_config import build_nmap_command, get_nmap_config_for_profile


class TargetValidationTests(unittest.TestCase):
    def _payload(self, target):
        return dict(name="t", target=target, scope="s", authorization_confirmed=True)

    def test_valid_targets_are_accepted(self):
        for target in ["127.0.0.1", "10.0.0.0/24", "example.com", "http://127.0.0.1:3000"]:
            self.assertEqual(AssessmentCreate(**self._payload(target)).target, target)

    def test_option_like_targets_are_rejected(self):
        for target in ["-iL /etc/hosts", "--script=vuln", "-oN /tmp/x", "127.0.0.1 -p-"]:
            with self.assertRaises(ValidationError):
                AssessmentCreate(**self._payload(target))

    def test_nmap_builder_rejects_option_like_targets(self):
        cfg = get_nmap_config_for_profile("safe")
        for target in ["--script=vuln", "-iL hosts.txt", "10.0.0.1 -A", ""]:
            with self.assertRaises(ValueError):
                build_nmap_command(target, cfg)

    def test_nmap_builder_still_accepts_normal_target(self):
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("safe"))
        self.assertEqual(cmd[-1], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
