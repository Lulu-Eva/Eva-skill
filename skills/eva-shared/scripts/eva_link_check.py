#!/usr/bin/env python3
"""Validate Eva Link configuration."""

from __future__ import annotations

import argparse
from pathlib import Path

from eva_common import (
    CORE_ENTRIES,
    VALID_ASSET_TYPES,
    VALID_HANDOFF_TARGETS,
    VALID_LOW_CONFIDENCE_REASONS,
    add_common_arguments,
    canonical_handoff_target,
    canonicalize_handoff_targets,
    default_base_from_script,
    exit_with,
    is_blank_value,
    normalize_path,
    read_json,
    required_fields_for_asset,
    result,
    simple_schema_validate,
)

FORBIDDEN_LINK_PREFERENCE_FIELDS = {
    "enabled",
    "default",
    "defaults",
    "default_for",
    "default_intents",
    "can_be_default_for",
    "confirmed",
    "confirmed_at",
    "confirmed_phrase",
}

BROAD_DEFAULT_INTENTS = {"写", "写内容", "创作", "帮我写", "写一条", "生成内容", "做内容", "内容创作"}


def find_link_config(path: Path) -> Path:
    if path.is_file():
        return path
    candidates = [
        path / "eva.link.json",
        path / "link.json",
        path / "module.link.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No eva.link.json / link.json / module.link.json found")


def validate_expected_asset(path: Path, base: Path, link_config: dict | None = None) -> list[str]:
    errors: list[str] = []
    try:
        asset = read_json(path)
    except Exception as exc:
        return [f"expected_asset cannot be read as JSON: {exc}"]
    if not isinstance(asset, dict):
        return ["expected_asset must be a JSON object"]

    asset_schema = read_json(base / "schemas" / "asset-card.schema.json")
    errors.extend(simple_schema_validate(asset, asset_schema))

    asset_type = asset.get("asset_type")
    if asset_type not in VALID_ASSET_TYPES:
        errors.append(f"expected_asset asset_type {asset_type!r} is invalid")
    else:
        missing_required = [
            field for field in required_fields_for_asset(str(asset_type), base)
            if field not in asset or is_blank_value(asset.get(field))
        ]
        if missing_required:
            errors.append("expected_asset missing required field(s): " + ", ".join(missing_required))

    invalid_next = sorted(set(asset.get("valid_next") or []) - VALID_HANDOFF_TARGETS)
    if invalid_next:
        errors.append("expected_asset valid_next contains invalid target(s): " + ", ".join(invalid_next))

    low_confidence_reason = asset.get("low_confidence_reason") or []
    if isinstance(low_confidence_reason, str):
        low_confidence_reason = [low_confidence_reason]
    invalid_reasons = sorted(set(low_confidence_reason) - VALID_LOW_CONFIDENCE_REASONS)
    if invalid_reasons:
        errors.append("expected_asset low_confidence_reason contains invalid reason(s): " + ", ".join(invalid_reasons))

    if link_config is not None:
        produces = set(link_config.get("produces") or [])
        link_id = str(link_config.get("id") or "")
        handoff_to = set(link_config.get("handoff_to") or [])
        if produces and asset_type not in produces:
            errors.append(
                f"expected_asset asset_type {asset_type!r} is not declared in Link produces: "
                + ", ".join(sorted(map(str, produces)))
            )
        source_module = asset.get("source_module")
        if link_id and source_module != link_id:
            errors.append(f"expected_asset source_module {source_module!r} must equal Link id {link_id!r}")
        asset_valid_next = set(canonicalize_handoff_targets(asset.get("valid_next") or [], base))
        normalized_handoff_to = set(canonicalize_handoff_targets(handoff_to, base))
        invalid_for_link = sorted(asset_valid_next - normalized_handoff_to)
        if handoff_to and invalid_for_link:
            errors.append(
                "expected_asset valid_next contains target(s) not declared in Link handoff_to: "
                + ", ".join(invalid_for_link)
            )

    return errors


def validate_link_manifest_semantics(link_config: dict, context: str = "Link") -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    preference_fields = sorted(set(link_config.keys()) & FORBIDDEN_LINK_PREFERENCE_FIELDS)
    if preference_fields:
        errors.append(
            f"{context} manifest contains user preference field(s); move them to .eva/links.json: "
            + ", ".join(preference_fields)
        )

    entry_aliases = [str(item).strip() for item in (link_config.get("entry_aliases") or [])]
    broad_aliases = sorted({item for item in entry_aliases if item in BROAD_DEFAULT_INTENTS or len(item) <= 2})
    if broad_aliases:
        warnings.append(f"{context} entry_aliases may be too broad: " + ", ".join(broad_aliases))

    handoff_to = [str(item) for item in (link_config.get("handoff_to") or [])]
    compatibility_aliases = sorted(
        target for target in handoff_to
        if canonical_handoff_target(target) != target
    )
    if compatibility_aliases:
        warnings.append(
            f"{context} handoff_to uses compatibility alias(es); new Link manifests should use canonical names: "
            + ", ".join(compatibility_aliases)
        )

    return errors, warnings


def registry_project_root(path: Path) -> Path:
    if path.name == "links.json" and path.parent.name == ".eva":
        return path.parent.parent
    return path.parent


def resolve_registry_link_path(raw_path: str, registry_path: Path, base: Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    project_root = registry_project_root(registry_path)
    candidates = [
        project_root / path,
        registry_path.parent / path,
        base / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (project_root / path).resolve()


def validate_link_registry(path: Path, base: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    data: dict = {"registry_path": str(path)}

    try:
        registry = read_json(path)
    except Exception as exc:
        return [f"registry cannot be read as JSON: {exc}"], warnings, data
    if not isinstance(registry, dict):
        return ["registry must be a JSON object"], warnings, data

    schema_path = base / "schemas" / "link-registry.schema.json"
    if not schema_path.exists():
        return [f"registry schema missing: {schema_path}"], warnings, data

    registry_schema = read_json(schema_path)
    errors.extend(simple_schema_validate(registry, registry_schema))
    link_schema = read_json(base / "schemas" / "eva-link.schema.json")

    links = registry.get("links") or []
    defaults = registry.get("defaults") or []
    if not isinstance(links, list):
        links = []
    if not isinstance(defaults, list):
        defaults = []

    enabled_links: set[str] = set()
    known_link_ids: list[str] = []
    known_links: set[str] = set()
    link_paths: dict[str, str] = {}
    for item in links:
        if not isinstance(item, dict):
            continue
        link_id = str(item.get("id", ""))
        known_link_ids.append(link_id)
        known_links.add(link_id)
        if item.get("enabled") is True:
            enabled_links.add(link_id)
        raw_path = str(item.get("path", ""))
        if raw_path:
            resolved = resolve_registry_link_path(raw_path, path, base)
            link_paths[link_id] = str(resolved)
            if not resolved.exists():
                errors.append(f"registry link path does not exist for {link_id}: {resolved}")
                continue
            try:
                link_config_path = find_link_config(resolved)
                link_config = read_json(link_config_path)
            except Exception as exc:
                errors.append(f"registry link {link_id} cannot read Link config: {exc}")
                continue
            link_config_errors = simple_schema_validate(link_config, link_schema)
            if link_config_errors:
                errors.extend([f"registry link {link_id}: {item}" for item in link_config_errors])
            semantic_errors, semantic_warnings = validate_link_manifest_semantics(link_config, f"registry link {link_id}")
            errors.extend(semantic_errors)
            warnings.extend(semantic_warnings)
            actual_id = link_config.get("id")
            if actual_id != link_id:
                errors.append(f"registry link id mismatch: {link_id} points to {actual_id!r}")
            entry_aliases = set(link_config.get("entry_aliases") or [])
            id_parts = {str(actual_id or "")}
            conflicting = sorted((entry_aliases | id_parts) & CORE_ENTRIES)
            if conflicting:
                errors.append(f"registry link {link_id} must not override core Eva entries: " + ", ".join(conflicting))

    duplicate_link_ids = sorted({item for item in known_link_ids if item and known_link_ids.count(item) > 1})
    if duplicate_link_ids:
        errors.append("registry contains duplicate link id(s): " + ", ".join(duplicate_link_ids))

    seen_intents: dict[str, int] = {}
    for index, item in enumerate(defaults):
        if not isinstance(item, dict):
            continue
        intent = str(item.get("intent", "")).strip()
        link_id = str(item.get("link_id", "")).strip()
        seen_intents[intent] = seen_intents.get(intent, 0) + 1
        if item.get("confirmed") is not True:
            errors.append(f"registry default {intent!r} must be explicitly confirmed")
        if not str(item.get("confirmed_phrase", "")).strip():
            errors.append(f"registry default {intent!r} missing confirmed_phrase")
        if not str(item.get("confirmed_at", "")).strip():
            errors.append(f"registry default {intent!r} missing confirmed_at")
        if link_id not in known_links:
            errors.append(f"registry default {intent!r} points to unknown link_id: {link_id}")
        elif link_id not in enabled_links:
            errors.append(f"registry default {intent!r} points to disabled link_id: {link_id}")
        if intent in BROAD_DEFAULT_INTENTS or len(intent) <= 2:
            warnings.append(f"registry default intent may be too broad: {intent!r}")
        if item.get("confirmed") is True and intent and link_id:
            phrase = str(item.get("confirmed_phrase", ""))
            if intent not in phrase or link_id not in phrase:
                warnings.append(
                    f"registry default #{index + 1} confirmation phrase should mention both intent and link_id/name"
                )

    duplicate_intents = sorted([intent for intent, count in seen_intents.items() if intent and count > 1])
    if duplicate_intents:
        errors.append("registry contains duplicate default intent(s): " + ", ".join(duplicate_intents))

    data["links"] = sorted(known_links)
    data["enabled_links"] = sorted(enabled_links)
    data["defaults"] = [
        {"intent": item.get("intent"), "link_id": item.get("link_id")}
        for item in defaults
        if isinstance(item, dict)
    ]
    data["link_paths"] = link_paths
    return errors, warnings, data


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an Eva Link config.")
    parser.add_argument("--link", help="Path to a link config JSON or link folder.")
    parser.add_argument("--registry", help="Optional project .eva/links.json registry to validate with the Link.")
    parser.add_argument("--schema", help="Path to eva-link.schema.json.")
    parser.add_argument("--strict", action="store_true", help="Also require module.md and test fixtures for a runnable Link.")
    add_common_arguments(parser)
    args = parser.parse_args()

    base = default_base_from_script(__file__)
    link_input = normalize_path(args.link) if args.link else None
    schema_path = normalize_path(args.schema) if args.schema else base / "schemas" / "eva-link.schema.json"

    errors: list[str] = []
    warnings: list[str] = []

    if not link_input and not args.registry:
        exit_with(result(False, "link_check", "必须提供 --link 或 --registry", []))
    if not schema_path.exists():
        exit_with(result(False, "link_check", "Schema 文件不存在", [str(schema_path)]))

    link_path: Path | None = None
    link_config: dict = {}
    produces = []
    accepts = []
    handoff_to = []
    strict_files: dict[str, str | None] = {}
    if link_input:
        if not link_input.exists():
            exit_with(result(False, "link_check", "Link 路径不存在", [str(link_input)]))

        try:
            link_path = find_link_config(link_input)
            link_config = read_json(link_path)
        except Exception as exc:
            exit_with(result(False, "link_check", "Link 配置读取失败", [str(exc)]))

        schema = read_json(schema_path)
        errors.extend(simple_schema_validate(link_config, schema))
        semantic_errors, semantic_warnings = validate_link_manifest_semantics(link_config)
        errors.extend(semantic_errors)
        warnings.extend(semantic_warnings)

        link_id = str(link_config.get("id", ""))
        entry_aliases = set(link_config.get("entry_aliases") or [])
        id_parts = {link_id}
        conflicting = sorted((entry_aliases | id_parts) & CORE_ENTRIES)
        if conflicting:
            errors.append("Link must not override core Eva entries: " + ", ".join(conflicting))

        produces = link_config.get("produces") or []
        accepts = link_config.get("accepts") or []
        handoff_to = link_config.get("handoff_to") or []
        if not accepts:
            errors.append("Link must declare accepts")
        if not produces:
            errors.append("Link must declare produces")
        if not handoff_to:
            errors.append("Link must declare handoff_to")

        invalid_accepts = sorted(set(accepts) - VALID_ASSET_TYPES)
        if invalid_accepts:
            errors.append("accepts contains invalid asset type(s): " + ", ".join(invalid_accepts))
        invalid_produces = sorted(set(produces) - VALID_ASSET_TYPES)
        if invalid_produces:
            errors.append("produces contains invalid asset type(s): " + ", ".join(invalid_produces))
        invalid_handoff = sorted(set(handoff_to) - VALID_HANDOFF_TARGETS)
        if invalid_handoff:
            errors.append("handoff_to contains invalid target(s): " + ", ".join(invalid_handoff))

    if args.strict and link_path:
        link_root = link_path.parent
        required_paths = {
            "module": link_root / "module.md",
            "input_example": link_root / "tests" / "input.example.md",
            "expected_asset": link_root / "tests" / "expected-asset.example.json",
        }
        for label, path in required_paths.items():
            strict_files[label] = str(path) if path.exists() else None
        missing_strict = [label for label, path in strict_files.items() if path is None]
        if missing_strict:
            errors.append("strict Link check missing file(s): " + ", ".join(missing_strict))
        expected_asset = required_paths["expected_asset"]
        if expected_asset.exists():
            strict_asset_errors = validate_expected_asset(expected_asset, base, link_config)
            errors.extend(strict_asset_errors)
    elif args.strict:
        warnings.append("--strict ignored because no --link was provided")

    registry_data: dict = {}
    if args.registry:
        registry_path = normalize_path(args.registry)
        if not registry_path.exists():
            errors.append(f"registry path does not exist: {registry_path}")
        else:
            registry_errors, registry_warnings, registry_data = validate_link_registry(registry_path, base)
            errors.extend(registry_errors)
            warnings.extend(registry_warnings)

    ok = not errors
    exit_with(
        result(
            ok,
            "link_check",
            "Link 完整校验通过" if ok and args.strict and link_path else ("Link/registry 校验通过" if ok else "Link 校验失败"),
            errors,
            warnings,
            {
                "link_path": str(link_path) if link_path else None,
                "schema_path": str(schema_path),
                "id": link_config.get("id"),
                "accepts": accepts,
                "produces": produces,
                "handoff_to": handoff_to,
                "strict": args.strict,
                "strict_files": strict_files,
                "registry": registry_data,
            },
        )
    )


if __name__ == "__main__":
    main()
