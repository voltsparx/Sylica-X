import unittest

from core.utils.quicktest_data import list_quicktest_templates, pick_quicktest_template, quicktest_template_ids


class TestQuicktestTemplates(unittest.TestCase):
    def test_template_inventory_has_five_items(self):
        templates = list_quicktest_templates()
        self.assertEqual(5, len(templates))
        self.assertEqual(5, len(quicktest_template_ids()))

    def test_pick_template_by_id(self):
        template = pick_quicktest_template(template_id="atlas-mercier")
        self.assertEqual("atlas-mercier", template["id"])
        self.assertEqual("explicit", template["selection_mode"])

    def test_pick_template_with_seed_is_deterministic(self):
        first = pick_quicktest_template(seed=11)
        second = pick_quicktest_template(seed=11)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual("random_seeded", first["selection_mode"])

    def test_pick_template_with_invalid_id_raises(self):
        with self.assertRaises(ValueError):
            pick_quicktest_template(template_id="not-a-template")


if __name__ == "__main__":
    unittest.main()
