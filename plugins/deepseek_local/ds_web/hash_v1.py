"""DeepSeekHashV1 (Keccak-based) used by chat.deepseek.com PoW."""

from __future__ import annotations

MASK64 = (1 << 64) - 1
RATE = 136

ROUND_CONSTANTS = [
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808A,
    0x8000000080008000,
    0x000000000000808B,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008A,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000A,
    0x000000008000808B,
    0x800000000000008B,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800A,
    0x800000008000000A,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
]

ROTATION_OFFSETS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]


def _rotl64(value: int, bits: int) -> int:
    value &= MASK64
    return ((value << bits) | (value >> (64 - bits))) & MASK64 if bits else value


def _keccak_f1600_deepseek(state: list[int]) -> None:
    for rc in ROUND_CONSTANTS[1:]:
        columns = [0] * 5
        for x in range(5):
            columns[x] = state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]

        deltas = [0] * 5
        for x in range(5):
            deltas[x] = columns[(x - 1) % 5] ^ _rotl64(columns[(x + 1) % 5], 1)

        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= deltas[x]
                state[x + 5 * y] &= MASK64

        rotated = [0] * 25
        for x in range(5):
            for y in range(5):
                rotated[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl64(
                    state[x + 5 * y],
                    ROTATION_OFFSETS[x][y],
                )

        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = (
                    rotated[x + 5 * y]
                    ^ ((~rotated[((x + 1) % 5) + 5 * y]) & rotated[((x + 2) % 5) + 5 * y])
                ) & MASK64

        state[0] ^= rc
        state[0] &= MASK64


def deepseek_hash_v1(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    else:
        data = bytes(data)

    state = [0] * 25
    offset = 0

    while offset + RATE <= len(data):
        block = data[offset : offset + RATE]
        for lane in range(RATE // 8):
            state[lane] ^= int.from_bytes(block[lane * 8 : lane * 8 + 8], "little")
            state[lane] &= MASK64
        _keccak_f1600_deepseek(state)
        offset += RATE

    block = bytearray(RATE)
    remaining = data[offset:]
    block[: len(remaining)] = remaining
    block[len(remaining)] = 0x06
    block[-1] |= 0x80

    for lane in range(RATE // 8):
        state[lane] ^= int.from_bytes(block[lane * 8 : lane * 8 + 8], "little")
        state[lane] &= MASK64
    _keccak_f1600_deepseek(state)

    digest = bytearray()
    for lane in range(4):
        digest.extend(state[lane].to_bytes(8, "little"))
    return digest.hex()


def solve(target_hex: str, prefix: str, max_nonce: int) -> int | None:
    max_nonce = int(max_nonce)
    for nonce in range(max_nonce):
        if deepseek_hash_v1(f"{prefix}{nonce}") == target_hex:
            return nonce
    return None
