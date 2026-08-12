import json
from typing import AsyncIterator, Iterator

import httpx

from src.llmproviders.LLMProvider import LLMProvider, ModelNotFoundError, AuthenticationError, RateLimitError, LLMError, \
	Model, CompletionRequest, Message, CompletionResponse, StreamChunk


def _extract_error_message(response: httpx.Response) -> str:
	"""Best-effort parse of OpenAI-style error bodies."""
	try:
		error_data = response.json() if response.text else {}
	except Exception:
		return ''
	if not isinstance(error_data, dict):
		return ''
	error = error_data.get('error')
	if isinstance(error, dict):
		message = error.get('message')
		if isinstance(message, str) and message.strip():
			return message.strip()
	message = error_data.get('message')
	if isinstance(message, str) and message.strip():
		return message.strip()
	return ''


class OpenAIClient(LLMProvider):

	def __init__(self, apiKey: str, baseUrl: str = 'https://api.openai.com/v1', timeout: float = 60.0):
		self.apiKey = apiKey
		self.baseUrl = baseUrl.rstrip('/')
		self.timeout = timeout
		self._client = httpx.Client(timeout=timeout)
		self._asyncClient = None

	async def _getAsyncClient(self) -> httpx.AsyncClient:
		if self._asyncClient is None:
			self._asyncClient = httpx.AsyncClient(timeout=self.timeout)
		return self._asyncClient

	def _getHeaders(self) -> dict[str, str]:
		# Local OpenAI-compatible servers (Ollama, LM Studio, etc.) often need
		# no auth. Only send Bearer when a key is actually configured.
		headers = {'Content-Type': 'application/json'}
		if self.apiKey and self.apiKey.strip():
			headers['Authorization'] = f'Bearer {self.apiKey.strip()}'
		return headers

	def _handleError(self, response: httpx.Response) -> None:
		if response.status_code == 401:
			detail = _extract_error_message(response)
			raise AuthenticationError(
				detail or 'Invalid API key (HTTP 401). Check the provider API key in Settings.'
			)
		elif response.status_code == 429:
			raise RateLimitError('Rate limit exceeded')
		elif response.status_code == 404:
			raise ModelNotFoundError('Model not found')
		else:
			errorMsg = _extract_error_message(response) or f'HTTP {response.status_code}'
			raise LLMError(errorMsg)

	def getModels(self) -> list[Model]:
		response = self._client.get(f'{self.baseUrl}/models', headers=self._getHeaders())
		if response.status_code != 200:
			self._handleError(response)

		data = response.json()
		models = []
		for item in data.get('data', []):
			models.append(Model(
				name=item['id'],
				displayName=item.get('id'),
				maxTokens=None,
				supportsStreaming=True
			))
		return models

	def send(self, model: Model, chat: str | CompletionRequest | list[Message]) -> CompletionResponse:
		if isinstance(chat, str):
			request = CompletionRequest(
				model=model.name,
				messages=[Message(role='user', content=chat)]
			)
		elif isinstance(chat, list):
			request = CompletionRequest(model=model.name, messages=chat)
		else:
			request = chat

		response = self._client.post(
			f'{self.baseUrl}/chat/completions',
			headers=self._getHeaders(),
			json=request.toDict()
		)

		if response.status_code != 200:
			self._handleError(response)

		data = response.json()
		choice = data['choices'][0]

		return CompletionResponse(
			content=choice['message']['content'],
			model=data['model'],
			usage=data.get('usage', {}),
			finishReason=choice.get('finish_reason'),
			rawResponse=data
		)

	async def sendAsync(self, model: Model, chat: str | CompletionRequest | list[Message]) -> CompletionResponse:
		client = await self._getAsyncClient()

		if isinstance(chat, str):
			request = CompletionRequest(
				model=model.name,
				messages=[Message(role='user', content=chat)]
			)
		elif isinstance(chat, list):
			request = CompletionRequest(model=model.name, messages=chat)
		else:
			request = chat

		response = await client.post(
			f'{self.baseUrl}/chat/completions',
			headers=self._getHeaders(),
			json=request.toDict()
		)

		if response.status_code != 200:
			self._handleError(response)

		data = response.json()
		choice = data['choices'][0]

		return CompletionResponse(
			content=choice['message']['content'],
			model=data['model'],
			usage=data.get('usage', {}),
			finishReason=choice.get('finish_reason'),
			rawResponse=data
		)

	def stream(self, model: Model, chat: str | list[Message]) -> Iterator[StreamChunk]:
		if isinstance(chat, str):
			messages = [Message(role='user', content=chat)]
		else:
			messages = chat

		request = CompletionRequest(
			model=model.name,
			messages=messages,
			stream=True
		)

		with self._client.stream(
				'POST',
				f'{self.baseUrl}/chat/completions',
				headers=self._getHeaders(),
				json=request.toDict()
		) as response:
			if response.status_code != 200:
				self._handleError(response)

			for line in response.iter_lines():
				if line and line.startswith('data: '):
					data = line[6:]
					if data == '[DONE]':
						break
					try:
						chunk = json.loads(data)
						delta = chunk['choices'][0].get('delta', {})
						content = delta.get('content', '')
						finishReason = chunk['choices'][0].get('finish_reason')

						yield StreamChunk(
							content=content,
							finishReason=finishReason,
							model=chunk.get('model')
						)
					except json.JSONDecodeError:
						continue

	async def streamAsync(self, model: Model, chat: str | list[Message]) -> AsyncIterator[StreamChunk]:
		client = await self._getAsyncClient()

		if isinstance(chat, str):
			messages = [Message(role='user', content=chat)]
		else:
			messages = chat

		request = CompletionRequest(
			model=model.name,
			messages=messages,
			stream=True
		)

		async with client.stream(
				'POST',
				f'{self.baseUrl}/chat/completions',
				headers=self._getHeaders(),
				json=request.toDict()
		) as response:
			if response.status_code != 200:
				self._handleError(response)

			async for line in response.aiter_lines():
				if line and line.startswith('data: '):
					data = line[6:]
					if data == '[DONE]':
						break
					try:
						chunk = json.loads(data)
						delta = chunk['choices'][0].get('delta', {})
						content = delta.get('content', '')
						finishReason = chunk['choices'][0].get('finish_reason')

						yield StreamChunk(
							content=content,
							finishReason=finishReason,
							model=chunk.get('model')
						)
					except json.JSONDecodeError:
						continue

	def close(self) -> None:
		self._client.close()
		if self._asyncClient:
			self._asyncClient.aclose()

	def __enter__(self):
		return self

	def __exit__(self, excType, excVal, excTb):
		self.close()

	async def __aenter__(self):
		return self

	async def __aexit__(self, excType, excVal, excTb):
		self.close()
