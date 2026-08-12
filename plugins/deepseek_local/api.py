"""Operation-panel HTTP handlers for deepseek_local (Plugin OpenAPI).

These handlers are declared by the plugin through ``get_plugin_api()`` and
dispatched by the core via ``/api/plugins/deepseek_local/api/...``. They act on
plugin-directory-level state (auth_state.json, conversation_links.json), not on
any single provider instance.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import threading
import time as _time

from src.chitrika.plugins.api import PluginAPI, PluginEndpoint

from provider import (
    DEFAULT_AUTH_STATE,
    clear_link_store,
    link_store_status,
)

logger = logging.getLogger("chitrika.plugins.deepseek_local.api")

LOGIN_COMMAND = "uv run python plugins/deepseek_local/login.py"
DEEPSEEK_URL = "https://chat.deepseek.com"
LOGIN_TIMEOUT_SECONDS = 300

_login_thread: threading.Thread | None = None

# Latest login/install progress, polled by the config form to render a progress bar.
_login_progress: dict = {"stage": "idle", "message": "", "percent": None}
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _set_progress(stage: str, message: str, percent: float | None = None) -> None:
    global _login_progress
    _login_progress = {
        "stage": stage,
        "message": message,
        "percent": percent,
        "updated_at": _time.time(),
    }


def _extract_percent(line: str) -> float | None:
    match = _PERCENT_RE.search(line)
    return float(match.group(1)) if match else None


def _looks_like_token(value: object) -> bool:
    """Heuristic: is this localStorage value actually a login token?

    AWS WAF stores challenge markers like ``aws_waf_token_challenge_attempts``
    whose value is ``{"attempts":1,...}`` — those must never count as auth.
    """
    if not isinstance(value, str) or not value.strip() or value.strip() == "null":
        return False
    stripped = value.strip()
    try:
        parsed = json.loads(stripped)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, dict):
        for field in ("token", "access_token", "value"):
            candidate = parsed.get(field)
            if isinstance(candidate, str) and len(candidate) > 10:
                return True
        return False
    if isinstance(parsed, str):
        # JSON-encoded string token (DeepSeek stores the JWT like this sometimes)
        return len(parsed) > 20
    return len(stripped) > 20


def _has_auth(page) -> bool:
    """True once the DeepSeek page holds a real login token in localStorage."""
    try:
        keys = page.evaluate("() => Object.keys(localStorage)")
    except Exception as exc:
        logger.debug("relogin: _has_auth evaluate failed: %s", exc)
        return False
    if not isinstance(keys, list):
        logger.debug("relogin: _has_auth keys not a list: %r", keys)
        return False
    for key in keys:
        if not isinstance(key, str):
            continue
        lower = key.lower()
        if "waf" in lower:
            # AWS WAF challenge markers are never a login token.
            continue
        if "token" not in lower and "auth" not in lower:
            continue
        try:
            value = page.evaluate("(k) => localStorage.getItem(k)", key)
        except Exception as exc:
            logger.debug("relogin: getItem(%r) failed: %s", key, exc)
            continue
        if _looks_like_token(value):
            logger.info("relogin: auth token found in localStorage key=%r", key)
            return True
        logger.debug("relogin: key=%r has value but not a valid token: %r", key, (value or "")[:80])
    logger.debug("relogin: no auth token yet, localStorage keys=%r", keys)
    return False


def _ensure_playwright() -> bool:
    """Make sure the playwright python package + chromium are installed.

    Called from the background login thread; installs on demand when missing.
    Progress is published to ``_login_progress`` for the config form's progress bar.
    """
    try:
        import playwright  # noqa: F401

        logger.info("relogin: playwright already installed")
        return True
    except ImportError:
        pass

    logger.info("relogin: playwright not found — installing…")
    _set_progress("installing", "正在安装 playwright 包…")
    install_ok = False
    for command in (
        ["uv", "pip", "install", "playwright"],
        [sys.executable, "-m", "pip", "install", "playwright"],
    ):
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=600)
            install_ok = True
            break
        except Exception:
            logger.exception("DeepSeek relogin: pip install playwright failed")
    if not install_ok:
        _set_progress("failed", "playwright 包安装失败")
        return False

    _set_progress("downloading", "正在下载 Chromium…", 0)
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            stripped = line.strip()
            percent = _extract_percent(stripped)
            _set_progress("downloading", stripped[:120] or "正在下载 Chromium…", percent)
        proc.wait(timeout=1800)
        if proc.returncode != 0:
            _set_progress("failed", "Chromium 下载失败（网络或权限问题）")
            logger.error("DeepSeek relogin: chromium install exited %s", proc.returncode)
            return False
    except Exception:
        logger.exception("DeepSeek relogin: chromium install failed")
        _set_progress("failed", "Chromium 下载失败")
        return False

    _set_progress("installing", "playwright 已就绪", 100)
    logger.info("DeepSeek relogin: playwright installed")
    return True


def _run_login() -> None:
    """Open a browser window and save auth_state once the user logs in.

    Runs in a background thread so the API call returns immediately; playwright
    is auto-installed if missing, and the page is polled until a token appears
    (or the timeout expires). Progress is exposed via ``GET /auth/login-progress``.
    """
    _set_progress("preparing", "正在准备登录…")
    if not _ensure_playwright():
        logger.error("DeepSeek relogin: could not install playwright")
        return

    from playwright.sync_api import sync_playwright

    _set_progress("opening", "正在打开浏览器窗口…", 100)
    out = DEFAULT_AUTH_STATE
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = None
        try:
            logger.info("relogin: launching chromium (headless=False)")
            browser = playwright.chromium.launch(headless=False)
            logger.info("relogin: browser launched")
            context = browser.new_context()
            page = context.new_page()
            logger.info("relogin: goto %s (wait_until=commit)", DEEPSEEK_URL)
            page.goto(DEEPSEEK_URL, wait_until="commit", timeout=60000)
            logger.info("relogin: goto returned url=%s", page.url)
            _set_progress("waiting", "请在浏览器里登录 DeepSeek…")
            deadline = _time.time() + LOGIN_TIMEOUT_SECONDS
            while _time.time() < deadline:
                has = _has_auth(page)
                if has:
                    logger.info("relogin: auth detected, saving storage_state to %s", out)
                    context.storage_state(path=str(out))
                    # New context = fresh cookies (no old account). Clear the
                    # web-session reuse links too, so a different account never
                    # reuses the previous account's chat sessions.
                    cleared = clear_link_store()
                    logger.info("relogin: auth_state saved to %s; cleared %d conversation links", out, cleared)
                    _set_progress("done", f"登录成功，auth_state 已保存，会话链已重置（清空 {cleared} 条）", 100)
                    return
                _time.sleep(2)
            _set_progress("failed", "登录超时，请重试")
            logger.warning("relogin: timed out waiting for login after %ss", LOGIN_TIMEOUT_SECONDS)
        except Exception as exc:
            logger.exception("relogin: browser flow failed")
            _set_progress("failed", f"打开浏览器/登录失败: {exc}")
        finally:
            if browser is not None:
                try:
                    browser.close()
                    logger.info("relogin: browser closed")
                except Exception as exc:
                    logger.warning("relogin: error closing browser: %s", exc)


def login_busy() -> bool:
    return _login_thread is not None and _login_thread.is_alive()


def _auth_status() -> dict:
    auth_path = DEFAULT_AUTH_STATE
    if not auth_path.exists():
        return {
            "path": str(auth_path),
            "exists": False,
            "ready": False,
            "hint": "还没有登录 DeepSeek Web",
        }
    try:
        from ds_web.client import DeepSeekClient

        status = DeepSeekClient(auth_path).get_auth_status()
    except Exception as exc:  # damaged / unreadable auth_state
        return {
            "path": str(auth_path),
            "exists": True,
            "ready": False,
            "error": str(exc),
            "hint": "auth_state 无法读取，请重新登录",
        }
    status["path"] = str(auth_path)
    status["hint"] = "已登录" if status.get("ready") else "auth_state 不完整，请重新登录"
    return status


def handle_status(query: dict, body: dict) -> dict:
    return {
        "auth": _auth_status(),
        "sessions": link_store_status(),
        "login": {
            "busy": login_busy(),
            "command": LOGIN_COMMAND,
            "hint": "登录会打开浏览器，完成后 auth_state.json 保存到 data/ 目录",
        },
    }


def handle_relogin(query: dict, body: dict) -> dict:
    global _login_thread
    if login_busy():
        return {"ok": False, "busy": True, "message": "登录窗口已经打开，请先在浏览器里完成登录"}
    _set_progress("preparing", "正在准备登录…")
    _login_thread = threading.Thread(target=_run_login, daemon=True)
    _login_thread.start()
    return {
        "ok": True,
        "started": True,
        "progress_endpoint": "/auth/login-progress",
        "message": "正在准备登录…如果缺少 playwright 会自动安装（首次要下载浏览器），装完自动打开浏览器窗口",
    }


def handle_login_progress(query: dict, body: dict) -> dict:
    return dict(_login_progress)


def handle_sessions_clear(query: dict, body: dict) -> dict:
    cleared = clear_link_store()
    return {"ok": True, "cleared_links": cleared}


def get_plugin_api() -> PluginAPI:
    return PluginAPI(
        endpoints=(
            PluginEndpoint(
                method="GET",
                path="/status",
                summary="登录状态与会话统计",
                description="查看 DeepSeek Web 登录状态与当前复用的 web 会话链数量",
            ),
            PluginEndpoint(
                method="POST",
                path="/auth/relogin",
                summary="重新登录",
                description="打开浏览器窗口重新登录 DeepSeek Web，登录成功自动保存 auth_state",
            ),
            PluginEndpoint(
                method="GET",
                path="/auth/login-progress",
                summary="登录进度",
                description="轮询重新登录/安装进度（下载百分比）",
            ),
            PluginEndpoint(
                method="POST",
                path="/sessions/clear",
                summary="清空会话复用链",
                description="重置 conversation_links.json，下次对话会新建 web 会话",
            ),
        ),
        handlers={
            "GET /status": handle_status,
            "POST /auth/relogin": handle_relogin,
            "GET /auth/login-progress": handle_login_progress,
            "POST /sessions/clear": handle_sessions_clear,
        },
    )
