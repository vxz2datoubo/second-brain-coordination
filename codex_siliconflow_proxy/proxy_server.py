from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse


SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
PROXY_MASTER_KEY = os.environ.get("CODEX_SILICONFLOW_PROXY_KEY", "")
UPSTREAM_MODEL = "deepseek-ai/DeepSeek-V4-Pro"
PUBLIC_MODEL_NAME = "deepseek-v4-pro"

app = FastAPI(title="Codex SiliconFlow Responses Proxy")
response_history: dict[str, list[dict[str, Any]]] = {}


def _require_auth(authorization: str | None) -> None:
    expected = f"Bearer {PROXY_MASTER_KEY}"
    if not PROXY_MASTER_KEY or authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _response_id() -> str:
    return f"resp_{uuid.uuid4().hex}"


def _item_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now() -> int:
    return int(time.time())


def _build_output_message(text: str) -> dict[str, Any]:
    return {
        "id": _item_id("msg"),
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [
            {
                "type": "output_text",
                "text": text,
                "annotations": [],
            }
        ],
    }


def _build_output_tool_call(name: str, arguments: str, call_id: str) -> dict[str, Any]:
    return {
        "id": _item_id("fc"),
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": arguments,
        "status": "completed",
    }


def _usage_from_completion(data: dict[str, Any]) -> dict[str, int]:
    usage = data.get("usage") or {}
    return {
        "input_tokens": int(usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def _message_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return ""

    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        part_type = part.get("type")
        if part_type in {"input_text", "output_text", "text"}:
            text_parts.append(str(part.get("text") or ""))
        elif part_type == "input_image":
            image_url = part.get("image_url") or ""
            text_parts.append(f"[image:{image_url}]")
    return "".join(text_parts)


def _responses_input_to_messages(input_value: Any) -> list[dict[str, Any]]:
    if isinstance(input_value, str):
        return [{"role": "user", "content": input_value}]

    messages: list[dict[str, Any]] = []
    if not isinstance(input_value, list):
        return messages

    for item in input_value:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")
        if item_type == "function_call_output":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.get("call_id"),
                    "content": str(item.get("output") or ""),
                }
            )
            continue

        role = item.get("role")
        if role in {"system", "user", "assistant", "developer"}:
            content = _message_text_from_content(item.get("content"))
            if role == "developer":
                role = "system"
            messages.append({"role": role, "content": content})

    return messages


def _responses_tools_to_chat_tools(tools: Any) -> list[dict[str, Any]] | None:
    if not isinstance(tools, list):
        return None

    mapped: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict) or tool.get("type") != "function":
            continue

        name = tool.get("name")
        if not name and isinstance(tool.get("function"), dict):
            name = tool["function"].get("name")

        description = tool.get("description")
        if description is None and isinstance(tool.get("function"), dict):
            description = tool["function"].get("description")

        parameters = tool.get("parameters")
        if parameters is None and isinstance(tool.get("function"), dict):
            parameters = tool["function"].get("parameters")

        mapped.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description or "",
                    "parameters": parameters or {"type": "object", "properties": {}},
                },
            }
        )

    return mapped or None


def _build_upstream_payload(request_body: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    messages: list[dict[str, Any]] = []

    previous_response_id = request_body.get("previous_response_id")
    if previous_response_id:
        messages.extend(response_history.get(str(previous_response_id), []))

    instructions = request_body.get("instructions")
    if instructions:
        messages.append({"role": "system", "content": str(instructions)})

    messages.extend(_responses_input_to_messages(request_body.get("input")))

    payload: dict[str, Any] = {
        "model": UPSTREAM_MODEL,
        "messages": messages,
    }

    if request_body.get("max_output_tokens") is not None:
        payload["max_tokens"] = request_body["max_output_tokens"]

    if request_body.get("temperature") is not None:
        payload["temperature"] = request_body["temperature"]

    mapped_tools = _responses_tools_to_chat_tools(request_body.get("tools"))
    if mapped_tools:
        payload["tools"] = mapped_tools

    tool_choice = request_body.get("tool_choice")
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    return payload, messages


def _build_response_object(
    *,
    response_id: str,
    output_items: list[dict[str, Any]],
    usage: dict[str, int],
) -> dict[str, Any]:
    output_text = ""
    for item in output_items:
        if item.get("type") == "message":
            content = item.get("content") or []
            for part in content:
                if part.get("type") == "output_text":
                    output_text += str(part.get("text") or "")

    return {
        "id": response_id,
        "object": "response",
        "created_at": _now(),
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "model": PUBLIC_MODEL_NAME,
        "output": output_items,
        "parallel_tool_calls": True,
        "temperature": None,
        "tool_choice": "auto",
        "tools": [],
        "top_p": None,
        "max_output_tokens": None,
        "previous_response_id": None,
        "reasoning": {},
        "store": False,
        "text": {"format": {"type": "text"}},
        "usage": usage,
        "user": None,
        "metadata": {},
        "output_text": output_text,
    }


def _store_history(
    response_id: str,
    base_messages: list[dict[str, Any]],
    output_items: list[dict[str, Any]],
) -> None:
    history = list(base_messages)
    for item in output_items:
        if item.get("type") == "message":
            text = ""
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    text += str(part.get("text") or "")
            history.append({"role": "assistant", "content": text})
    response_history[response_id] = history


async def _chat_completion(payload: dict[str, Any], stream: bool) -> httpx.Response:
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{SILICONFLOW_BASE_URL}/chat/completions",
            headers=headers,
            json={**payload, "stream": stream},
        )
        response.raise_for_status()
        return response


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


@app.get("/health/liveliness")
async def liveliness() -> JSONResponse:
    return JSONResponse("I'm alive!")


@app.get("/v1/models")
async def models(authorization: str | None = Header(default=None, alias="Authorization")) -> JSONResponse:
    _require_auth(authorization)
    return JSONResponse(
        {
            "object": "list",
            "data": [
                {
                    "id": PUBLIC_MODEL_NAME,
                    "object": "model",
                    "created": 0,
                    "owned_by": "siliconflow",
                }
            ],
        }
    )


@app.post("/v1/responses")
async def create_response(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Any:
    _require_auth(authorization)
    request_body = await request.json()
    payload, base_messages = _build_upstream_payload(request_body)
    should_stream = bool(request_body.get("stream"))
    response_id = _response_id()

    if not should_stream:
        upstream = await _chat_completion(payload, stream=False)
        data = upstream.json()
        choice = ((data.get("choices") or [{}])[0]) or {}
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []

        output_items: list[dict[str, Any]] = []
        if tool_calls:
            for tool_call in tool_calls:
                function = tool_call.get("function") or {}
                output_items.append(
                    _build_output_tool_call(
                        str(function.get("name") or ""),
                        str(function.get("arguments") or ""),
                        str(tool_call.get("id") or _item_id("call")),
                    )
                )
        else:
            output_items.append(_build_output_message(str(message.get("content") or "")))

        usage = _usage_from_completion(data)
        response_object = _build_response_object(
            response_id=response_id,
            output_items=output_items,
            usage=usage,
        )
        _store_history(response_id, base_messages, output_items)
        return JSONResponse(response_object)

    async def stream_events() -> Any:
        text_parts: list[str] = []
        tool_calls: dict[int, dict[str, str]] = {}
        message_item_id = _item_id("msg")

        yield _sse(
            "response.created",
            {
                "type": "response.created",
                "response": {
                    "id": response_id,
                    "object": "response",
                    "created_at": _now(),
                    "model": PUBLIC_MODEL_NAME,
                    "status": "in_progress",
                    "output": [],
                },
            },
        )

        headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{SILICONFLOW_BASE_URL}/chat/completions",
                headers=headers,
                json={**payload, "stream": True},
            ) as upstream:
                upstream.raise_for_status()

                emitted_message_added = False
                async for raw_line in upstream.aiter_lines():
                    if not raw_line or not raw_line.startswith("data: "):
                        continue

                    data_str = raw_line[6:]
                    if data_str == "[DONE]":
                        break

                    chunk = json.loads(data_str)
                    choice = ((chunk.get("choices") or [{}])[0]) or {}
                    delta = choice.get("delta") or {}

                    tool_deltas = delta.get("tool_calls") or []
                    if tool_deltas:
                        for tool_delta in tool_deltas:
                            index = int(tool_delta.get("index") or 0)
                            tool_state = tool_calls.setdefault(
                                index,
                                {
                                    "id": str(tool_delta.get("id") or _item_id("call")),
                                    "name": "",
                                    "arguments": "",
                                    "item_id": _item_id("fc"),
                                },
                            )

                            if tool_delta.get("id"):
                                tool_state["id"] = str(tool_delta["id"])

                            function = tool_delta.get("function") or {}
                            if function.get("name"):
                                tool_state["name"] = str(function["name"])

                            if not tool_state.get("emitted_added"):
                                yield _sse(
                                    "response.output_item.added",
                                    {
                                        "type": "response.output_item.added",
                                        "output_index": index,
                                        "item": {
                                            "id": tool_state["item_id"],
                                            "type": "function_call",
                                            "call_id": tool_state["id"],
                                            "name": tool_state["name"],
                                            "arguments": "",
                                            "status": "in_progress",
                                        },
                                    },
                                )
                                tool_state["emitted_added"] = "1"

                            arguments_delta = str(function.get("arguments") or "")
                            if arguments_delta:
                                tool_state["arguments"] += arguments_delta
                                yield _sse(
                                    "response.function_call_arguments.delta",
                                    {
                                        "type": "response.function_call_arguments.delta",
                                        "item_id": tool_state["item_id"],
                                        "output_index": index,
                                        "delta": arguments_delta,
                                    },
                                )
                        continue

                    content_delta = str(delta.get("content") or "")
                    if content_delta:
                        if not emitted_message_added:
                            emitted_message_added = True
                            yield _sse(
                                "response.output_item.added",
                                {
                                    "type": "response.output_item.added",
                                    "output_index": 0,
                                    "item": {
                                        "id": message_item_id,
                                        "type": "message",
                                        "role": "assistant",
                                        "status": "in_progress",
                                        "content": [],
                                    },
                                },
                            )
                        text_parts.append(content_delta)
                        yield _sse(
                            "response.output_text.delta",
                            {
                                "type": "response.output_text.delta",
                                "item_id": message_item_id,
                                "output_index": 0,
                                "content_index": 0,
                                "delta": content_delta,
                            },
                        )

        output_items: list[dict[str, Any]] = []
        if tool_calls:
            for index in sorted(tool_calls):
                tool_state = tool_calls[index]
                yield _sse(
                    "response.function_call_arguments.done",
                    {
                        "type": "response.function_call_arguments.done",
                        "item_id": tool_state["item_id"],
                        "output_index": index,
                        "arguments": tool_state["arguments"],
                    },
                )
                output_item = _build_output_tool_call(
                    tool_state["name"],
                    tool_state["arguments"],
                    tool_state["id"],
                )
                output_item["id"] = tool_state["item_id"]
                output_items.append(output_item)
                yield _sse(
                    "response.output_item.done",
                    {
                        "type": "response.output_item.done",
                        "output_index": index,
                        "item": output_item,
                    },
                )
        else:
            text = "".join(text_parts)
            output_item = _build_output_message(text)
            output_item["id"] = message_item_id
            output_items.append(output_item)
            yield _sse(
                "response.output_text.done",
                {
                    "type": "response.output_text.done",
                    "item_id": message_item_id,
                    "output_index": 0,
                    "content_index": 0,
                    "text": text,
                },
            )
            yield _sse(
                "response.output_item.done",
                {
                    "type": "response.output_item.done",
                    "output_index": 0,
                    "item": output_item,
                },
            )

        response_object = _build_response_object(
            response_id=response_id,
            output_items=output_items,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        _store_history(response_id, base_messages, output_items)
        yield _sse(
            "response.completed",
            {
                "type": "response.completed",
                "response": response_object,
            },
        )

    return StreamingResponse(stream_events(), media_type="text/event-stream")
