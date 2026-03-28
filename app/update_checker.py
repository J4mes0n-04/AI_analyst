"""Optional online version check via JSON URL (env or default)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from app import __version__


def check_for_updates(timeout: float = 8.0) -> tuple[bool, str, str | None]:
    """
    Returns (update_available, message, download_url).
    Set AI_ANALYST_UPDATE_JSON to URL returning {\"latest\": \"1.0.1\", \"url\": \"https://...\"}
    """
    url = os.environ.get("AI_ANALYST_UPDATE_JSON", "").strip()
    if not url:
        return False, "Проверка обновлений: задайте переменную окружения AI_ANALYST_UPDATE_JSON с URL JSON.", None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Analyst-UpdateCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        latest = str(data.get("latest", "")).strip()
        dl = data.get("url")
        if not latest:
            return False, "Ответ сервера не содержит поле latest.", None
        if _semver_tuple(latest) > _semver_tuple(__version__):
            return True, f"Доступна новая версия: {latest} (у вас {__version__}).", str(dl) if dl else None
        return False, f"У вас актуальная версия ({__version__}).", None
    except urllib.error.URLError as e:
        return False, f"Сеть недоступна или URL некорректен: {e}", None
    except (json.JSONDecodeError, ValueError) as e:
        return False, f"Некорректный JSON: {e}", None


def _semver_tuple(v: str) -> tuple[int, int, int]:
    parts = v.replace("v", "").split(".")
    nums: list[int] = []
    for p in parts[:3]:
        try:
            nums.append(int("".join(ch for ch in p if ch.isdigit()) or "0"))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]
