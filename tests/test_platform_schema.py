import json
import os
import shutil
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
            "Mastodon",
            "Threads",
            "DeviantArt",
        }
        self.assertTrue(expected_new.issubset(names))

    def test_invalid_manifest_rejected(self):
        temp_root = os.path.join(os.getcwd(), ".tmp-tests")
        os.makedirs(temp_root, exist_ok=True)
        temp_dir = os.path.join(temp_root, "platform-schema-invalid")
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

        try:
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
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
