"""Resolve monorepo vs sibling-project paths."""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    return (start or Path(__file__)).resolve().parents[1]


def ephys_root(root: Path | None = None) -> Path:
    root = repo_root() if root is None else root
    bundled = root / "ephys"
    if bundled.is_dir():
        return bundled
    sibling = root.parent / "2026:5:5"
    return sibling if sibling.is_dir() else bundled


def prx_root(root: Path | None = None) -> Path:
    root = repo_root() if root is None else root
    bundled = root / "prx"
    if bundled.is_dir():
        return bundled
    sibling = root.parent / "2026:5:18"
    return sibling if sibling.is_dir() else bundled


def crossover_csv(root: Path | None = None) -> Path:
    root = repo_root() if root is None else root
    local = root / "results" / "crossover_and_resources.csv"
    if local.is_file():
        return local
    return ephys_root(root) / "results" / "crossover_and_resources.csv"
