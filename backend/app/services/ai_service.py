from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()


TEST_CASE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "module": {"type": "string"},
        "feature": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "test_type": {
                        "type": "string",
                        "enum": ["Functional", "Negative", "Boundary", "UI", "API", "Security", "Performance", "Validation"],
                    },
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
                    "severity": {"type": "string", "enum": ["Minor", "Major", "Critical", "Blocker"]},
                    "preconditions": {"type": "array", "items": {"type": "string"}},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "test_data": {"type": "string"},
                    "expected_result": {"type": "string"},
                },
                "required": [
                    "title",
                    "test_type",
                    "priority",
                    "severity",
                    "preconditions",
                    "steps",
                    "test_data",
                    "expected_result",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["module", "feature", "assumptions", "test_cases"],
    "additionalProperties": False,
}

ALLOWED_TYPES = {"Functional", "Negative", "Boundary", "UI", "API", "Security", "Performance", "Validation"}
ALLOWED_PRIORITIES = {"Low", "Medium", "High", "Critical"}
ALLOWED_SEVERITIES = {"Minor", "Major", "Critical", "Blocker"}


def _fallback_generator(requirement_text: str, module_name: str, test_types: List[str], number_of_cases: int, note: str = "") -> Dict[str, Any]:
    """Local demo generator so the product works even without an API key or local LLM."""
    templates = [
        ("Verify successful flow with valid input", "Functional", "High", "Major"),
        ("Verify required fields validation", "Validation", "High", "Major"),
        ("Verify invalid input is rejected", "Negative", "High", "Major"),
        ("Verify boundary/minimum allowed value", "Boundary", "Medium", "Minor"),
        ("Verify duplicate or already existing data handling", "Negative", "High", "Major"),
        ("Verify UI error message is clear", "UI", "Medium", "Minor"),
        ("Verify unauthorized access is blocked", "Security", "High", "Critical"),
        ("Verify system handles empty input safely", "Negative", "Medium", "Major"),
        ("Verify data is saved correctly after submission", "Functional", "High", "Major"),
        ("Verify page remains stable after refresh", "Functional", "Medium", "Minor"),
        ("Verify API returns correct response code", "API", "Medium", "Major"),
        ("Verify feature responds within acceptable time", "Performance", "Medium", "Minor"),
    ]

    selected = []
    allowed = set(test_types) if test_types else {"Functional", "Negative", "Boundary"}
    for idx, (title, case_type, priority, severity) in enumerate(templates, start=1):
        if case_type not in allowed and len(selected) < max(1, number_of_cases // 2):
            continue
        selected.append(
            {
                "title": f"TC-{idx:03d}: {title}",
                "test_type": case_type,
                "priority": priority,
                "severity": severity,
                "preconditions": ["Application is running", "User has access to the relevant module"],
                "steps": [
                    "Open the feature screen",
                    "Enter the required test data",
                    "Perform the user action described in the requirement",
                    "Observe the system response",
                ],
                "test_data": "Use valid and invalid sample data according to the requirement.",
                "expected_result": f"System should behave according to this requirement: {requirement_text[:180]}",
            }
        )
        if len(selected) >= number_of_cases:
            break

    assumptions = ["Fallback generator used because no configured LLM completed successfully."]
    if note:
        assumptions.append(note[:220])

    return {
        "module": module_name or "General",
        "feature": "Generated Feature",
        "assumptions": assumptions,
        "test_cases": selected,
    }


def _build_prompt(requirement_text: str, module_name: str, requirement_title: str, test_types: List[str], number_of_cases: int) -> str:
    return f"""
You are a senior QA engineer.

Generate exactly {number_of_cases} professional QA test cases for the requirement below.

Module: {module_name}
Feature title: {requirement_title}
Requirement:
{requirement_text}

Selected test types: {', '.join(test_types)}

Return ONLY valid JSON with this exact shape:
{{
  "module": "string",
  "feature": "string",
  "assumptions": ["string"],
  "test_cases": [
    {{
      "title": "string",
      "test_type": "Functional | Negative | Boundary | UI | API | Security | Performance | Validation",
      "priority": "Low | Medium | High | Critical",
      "severity": "Minor | Major | Critical | Blocker",
      "preconditions": ["string"],
      "steps": ["string"],
      "test_data": "string",
      "expected_result": "string"
    }}
  ]
}}

Rules:
- Cover positive, negative, boundary, validation, UI, security, API, or performance cases only when relevant.
- Do not invent unrelated features.
- Keep steps clear enough for a junior QA tester to execute manually.
- Expected result must be specific and testable.
- Use concise professional QA wording.
- JSON only. No markdown. No explanation outside JSON.
""".strip()


def _extract_json_object(text: str) -> Dict[str, Any]:
    """Robust parser for local models that sometimes wrap JSON in text/code fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def _normalize_result(data: Dict[str, Any], module_name: str, requirement_title: str, number_of_cases: int, provider_note: str) -> Dict[str, Any]:
    normalized_cases = []
    raw_cases = data.get("test_cases") if isinstance(data, dict) else []
    if not isinstance(raw_cases, list):
        raw_cases = []

    for item in raw_cases[:number_of_cases]:
        if not isinstance(item, dict):
            continue
        test_type = str(item.get("test_type") or "Functional")
        priority = str(item.get("priority") or "Medium")
        severity = str(item.get("severity") or "Major")
        normalized_cases.append(
            {
                "title": str(item.get("title") or "Untitled test case")[:220],
                "test_type": test_type if test_type in ALLOWED_TYPES else "Functional",
                "priority": priority if priority in ALLOWED_PRIORITIES else "Medium",
                "severity": severity if severity in ALLOWED_SEVERITIES else "Major",
                "preconditions": [str(x) for x in item.get("preconditions", [])] if isinstance(item.get("preconditions"), list) else [],
                "steps": [str(x) for x in item.get("steps", [])] if isinstance(item.get("steps"), list) else [],
                "test_data": str(item.get("test_data") or "Use suitable QA test data."),
                "expected_result": str(item.get("expected_result") or "System should behave according to the requirement."),
            }
        )

    assumptions = data.get("assumptions", []) if isinstance(data.get("assumptions"), list) else []
    assumptions = [str(item) for item in assumptions]
    assumptions.insert(0, provider_note)

    return {
        "module": str(data.get("module") or module_name or "General"),
        "feature": str(data.get("feature") or requirement_title or "Generated Requirement"),
        "assumptions": assumptions,
        "test_cases": normalized_cases,
    }


def _generate_with_openai(prompt: str, module_name: str, requirement_title: str, number_of_cases: int) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    from openai import OpenAI

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You generate structured QA test cases only."},
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "qa_test_case_generation",
                "schema": TEST_CASE_SCHEMA,
                "strict": True,
            },
        },
    )
    content = response.choices[0].message.content or "{}"
    return _normalize_result(json.loads(content), module_name, requirement_title, number_of_cases, f"Generated with OpenAI model: {model}.")


def _generate_with_ollama(prompt: str, module_name: str, requirement_title: str, number_of_cases: int) -> Dict[str, Any]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip() or "llama3.1:8b"
    timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_predict": 4096,
        },
    }
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    raw_text = data.get("response", "{}")
    parsed = _extract_json_object(raw_text)
    return _normalize_result(parsed, module_name, requirement_title, number_of_cases, f"Generated locally with Ollama model: {model}.")


def get_llm_status() -> Dict[str, Any]:
    """Returns the currently configured generation provider for the UI."""
    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower() or "auto"
    openai_key_set = bool(os.getenv("OPENAI_API_KEY", "").strip())
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip() or "llama3.1:8b"
    ollama_available = False
    ollama_error = ""

    try:
        with urllib.request.urlopen(f"{ollama_base_url}/api/tags", timeout=2) as response:
            tags = json.loads(response.read().decode("utf-8"))
            models = [item.get("name", "") for item in tags.get("models", [])]
            ollama_available = True
    except Exception as exc:  # noqa: BLE001 - status endpoint should not crash the app
        models = []
        ollama_error = str(exc)[:180]

    if provider == "auto":
        active = "openai" if openai_key_set else "ollama" if ollama_available else "fallback"
    elif provider in {"openai", "ollama", "fallback"}:
        active = provider
    else:
        active = "fallback"

    return {
        "configured_provider": provider,
        "active_provider": active,
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "openai_key_set": openai_key_set,
        "ollama_base_url": ollama_base_url,
        "ollama_model": ollama_model,
        "ollama_available": ollama_available,
        "ollama_models_installed": models[:20],
        "ollama_error": ollama_error,
    }


def generate_test_cases_with_ai(
    requirement_text: str,
    module_name: str,
    requirement_title: str,
    test_types: List[str],
    number_of_cases: int,
) -> Dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower() or "auto"
    prompt = _build_prompt(requirement_text, module_name, requirement_title, test_types, number_of_cases)
    errors: list[str] = []

    if provider in {"openai", "auto"}:
        try:
            return _generate_with_openai(prompt, module_name, requirement_title, number_of_cases)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OpenAI failed: {str(exc)[:160]}")
            if provider == "openai":
                return _fallback_generator(requirement_text, module_name, test_types, number_of_cases, errors[-1])

    if provider in {"ollama", "auto"}:
        try:
            return _generate_with_ollama(prompt, module_name, requirement_title, number_of_cases)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
            errors.append(f"Ollama failed: {str(exc)[:160]}")
            if provider == "ollama":
                return _fallback_generator(requirement_text, module_name, test_types, number_of_cases, errors[-1])

    return _fallback_generator(requirement_text, module_name, test_types, number_of_cases, " | ".join(errors))
