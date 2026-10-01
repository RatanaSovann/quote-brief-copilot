"""The one door to the Anthropic API. Every call records model, tokens, time and cost.

If Langfuse keys are in .env, each call is also sent there as a trace so runs
can be inspected in a browser. Without the keys, everything still works.
"""
import contextlib
import os
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic
from dotenv import load_dotenv

import config

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_client = anthropic.Anthropic()
_langfuse = None
if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
    from langfuse import get_client
    _langfuse = get_client()


@dataclass
class CallRecord:
    step: str
    model: str
    input_tokens: int
    output_tokens: int
    seconds: float
    cost_usd: float

    @property
    def cost_aud(self):
        return self.cost_usd * config.AUD_PER_USD


def cost_usd(model, input_tokens, output_tokens):
    in_price, out_price = config.PRICES_USD_PER_MTOK[model]
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


def _trace(step, model, system, user):
    if _langfuse is None:
        return contextlib.nullcontext()
    return _langfuse.start_as_current_observation(
        name=step, as_type="generation", model=model,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )


def call_structured(step, model, system, user, output_format, effort=None, max_tokens=16000):
    """Ask the model for JSON matching a pydantic class. Returns (parsed object, CallRecord).

    effort=None leaves it out: Haiku 4.5 rejects the effort setting.
    """
    extra = {"output_config": {"effort": effort}} if effort else {}
    start = time.perf_counter()
    with _trace(step, model, system, user) as gen:
        response = _client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=output_format,
            **extra,
        )
        usage = response.usage
        record = CallRecord(
            step=step,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,  # includes thinking tokens, which are billed as output
            seconds=round(time.perf_counter() - start, 2),
            cost_usd=cost_usd(model, usage.input_tokens, usage.output_tokens),
        )
        if gen is not None:
            gen.update(
                output=response.parsed_output.model_dump() if response.parsed_output else None,
                usage_details={"input": usage.input_tokens, "output": usage.output_tokens},
                cost_details={"total": record.cost_usd},
                metadata={"stop_reason": response.stop_reason},
            )

    # A refusal or a cut-off answer is not a job card; fail loudly rather than pass on half a result.
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise RuntimeError(f"{step}: model stopped with '{response.stop_reason}', no usable output")
    return response.parsed_output, record


def flush():
    """Send any queued Langfuse traces before a short script exits."""
    if _langfuse is not None:
        _langfuse.flush()
