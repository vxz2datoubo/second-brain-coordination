"""A loopback-only, GET-only control console with polling recovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from .models import PortManifest, ValidationError, redact


def _primitive(value: Any) -> Any:
    if is_dataclass(value):
        return _primitive(asdict(value))
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_primitive(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


@dataclass
class ConsoleSnapshot:
    status: dict[str, Any]
    services: list[dict[str, Any]] = field(default_factory=list)
    ports: list[dict[str, Any]] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)
    revision: int = 1

    def payload(self, section: str) -> dict[str, Any]:
        values = {
            "status": self.status,
            "services": self.services,
            "ports": self.ports,
            "audit": self.audit,
        }
        return {"revision": self.revision, section: redact(_primitive(values[section]))}


UI_HTML = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>BrainOps</title>
<style>body{font-family:Segoe UI,sans-serif;margin:2rem;max-width:72rem}button{margin:.2rem}code{white-space:pre-wrap}</style>
</head><body><h1>BrainOps local control plane</h1>
<p id=\"connection\">connecting</p><p>Mode: read-only and shadow-only. No route will be dispatched.</p>
<section><button disabled>Global automation disabled</button><button disabled>Pause dispatch</button><button disabled>Safe stop</button><button disabled>Terminate fallback executor</button><button disabled>Emergency stop</button></section>
<h2>Observed state</h2><code id=\"state\"></code>
<script>
const state=document.getElementById('state'), connection=document.getElementById('connection');
async function sync(){try{const response=await fetch('/api/v1/status',{cache:'no-store'});if(!response.ok)throw Error('status');state.textContent=JSON.stringify(await response.json(),null,2);connection.textContent='connected and synchronized';}catch(_){connection.textContent='offline; polling recovery will retry';}}
sync(); setInterval(sync,5000);
</script></body></html>"""


class ReadOnlyControlServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler]) -> None:
        host, port = address
        PortManifest(port=port, bind_host=host)
        super().__init__(address, handler)


def make_handler(snapshot: ConsoleSnapshot) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                body = UI_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK.value)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            routes = {
                "/api/v1/status": "status",
                "/api/v1/services": "services",
                "/api/v1/ports": "ports",
                "/api/v1/audit": "audit",
            }
            section = routes.get(self.path)
            if section is None:
                self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(snapshot.payload(section))

        def do_POST(self) -> None:  # noqa: N802
            self._send_json({"error": "mutating_endpoints_disabled"}, HTTPStatus.METHOD_NOT_ALLOWED)

        def do_PUT(self) -> None:  # noqa: N802
            self.do_POST()

        def do_DELETE(self) -> None:  # noqa: N802
            self.do_POST()

    return Handler


def create_server(snapshot: ConsoleSnapshot, port: int = 32100) -> ReadOnlyControlServer:
    """Construct a server. Calling serve_forever remains an explicit manual action."""
    return ReadOnlyControlServer(("127.0.0.1", port), make_handler(snapshot))
