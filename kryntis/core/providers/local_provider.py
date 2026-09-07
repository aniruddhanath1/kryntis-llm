"""
Local LLM Provider — supports loading custom PyTorch .pt model checkpoints & llama.cpp GGUF files.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import torch

from kryntis.core.model import DecoderTransformer, ModelConfig
from kryntis.core.providers.base import BaseLLMProvider, GenerationConfig, LLMResponse, Message
from kryntis.core.tokenizer import CodeBPETokenizer
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class LocalProvider(BaseLLMProvider):
    """
    Runs local inference using custom-trained PyTorch Transformer checkpoints
    or llama-cpp GGUF models.
    """

    def __init__(
        self,
        model_path: str = "data/models/checkpoints/final_model.pt",
        n_ctx: int = 256,
        n_threads: int = 4,
        n_gpu_layers: int = 0,
    ) -> None:
        self._model_path = Path(model_path)
        self._n_ctx = n_ctx
        self._n_threads = n_threads
        self._n_gpu_layers = n_gpu_layers
        self._model = None
        self._tokenizer = None
        self._backend_type = "pytorch" if self._model_path.suffix == ".pt" else "llama_cpp"

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model_path.name

    async def is_available(self) -> bool:
        return self._model_path.exists() or Path("data/models").exists()

    def _load(self) -> None:
        if self._model is not None:
            return

        if not self._model_path.exists():
            # Fallback check for any checkpoint
            ckpts = sorted(Path("data/models/checkpoints").glob("*.pt"))
            if ckpts:
                self._model_path = ckpts[-1]
            else:
                raise FileNotFoundError(f"No trained model checkpoint found at {self._model_path}")

        log.info("loading_local_model", path=str(self._model_path), type=self._backend_type)

        if self._backend_type == "pytorch":
            self._tokenizer = CodeBPETokenizer()
            self._tokenizer.load()

            model_cfg = ModelConfig(
                vocab_size=32000,
                max_context_len=self._n_ctx,
                n_layers=12,
                n_heads=8,
                d_model=512,
                d_ff=2048,
            )

            device = torch.device("cuda" if torch.cuda.is_available() and self._n_gpu_layers > 0 else "cpu")
            self._model = DecoderTransformer(model_cfg).to(device)
            checkpoint = torch.load(self._model_path, map_location=device)
            self._model.load_state_dict(checkpoint["model_state_dict"])
            self._model.eval()
            self._device = device
        else:
            try:
                from llama_cpp import Llama
                self._model = Llama(
                    model_path=str(self._model_path),
                    n_ctx=self._n_ctx,
                    n_threads=self._n_threads,
                    n_gpu_layers=self._n_gpu_layers,
                    verbose=False,
                )
            except ImportError as e:
                raise ImportError("Install llama-cpp-python: pip install llama-cpp-python") from e

        log.info("local_model_loaded_successfully")

    async def chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> LLMResponse:
        self._load()
        cfg = config or GenerationConfig()
        prompt = self._format_prompt(messages)

        if self._backend_type == "pytorch":
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._generate_pytorch, prompt, cfg)
            return LLMResponse(
                content=text,
                provider=self.provider_name,
                model=self.model_name,
                prompt_tokens=len(self._tokenizer.encode(prompt)),
                completion_tokens=len(self._tokenizer.encode(text)),
            )
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, self._generate_llama, prompt, cfg)
            return LLMResponse(
                content=res["choices"][0]["text"],
                provider=self.provider_name,
                model=self.model_name,
                prompt_tokens=res["usage"]["prompt_tokens"],
                completion_tokens=res["usage"]["completion_tokens"],
            )

    async def stream_chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        res = await self.chat(messages, config)
        yield res.content

    def _generate_pytorch(self, prompt: str, cfg: GenerationConfig) -> str:
        input_ids = self._tokenizer.encode(prompt)
        x = torch.tensor([input_ids], dtype=torch.long, device=self._device)
        
        with torch.no_grad():
            for _ in range(cfg.max_tokens):
                logits = self._model(x[:, -self._n_ctx:])
                next_token_logits = logits[0, -1, :] / max(cfg.temperature, 1e-5)
                probs = torch.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                x = torch.cat([x, next_token.unsqueeze(0)], dim=1)
                if next_token.item() == self._tokenizer.eos_id:
                    break
                    
        generated = x[0, len(input_ids):].tolist()
        return self._tokenizer.decode(generated)

    def _generate_llama(self, prompt: str, cfg: GenerationConfig) -> dict:
        return self._model(
            prompt,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            stop=["</s>", "<|user|>", "<|assistant|>"],
        )

    def _format_prompt(self, messages: list[Message]) -> str:
        parts: list[str] = []
        for m in messages:
            if m.role == "system":
                parts.append(f"<|system|>\n{m.content}")
            elif m.role == "user":
                parts.append(f"<|user|>\n{m.content}")
            elif m.role == "assistant":
                parts.append(f"<|assistant|>\n{m.content}")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        log.info("local_model_unloaded")
