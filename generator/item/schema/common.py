from __future__ import annotations

from collections.abc import Callable
from typing import Any

FieldExtractor = Callable[[dict[str, Any], dict[str, Any]], Any]
VALUE_KEYS = (
    "LocalizedString",
    "SourceString",
    "AssetPathName",
    "ObjectPath",
    "ObjectName",
    "Value",
)


def extract_value(properties, key):
    value = properties.get(key)

    if not isinstance(value, dict):
        return value

    for k in VALUE_KEYS:
        v = value.get(k)

        if v not in (None, ""):
            return v

    return None


def nested_value(
    properties: dict[str, Any],
    keys: tuple[str, ...],
    fallback: Any = "",
) -> Any:
    value: Any = properties

    for key in keys:
        if not isinstance(value, dict):
            return fallback

        value = value.get(key)

    return fallback if value is None else value


def asset_reference_name(value):
    if isinstance(value, dict):
        value = next(
            (
                value.get(k)
                for k in (
                    "ObjectPath",
                    "AssetPathName",
                    "ObjectName",
                )
                if value.get(k)
            ),
            None,
        )

    if not isinstance(value, str) or not value:
        return ""

    if value.startswith("/Game/"):
        value = value.rsplit("/", 1)[-1].split(".", 1)[0]
    else:
        value = value.rsplit("'", 1)[-1]

    return value.removesuffix("_C")


def enum_value(value):
    return value.rsplit("::", 1)[-1] if isinstance(value, str) else ""


def required_skill_value(value):
    if not isinstance(value, list):
        return ""

    out = []

    for r in value:
        if (
            isinstance(r, dict)
            and r.get("Key") is not None
            and r.get("Value") is not None
        ):
            out.append(f"{str(r['Key']).rsplit('::', 1)[-1]}: {r['Value']}")

    return ", ".join(out)


def field(key, fallback="", transform=None):
    def get(properties, context):
        value = (
            transform(properties.get(key))
            if transform
            else extract_value(properties, key)
        )

        return fallback if value is None else value

    return get


def nested_field(
    *keys: str,
    fallback: str = "",
) -> FieldExtractor:
    return lambda properties, _context: nested_value(
        properties,
        keys,
        fallback,
    )


def context_field(key):
    return lambda properties, context: context.get(key, "")


def tier(properties, context):
    value = properties.get("Tier")

    if value is not None:
        return value

    for part in (
        str(context.get("path", ""))
        .replace(
            "\\",
            "/",
        )
        .split("/")
    ):
        if part.startswith("Tier") and part[4:].isdigit():
            return int(part[4:])

    return ""
