from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vb6_parser._node import Node


class TreeCursor:
    __slots__ = ("_node",)

    def __init__(self, node: "Node"):
        self._node = node

    @property
    def node(self) -> "Node":
        return self._node

    @property
    def current_field_name(self) -> str | None:
        return self._node._data.get("field_name")

    def goto_first_child(self) -> bool:
        children = self._node.children
        if not children:
            return False
        self._node = children[0]
        return True

    def goto_next_sibling(self) -> bool:
        parent = self._node.parent
        if parent is None:
            return False
        siblings = parent.children
        idx = next((i for i, c in enumerate(siblings) if c is self._node), -1)
        if idx < 0 or idx + 1 >= len(siblings):
            return False
        self._node = siblings[idx + 1]
        return True

    def goto_parent(self) -> bool:
        if self._node.parent is None:
            return False
        self._node = self._node.parent
        return True

    def reset(self, node: "Node") -> None:
        self._node = node
