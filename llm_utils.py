"""
Lightweight LLM helpers used by the training script and MLSecOps checks.

We intentionally pick a tiny Hugging Face model so that inference and security
scans remain fast and do not disrupt the existing pipeline.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Dict

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

DEFAULT_LLM_MODEL = "sshleifer/tiny-gpt2"


@lru_cache(maxsize=2)
def _get_text_generation_pipeline(model_name: str = DEFAULT_LLM_MODEL):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # GPT-2 style models often lack a pad token; align to EOS to avoid warnings.
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(model_name)
    return pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        device=-1,  # force CPU for broad compatibility
    )


def ensure_model_ready(model_name: str = DEFAULT_LLM_MODEL) -> None:
    """Trigger a one-time download/cache of the requested HF model."""
    _get_text_generation_pipeline(model_name)


def _build_metrics_prompt(metrics: Dict[str, float]) -> str:
    pretty_metrics = json.dumps(metrics, sort_keys=True, indent=2)
    return (
        "You are assisting an ML engineer. Summarise these evaluation metrics "
        "for a churn model in 3 sentences with a risk note at the end:\n"
        f"{pretty_metrics}\n"
    )


def generate_metrics_summary(
    metrics: Dict[str, float],
    *,
    model_name: str = DEFAULT_LLM_MODEL,
    max_new_tokens: int = 72,
    temperature: float = 0.7,
) -> str:
    """Generate a short natural-language summary of the evaluation metrics."""
    generator = _get_text_generation_pipeline(model_name)
    prompt = _build_metrics_prompt(metrics)
    outputs = generator(
        prompt,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
        num_return_sequences=1,
        pad_token_id=generator.tokenizer.eos_token_id,
    )

    generated_text = outputs[0]["generated_text"]
    if generated_text.startswith(prompt):
        generated_text = generated_text[len(prompt) :].strip()
    return generated_text.strip()

