"""PoW challenge parsing and solving for chat.deepseek.com."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from .hash_v1 import deepseek_hash_v1

MAX_SAFE_NONCE = 9007199254740991
TARGET_HEX_LENGTH = 64


@dataclass(frozen=True)
class PowChallenge:
    target_hex: str
    prefix: str
    max_nonce: int


@dataclass(frozen=True)
class DeepSeekPowChallenge:
    algorithm: str
    challenge: str
    salt: str
    difficulty: int
    expire_at: int
    signature: str
    target_path: str

    @property
    def prefix(self) -> str:
        return f"{self.salt}_{self.expire_at}_"


def parse_deepseek_challenge(value, target_path: str | None = None) -> DeepSeekPowChallenge:
    if isinstance(value, str):
        value = json.loads(value)

    while True:
        if "data" in value and isinstance(value["data"], dict):
            value = value["data"]
            continue
        if "biz_data" in value and isinstance(value["biz_data"], dict):
            value = value["biz_data"]
            continue
        if "challenge" in value and isinstance(value["challenge"], dict):
            value = value["challenge"]
            continue
        break

    expire_at = value.get("expire_at") or value.get("expireAt")
    if expire_at is None:
        raise ValueError("challenge must include expire_at or expireAt")

    return DeepSeekPowChallenge(
        algorithm=value.get("algorithm", "DeepSeekHashV1"),
        challenge=value["challenge"],
        salt=value["salt"],
        difficulty=int(value["difficulty"]),
        expire_at=int(expire_at),
        signature=value["signature"],
        target_path=target_path
        or value.get("target_path")
        or value.get("targetPath")
        or "/api/v0/chat/completion",
    )


def validate_challenge(challenge: PowChallenge) -> None:
    if not isinstance(challenge.target_hex, str):
        raise ValueError("target_hex must be a string")
    if len(challenge.target_hex) != TARGET_HEX_LENGTH:
        raise ValueError("target_hex must be 64 hex characters, representing 32 bytes")
    try:
        bytes.fromhex(challenge.target_hex)
    except ValueError as exc:
        raise ValueError("target_hex must contain only hexadecimal characters") from exc

    if not isinstance(challenge.prefix, str):
        raise ValueError("prefix must be a string")
    if not (0 < challenge.max_nonce < MAX_SAFE_NONCE):
        raise ValueError(f"max_nonce must be an integer in range 1..{MAX_SAFE_NONCE - 1}")


def solve_challenge(challenge: PowChallenge) -> dict:
    validate_challenge(challenge)
    for nonce in range(challenge.max_nonce):
        digest = deepseek_hash_v1(f"{challenge.prefix}{nonce}")
        if digest == challenge.target_hex:
            return {
                "ok": True,
                "nonce": nonce,
                "answer": nonce,
                "hash": digest,
                "input": f"{challenge.prefix}{nonce}",
            }
    return {"ok": False, "nonce": None, "answer": None, "hash": None, "input": None}


def solve_deepseek_challenge(challenge: DeepSeekPowChallenge) -> dict:
    if challenge.algorithm != "DeepSeekHashV1":
        raise ValueError(f"unsupported algorithm: {challenge.algorithm}")

    generic = PowChallenge(
        target_hex=challenge.challenge,
        prefix=challenge.prefix,
        max_nonce=challenge.difficulty,
    )
    result = solve_challenge(generic)
    if not result["ok"]:
        return {
            "ok": False,
            "answer": None,
            "header_json": None,
            "header_value": None,
            "input": None,
            "hash": None,
        }

    header_json = {
        "algorithm": challenge.algorithm,
        "challenge": challenge.challenge,
        "salt": challenge.salt,
        "answer": result["answer"],
        "signature": challenge.signature,
        "target_path": challenge.target_path,
    }
    encoded = base64.b64encode(json.dumps(header_json, separators=(",", ":")).encode()).decode()
    return {
        "ok": True,
        "answer": result["answer"],
        "header_json": header_json,
        "header_value": encoded,
        "input": result["input"],
        "hash": result["hash"],
    }
