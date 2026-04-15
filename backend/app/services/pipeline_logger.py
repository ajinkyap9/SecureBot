from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


def _resolve_remote_url(base_url: str, api_path: str) -> str:
    if not base_url:
        return ""
    normalized_base = base_url.rstrip("/") + "/"
    normalized_path = api_path.lstrip("/")
    return parse.urljoin(normalized_base, normalized_path)


def _append_json_line(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=True) + "\n"
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _post_json(url: str, payload: dict[str, Any], timeout_seconds: int = 4) -> None:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=timeout_seconds):  # nosec B310
        return


def write_pipeline_event(
    endpoint: str,
    mode: str,
    alert_id: str,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    """Persist pipeline event locally and optionally forward to external DB API."""

    settings = get_settings()
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")

    event = {
        "timestamp": now.isoformat(),
        "endpoint": endpoint,
        "mode": mode,
        "alert_id": str(alert_id or ""),
        "request": request_payload,
        "response": response_payload,
    }

    log_file = Path(settings.pipeline_log_storage_path) / f"{day}.jsonl"
    _append_json_line(log_file, event)

    forward_result = {
        "forwarded": False,
        "url": "",
        "error": "",
    }

    remote_url = _resolve_remote_url(
        settings.pipeline_log_db_api_url,
        settings.pipeline_log_db_api_path,
    )

    if settings.pipeline_log_forward_enabled and remote_url:
        try:
            _post_json(remote_url, event)
            forward_result["forwarded"] = True
            forward_result["url"] = remote_url
        except (error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
            forward_result["url"] = remote_url
            forward_result["error"] = str(exc)
            logger.warning("Pipeline log forwarding failed: %s", str(exc))

    return {
        "stored_path": str(log_file),
        **forward_result,
    }
