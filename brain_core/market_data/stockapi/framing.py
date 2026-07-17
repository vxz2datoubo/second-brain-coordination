"""Byte-level frame parser for StockAPI TCP streams."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import time
from typing import Any


@dataclass
class FrameRecord:
    raw_bytes: bytes
    decoded_text: str = ""
    decode_error: str = ""
    raw_sha256: str = ""
    frame_length: int = 0
    connection_id: str = ""
    source_server: str = ""
    source_port: int = 0
    receive_wall_time_ns: int = 0
    receive_monotonic_ns: int = 0
    local_sequence: int = 0
    parse_status: str = "ok"
    parse_error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: bytes,
        *,
        connection_id: str,
        source_server: str,
        source_port: int,
        local_sequence: int,
        parse_status: str = "ok",
        parse_error: str = "",
    ) -> "FrameRecord":
        try:
            decoded = payload.decode("utf-8")
            decode_error = ""
        except UnicodeDecodeError as exc:
            decoded = payload.decode("utf-8", errors="replace")
            decode_error = str(exc)
            if parse_status == "ok":
                parse_status = "decode_error"
        now_wall = time.time_ns()
        now_mono = time.monotonic_ns()
        return cls(
            raw_bytes=payload,
            decoded_text=decoded,
            decode_error=decode_error,
            raw_sha256=hashlib.sha256(payload).hexdigest(),
            frame_length=len(payload),
            connection_id=connection_id,
            source_server=source_server,
            source_port=source_port,
            receive_wall_time_ns=now_wall,
            receive_monotonic_ns=now_mono,
            local_sequence=local_sequence,
            parse_status=parse_status,
            parse_error=parse_error,
        )

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "raw_bytes_hex": self.raw_bytes.hex(),
            "decoded_text": self.decoded_text,
            "decode_error": self.decode_error,
            "raw_sha256": self.raw_sha256,
            "frame_length": self.frame_length,
            "connection_id": self.connection_id,
            "source_server": self.source_server,
            "source_port": self.source_port,
            "receive_wall_time_ns": self.receive_wall_time_ns,
            "receive_monotonic_ns": self.receive_monotonic_ns,
            "local_sequence": self.local_sequence,
            "parse_status": self.parse_status,
            "parse_error": self.parse_error,
            "metadata": dict(self.metadata),
        }


class ByteFrameParser:
    """Incremental byte parser for `<...>` frames.

    It keeps residual partial frames, tolerates noise before a frame, and never
    decodes a raw recv chunk with `errors=ignore` before boundaries are found.
    """

    def __init__(
        self,
        *,
        connection_id: str,
        source_server: str,
        source_port: int,
        max_frame_bytes: int = 1_048_576,
    ) -> None:
        self.connection_id = connection_id
        self.source_server = source_server
        self.source_port = int(source_port)
        self.max_frame_bytes = int(max_frame_bytes)
        self._buffer = bytearray()
        self._sequence = 0
        self.dropped_noise_bytes = 0
        self.oversize_frames = 0

    @property
    def residual_bytes(self) -> bytes:
        return bytes(self._buffer)

    def feed(self, chunk: bytes) -> list[FrameRecord]:
        if not isinstance(chunk, (bytes, bytearray)):
            raise TypeError("chunk must be bytes")
        self._buffer.extend(chunk)
        frames: list[FrameRecord] = []
        while True:
            start = self._buffer.find(b"<")
            if start < 0:
                self.dropped_noise_bytes += len(self._buffer)
                self._buffer.clear()
                break
            if start > 0:
                self.dropped_noise_bytes += start
                del self._buffer[:start]
            end = self._buffer.find(b">", 1)
            if end < 0:
                if len(self._buffer) > self.max_frame_bytes:
                    payload = bytes(self._buffer[: self.max_frame_bytes])
                    del self._buffer[: self.max_frame_bytes]
                    self.oversize_frames += 1
                    frames.append(self._make_record(payload, "frame_too_long", "missing closing delimiter"))
                break
            payload = bytes(self._buffer[1:end])
            del self._buffer[: end + 1]
            if payload == b"":
                frames.append(self._make_record(payload, "empty_frame", "empty frame"))
            elif len(payload) > self.max_frame_bytes:
                self.oversize_frames += 1
                frames.append(self._make_record(payload, "frame_too_long", "frame exceeds max_frame_bytes"))
            else:
                frames.append(self._make_record(payload, "ok", ""))
        return frames

    def flush_partial(self) -> FrameRecord | None:
        if not self._buffer:
            return None
        payload = bytes(self._buffer)
        self._buffer.clear()
        return self._make_record(payload, "partial_frame", "residual bytes at shutdown")

    def _make_record(self, payload: bytes, status: str, error: str) -> FrameRecord:
        self._sequence += 1
        return FrameRecord.from_payload(
            payload,
            connection_id=self.connection_id,
            source_server=self.source_server,
            source_port=self.source_port,
            local_sequence=self._sequence,
            parse_status=status,
            parse_error=error,
        )

