from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "model_registry.yaml"


@lru_cache(maxsize=1)
def get_registry() -> dict[str, dict[str, str]]:
    """Load model registry from YAML config.

    Returns:
        Dict mapping role -> {provider: model_id}

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If YAML is malformed or missing required keys
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Model registry config not found at {CONFIG_PATH}. "
            "Copy config/model_registry.yaml.example to config/model_registry.yaml "
            "and fill in model IDs from https://build.nvidia.com/models"
        )

    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)

    if not data or "roles" not in data:
        raise ValueError("model_registry.yaml must have a 'roles' key")

    return data["roles"]


def model_for(role: str, provider: str) -> str:
    """Get model ID for a given role and provider.

    Args:
        role: Model role (e.g., "fast_chat", "reasoning", "multilingual_indic")
        provider: Provider name ("gemini" or "nvidia")

    Returns:
        Model ID string

    Raises:
        ValueError: If role is unknown
        RuntimeError: If model ID not configured for role/provider
    """
    registry = get_registry()

    if role not in registry:
        raise ValueError(
            f"Unknown model role: {role}. "
            f"Available roles: {list(registry.keys())}"
        )

    role_config = registry[role]

    # Determine which key to use based on provider
    if provider == "gemini":
        key = "gemini"
    elif provider == "nvidia":
        # Prefer primary, fall back to fallback
        key = "nvidia_primary" if "nvidia_primary" in role_config else "nvidia_fallback"
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'nvidia'")

    model_id = role_config.get(key, "")
    if not model_id:
        raise RuntimeError(
            f"Model ID for role={role} provider={provider} not set in model_registry.yaml. "
            f"Check https://build.nvidia.com/models and fill in the config."
        )

    return model_id


def list_roles() -> list[str]:
    """List all available model roles."""
    return list(get_registry().keys())


def function_id_for(role: str, *, fallback: bool = False) -> str:
    """Riva NVCF function-id for a role (TTS today). Raises RuntimeError if unset.

    Riva models are addressed by function-id over gRPC, not a model name over
    REST, so this is a parallel lookup to model_for() rather than a substitute.
    """
    registry = get_registry()
    if role not in registry:
        raise ValueError(f"Unknown model role: {role}")
    key = "nvidia_fallback_function_id" if fallback else "nvidia_primary_function_id"
    function_id = registry[role].get(key, "")
    if not function_id:
        raise RuntimeError(f"No function_id configured for role={role} ({key}) in model_registry.yaml")
    return function_id


def validate_registry() -> list[str]:
    """Validate that all required model IDs are configured.

    Returns:
        List of warning messages (empty if all good)
    """
    warnings = []
    registry = get_registry()

    required_roles = [
        "fast_chat",
        "reasoning",
        "multilingual_indic",
        "vision",
        "ocr",
        "asr",
        "embeddings",
        "safety_jailbreak",
    ]

    for role in required_roles:
        if role not in registry:
            warnings.append(f"Missing role: {role}")
            continue

        role_config = registry[role]

        # Check Gemini models
        if "gemini" in role_config and not role_config["gemini"]:
            warnings.append(f"Role {role}: gemini model ID is empty")

        # Check NVIDIA models (at least one of primary/fallback)
        nvidia_primary = role_config.get("nvidia_primary", "")
        nvidia_fallback = role_config.get("nvidia_fallback", "")
        if not nvidia_primary and not nvidia_fallback:
            warnings.append(f"Role {role}: no NVIDIA model configured (primary or fallback)")

    return warnings


def reload_registry() -> None:
    """Force reload of registry (clears cache). Useful for tests."""
    get_registry.cache_clear()
