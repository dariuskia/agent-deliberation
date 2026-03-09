import asyncio
import json
import re

from openai import AsyncOpenAI


def extract_json(text: str):
    """Extract and parse JSON from LLM response, handling markdown fences and surrounding prose."""
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")

    # Try parsing the whole thing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first JSON array or object in the text
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Find matching closing bracket, accounting for nesting
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not extract JSON from response: {text[:200]}")


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-sonnet-4",
        base_url: str = "https://openrouter.ai/api/v1",
        max_concurrent: int = 5,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def complete(
        self, system: str, user: str, temperature: float = 0.7
    ) -> str:
        async with self.semaphore:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content

    async def complete_batch(
        self, requests: list[tuple[str, str]], temperature: float = 0.7
    ) -> list[str]:
        tasks = [self.complete(s, u, temperature) for s, u in requests]
        return await asyncio.gather(*tasks)
