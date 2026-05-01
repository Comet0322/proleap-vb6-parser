from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from vb6_parser._errors import InternalError, ParseError, VbRuntimeError
from vb6_parser._jar import find_jar
from vb6_parser._node import Node
from vb6_parser._tree import Tree

# Candidate Java binary paths to try when 'java' on PATH is broken (e.g. macOS stub)
_JAVA_FALLBACK_PATHS = [
    "/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/bin/java",
    "/opt/homebrew/opt/openjdk/bin/java",
    "/usr/local/bin/java",
]


def _find_java() -> str:
    """Return a working java executable path."""
    # 1. Honour explicit JAVA_HOME env var
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / "java"
        if candidate.exists():
            return str(candidate)

    # 2. Try PATH java (may be a stub on macOS; verify it actually works)
    path_java = shutil.which("java")
    if path_java:
        try:
            probe = subprocess.run(
                [path_java, "-version"],
                capture_output=True,
                timeout=10,
            )
            if probe.returncode == 0 or b"version" in probe.stderr:
                return path_java
        except (OSError, subprocess.TimeoutExpired):
            pass

    # 3. Try well-known macOS / Homebrew paths
    for candidate in _JAVA_FALLBACK_PATHS:
        p = Path(candidate)
        if p.exists():
            return str(p)

    raise VbRuntimeError(
        "java not found. Install Java 17+ and set JAVA_HOME or ensure java is on your PATH."
    )


class Parser:
    def __init__(self, jar_path: str | Path | None = None, java_path: str | None = None):
        self._jar = Path(jar_path) if jar_path else find_jar()
        self._java = java_path or _find_java()

    def parse(self, code: str | bytes, module_name: str = "Module") -> Tree:
        if isinstance(code, str):
            source = code.encode("utf-8")
        else:
            source = code

        with tempfile.NamedTemporaryFile(suffix=".bas", delete=False) as f:
            f.write(source)
            tmp_path = f.name

        try:
            return self._run(tmp_path, source, module_name)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def parse_file(self, path: str | Path) -> Tree:
        p = Path(path)
        source = p.read_bytes()
        return self._run(str(p), source, p.stem)

    def _run(self, file_path: str, source: bytes, module_name: str) -> Tree:
        try:
            result = subprocess.run(
                [self._java, "-jar", str(self._jar),
                 "--file", file_path,
                 "--module-name", module_name],
                capture_output=True,
                timeout=30,
            )
        except FileNotFoundError:
            raise VbRuntimeError(
                f"java not found at {self._java!r}. Install Java 17+ and ensure it is on your PATH."
            )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise ParseError(f"VB6 parse failed for module '{module_name}'", stderr=stderr)

        stdout = result.stdout.decode("utf-8", errors="replace")
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise InternalError(f"JSON decode failed: {e}\nOutput was: {stdout[:200]}")

        root = Node(data, source)
        return Tree(root, source)
