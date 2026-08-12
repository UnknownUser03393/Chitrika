"""HTTP client for chat.deepseek.com using browser storage-state auth."""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

import requests

from .pow import parse_deepseek_challenge, solve_deepseek_challenge

BASE_URL = "https://chat.deepseek.com"
_MODULE_DIR = Path(__file__).resolve().parent
CPP_SOLVER_PATH = _MODULE_DIR / "deepseek_hash_v1.exe"

MODEL_TYPE_ALIASES = {
    "default": "default",
    "fast": "default",
    "expert": "expert",
    "deepseek-reasoner": "expert",
    "reasoner": "expert",
    "vision": "vision",
    "deepseek-chat": "default",
}


def normalize_model_type(model_type, default_model_type="default"):
    normalized = MODEL_TYPE_ALIASES.get(model_type, model_type)
    if not normalized:
        return default_model_type or "default"
    return normalized


class DeepSeekClient:
    def __init__(self, auth_state_path: str | Path):
        self.auth_state_path = Path(auth_state_path)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept": "*/*",
                "content-type": "application/json",
                "origin": BASE_URL,
                "referer": f"{BASE_URL}/",
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
                ),
                "x-client-bundle-id": "com.deepseek.chat",
                "x-client-locale": "zh_CN",
                "x-client-platform": "web",
                "x-client-timezone-offset": "28800",
                "x-client-version": "2.3.0",
            }
        )
        self.did = None
        self.model_settings = None
        self._load_auth_state(self.auth_state_path)

    def _load_auth_state(self, auth_state_path: Path) -> None:
        state = json.loads(auth_state_path.read_text(encoding="utf-8"))

        for cookie in state.get("cookies", []):
            domain = cookie.get("domain", "")
            if "deepseek.com" not in domain:
                continue
            self.session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=domain,
                path=cookie.get("path", "/"),
            )

        token = self._find_token(state)
        if token:
            self.session.headers["authorization"] = f"Bearer {token}"

        settings_token = self._find_settings_token(state)
        if settings_token:
            self.session.headers["x-settings-token"] = settings_token

        self.did = self._find_did(state)
        self.session.headers.update(self._find_extra_headers(state))

    def _find_token(self, state):
        for origin in state.get("origins", []):
            if origin.get("origin") != BASE_URL:
                continue
            for item in origin.get("localStorage", []):
                key = item.get("name", "").lower()
                value = item.get("value", "")
                if "token" in key and value and value != "null":
                    try:
                        parsed = json.loads(value)
                    except json.JSONDecodeError:
                        return value
                    if isinstance(parsed, str):
                        return parsed
                    if isinstance(parsed, dict):
                        for candidate_key in ("token", "access_token", "value"):
                            candidate = parsed.get(candidate_key)
                            if isinstance(candidate, str) and candidate:
                                return candidate
        return None

    def _find_did(self, state):
        for origin in state.get("origins", []):
            if origin.get("origin") != BASE_URL:
                continue
            for item in origin.get("localStorage", []):
                if item.get("name") != "__ds_remote_feature_did":
                    continue
                value = item.get("value", "")
                if value and value != "null":
                    return value
        return None

    def _find_settings_token(self, state):
        for origin in state.get("origins", []):
            if origin.get("origin") != BASE_URL:
                continue
            for item in origin.get("localStorage", []):
                if item.get("name") != "settingsJwt":
                    continue
                value = item.get("value", "")
                if not value or value == "null":
                    continue
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    continue
                payload = parsed.get("value") if isinstance(parsed, dict) else None
                if isinstance(payload, dict):
                    token = payload.get("jwt")
                    if isinstance(token, str) and token:
                        return token
        return None

    def _find_extra_headers(self, state):
        headers = {}
        for origin in state.get("origins", []):
            if origin.get("origin") != BASE_URL:
                continue
            for item in origin.get("localStorage", []):
                name = item.get("name", "")
                value = item.get("value", "")
                if not value or value == "null":
                    continue
                lowered = name.lower()
                if lowered in {"x-hif-dliq", "x-hif-leim"}:
                    headers[lowered] = value
        return headers

    def _get_json(self, path, params=None, headers=None):
        response = self.session.get(
            f"{BASE_URL}{path}",
            params=params,
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()
        return response

    def _post_json(self, path, payload, headers=None, stream=False):
        response = self.session.post(
            f"{BASE_URL}{path}",
            json=payload,
            headers=headers,
            stream=stream,
            timeout=120,
        )
        response.raise_for_status()
        return response

    def create_session(self):
        response = self._post_json("/api/v0/chat_session/create", {})
        data = response.json()
        biz_data = data.get("data", {}).get("biz_data", {})
        chat_session = biz_data.get("chat_session", {})
        if not chat_session.get("id"):
            raise ValueError("create_session response did not include chat_session.id")
        return data

    def create_pow_challenge(self, target_path):
        response = self._post_json(
            "/api/v0/chat/create_pow_challenge",
            {"target_path": target_path},
        )
        return response.json()

    def fetch_model_settings(self, refresh=False):
        if self.model_settings is not None and not refresh:
            return self.model_settings
        if not self.did:
            self.model_settings = None
            return None
        response = self._get_json(
            "/api/v0/client/settings",
            params={"did": self.did, "scope": "model"},
        )
        data = response.json()
        settings = data.get("data", {}).get("biz_data", {}).get("settings", {})
        model_configs = settings.get("model_configs", {})
        configs = model_configs.get("value") if isinstance(model_configs, dict) else None
        if not isinstance(configs, list):
            self.model_settings = None
            return None
        self.model_settings = configs
        return self.model_settings

    def get_available_model_types(self, refresh=False):
        settings = self.fetch_model_settings(refresh=refresh) or []
        model_types = []
        for item in settings:
            if not isinstance(item, dict):
                continue
            if not item.get("enabled") or not item.get("switchable"):
                continue
            model_type = item.get("model_type")
            if isinstance(model_type, str) and model_type:
                model_types.append(model_type)
        return model_types

    def get_default_model_type(self, refresh=False):
        settings = self.fetch_model_settings(refresh=refresh) or []
        for item in settings:
            if not isinstance(item, dict):
                continue
            if item.get("is_default"):
                model_type = item.get("model_type")
                if isinstance(model_type, str) and model_type:
                    return model_type
        return "default"

    def resolve_model_type(self, model_type, refresh=False):
        default_model_type = self.get_default_model_type(refresh=refresh)
        resolved = normalize_model_type(model_type, default_model_type=default_model_type)
        available_model_types = self.get_available_model_types(refresh=refresh)
        if available_model_types and resolved not in available_model_types:
            if default_model_type in available_model_types:
                return default_model_type
        return resolved

    def get_auth_status(self):
        authorization = self.session.headers.get("authorization")
        settings_token = self.session.headers.get("x-settings-token")
        return {
            "auth_state_path": str(self.auth_state_path),
            "auth_state_exists": self.auth_state_path.exists(),
            "cookie_count": len(self.session.cookies),
            "has_authorization": bool(authorization),
            "has_did": bool(self.did),
            "has_settings_token": bool(settings_token),
            "ready": bool(authorization and self.did and settings_token),
        }

    def solve_pow(self, challenge_response, target_path):
        challenge = parse_deepseek_challenge(challenge_response, target_path)
        if CPP_SOLVER_PATH.exists():
            proc = subprocess.run(
                [
                    str(CPP_SOLVER_PATH.resolve()),
                    "solve",
                    challenge.challenge,
                    challenge.prefix,
                    str(challenge.difficulty),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            answer = int(proc.stdout.strip())
            if answer < 0:
                raise RuntimeError("C++ solver did not find a PoW answer")
            header_json = {
                "algorithm": challenge.algorithm,
                "challenge": challenge.challenge,
                "salt": challenge.salt,
                "answer": answer,
                "signature": challenge.signature,
                "target_path": challenge.target_path,
            }
            header_value = base64.b64encode(
                json.dumps(header_json, separators=(",", ":")).encode()
            ).decode()
            return {"answer": answer, "header_json": header_json, "header_value": header_value}

        result = solve_deepseek_challenge(challenge)
        if not result["ok"]:
            raise RuntimeError("Python solver did not find a PoW answer")
        return result

    def chat_request(self, target_path, payload, chat_session_id=None):
        if chat_session_id:
            self.session.headers["referer"] = f"{BASE_URL}/a/chat/s/{chat_session_id}"
        challenge_response = self.create_pow_challenge(target_path)
        pow_result = self.solve_pow(challenge_response, target_path)
        return self._post_json(
            target_path,
            payload,
            headers={"x-ds-pow-response": pow_result["header_value"]},
            stream=True,
        )

    def completion(self, payload):
        return self.chat_request(
            "/api/v0/chat/completion",
            payload,
            chat_session_id=payload.get("chat_session_id"),
        )
