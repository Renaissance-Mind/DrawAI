from __future__ import annotations

import json
import sys
from pathlib import Path

from drawai.acp_agent import invoke_acp_agent_svg_text, invoke_acp_agent_text


FAKE_ACP_SERVER = r"""
import json
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])


def write_log(payload):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def emit(payload):
    print(json.dumps(payload, separators=(",", ":")), flush=True)


def read_response(expected_id):
    while True:
        line = sys.stdin.readline()
        if not line:
            raise SystemExit(1)
        message = json.loads(line)
        write_log({"from_client": message})
        if message.get("id") == expected_id:
            return message


def output_content(path):
    if path.suffix == ".svg":
        return '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="8"><rect width="12" height="8"/></svg>\n'
    return '{"ok": true}\n'


for line in sys.stdin:
    message = json.loads(line)
    write_log({"from_client": message})
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        emit(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": 1,
                    "agentCapabilities": {
                        "promptCapabilities": {
                            "image": True,
                            "audio": False,
                            "embeddedContext": False,
                        }
                    },
                    "agentInfo": {"name": "fake-acp-agent", "version": "1.0.0"},
                    "authMethods": [],
                },
            }
        )
    elif method == "session/new":
        emit({"jsonrpc": "2.0", "id": request_id, "result": {"sessionId": "sess_fake"}})
    elif method == "session/prompt":
        server_request_id = "srv-write-output"
        emit(
            {
                "jsonrpc": "2.0",
                "id": server_request_id,
                "method": "fs/write_text_file",
                "params": {
                    "sessionId": "sess_fake",
                    "path": str(output_path),
                    "content": output_content(output_path),
                },
            }
        )
        write_response = read_response(server_request_id)
        write_log({"write_response_result": write_response.get("result")})
        emit(
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": "sess_fake",
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "messageId": "msg_fake",
                        "content": {"type": "text", "text": "wrote requested output\n"},
                    },
                },
            }
        )
        emit({"jsonrpc": "2.0", "id": request_id, "result": {"stopReason": "end_turn"}})
    elif method == "session/close":
        emit({"jsonrpc": "2.0", "id": request_id, "result": {}})
    elif request_id is not None:
        emit({"jsonrpc": "2.0", "id": request_id, "result": {}})
"""


def test_acp_agent_writes_svg_via_client_filesystem(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    output_svg_path = tmp_path / "out" / "semantic.svg"
    response_path = tmp_path / "out" / "response.txt"
    log_path = tmp_path / "fake_acp.jsonl"
    trace_path = tmp_path / "trace.jsonl"

    svg = invoke_acp_agent_svg_text(
        image_paths=image_path,
        prompt="Draw the sample.",
        task_name="test.acp.svg",
        runtime_config={
            "provider": "acp-agent",
            "connection_id": "kimi",
            "timeout_seconds": 5,
            "acp": {
                "agent": "kimi",
                "command": [sys.executable, "-c", FAKE_ACP_SERVER, str(log_path), str(output_svg_path)],
            },
        },
        trace_path=trace_path,
        isolated_cwd=tmp_path,
        output_svg_path=output_svg_path,
        output_response_path=response_path,
    )

    assert svg.startswith("<svg")
    assert output_svg_path.read_text(encoding="utf-8").strip() == svg
    assert response_path.read_text(encoding="utf-8") == "wrote requested output\n"
    messages = [json.loads(line)["from_client"] for line in log_path.read_text(encoding="utf-8").splitlines() if "from_client" in line]
    assert [message["method"] for message in messages if "method" in message][:3] == [
        "initialize",
        "session/new",
        "session/prompt",
    ]
    prompt_request = next(message for message in messages if message.get("method") == "session/prompt")
    blocks = prompt_request["params"]["prompt"]
    assert blocks[0]["type"] == "text"
    assert "Required SVG output path" in blocks[0]["text"]
    assert any(block["type"] == "image" and block["mimeType"] == "image/png" for block in blocks)
    trace_events = [json.loads(line)["type"] for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert "acp_client_method" in trace_events
    assert "acp_text_response" in trace_events


def test_acp_agent_text_invocation_allows_declared_json_output(tmp_path: Path) -> None:
    output_path = tmp_path / "output" / "result.json"
    log_path = tmp_path / "fake_acp.jsonl"

    text = invoke_acp_agent_text(
        image_paths=(),
        prompt="Write output/result.json.",
        task_name="test.acp.text",
        runtime_config={
            "provider": "acp-agent",
            "connection_id": "kimi",
            "timeout_seconds": 5,
            "acp": {
                "agent": "kimi",
                "command": [sys.executable, "-c", FAKE_ACP_SERVER, str(log_path), str(output_path)],
            },
        },
        isolated_cwd=tmp_path,
    )

    assert text == "wrote requested output\n"
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"ok": True}
