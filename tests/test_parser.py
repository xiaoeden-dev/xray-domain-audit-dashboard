import unittest

from app import parse_access_line


class AccessLogParserTests(unittest.TestCase):
    def test_domain_connection_is_attributed_to_client(self):
        line = (
            "2026/11/11 09:33:45.005707 from [REDACTED] accepted tcp:github.com:443 "
            "[in-22872-tcp >> direct] email: client-a"
        )
        event = parse_access_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["client"], "client-a")
        self.assertEqual(event["domain"], "github.com")
        self.assertEqual(event["protocol"], "tcp")
        self.assertEqual(event["port"], 443)
        self.assertEqual(event["inbound"], "in-22872-tcp >> direct")
        self.assertNotIn("source_ip", event)
        self.assertNotIn("raw_line", event)

    def test_masked_destination_is_not_misidentified_as_domain(self):
        line = (
            "2026/11/11 09:33:45.005707 from [REDACTED] accepted udp:[Masked IPv4]:443 "
            "[inbound >> direct] email: client-b"
        )
        event = parse_access_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["destination_kind"], "masked")
        self.assertIsNone(event["domain"])
        self.assertEqual(event["port"], 443)

    def test_ip_destination_is_not_misidentified_as_domain(self):
        line = (
            "2026/11/11 09:33:45.005707 from [REDACTED] accepted tcp:192.0.2.10:443 "
            "[inbound >> direct] email: client-c"
        )
        event = parse_access_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["destination_kind"], "ip")
        self.assertIsNone(event["domain"])

    def test_non_connection_or_unattributed_line_is_ignored(self):
        self.assertIsNone(parse_access_line("not an Xray access entry"))
        self.assertIsNone(
            parse_access_line(
                "2026/11/11 09:33:45.005707 accepted tcp:example.com:443 [inbound >> direct]"
            )
        )

    def test_fingerprint_is_stable_for_duplicate_line(self):
        line = (
            "2026/11/11 09:33:45.005707 from [REDACTED] accepted tcp:example.com:443 "
            "[inbound >> direct] email: client-a"
        )
        first = parse_access_line(line)
        second = parse_access_line(line)
        self.assertEqual(first["fingerprint"], second["fingerprint"])


if __name__ == "__main__":
    unittest.main()
