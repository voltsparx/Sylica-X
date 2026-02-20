import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

from core.domain_intel import HttpArtifact, normalize_domain, scan_domain_surface


class TestDomainIntel(unittest.IsolatedAsyncioTestCase):
    def test_normalize_domain(self):
        self.assertEqual(normalize_domain(" https://Example.com/path "), "example.com")
        self.assertEqual(normalize_domain("http://sub.example.com///"), "sub.example.com")

    async def test_surface_optional_collectors_run_concurrently(self):
        async def fake_http_probe(session, url, timeout_seconds):
            await asyncio.sleep(0.05)
            return HttpArtifact(
                status=200,
                final_url=url,
                headers={"server": "unit-test"},
                body="ok",
                error=None,
            )

        async def fake_ct(session, domain, timeout_seconds, max_subdomains):
            await asyncio.sleep(0.2)
            return ["a.example.com", "b.example.com"], None

        async def fake_rdap(session, domain, timeout_seconds):
            await asyncio.sleep(0.2)
            return {"handle": "HANDLE-1"}, None

        with (
            patch("core.domain_intel._resolve_addresses", AsyncMock(return_value=["1.1.1.1"])),
            patch("core.domain_intel._http_probe", new=fake_http_probe),
            patch("core.domain_intel._load_ct_subdomains", new=fake_ct),
            patch("core.domain_intel._load_rdap", new=fake_rdap),
        ):
            started = time.perf_counter()
            result = await scan_domain_surface(
                domain="example.com",
                timeout_seconds=1,
                include_ct=True,
                include_rdap=True,
                max_subdomains=50,
            )
            elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.35)
        self.assertEqual(result["subdomains"], ["a.example.com", "b.example.com"])
        self.assertEqual(result["rdap"], {"handle": "HANDLE-1"})


if __name__ == "__main__":
    unittest.main()
