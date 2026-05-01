from __future__ import annotations
from vb6_parser._node import Node


class Tree:
    __slots__ = ("_root", "_source")

    def __init__(self, root: Node, source: bytes):
        self._root = root
        self._source = source

    @property
    def root_node(self) -> Node:
        return self._root

    @property
    def source(self) -> bytes:
        return self._source

    def __repr__(self) -> str:
        return f"<Tree root={self._root.type!r}>"
