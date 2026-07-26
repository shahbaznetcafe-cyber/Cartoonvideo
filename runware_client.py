"""Shared Runware REST transport for media and Phase 7 text generation.

The API key never leaves this backend module. Error messages are redacted before
they are returned to Flask/UI callers.
"""
from __future__ import annotations

import json
import re
import time
import uuid

import requests

import config


TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class RunwareError(RuntimeError):
    def __init__(self, message, *, status=None, retryable=False, code="runware_error"):
        super().__init__(redact_sensitive(message))
        self.status = status
        self.retryable = retryable
        self.code = code


class RunwareCancelled(RunwareError):
    def __init__(self):
        super().__init__("Runware request cancelled", retryable=False, code="cancelled")


def redact_sensitive(value):
    text = str(value or "")
    key = str(getattr(config, "RUNWARE_API_KEY", "") or "")
    if key:
        text = text.replace(key, "[REDACTED]")
    text = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return text[:1200]


def _headers():
    if not config.RUNWARE_API_KEY:
        raise RunwareError("RUNWARE_API_KEY is not configured", code="missing_credentials")
    return {"Content-Type": "application/json",
            "Authorization": f"Bearer {config.RUNWARE_API_KEY}"}


def _cancelled(cancel_event):
    return bool(cancel_event and cancel_event.is_set())


def _request_json(url, payload, *, timeout=90, retries=0, cancel_event=None,
                  session=None, sleeper=time.sleep):
    client = session or requests
    attempts = 0
    while True:
        if _cancelled(cancel_event):
            raise RunwareCancelled()
        attempts += 1
        try:
            response = client.post(url, headers=_headers(), json=payload, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempts <= retries and not _cancelled(cancel_event):
                sleeper(min(8.0, 0.75 * (2 ** (attempts - 1))))
                continue
            raise RunwareError(f"Runware network error: {exc}", retryable=True,
                               code="network_error") from exc
        if _cancelled(cancel_event):
            raise RunwareCancelled()
        if response.status_code != 200:
            detail = redact_sensitive(getattr(response, "text", "")[:500])
            retryable = response.status_code in TRANSIENT_STATUS
            if retryable and attempts <= retries:
                retry_after = response.headers.get("Retry-After") if hasattr(response, "headers") else None
                try:
                    delay = min(10.0, max(0.5, float(retry_after)))
                except (TypeError, ValueError):
                    delay = min(8.0, 0.75 * (2 ** (attempts - 1)))
                sleeper(delay)
                continue
            raise RunwareError(f"Runware HTTP {response.status_code}: {detail}",
                               status=response.status_code, retryable=retryable,
                               code="http_error")
        try:
            return response.json(), attempts
        except (ValueError, json.JSONDecodeError) as exc:
            raise RunwareError("Runware returned malformed JSON", retryable=False,
                               code="malformed_response") from exc


def post_tasks_detailed(tasks, timeout=180, retries=0, cancel_event=None, session=None):
    body, attempts = _request_json(config.RUNWARE_ENDPOINT, tasks, timeout=timeout,
                                   retries=retries, cancel_event=cancel_event, session=session)
    if isinstance(body, dict) and body.get("errors"):
        errors = body.get("errors") or []
        message = "; ".join(str(item.get("message") if isinstance(item, dict) else item)
                            for item in errors)
        retryable = any(str(item.get("code", "")).lower() in
                        {"ratelimited", "timeout", "serviceunavailable"}
                        for item in errors if isinstance(item, dict))
        raise RunwareError(f"Runware task error: {message}", retryable=retryable,
                           code="task_error")
    data = body.get("data") if isinstance(body, dict) else None
    if not data:
        raise RunwareError("Runware returned an empty data array", code="empty_response")
    return {"data": data, "attempts": attempts}


def post_tasks(tasks, timeout=180):
    """Backward-compatible media/native API helper."""
    return post_tasks_detailed(tasks, timeout=timeout)["data"]


def chat_completion_detailed(payload, *, timeout=90, retries=0,
                             cancel_event=None, session=None):
    endpoint = config.RUNWARE_ENDPOINT.rstrip("/") + "/chat/completions"
    body, attempts = _request_json(endpoint, payload, timeout=timeout, retries=retries,
                                   cancel_event=cancel_event, session=session)
    try:
        message = body["choices"][0]["message"]
        text = message.get("content") or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise RunwareError("Runware chat response is missing choices/message/content",
                           code="malformed_response") from exc
    usage = body.get("usage") or {}
    return {
        "text": text,
        "responseId": body.get("id"),
        "model": body.get("model") or payload.get("model"),
        "finishReason": body.get("choices", [{}])[0].get("finish_reason"),
        "usage": usage,
        "cost": usage.get("cost"),
        "attempts": attempts,
        "transport": "openai_compatible",
    }


def stream_chat_completion(payload, *, timeout=90, cancel_event=None, session=None):
    """Yield OpenAI-compatible SSE text chunks and close promptly on cancellation."""
    client = session or requests
    endpoint = config.RUNWARE_ENDPOINT.rstrip("/") + "/chat/completions"
    request_payload = dict(payload, stream=True, stream_options={"include_usage": True})
    if _cancelled(cancel_event):
        raise RunwareCancelled()
    response = client.post(endpoint, headers=_headers(), json=request_payload,
                           timeout=timeout, stream=True)
    try:
        if response.status_code != 200:
            raise RunwareError(f"Runware HTTP {response.status_code}: {response.text[:500]}",
                               status=response.status_code,
                               retryable=response.status_code in TRANSIENT_STATUS)
        for raw_line in response.iter_lines(decode_unicode=True):
            if _cancelled(cancel_event):
                raise RunwareCancelled()
            line = str(raw_line or "").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                chunk = json.loads(data)
            except ValueError:
                raise RunwareError("Malformed Runware streaming event", code="malformed_response")
            choices = chunk.get("choices") or []
            if choices:
                content = (choices[0].get("delta") or {}).get("content")
                if content:
                    yield content
    finally:
        response.close()


def discover_models(search, *, limit=20, timeout=45):
    task = {"taskType": "modelSearch", "taskUUID": new_uuid(),
            "search": str(search)[:120], "visibility": "public",
            "limit": max(1, min(100, int(limit)))}
    result = post_tasks_detailed([task], timeout=timeout)["data"][0]
    return [{key: item.get(key) for key in ("name", "air", "capabilities", "provider")}
            for item in result.get("results", [])]


def new_uuid():
    return str(uuid.uuid4())
