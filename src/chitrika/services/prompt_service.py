"""Prompt Service — assembles the full LLM context for every generation.

Injects character personality, current emotional state, relevant memories,
and recent conversation history into each call.
"""

from __future__ import annotations

from src.chitrika.models.character import Character
from src.chitrika.models.emotion import EmotionState
from src.chitrika.models.memory import Memory
from src.chitrika.models.message import Message
from src.chitrika.utils.emotion_algorithms import compute_loneliness, compute_mood


class PromptService:
    """Builds system and user prompts enriched with state and memory."""

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def build_system_prompt(
        self,
        character: Character,
        emotion_state: EmotionState,
        memories: list[Memory],
    ) -> str:
        """Assemble the system prompt: personality + state + memories + instructions."""
        emotions = emotion_state.to_dict()
        mood = compute_mood(emotions)
        loneliness = compute_loneliness(emotions)

        # Emotion summary
        top_emotions = sorted(emotions.items(), key=lambda kv: abs(kv[1]), reverse=True)
        emotion_summary = ", ".join(
            f"{name}={value:+.2f}" for name, value in top_emotions[:4]
        )

        # Memory context (top 10)
        memory_lines: list[str] = []
        active_memories = [m for m in memories if not m.is_forgotten]
        for mem in sorted(active_memories, key=lambda m: m.importance, reverse=True)[:10]:
            memory_lines.append(f"- {mem.content}")

        memory_block = "\n".join(memory_lines) if memory_lines else "（还没有关于用户的记忆）"

        # Build
        parts: list[str] = []

        # 1. Character personality (the bulk of the prompt)
        if character.personality_prompt:
            parts.append(character.personality_prompt)
        else:
            parts.append(f"你是{character.display_name}。")

        # 2. Current emotional state
        parts.append("")
        parts.append("=== 当前状态 ===")
        parts.append(f"心情：{mood}")
        parts.append(f"情绪：{emotion_summary}")
        parts.append(f"孤独感：{loneliness:.2f}")

        # 3. Memories
        parts.append("")
        parts.append("=== 你记得的事 ===")
        parts.append(memory_block)

        # 4. Instructions
        parts.append("")
        parts.append("=== 指示 ===")
        parts.append(f"以{character.display_name}的身份回复。保持角色一致性。")
        parts.append("使用短消息，一次只说一件事。不要写长段落。")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Full message list for chat completion
    # ------------------------------------------------------------------

    def build_messages(
        self,
        character: Character,
        emotion_state: EmotionState,
        memories: list[Memory],
        recent_messages: list[Message],
        *,
        system_prompt_override: str | None = None,
    ) -> list[dict[str, str]]:
        """Build the complete message list for an LLM chat completion call.

        Structure:
            1. system: enriched character prompt
            2. user/assistant pairs: recent conversation history (last ~30)
        """
        system = system_prompt_override or self.build_system_prompt(
            character, emotion_state, memories
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]

        for msg in recent_messages:
            if msg.is_deleted:
                continue
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    # ------------------------------------------------------------------
    # Proactive messaging prompt
    # ------------------------------------------------------------------

    def build_proactive_prompt(
        self,
        character: Character,
        emotion_state: EmotionState,
        hours_since_last: float,
    ) -> str:
        """Build the prompt used to decide whether to initiate contact."""
        emotions = emotion_state.to_dict()
        mood = compute_mood(emotions)
        loneliness = compute_loneliness(emotions)

        return f"""你是{character.display_name}。

你当前的状态：
心情：{mood}
孤独感：{loneliness:.2f}（0=不孤独，1=非常孤独）

你已经 {hours_since_last:.1f} 小时没有和用户说话了。

根据你的性格，你现在想主动联系用户吗？

请**只**回复一个JSON对象（不要有其他文字）：
{{
  "action": "now" | "wait" | "cancel",
  "wait_minutes": <仅在action="wait"时填写，等待分钟数>,
  "message_content": "<如果你想现在发消息，这裡写消息内容>"
}}"""
