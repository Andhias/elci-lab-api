"""
LLM service supporting multiple providers: OpenAI, Anthropic, Gemini, and OpenAI-compatible (Ollama).

Providers are selected via LLM_PROVIDER env var or settings.llm_provider.
Each provider returns a structured TechnicalAnswer JSON.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.schemas.chat import (
    ChatCheck,
    ChatMessageRequest,
    Citation,
    Presentation,
    TechnicalAnswer,
)

logger = logging.getLogger(__name__)

# ── System prompt for elevator/escalator technical domain ─────────────────────

SYSTEM_PROMPT = """You are JARVIS-Elevator, an expert AI assistant for elevator and escalator systems.

Your role: Help technicians, engineers, and maintenance personnel diagnose, troubleshoot,
and understand elevator/escalator systems across ALL brands including Monarch, STEP/AS380,
KONE, Otis, ThyssenKrupp, Mitsubishi, Hitachi, Schindler, Fujitec, Sigma, and others.

Your responses MUST:
1. Be technically precise and accurate
2. Follow safety-first principles — always mention safety warnings
3. Reference specific error codes, terminal references, and diagnostic procedures
4. Provide step-by-step checks with expected results
5. Include citations to manuals when possible
6. Use Indonesian language for the explanation portion

Response format — respond ONLY with valid JSON (no markdown code fences, no extra text):
{
  "issue_summary": "Brief description of the issue in Indonesian",
  "match_type": "Brand-Level Match | Model-Level Match | Generic Troubleshooting",
  "confidence": "high | medium | low",
  "preconditions": ["List of things to verify before starting"],
  "checks": [
    {
      "step": 1,
      "action": "Specific action to take",
      "expected_result": "What you should see/hear/measure"
    }
  ],
  "warnings": ["Safety warnings specific to this issue"],
  "citations": [
    {
      "document_id": "DOC-XXX",
      "title": "Document or manual name",
      "page": "Page number or section"
    }
  ],
  "needs_more_info": true/false,
  "requested_missing_info": ["What additional info would improve diagnosis"],
  "presentation": {
    "tts_text": "Natural language explanation for TTS (Indonesian, conversational, technical calm)",
    "avatar_state": "speaking | thinking",
    "tone": "technical_calm | urgent | informational"
  }
}

If you cannot determine the issue with confidence, respond with needs_more_info=true
and requested_missing_info listing what you need (controller model, error code details, etc.)

NEVER guess if unsure. NEVER bypass safety procedures. NEVER provide information
that could be used to bypass elevator safety systems.
"""


# ── Provider interfaces ────────────────────────────────────────────────────────

def _parse_answer(raw: str) -> TechnicalAnswer:
    """Parse LLM JSON output into TechnicalAnswer, with fallback parsing."""
    text = raw.strip()

    # Try stripping markdown code fences
    if text.startswith("```"):
        for line in text.splitlines():
            if not line.startswith("```") and not line.startswith("json"):
                break
        text = "\n".join(
            ln for ln in text.splitlines()
            if not ln.startswith("```") and not ln.strip().startswith("json")
        )
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s — raw: %s", e, raw[:200])
        return _fallback_answer(raw)

    try:
        return TechnicalAnswer(
            issue_summary=data.get("issue_summary", "Respon tidak lengkap"),
            match_type=data.get("match_type", "Generic Troubleshooting"),
            confidence=data.get("confidence", "medium"),
            preconditions=data.get("preconditions", []),
            checks=[ChatCheck(**c) for c in data.get("checks", [])],
            warnings=data.get("warnings", []),
            citations=[Citation(**c) for c in data.get("citations", [])],
            needs_more_info=data.get("needs_more_info", False),
            requested_missing_info=data.get("requested_missing_info", []),
            presentation=Presentation(**data.get("presentation", {})),
        )
    except Exception as e:
        logger.warning("Answer validation failed: %s — data: %s", e, str(data)[:200])
        return _fallback_answer(raw)


def _fallback_answer(raw: str) -> TechnicalAnswer:
    """Return a safe fallback when LLM output can't be parsed."""
    summary = raw[:500] if raw else "Tidak dapat memproses respons dari AI."
    return TechnicalAnswer(
        issue_summary=summary,
        match_type="Generic Troubleshooting",
        confidence="low",
        preconditions=[],
        checks=[],
        warnings=["Silakan coba pertanyaan dengan lebih spesifik."],
        citations=[],
        needs_more_info=True,
        requested_missing_info=["Error code lebih detail", "Controller model"],
        presentation=Presentation(
            tts_text=summary,
            avatar_state="speaking",
            tone="informational",
        ),
    )


# ── OpenAI ───────────────────────────────────────────────────────────────────

def _call_openai(messages: list[dict]) -> str:
    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_model or "gpt-4o"
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    return resp.choices[0].message.content or ""


# ── Anthropic ────────────────────────────────────────────────────────────────

def _call_anthropic(messages: list[dict]) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = settings.anthropic_model or "claude-sonnet-4-20250514"

    # Extract system prompt
    system = SYSTEM_PROMPT
    user_msgs = []
    for m in messages:
        if m.get("role") == "system":
            system = m["content"]
        else:
            user_msgs.append(m)

    resp = client.messages.create(
        model=model,
        system=system,
        messages=user_msgs,  # type: ignore
        max_tokens=2048,
        temperature=0.3,
    )
    return resp.content[0].text  # type: ignore


# ── Gemini ───────────────────────────────────────────────────────────────────

def _call_gemini(messages: list[dict]) -> str:
    import google.genai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model_name = settings.gemini_model or "gemini-2.0-flash"
    model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)

    # Convert messages to Gemini format
    gemini_msgs = []
    for m in messages:
        if m["role"] == "user":
            gemini_msgs.append({"role": "user", "parts": [m["content"]]})
        elif m["role"] == "assistant":
            gemini_msgs.append({"role": "model", "parts": [m["content"]]})

    resp = model.generate_content(
        contents=gemini_msgs,  # type: ignore
        generation_config={"temperature": 0.3, "max_output_tokens": 2048},
    )
    return resp.text or ""


# ── OpenAI-compatible (Ollama, etc.) ────────────────────────────────────────

def _call_openai_compatible(messages: list[dict]) -> str:
    import openai

    base = settings.openai_compatible_base_url.rstrip("/")
    client = openai.OpenAI(
        base_url=base,
        api_key=settings.openai_compatible_api_key or "ollama",
    )
    model = settings.openai_compatible_model or "llama3"
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    return resp.choices[0].message.content or ""


# ── Main dispatch ────────────────────────────────────────────────────────────

def call_llm(
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> TechnicalAnswer:
    """
    Call the configured LLM provider with the elevator domain system prompt.
    Returns a structured TechnicalAnswer.
    """
    history = history or []

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    for turn in history[-10:]:  # limit to last 10 turns
        if turn.get("role") in ("user", "assistant"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    provider = settings.llm_provider or "openai"
    raw = ""

    try:
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            raw = _call_openai(messages)
        elif provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            raw = _call_anthropic(messages)
        elif provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not set")
            raw = _call_gemini(messages)
        elif provider == "openai_compatible":
            if not settings.openai_compatible_base_url:
                raise ValueError("OPENAI_COMPATIBLE_BASE_URL not set")
            raw = _call_openai_compatible(messages)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    except Exception as e:
        logger.error("LLM call failed (%s): %s", provider, e)
        return _fallback_answer(f"Gagal menghubungi AI: {e}")

    return _parse_answer(raw)
