from __future__ import annotations

import gzip
import base64
import json
import tempfile
from pathlib import Path
import unittest

from brain_core.market_data.stockapi import (
    AppendOnlyRawWriter,
    BackfillRequest,
    ByteFrameParser,
    GapDetector,
    MockHttpBackfillClient,
    RuntimeClientConfig,
    SessionState,
    StockApiPayloadParser,
    StockApiRuntimeClient,
    StreamType,
    build_login_command,
    build_subscribe_command,
)
from brain_core.market_data.stockapi.parser import decompress_gzip_base64_to_text
from brain_core.market_data.stockapi.protocol import ON_DEMAND_PORTS, redact_command
from brain_core.market_data.stockapi.health import BoundedEventQueue


def market_payload(symbol: str = "000001.SZ") -> str:
    fields = [
        "100",
        "SZ",
        symbol,
        "20260717",
        "135306980",
        "OPEN",
        "10.00",
        "10.10",
        "10.50",
        "9.90",
        "10.20",
    ]
    fields += [f"10.{i:02d}" for i in range(11, 21)]
    fields += [str(i * 100) for i in range(21, 31)]
    fields += [f"9.{i:02d}" for i in range(31, 41)]
    fields += [str(i * 100) for i in range(41, 51)]
    fields += [
        "66",
        "123456",
        "987654321",
        "8888",
        "7777",
        "10.11",
        "10.12",
        "12.24",
        "8.16",
        "31",
        "29",
        "3",
        "300",
        "2",
        "200",
    ]
    return ",".join(fields)


ORDER_PAYLOAD = "200,SZ,000001.SZ,20260717,135307001,O123,10.21,500,L,B,O122,9001,7"
TRAN_PAYLOAD = "300,SZ,000001.SZ,20260717,135307002,T123,10.22,300,3066,B,0,O123,A9,B8"
QUEUE_V1_PAYLOAD = "400,SZ,000001.SZ,20260717,135307003,10.22,3,100,200,300"
QUEUE_V2_PAYLOAD = ",".join(
    ["500", "SZ", "000001.SZ", "20260717", "135307004", "10.22", "10.21", "50", "50"]
    + [str(i) for i in range(1, 101)]
)


class StockApiFrameParserTests(unittest.TestCase):
    def test_byte_frame_parser_handles_half_sticky_noise_empty_and_corrupt(self):
        parser = ByteFrameParser(connection_id="c1", source_server="fixture", source_port=18100, max_frame_bytes=2048)
        self.assertEqual(parser.feed(b"noise<Market"), [])
        frames = parser.feed(b"><" + market_payload().encode("utf-8") + b"><><bad\xff>")

        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[0].decoded_text, "Market")
        self.assertEqual(frames[0].local_sequence, 1)
        self.assertEqual(frames[1].parse_status, "ok")
        self.assertEqual(frames[2].parse_status, "empty_frame")
        self.assertEqual(frames[3].parse_status, "decode_error")
        self.assertGreater(frames[1].receive_wall_time_ns, 0)
        self.assertGreater(frames[1].receive_monotonic_ns, 0)
        self.assertEqual(parser.dropped_noise_bytes, 5)

    def test_parser_flushes_residual_partial_frame(self):
        parser = ByteFrameParser(connection_id="c2", source_server="fixture", source_port=18100)
        parser.feed(b"<partial")
        residual = parser.flush_partial()
        self.assertIsNotNone(residual)
        self.assertEqual(residual.parse_status, "partial_frame")

    def test_oversize_frame_is_reported(self):
        parser = ByteFrameParser(connection_id="c3", source_server="fixture", source_port=18100, max_frame_bytes=5)
        frames = parser.feed(b"<1234567890>")
        self.assertEqual(frames[0].parse_status, "frame_too_long")


class StockApiPayloadParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = StockApiPayloadParser()

    def test_market_schema_preserves_66_raw_fields_and_ten_levels(self):
        event = self.parser.parse_frame(StreamType.MARKET, market_payload())[0]

        self.assertEqual(event["event_type"], "market_snapshot_v2")
        self.assertEqual(event["symbol"], "000001.SZ")
        self.assertEqual(event["source_time_raw"], "135306980")
        self.assertEqual(event["source_time_candidate"], "13:53:06.980")
        self.assertEqual(len(event["raw_fields"]), 66)
        self.assertEqual(len(event["source_specific_fields"]["ask_price_raw"]), 10)
        self.assertFalse(event["governance"]["ten_level_verified"])
        self.assertFalse(event["governance"]["raw_l2_gate_cleared"])

    def test_order_tran_and_hash_multirecord_parse(self):
        order_events = self.parser.parse_frame(StreamType.ORDER, ORDER_PAYLOAD + "#SZ,000001.SZ,20260717,135307002,O124,10.22,100,L,S,O123,9002,7")
        tran_events = self.parser.parse_frame(StreamType.TRAN, TRAN_PAYLOAD)

        self.assertEqual(len(order_events), 2)
        self.assertEqual(order_events[1]["packet_no"], "200")
        self.assertEqual(order_events[0]["source_specific_fields"]["event_sequence"], "9001")
        self.assertEqual(tran_events[0]["source_specific_fields"]["trade_no"], "T123")
        self.assertEqual(tran_events[0]["event_type"], "trade_print_candidate_v2")

    def test_queue_v1_v2_and_ambiguous_queue_format(self):
        q1 = self.parser.parse_frame(StreamType.QUEUE, QUEUE_V1_PAYLOAD, queue_version="v1")[0]
        q2 = self.parser.parse_frame(StreamType.QUEUE, QUEUE_V2_PAYLOAD, queue_version="v2")[0]
        ambiguous = self.parser.parse_frame(StreamType.QUEUE, QUEUE_V1_PAYLOAD)[0]

        self.assertEqual(q1["event_type"], "queue_v1")
        self.assertEqual(q2["event_type"], "queue_v2")
        self.assertEqual(len(q2["source_specific_fields"]["ask_queue_50_raw"]), 50)
        self.assertEqual(len(q2["source_specific_fields"]["bid_queue_50_raw"]), 50)
        self.assertEqual(ambiguous["quality"]["validation_status"], "AMBIGUOUS_QUEUE_FORMAT")

    def test_control_login_kick_and_gzip_helpers(self):
        heartbeat = self.parser.parse_frame(StreamType.MARKET, "HeartBeat")[0]
        kick = self.parser.parse_frame(StreamType.MARKET, "KICK,another_login")[0]
        payload = base64.b64encode(gzip.compress(b"hello")).decode("ascii")

        self.assertEqual(heartbeat["event_type"], "control")
        self.assertEqual(kick["event_type"], "control_kick")
        self.assertEqual(decompress_gzip_base64_to_text(payload), "hello")

    def test_field_shortage_and_extra_fields_are_preserved(self):
        short_event = self.parser.parse_frame(StreamType.ORDER, "1,SZ,000001.SZ")[0]
        extra_event = self.parser.parse_frame(StreamType.TRAN, TRAN_PAYLOAD + ",EXTRA")[0]

        self.assertEqual(short_event["source_specific_fields"]["event_sequence"], "")
        self.assertIn("EXTRA", extra_event["raw_fields"])


class StockApiRuntimeAndGovernanceTests(unittest.TestCase):
    def test_runtime_skeleton_blocks_network_and_waits_for_login_success(self):
        client = StockApiRuntimeClient(RuntimeClientConfig(host="example.invalid", symbols=["000001.SZ"]))

        with self.assertRaises(RuntimeError):
            client.on_subscribe_sent()
        self.assertEqual(client.on_login_sent(), SessionState.LOGIN_SENT)
        self.assertEqual(client.on_login_response("DL,OK,1"), SessionState.AUTHENTICATED)
        self.assertTrue(client.can_subscribe())
        self.assertEqual(client.on_subscribe_sent(), SessionState.SUBSCRIBE_SENT)
        with self.assertRaises(RuntimeError):
            client.connect()

    def test_runtime_ports_include_four_181xx_streams(self):
        self.assertEqual(set(ON_DEMAND_PORTS.keys()), {18100, 18103, 18104, 18105})
        self.assertEqual(ON_DEMAND_PORTS[18104], StreamType.QUEUE)

    def test_credentials_are_redacted_in_commands(self):
        login = build_login_command("acct", "pwd_value")
        sub = build_subscribe_command("acct", "pwd_value", "000001.SZ")

        self.assertEqual(redact_command(login), "<DL,***,***>")
        self.assertEqual(redact_command(sub), "<DY2,***,***,000001.SZ>")

    def test_bounded_queue_records_backpressure(self):
        q = BoundedEventQueue(maxsize=1)
        self.assertTrue(q.put("a"))
        self.assertFalse(q.put("b"))
        self.assertEqual(q.metrics.dropped_count, 1)
        self.assertEqual(q.metrics.queue_high_watermark, 1)

    def test_raw_writer_saves_raw_before_normalized_with_double_clock(self):
        frame_parser = ByteFrameParser(connection_id="c4", source_server="fixture", source_port=18100)
        frame = frame_parser.feed(b"<" + market_payload().encode("utf-8") + b">")[0]
        event = StockApiPayloadParser().parse_frame(StreamType.MARKET, frame.decoded_text)[0]
        with tempfile.TemporaryDirectory() as tmp:
            writer = AppendOnlyRawWriter(Path(tmp))
            raw_path = writer.write_raw_frame(frame, trade_date="20260717", stream_type="Market", symbol="000001.SZ")
            event_path = writer.write_normalized_event(event)
            receipt = writer.close()

            raw_row = json.loads(raw_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("raw_bytes_hex", raw_row)
            self.assertGreater(raw_row["receive_wall_time_ns"], 0)
            self.assertGreater(raw_row["receive_monotonic_ns"], 0)
            self.assertTrue(event_path.exists())
            self.assertEqual(receipt["raw_count"], 1)
            self.assertEqual(receipt["normalized_count"], 1)

    def test_gap_detector_and_backfill_mock(self):
        parser = StockApiPayloadParser()
        event1 = parser.parse_frame(StreamType.ORDER, ORDER_PAYLOAD)[0]
        event2 = parser.parse_frame(
            StreamType.ORDER,
            "200,SZ,000001.SZ,20260717,135307002,O124,10.22,100,L,S,O123,9003,7",
        )[0]
        detector = GapDetector(field_name="event_sequence")

        self.assertEqual(detector.observe(event1)["status"], "continuous")
        gap = detector.observe(event2)
        self.assertEqual(gap["status"], "gap")
        backfill = MockHttpBackfillClient()
        result = backfill.request_backfill(
            BackfillRequest(stream_type="Order", symbol="000001.SZ", trade_date="20260717", offset=9002)
        )
        self.assertEqual(result["status"], "mocked")
        self.assertFalse(result["network_used"])

    def test_cross_day_reset_candidate(self):
        parser = StockApiPayloadParser()
        detector = GapDetector(field_name="event_sequence")
        first = parser.parse_frame(StreamType.ORDER, ORDER_PAYLOAD)[0]
        second = parser.parse_frame(
            StreamType.ORDER,
            "200,SZ,000001.SZ,20260718,093000000,O001,10.00,100,L,B,O000,1,7",
        )[0]

        detector.observe(first)
        self.assertEqual(detector.observe(second)["status"], "reset_candidate")


if __name__ == "__main__":
    unittest.main()
