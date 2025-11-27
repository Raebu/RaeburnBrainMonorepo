"""Deadlock detector for mission DAGs."""

from __future__ import annotations

from typing import Dict, List, Set


def has_cycle(graph: Dict[str, List[str]]) -> bool:
    """Return True if the directed graph contains a cycle."""
    visited: Set[str] = set()
    stack: Set[str] = set()

    def dfs(node: str) -> bool:
        if node in stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        stack.add(node)
        for nbr in graph.get(node, []):
            if dfs(nbr):
                return True
        stack.remove(node)
        return False

    return any(dfs(n) for n in graph)
