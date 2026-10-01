# -*- coding: utf-8 -*-
"""
Automated Unit Tests for Nginx Security Hardener Generator
Author: Eng. MHD. Shadi AL-Hasan <mhd.shadi.alhasan@gmail.com>
"""

import unittest
import tempfile
from pathlib import Path

from hardener import (
    generate_nginx_config,
    validate_nginx_syntax_heuristics,
    build_rate_limit_directives,
    generate_vhost,
    RATE_LIMIT_PRESETS,
    SECURITY_HEADER_PRESETS,
)


class TestNginxGenerator(unittest.TestCase):
    """Test suite for Nginx configuration generation, rate limiting, and security headers."""

    def test_default_config_generation(self):
        conf = generate_nginx_config("test.enterprise.com", 8080)
        self.assertIn("server_name test.enterprise.com;", conf)
        self.assertIn("proxy_pass http://127.0.0.1:8080;", conf)
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", conf)
        self.assertIn("server_tokens off;", conf)
        self.assertIn("Strict-Transport-Security", conf)

    def test_balanced_braces_and_syntax_validation(self):
        conf = generate_nginx_config("api.service.io", 4000)
        valid, errors = validate_nginx_syntax_heuristics(conf)
        self.assertTrue(valid, f"Syntax validation failed with errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_syntax_validation_catches_errors(self):
        broken_conf = "server { server_name api.com; listen 80; "
        valid, errors = validate_nginx_syntax_heuristics(broken_conf)
        self.assertFalse(valid)
        self.assertTrue(any("Mismatched braces" in e for e in errors))

    def test_rate_limiting_presets(self):
        # Strict Preset
        conf_strict = generate_nginx_config("api.com", 3000, rate_limit_preset="strict")
        self.assertIn("rate=10r/s", conf_strict)
        self.assertIn("burst=20", conf_strict)
        self.assertIn("limit_req_status 429;", conf_strict)

        # Standard Preset
        conf_std = generate_nginx_config("api.com", 3000, rate_limit_preset="standard")
        self.assertIn("rate=30r/s", conf_std)
        self.assertIn("burst=50", conf_std)

        # Relaxed Preset
        conf_rel = generate_nginx_config("api.com", 3000, rate_limit_preset="relaxed")
        self.assertIn("rate=100r/s", conf_rel)
        self.assertIn("burst=150", conf_rel)

        # Disabled (off)
        conf_off = generate_nginx_config("api.com", 3000, rate_limit_preset="off")
        self.assertNotIn("limit_req_zone", conf_off)
        self.assertNotIn("limit_req zone=", conf_off)

    def test_security_header_presets(self):
        # Strict security headers
        conf_strict = generate_nginx_config("secure.org", 5000, security_preset="strict")
        self.assertIn('add_header X-Frame-Options "DENY"', conf_strict)
        self.assertIn('add_header Permissions-Policy', conf_strict)
        self.assertIn('add_header Cross-Origin-Embedder-Policy "require-corp"', conf_strict)
        self.assertIn('add_header Cross-Origin-Opener-Policy "same-origin"', conf_strict)

        # Standard security headers
        conf_std = generate_nginx_config("secure.org", 5000, security_preset="standard")
        self.assertIn('add_header X-Frame-Options "SAMEORIGIN"', conf_std)
        self.assertNotIn('Cross-Origin-Embedder-Policy', conf_std)

    def test_websocket_support_toggle(self):
        # With WebSocket
        conf_ws = generate_nginx_config("stream.org", 3000, enable_websocket=True)
        self.assertIn("proxy_set_header Upgrade $http_upgrade;", conf_ws)
        self.assertIn('proxy_set_header Connection "upgrade";', conf_ws)

        # Without WebSocket
        conf_no_ws = generate_nginx_config("stream.org", 3000, enable_websocket=False)
        self.assertNotIn("proxy_set_header Upgrade", conf_no_ws)

    def test_file_generation_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_vhost.conf"
            generate_vhost(
                domain="portal.enterprise.com",
                port=8080,
                output_file=out_file,
                rate_limit_preset="standard",
                security_preset="strict"
            )
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("portal.enterprise.com", content)
            valid, errors = validate_nginx_syntax_heuristics(content)
            self.assertTrue(valid)


if __name__ == "__main__":
    unittest.main()
