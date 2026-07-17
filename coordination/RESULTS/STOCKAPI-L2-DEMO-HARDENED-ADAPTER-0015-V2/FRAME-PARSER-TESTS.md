# Frame Parser Tests

Covered cases:

- half frame split across chunks
- sticky multiple frames in one chunk
- noise before frame
- empty frame
- oversized frame
- residual partial frame flush
- corrupt UTF-8 bytes with decode error captured
- raw SHA256, raw bytes hex, frame length, connection id, port, wall clock, monotonic clock, local sequence

The parser works on bytes first and never decodes a raw recv chunk with `errors=ignore` before frame boundaries are identified.
