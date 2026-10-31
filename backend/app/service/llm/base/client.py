"""Optional OpenAI-compatible client, unused by the placeholder workflow."""
from openai import APIError, APITimeoutError, AsyncOpenAI

from app.core.config import Settings


class ModelError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: Settings):
        if not settings.llm_api_key or not settings.llm_model:
            raise ModelError("Configure LLM_API_KEY and LLM_MODEL before invoking a model")
        self.model = settings.llm_model
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key, base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds, max_retries=0,
        )

    async def invoke(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": prompt}],
            )
            if not response.choices:
                raise ModelError("Model returned no choices")
            return response.choices[0].message.content or ""
        except APITimeoutError as exc:
            raise ModelError("Model request timed out") from exc
        except APIError as exc:
            raise ModelError("Model request failed") from exc

    async def close(self) -> None:
        await self.client.close()
