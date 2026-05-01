from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vb6_parser._cursor import TreeCursor


class Node:
    __slots__ = ("_data", "_source", "_parent", "_children")

    def __init__(self, data: dict, source: bytes, parent: "Node | None" = None):
        self._data = data
        self._source = source
        self._parent = parent
        self._children: list[Node] | None = None

    def _build_children(self) -> list["Node"]:
        if self._children is None:
            self._children = [
                Node(c, self._source, parent=self)
                for c in self._data.get("children", [])
            ]
        return self._children

    @property
    def type(self) -> str:
        return self._data["type"]

    @property
    def is_named(self) -> bool:
        return bool(self._data["is_named"])

    @property
    def start_point(self) -> tuple[int, int]:
        p = self._data["start_point"]
        return (p[0], p[1])

    @property
    def end_point(self) -> tuple[int, int]:
        p = self._data["end_point"]
        return (p[0], p[1])

    @property
    def start_byte(self) -> int:
        return self._data["start_byte"]

    @property
    def end_byte(self) -> int:
        return self._data["end_byte"]

    @property
    def text(self) -> bytes:
        return self._source[self.start_byte:self.end_byte]

    @property
    def parent(self) -> "Node | None":
        return self._parent

    @property
    def children(self) -> list["Node"]:
        return self._build_children()

    @property
    def named_children(self) -> list["Node"]:
        return [c for c in self.children if c.is_named]

    @property
    def child_count(self) -> int:
        return len(self.children)

    @property
    def named_child_count(self) -> int:
        return len(self.named_children)

    @property
    def semantic(self) -> dict | None:
        return self._data.get("semantic") or None

    def child_by_field_name(self, name: str) -> "Node | None":
        for child in self.children:
            if child._data.get("field_name") == name:
                return child
        return None

    def children_by_field_name(self, name: str) -> list["Node"]:
        return [c for c in self.children if c._data.get("field_name") == name]

    def descendants_of_type(self, *types: str) -> list["Node"]:
        result: list[Node] = []
        type_set = set(types)
        self._collect_descendants(type_set, result)
        return result

    def _collect_descendants(self, types: set[str], acc: list["Node"]) -> None:
        for child in self.children:
            if child.type in types:
                acc.append(child)
            child._collect_descendants(types, acc)

    def walk(self) -> "TreeCursor":
        from vb6_parser._cursor import TreeCursor
        return TreeCursor(self)

    def __repr__(self) -> str:
        return f"<Node type={self.type!r} [{self.start_point}..{self.end_point}]>"
