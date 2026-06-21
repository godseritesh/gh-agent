from __future__ import annotations

from typing import Any

try:
    import libcst as cst  # type: ignore[import-untyped]
    import libcst.helpers as cst_helpers
    HAS_LIBCST = True
except ImportError:
    HAS_LIBCST = False


def _get_docstring(body: list[Any]) -> str:
    if not body:
        return ""
    first = body[0]
    if isinstance(first, cst.SimpleStatementLine):
        for stmt in first.body:
            if isinstance(stmt, cst.Expr) and isinstance(
                stmt.value, cst.SimpleString | cst.ConcatenatedString
            ):
                raw = (
                    stmt.value.raw_value
                    if hasattr(stmt.value, "raw_value")
                    else stmt.value.value
                )
                return raw.strip('"').strip("'").strip()
    return ""


def _get_source_segment(module: cst.Module, node: cst.CSTNode) -> str:
    """Extract source code for a node."""
    code = module.code_for_node(node)
    lines = code.splitlines()
    return "\n".join(lines[:20])


def parse_python(filepath: str | Any, rel: str) -> list[dict[str, Any]]:
    """Parse a Python file using libCST into semantic chunks."""
    if not HAS_LIBCST:
        raise RuntimeError("libCST not installed — pip install libcst")

    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    try:
        module = cst.parse_module(source)
    except Exception:
        return []

    wrapper = cst.MetadataWrapper(module)
    visitor = _IndexVisitor(source, rel)
    wrapper.visit(visitor)

    return visitor.nodes


class _IndexVisitor(cst.CSTVisitor):
    """Collects classes, functions, methods, and imports from a Python module."""

    def __init__(self, source: str, rel: str) -> None:
        self.source = source
        self.rel = rel
        self.nodes: list[dict[str, Any]] = []
        self._imports: list[str] = []
        self._current_class: str | None = None
        self._lines = source.splitlines()

    def _import_name(self, node: cst.BaseSmallStatement) -> None:
        if isinstance(node, cst.Import):
            for alias in node.names:
                self._imports.append(alias.evaluated_name)
        elif isinstance(node, cst.ImportFrom):
            module = cst_helpers.get_full_name_for_node(node.module) if node.module else ""
            for alias in node.names:
                name = alias.evaluated_name
                full = f"{module}.{name}" if module else name
                self._imports.append(full)

    def visit_Import(self, node: cst.Import) -> bool | None:  # noqa: N802
        self._import_name(node)
        return True

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool | None:  # noqa: N802
        self._import_name(node)
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:  # noqa: N802
        name = node.name.value
        bases: list[str] = []
        for base in node.bases:
            if isinstance(base.value, cst.Name):
                bases.append(base.value.value)
            elif isinstance(base.value, cst.Attribute):
                bases.append(base.value.attr.value)

        doc = _get_docstring(node.body.body)
        sig = f"class {name}({', '.join(bases)})" if bases else f"class {name}"
        body_preview = "\n".join(
            self._lines[node.body.lineno - 1 : node.body.end_lineno - 1][:20]
        ) if hasattr(node.body, "lineno") else ""
        line_start = node.lineno if hasattr(node, "lineno") else 0
        line_end = node.end_lineno if hasattr(node, "end_lineno") else line_start

        self._current_class = name
        children: list[str] = []

        top_node = {
            "id": f"{self.rel}:class:{name}",
            "file": self.rel,
            "type": "class",
            "name": name,
            "signature": sig,
            "line_start": line_start,
            "line_end": line_end,
            "docstring": doc,
            "body_preview": body_preview,
            "imports": self._imports[:],
            "children": children,
            "parents": bases,
        }
        self.nodes.append(top_node)

        # Visit class body to collect methods
        self.visit_ClassBody(node.body, children)
        self._current_class = None

        return False

    def visit_ClassBody(self, body: cst.BaseSuite, children: list[str]) -> None:  # noqa: N802
        for stmt in body.body:
            if isinstance(stmt, cst.FunctionDef):
                self._visit_method(stmt, children)

    def _visit_method(self, node: cst.FunctionDef, children: list[str]) -> None:
        name = node.name.value
        children.append(name)

        params = []
        for param in node.params.params:
            if param.name.value == "self":
                continue
            params.append(param.name.value)
        sig = f"def {name}({', '.join(params)})"
        doc = _get_docstring(node.body.body)
        line_start = node.lineno if hasattr(node, "lineno") else 0
        line_end = node.end_lineno if hasattr(node, "end_lineno") else line_start
        body_preview = "\n".join(
            self._lines[node.body.lineno - 1 : node.body.end_lineno - 1][:20]
        ) if hasattr(node.body, "lineno") else ""

        method_node = {
            "id": f"{self.rel}:method:{name}",
            "file": self.rel,
            "type": "method",
            "name": name,
            "signature": sig,
            "parent": self._current_class or "",
            "line_start": line_start,
            "line_end": line_end,
            "docstring": doc,
            "body_preview": body_preview,
        }
        self.nodes.append(method_node)

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:  # noqa: N802
        if self._current_class is not None:
            return False  # handled in ClassBody

        name = node.name.value
        params = [p.name.value for p in node.params.params]
        sig = f"def {name}({', '.join(params)})"
        doc = _get_docstring(node.body.body)
        line_start = node.lineno if hasattr(node, "lineno") else 0
        line_end = node.end_lineno if hasattr(node, "end_lineno") else line_start
        body_preview = "\n".join(
            self._lines[node.body.lineno - 1 : node.body.end_lineno - 1][:20]
        ) if hasattr(node.body, "lineno") else ""

        self.nodes.append({
            "id": f"{self.rel}:function:{name}",
            "file": self.rel,
            "type": "function",
            "name": name,
            "signature": sig,
            "line_start": line_start,
            "line_end": line_end,
            "docstring": doc,
            "body_preview": body_preview,
            "imports": self._imports[:],
            "children": [],
            "parents": [],
        })
        return False
