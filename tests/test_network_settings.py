import os
import unittest
from unittest.mock import patch

from core.network import get_network_settings


class TestNetworkSettings(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_tor_returns_socks5h_proxy(self):
        self.assertEqual(get_network_settings(use_proxy=False, use_tor=True), "socks5h://127.0.0.1:9050")

    @patch.dict(os.environ, {"HTTP_PROXY": "http://proxy.local:8080"}, clear=True)
    def test_proxy_uses_http_proxy(self):
        self.assertEqual(get_network_settings(use_proxy=True, use_tor=False), "http://proxy.local:8080")

    @patch.dict(os.environ, {"HTTPS_PROXY": "https://secure-proxy.local:8443"}, clear=True)
    def test_proxy_falls_back_to_https_proxy(self):
        self.assertEqual(
            get_network_settings(use_proxy=True, use_tor=False),
            "https://secure-proxy.local:8443",
        )

    @patch.dict(os.environ, {"HTTP_PROXY": "ftp://proxy.local:21"}, clear=True)
    def test_invalid_proxy_scheme_is_rejected(self):
        with self.assertRaises(RuntimeError):
            get_network_settings(use_proxy=True, use_tor=False)

    @patch.dict(os.environ, {}, clear=True)
    def test_proxy_missing_env_is_rejected(self):
        with self.assertRaises(RuntimeError):
            get_network_settings(use_proxy=True, use_tor=False)


if __name__ == "__main__":
    unittest.main()
