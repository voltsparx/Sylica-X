import unittest

from core.platform_schema import PlatformConfig
from core.scanner import evaluate_presence


class TestScannerDecisionLogic(unittest.TestCase):
    def test_status_code_found(self):
        platform = PlatformConfig(
            name="GitHub",
            url="https://github.com/{username}",
            url_probe="https://github.com/{username}",
            detection_methods=("status_code",),
            exists_statuses=(200,),
            not_found_statuses=(),
            error_messages=(),
            error_url=None,
            regex_check=None,
            headers={},
            request_method="HEAD",
            request_payload=None,
            confidence_weight=0.95,
        )
        verdict, reason = evaluate_presence(
            platform=platform,
            username="alice",
            status_code=200,
            body="",
            response_url="https://github.com/alice",
        )
        self.assertEqual(verdict, "FOUND")
        self.assertIn("status_code", reason)

    def test_message_not_found(self):
        platform = PlatformConfig(
            name="GitLab",
            url="https://gitlab.com/{username}",
            url_probe="https://gitlab.com/api/v4/users?username={username}",
            detection_methods=("message",),
            exists_statuses=(),
            not_found_statuses=(),
            error_messages=("[]",),
            error_url=None,
            regex_check=None,
            headers={},
            request_method="GET",
            request_payload=None,
            confidence_weight=0.85,
        )
        verdict, _ = evaluate_presence(
            platform=platform,
            username="nobody",
            status_code=200,
            body="[]",
            response_url="https://gitlab.com/api/v4/users?username=nobody",
        )
        self.assertEqual(verdict, "NOT FOUND")

    def test_mixed_methods_are_conservative(self):
        platform = PlatformConfig(
            name="Mixed",
            url="https://example.com/{username}",
            url_probe="https://example.com/{username}",
            detection_methods=("status_code", "message"),
            exists_statuses=(200,),
            not_found_statuses=(),
            error_messages=("missing user",),
            error_url=None,
            regex_check=None,
            headers={},
            request_method="GET",
            request_payload=None,
            confidence_weight=0.7,
        )
        verdict, _ = evaluate_presence(
            platform=platform,
            username="alice",
            status_code=200,
            body="missing user",
            response_url="https://example.com/alice",
        )
        self.assertEqual(verdict, "NOT FOUND")


if __name__ == "__main__":
    unittest.main()
