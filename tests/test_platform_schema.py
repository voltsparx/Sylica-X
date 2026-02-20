import json
import os
import tempfile
import unittest

from core.platform_schema import PlatformValidationError, load_platforms


class TestPlatformSchema(unittest.TestCase):
    def test_repo_platform_manifest_loads(self):
        platforms = load_platforms("platforms")
        self.assertGreater(len(platforms), 0)
        self.assertTrue(all(platform.url for platform in platforms))
        names = {platform.name for platform in platforms}
        expected_new = {
            "HackerRank",
            "CodePen",
            "Replit",
            "Keybase",
            "Unsplash",
            "Vimeo",
            "Quora",
            "ProductHunt",
            "BuyMeACoffee",
            "SteamCommunity",
        }
        self.assertTrue(expected_new.issubset(names))

    def test_invalid_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_file = os.path.join(temp_dir, "bad.json")
            with open(bad_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "name": "BrokenPlatform",
                        "url": "https://example.com/profile",  # Missing {username}
                    },
                    handle,
                )

            with self.assertRaises(PlatformValidationError):
                load_platforms(temp_dir)


if __name__ == "__main__":
    unittest.main()
