import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.config import Settings
from app.execution.factory import get_action_executor
from app.models import ProposedAction


@contextmanager
def webhook_server():
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            payload = self.rfile.read(length)
            received.append(json.loads(payload))
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield received, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()



def test_webhook_executor_posts_normalized_envelope():
    action = ProposedAction(
        id=7,
        request_id=3,
        triage_id=2,
        action_type="create_task",
        title="Create task",
        payload_json='{"title": "Follow up", "priority": "High"}',
    )
    with webhook_server() as (received, sink_url):
        executor = get_action_executor(
            Settings(execution_mode="webhook", webhook_sink_url=sink_url, webhook_timeout_seconds=2)
        )
        result = executor.execute(action)
    assert result.success is True
    assert result.output["response_status"] == 200
    assert received == [
        {
            "request_id": 3,
            "action_id": 7,
            "action_type": "create_task",
            "title": "Create task",
            "payload": {"title": "Follow up", "priority": "High"},
        }
    ]
