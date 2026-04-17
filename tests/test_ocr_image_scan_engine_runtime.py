import asyncio
import unittest
from unittest.mock import patch

from core.collect.ocr_image_scan import OCRScanItem
from core.engines.ocr_image_scan_engine import OCRImageScanEngine


class TestOCRImageScanEngineRuntime(unittest.TestCase):
    def test_ocr_engine_returns_summary_and_failures(self):
        fake_item = OCRScanItem(
            source="C:/tmp/one.png",
            source_kind="local_path",
            display_name="one.png",
            content_type="image/png",
            size_bytes=1024,
            sha256="a" * 64,
            width=1200,
            height=800,
            preprocess_pipeline=("grayscale", "autocontrast"),
            raw_text="alice@example.com https://example.com",
            ocr_engine="pytesseract",
            extracted_signals={
                "emails": ["alice@example.com"],
                "urls": ["https://example.com"],
                "phones": [],
                "mentions": [],
                "hashtags": [],
                "names": ["Alice Example"],
                "keywords": ["example"],
            },
            language="en",
            confidence_hint="high",
            notes=(),
        )

        async def fake_local(self, source, **kwargs):
            return fake_item

        async def fake_remote(self, session, source, **kwargs):
            raise ValueError("HTTP 404")

        with (
            patch.object(OCRImageScanEngine, "_process_local_source", new=fake_local),
            patch.object(OCRImageScanEngine, "_process_remote_source", new=fake_remote),
        ):
            result = asyncio.run(
                OCRImageScanEngine().run_ocr_scan(
                    paths=["one.png"],
                    urls=["https://example.com/two.png"],
                    preprocess_mode="balanced",
                    timeout_seconds=10,
                    max_concurrency=2,
                    max_bytes=2_000_000,
                )
            )

        self.assertEqual(result.summary.image_count, 2)
        self.assertEqual(result.summary.processed_count, 1)
        self.assertEqual(result.summary.failed_count, 1)
        self.assertEqual(result.summary.ocr_hits, 1)
        self.assertEqual(result.summary.signal_totals.get("emails"), 1)
        self.assertEqual(result.failures[0].source_kind, "remote_url")


if __name__ == "__main__":
    unittest.main()
