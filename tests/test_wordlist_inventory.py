import unittest

from wordlists import (
    attack_surface_inventory,
    build_wordlist_inventory,
    load_attack_surface_port_wordlist,
    load_attack_surface_text_wordlist,
)


class TestWordlistInventory(unittest.TestCase):
    def test_inventory_discovers_attack_surface_assets(self):
        inventory = build_wordlist_inventory()
        filenames = {asset.filename for asset in inventory.assets}
        self.assertIn("subdomains_small.txt", filenames)
        self.assertIn("paths_common.txt", filenames)
        self.assertIn("ports_top100.txt", filenames)

    def test_attack_surface_inventory_returns_collection_assets(self):
        assets = attack_surface_inventory()
        self.assertEqual({asset.collection for asset in assets}, {"attack_surface"})
        self.assertEqual(len(assets), 3)

    def test_attack_surface_wordlist_loaders_return_runtime_values(self):
        text_values = load_attack_surface_text_wordlist("subdomains_small.txt")
        port_values = load_attack_surface_port_wordlist("ports_top100.txt")
        self.assertIn("www", text_values)
        self.assertIn(80, port_values)
        self.assertTrue(all(isinstance(value, int) for value in port_values))


if __name__ == "__main__":
    unittest.main()
