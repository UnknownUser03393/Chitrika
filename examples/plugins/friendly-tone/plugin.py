"""Example Chitrika prompt plugin."""

from src.chitrika.plugins import PromptContext


class FriendlyTonePlugin:
    def on_system_prompt(self, context: PromptContext) -> str:
        return context.system_prompt + "\nUse a warm, friendly, and concise tone."


plugin = FriendlyTonePlugin()
