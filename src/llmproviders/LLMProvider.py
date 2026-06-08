from abc import ABC, abstractmethod
from dataclasses import dataclass as dc, field
from typing import Any, Iterator, AsyncIterator, Optional, Union
from enum import Enum
import json
import httpx


@dc
class Model:
	name: str
	displayName: Optional[str] = None
	maxTokens: Optional[int] = None
	supportsStreaming: bool = True


@dc
class Message:
	role: str
	content: str

	def toDict(self) -> dict[str, str]:
		return {'role': self.role, 'content': self.content}


@dc
class CompletionRequest:
	model: str
	messages: list[Message]
	temperature: float = 0.7
	maxTokens: Optional[int] = None
	stream: bool = False
	topP: float = 1.0
	frequencyPenalty: float = 0.0
	presencePenalty: float = 0.0
	stop: Optional[Union[str, list[str]]] = None

	def toDict(self) -> dict[str, Any]:
		data = {
			'model': self.model,
			'messages': [m.toDict() if isinstance(m, Message) else m for m in self.messages],
			'temperature': self.temperature,
			'stream': self.stream,
			'top_p': self.topP,
			'frequency_penalty': self.frequencyPenalty,
			'presence_penalty': self.presencePenalty,
		}
		if self.maxTokens:
			data['max_tokens'] = self.maxTokens
		if self.stop:
			data['stop'] = self.stop
		return data


@dc
class CompletionResponse:
	content: str
	model: str
	usage: dict[str, int] = field(default_factory=dict)
	finishReason: Optional[str] = None
	rawResponse: Any = None


@dc
class StreamChunk:
	content: str
	finishReason: Optional[str] = None
	model: Optional[str] = None


class LLMError(Exception): pass
class AuthenticationError(LLMError): pass
class RateLimitError(LLMError): pass
class ModelNotFoundError(LLMError): pass

class LLMProvider(ABC):

	@abstractmethod
	def getModels(self) -> list[Model]:
		pass

	@abstractmethod
	def send(self, model: Model, chat: str) -> CompletionResponse:
		pass

	@abstractmethod
	async def sendAsync(self, model: Model, chat: str) -> CompletionResponse:
		pass

	@abstractmethod
	def stream(self, model: Model, chat: str) -> Iterator[StreamChunk]:
		pass

	@abstractmethod
	async def streamAsync(self, model: Model, chat: str) -> AsyncIterator[StreamChunk]:
		pass

	def chat(self, model: Model, messages: list[Message], **kwargs) -> CompletionResponse:
		request = CompletionRequest(
			model=model.name,
			messages=messages,
			**kwargs
		)
		return self.send(model, request) # type: ignore