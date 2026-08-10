"""
Thin abstraction so the rest of the app doesn't care whether it's talking
to the Anthropic API or your local Ollama/Qwen setup. Every other service
(resume_parser, question_generator, interview_engine, feedback_service)
calls `llm.complete(...)` and gets plain text back.
"""

import json
import httpx
from anthropic import Anthropic
from groq import Groq

from app.config import settings


class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider
        if self.provider == "anthropic":
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        elif self.provider == "groq":
            self._groq_client = Groq(api_key=settings.groq_api_key)

    def complete(self, system: str, user: str, max_tokens: int = 1500, json_mode: bool = False) -> str:
        if self.provider == "anthropic":
            return self._complete_anthropic(system, user, max_tokens)
        elif self.provider == "ollama":
            return self._complete_ollama(system, user)
        elif self.provider == "groq":
            return self._complete_groq(system, user, max_tokens, json_mode)
        elif self.provider == "openai":
            return self._complete_openai(system, user, max_tokens)
        raise ValueError(f"Unknown LLM_PROVIDER: {self.provider}")

    def complete_json(self, system: str, user: str, max_tokens: int = 1500) -> dict:
        """Same as complete(), but instructs the model to return only JSON
        and parses it. Use for structured outputs (resume analysis,
        next-question objects, feedback reports)."""
        json_system = (
            system
            + "\n\nRespond with ONLY valid JSON. No markdown fences, "
              "no preamble, no explanation before or after."
        )
        raw = self.complete(json_system, user, max_tokens, json_mode=True)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e}")
            print(f"Raw output: {raw}")
            raise

    def _complete_anthropic(self, system: str, user: str, max_tokens: int) -> str:
        resp = self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def _complete_ollama(self, system: str, user: str) -> str:
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def _complete_groq(self, system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
        kwargs = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "model": settings.groq_model,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        chat_completion = self._groq_client.chat.completions.create(**kwargs)
        return chat_completion.choices[0].message.content

    def _complete_openai(self, system: str, user: str, max_tokens: int) -> str:
        chat_completion = self._openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            model=settings.openai_model,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return chat_completion.choices[0].message.content


llm = LLMClient()
