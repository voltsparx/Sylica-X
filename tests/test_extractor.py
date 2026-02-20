import unittest

from core.extractor import extract_bio, extract_contacts, extract_links, extract_username_mentions


class TestExtractor(unittest.TestCase):
    def test_extract_bio_supports_single_quote_meta(self):
        html = "<meta name='description' content='Hello &amp; welcome'>"
        self.assertEqual(extract_bio(html), "Hello & welcome")

    def test_extract_links_handles_quote_variants_and_dedupes(self):
        html = (
            '<a href="https://alpha.example">A</a>'
            "<a href='https://beta.example/path'>B</a>"
            '<a href="https://alpha.example#fragment">A2</a>'
        )
        self.assertEqual(extract_links(html), ["https://alpha.example", "https://beta.example/path"])

    def test_extract_contacts_ignores_short_phone_noise(self):
        html = (
            "<script>var hidden='bot@spam.example';</script>"
            "<p>Mail me at User@Test.com and call +1 (202) 555-0188 or 123-45.</p>"
        )
        contacts = extract_contacts(html)
        self.assertEqual(contacts["emails"], ["user@test.com"])
        self.assertEqual(contacts["phones"], ["+1 (202) 555-0188"])

    def test_extract_username_mentions_from_text(self):
        html = "<p>Alice account @alice has alias alice and mirror /alice</p>"
        mentions = extract_username_mentions(html, "alice")
        self.assertIn("alice", [value.lower() for value in mentions])
        self.assertIn("@alice", [value.lower() for value in mentions])
        self.assertIn("/alice", [value.lower() for value in mentions])


if __name__ == "__main__":
    unittest.main()
