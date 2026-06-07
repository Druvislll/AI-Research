"""统一的 LLM 客户端，支持 OpenAI / DeepSeek / 自定义 API"""

import json
from typing import Optional
import openai
from src import config


class LLMClient:
    """LLM 调用封装，支持切换不同提供商"""

    def __init__(self, provider: str = ""):
        self.provider = provider or config.LLM_PROVIDER
        if self.provider == "deepseek":
            self.client = openai.OpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL,
            )
            self.model = config.DEEPSEEK_MODEL
        else:
            self.client = openai.OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )
            self.model = config.OPENAI_MODEL

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> str:
        """调用 LLM 进行对话"""
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_json(self, system_prompt: str, user_prompt: str, **kwargs) -> dict:
        """调用 LLM 并返回 JSON 对象"""
        text = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format="json",
            **kwargs,
        )
        # 清理可能的 Markdown 代码块标记
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())
