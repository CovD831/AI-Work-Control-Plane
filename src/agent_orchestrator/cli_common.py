"""Shared helpers for command-line presenters."""
from __future__ import annotations

# DEPS: __future__, argparse, json
# RESPONSIBILITY: Provide common CLI format and JSON emission helpers.
# MODULE: interface
# ---

import argparse
import json


FORMAT_CHOICES = ["pretty", "json"]


def json_only(args: argparse.Namespace) -> bool:
    return getattr(args, "format", "pretty") == "json"


def emit_json(payload: dict[str, object], args: argparse.Namespace, *, summary: object | None = None) -> None:
    if not json_only(args) and callable(summary):
        summary()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
