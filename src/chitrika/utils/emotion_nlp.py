"""Local NLP-style emotion delta classification.

This is deliberately lightweight: no remote calls and no heavyweight model files.
It uses clause-level discourse features, speech-act detection, negation and
context repair instead of direct keyword-to-emotion accounting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.chitrika.utils.emotion_algorithms import DIMENSIONS, clamp


@dataclass
class _Context:
    intimacy: bool = False
    explicit_distress: bool = False
    playful_fear: bool = False
    protective_reply: bool = False
    teasing_reply: bool = False


class EmotionNLPClassifier:
    """Classify one exchange into bounded Plutchik-style emotion deltas."""

    def classify(self, user_text: str, assistant_text: str = "") -> dict[str, float]:
        deltas = {dim: 0.0 for dim in DIMENSIONS}
        context = _Context()

        target_text = assistant_text.strip() or user_text.strip()
        target_clauses = _split_clauses(target_text)

        for clause in target_clauses:
            self._score_assistant_clause(clause, deltas, context)

        self._repair_context(deltas, context)
        return {
            dim: round(clamp(value, -0.2, 0.2), 4)
            for dim, value in deltas.items()
            if abs(value) >= 0.001
        }

    def _score_user_clause(
        self,
        clause: str,
        deltas: dict[str, float],
        context: _Context,
    ) -> None:
        intensity = _intensity(clause)
        fear_context = _has_fear_context(clause)

        if _is_affectionate(clause):
            context.intimacy = True
            _add(deltas, "joy", 0.08 * intensity)
            _add(deltas, "trust", 0.08 * intensity)
            _add(deltas, "anticipation", 0.04 * intensity)

        if _requests_company(clause):
            context.intimacy = True
            _add(deltas, "trust", 0.06 * intensity)
            _add(deltas, "anticipation", 0.05 * intensity)

        if _contains(clause, ["谢谢", "感谢", "辛苦", "thank", "thanks"]):
            _add(deltas, "joy", 0.04 * intensity)
            _add(deltas, "trust", 0.06 * intensity)

        if _contains(clause, ["哈哈", "hhh", "笑死", "开心", "高兴", "好棒", "厉害", "great", "nice"]):
            _add(deltas, "joy", 0.06 * intensity)
            _add(deltas, "surprise", 0.02)

        if fear_context:
            if _contains(clause, ["密室", "微恐", "恐怖", "吓", "npc", "鬼屋", "害怕", "怕", "scared", "afraid"]):
                _add(deltas, "fear", 0.08 * intensity)
                _add(deltas, "anticipation", 0.03 * intensity)
            if _contains(clause, ["吓哭", "吓死", "吓懵", "吓傻"]):
                _add(deltas, "fear", 0.04 * intensity)
            if _is_play_context(clause):
                context.playful_fear = True
        else:
            if _contains(clause, ["难过", "伤心", "委屈", "崩溃", "哭", "sad", "cry"]):
                context.explicit_distress = True
                _add(deltas, "sadness", 0.09 * intensity)
                _add(deltas, "trust", 0.02)

        if _contains(clause, ["累", "疲惫", "状态不好", "不太好", "low mood"]):
            _add(deltas, "sadness", 0.04 * intensity)
            _add(deltas, "trust", 0.02)

        if _contains(clause, ["孤独", "寂寞", "没人理", "lonely", "alone"]):
            context.explicit_distress = True
            _add(deltas, "sadness", 0.08 * intensity)
            _add(deltas, "anticipation", 0.05)
            _add(deltas, "trust", -0.03)

        if _contains(clause, ["担心", "紧张", "焦虑", "不安", "anxious"]):
            _add(deltas, "fear", 0.08 * intensity)
            _add(deltas, "anticipation", 0.04)

        if _contains(clause, ["期待", "等你", "想知道", "下次", "以后", "hope"]):
            _add(deltas, "anticipation", 0.07 * intensity)
            _add(deltas, "trust", 0.02)

        if _contains(clause, ["讨厌", "烦", "傻逼", "生气", "闭嘴", "bad", "hate", "stupid"]):
            _add(deltas, "anger", 0.10 * intensity)
            _add(deltas, "trust", -0.06)
            _add(deltas, "disgust", 0.04)

        if _contains(clause, ["恶心", "反胃", "嫌弃", "disgusting", "gross"]):
            _add(deltas, "disgust", 0.10 * intensity)
            _add(deltas, "trust", -0.03)

        if _contains(clause, ["我靠", "我去", "天哪", "居然", "竟然", "wow", "omg", "卧槽"]):
            _add(deltas, "surprise", 0.10 * intensity)

        if "?" in clause or "？" in clause:
            _add(deltas, "anticipation", 0.02)
        if "!" in clause or "！" in clause:
            _add(deltas, "surprise", min(0.05, 0.015 * (clause.count("!") + clause.count("！"))))

    def _score_assistant_clause(
        self,
        clause: str,
        deltas: dict[str, float],
        context: _Context,
    ) -> None:
        intensity = _intensity(clause)

        if _is_affectionate(clause):
            context.intimacy = True
            _add(deltas, "joy", 0.06 * intensity)
            _add(deltas, "trust", 0.07 * intensity)
            _add(deltas, "anticipation", 0.03)

        if _contains(clause, ["保护你", "陪你", "我听着", "都听着", "说不定我就不累了"]):
            context.protective_reply = True
            _add(deltas, "trust", 0.07 * intensity)
            _add(deltas, "joy", 0.04 * intensity)

        if _contains(clause, ["hhh", "哈哈", "菜", "犯规", "你你你"]):
            context.teasing_reply = True
            _add(deltas, "joy", 0.05 * intensity)
            _add(deltas, "surprise", 0.02)

        if _contains(clause, ["累", "状态不太好", "状态不好", "不太好"]):
            _add(deltas, "sadness", 0.035 * intensity)
            _add(deltas, "trust", 0.02)

        if _contains(clause, ["对不起", "抱歉", "sorry"]):
            _add(deltas, "sadness", 0.02)
            _add(deltas, "trust", 0.02)

    def _repair_context(self, deltas: dict[str, float], context: _Context) -> None:
        if context.playful_fear and (context.protective_reply or context.teasing_reply):
            deltas["sadness"] *= 0.25
            _add(deltas, "trust", 0.04)
            _add(deltas, "joy", 0.03)

        if context.intimacy and deltas["sadness"] > 0 and not context.explicit_distress:
            deltas["sadness"] *= 0.35
            _add(deltas, "trust", 0.03)


def classify_emotion_delta(user_text: str, assistant_text: str = "") -> dict[str, float]:
    """Return local NLP emotion deltas for a completed exchange."""
    return EmotionNLPClassifier().classify(user_text, assistant_text)


def _split_clauses(text: str) -> list[str]:
    clauses = re.split(r"[\n。！？!?；;，,]+", text)
    return [clause.strip() for clause in clauses if clause.strip()]


def _contains(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _add(deltas: dict[str, float], dim: str, amount: float) -> None:
    deltas[dim] = deltas.get(dim, 0.0) + amount


def _intensity(text: str) -> float:
    multiplier = 1.0
    if _contains(text, ["非常", "特别", "超级", "太", "好", "很", "really", "very"]):
        multiplier += 0.18
    marks = text.count("!") + text.count("！") + text.count("啊")
    if marks:
        multiplier += min(0.35, marks * 0.04)
    return multiplier


def _is_affectionate(text: str) -> bool:
    if re.search(r"想死你[了啦呀]?", text):
        return True
    return _contains(text, [
        "想你", "好想你", "我也想你", "爱你", "喜欢你", "抱抱", "亲亲", "贴贴",
        "miss you", "love you",
    ])


def _requests_company(text: str) -> bool:
    return bool(
        re.search(r"陪.*(聊|说话|一会|会儿)", text)
        or re.search(r"(能|可以).*陪", text)
        or _contains(text, ["陪我", "聊会儿", "聊一会"])
    )


def _has_fear_context(text: str) -> bool:
    return _contains(text, [
        "密室", "微恐", "恐怖", "吓", "害怕", "怕", "鬼屋", "npc", "scared", "afraid",
    ])


def _is_play_context(text: str) -> bool:
    return _contains(text, ["密室", "微恐", "鬼屋", "npc", "游戏", "玩"])
