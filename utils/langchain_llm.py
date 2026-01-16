from langchain_core.language_models import LLM
from typing import Optional, List
from llm_clients import llm_clients


class OpenRouterLLM(LLM):
    llm_backend: str = "openrouter_free"

    @property
    def _llm_type(self) -> str:
        return "openrouter_custom"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        llm = llm_clients[self.llm_backend]
        return llm(prompt)
