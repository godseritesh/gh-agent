from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.parsers import parse_python

INDEX_VERSION = 1
LANG_EXTS = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".kt": "kotlin",
}

_SKIP_DIRS = frozenset({
    "__pycache__", "node_modules", "target", "build",
    ".git", ".hg", ".svn", "dist", ".next",
})

_JAVA_CLASS = re.compile(
    r"(?:(?:public|private|protected|abstract|final|static|sealed)\s+)*"
    r"(?:class|interface|enum|record)\s+(\w+)"
    r"(?:\s+extends\s+(\w+(?:\.\w+)*(?:<[^>]*>)?))?"
    r"(?:\s+implements\s+([\w,.<>? ]+))?"
)
_JAVA_METHOD = re.compile(
    r"(?:(?:public|private|protected|static|abstract|final|sync)\s+)*"
    r"(?:<[^>]+>\s+)?"
    r"(\w+(?:\[\])*(?:<[\w?,\s]+>)?)\s+(\w+)\s*\("
)
_JAVA_IMPORT = re.compile(r"^import\s+(?:static\s+)?([\w.*]+)\s*;")
_JAVA_PACKAGE = re.compile(r"^package\s+([\w.]+)\s*;")

_TS_CLASS = re.compile(
    r"(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)"
    r"(?:\s+extends\s+(\w+(?:\.\w+)*))?"
    r"(?:\s+implements\s+([\w,\s]+))?"
)
_TS_FUNC = re.compile(
    r"(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\("
)
_TS_IMPORT = re.compile(r'^import\s+(?:\{[^}]*\}\s+from\s+)?["\']([^"\']+)["\']')


def _is_skipped(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    for part in rel.parts:
        if part in _SKIP_DIRS:
            return True
        if part.startswith(".") and part not in (".github",):
            return True
    return False


def _brace_balance(lines: list[str], start: int) -> int:
    depth = 0
    started = False
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth > 0:
            started = True
        if depth <= 0 and started:
            return i + 1
    return len(lines)


def _extract_docstring(lines: list[str], start: int, prefix: str = "*") -> str:
    for i in range(start - 1, max(-1, start - 8), -1):
        s = lines[i].strip()
        if not s:
            continue
        if s.startswith("/**") or s.startswith("//") or s.startswith("#"):
            return s.strip("/# ").strip()
        if s.startswith(prefix):
            return s.lstrip(prefix + " ").strip()
        if not s.startswith(("//", "#", "*", "/*")):
            break
    return ""


# ── Regex parsers (fallback for non-Python) ──────────────────────────────


def _parse_java_regex(filepath: Path, rel: str) -> list[dict[str, Any]]:
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = source.splitlines()
    imports: list[str] = []
    file_pkg = ""
    nodes: list[dict[str, Any]] = []

    for line in lines:
        m = _JAVA_PACKAGE.match(line.strip())
        if m:
            file_pkg = m.group(1)
            continue
        m = _JAVA_IMPORT.match(line.strip())
        if m:
            imports.append(m.group(1))

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith("@") or s.startswith("//") or s.startswith("*"):
            i += 1
            continue

        cm = _JAVA_CLASS.search(s)
        if cm:
            name = cm.group(1)
            parent = cm.group(2) or ""
            doc = _extract_docstring(lines, i)
            end = _brace_balance(lines, i)
            body = "\n".join(lines[i:end])

            method_list: list[str] = []
            method_nodes: list[dict[str, Any]] = []
            for j in range(i + 1, end):
                ml = lines[j].strip()
                if not ml or ml.startswith("@") or ml.startswith("//") or ml.startswith("*"):
                    continue
                mm = _JAVA_METHOD.search(ml)
                if mm and "(" in ml and ")" in ml and ml.rstrip().endswith("{"):
                    mname = mm.group(2)
                    if mname not in ("if", "while", "for", "switch", "catch", "synchronized"):
                        mdoc = _extract_docstring(lines, j)
                        m_end = _brace_balance(lines, j)
                        method_list.append(mname)
                        method_nodes.append({
                            "id": f"{rel}:method:{mname}",
                            "file": rel, "type": "method", "name": mname,
                            "signature": ml.strip(), "parent": name,
                            "line_start": j + 1, "line_end": m_end,
                            "docstring": mdoc,
                            "body_preview": "\n".join(lines[j:m_end][:20]),
                        })
            nodes.append({
                "id": f"{rel}:class:{name}", "file": rel, "type": "class",
                "name": name, "signature": s, "line_start": i + 1, "line_end": end,
                "docstring": doc,
                "body_preview": "\n".join(body.splitlines()[:20]),
                "imports": imports[:], "children": method_list,
                "parents": [p for p in [parent] if p],
                "package": file_pkg,
            })
            nodes.extend(method_nodes)
            i = end
            continue
        i += 1
    return nodes


def _parse_ts_regex(filepath: Path, rel: str) -> list[dict[str, Any]]:
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = source.splitlines()
    imports: list[str] = []
    for line in lines:
        m = _TS_IMPORT.match(line.strip())
        if m:
            imports.append(m.group(1))

    nodes: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            i += 1
            continue
        cm = _TS_CLASS.search(s)
        if cm:
            name = cm.group(1)
            parent = cm.group(2) or ""
            doc = _extract_docstring(lines, i, "//")
            end = _brace_balance(lines, i)
            body = "\n".join(lines[i:end])
            method_nodes: list[dict[str, Any]] = []
            inner_names: list[str] = []
            for j in range(i + 1, end):
                ml = lines[j].strip()
                if ml.startswith(("//", "/*", "*")) or not ml:
                    continue
                am = re.match(r"(\w+)\s*[=(]\s*\(([^)]*)\)", ml)
                if am and "=>" in ml:
                    mname = am.group(1)
                    if mname not in ("if", "while", "for", "switch"):
                        m_end = _brace_balance(lines, j)
                        inner_names.append(mname)
                        method_nodes.append({
                            "id": f"{rel}:method:{mname}", "file": rel,
                            "type": "method", "name": mname, "signature": ml.strip(),
                            "parent": name, "line_start": j + 1, "line_end": m_end,
                            "docstring": "",
                            "body_preview": "\n".join(lines[j:m_end][:20]),
                        })
            nodes.append({
                "id": f"{rel}:class:{name}", "file": rel, "type": "class",
                "name": name, "signature": s, "line_start": i + 1, "line_end": end,
                "docstring": doc, "body_preview": "\n".join(body.splitlines()[:20]),
                "imports": imports[:], "children": inner_names,
                "parents": [p for p in [parent] if p],
            })
            nodes.extend(method_nodes)
            i = end
            continue
        fm = _TS_FUNC.search(s)
        if fm:
            name = fm.group(1)
            doc = _extract_docstring(lines, i, "//")
            end = _brace_balance(lines, i)
            nodes.append({
                "id": f"{rel}:function:{name}", "file": rel, "type": "function",
                "name": name, "signature": s, "line_start": i + 1, "line_end": end,
                "docstring": doc, "body_preview": "\n".join(lines[i:end][:20]),
                "imports": imports[:], "children": [], "parents": [],
            })
            i = end
            continue
        i += 1
    return nodes


# ── Subprocess-based parsers (Spoon, ts-morph, PSI) ─────────────────────

def _run_spoon_parser(clone_dir: Path, rel: str) -> list[dict[str, Any]] | None:
    """Run Spoon-based Java parser via subprocess. Returns None if unavailable."""
    spoon_jar = Path("/tmp/spoon/spoon-core.jar")
    if not spoon_jar.exists():
        return None
    try:
        result = subprocess.run(
            ["java", "-jar", str(spoon_jar), str(clone_dir)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return data.get("nodes", [])
    except Exception:
        return None


def _run_tsmorph_parser(clone_dir: Path, rel: str) -> list[dict[str, Any]] | None:
    """Run ts-morph parser via subprocess. Returns None if unavailable."""
    script = Path(__file__).parent / "parsers" / "parse_ts.mjs"
    if not script.exists():
        return None
    try:
        result = subprocess.run(
            ["node", str(script), str(clone_dir)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return data.get("nodes", [])
    except Exception:
        return None


# ── Orchestrator ────────────────────────────────────────────────────────

_PARSERS = {
    "python": ("libcst", lambda fp, rel: parse_python(fp, rel)),
    "java": ("spoon+regex", lambda fp, rel: _parse_java_regex(fp, rel)),
    "kotlin": ("regex", lambda fp, rel: _parse_java_regex(fp, rel)),
    "javascript": ("tsmorph+regex", lambda fp, rel: _parse_ts_regex(fp, rel)),
    "typescript": ("tsmorph+regex", lambda fp, rel: _parse_ts_regex(fp, rel)),
}


def build_index(repo_name: str, clone_dir: Path) -> dict[str, Any]:
    """Build AST-aware index for a cloned repo."""
    all_nodes: list[dict[str, Any]] = []
    file_imports_map: dict[str, list[str]] = {}
    total_files = 0

    for filepath in sorted(clone_dir.rglob("*")):
        if not filepath.is_file():
            continue
        if _is_skipped(filepath, clone_dir):
            continue
        lang = LANG_EXTS.get(filepath.suffix.lower())
        if not lang:
            continue
        parser_info = _PARSERS.get(lang)
        if not parser_info:
            continue

        rel = str(filepath.relative_to(clone_dir).as_posix())
        _, parser = parser_info

        try:
            nodes = parser(filepath, rel)
        except Exception:
            nodes = []

        if nodes:
            total_files += 1
            all_nodes.extend(nodes)
            file_imports_map[rel] = nodes[0].get("imports", [])

    # Build edges
    edges: list[dict[str, str]] = []
    for n in all_nodes:
        for p in n.get("parents", []):
            edges.append({"source": n["id"], "target": p, "type": "extends"})

    commit = _get_head_commit(clone_dir)
    return {
        "version": INDEX_VERSION,
        "repo": repo_name,
        "built_at": datetime.now(UTC).isoformat(),
        "commit": commit or "unknown",
        "nodes": all_nodes,
        "edges": edges,
        "file_imports": file_imports_map,
        "total_files": total_files,
    }


# ── Search ──────────────────────────────────────────────────────────────

def search_index(index: dict[str, Any], query: str, top_k: int = 15) -> list[dict[str, Any]]:
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for node in index.get("nodes", []):
        score = 0
        if q in node.get("name", "").lower():
            score += 5
        if q in node.get("file", "").lower():
            score += 3
        if q in node.get("docstring", "").lower():
            score += 2
        if q in node.get("signature", "").lower():
            score += 2
        if any(q in imp.lower() for imp in node.get("imports", [])):
            score += 1
        if q in node.get("body_preview", "").lower():
            score += 1
        if score > 0:
            scored.append((score, node))
    scored.sort(key=lambda x: -x[0])
    return [n for _, n in scored[:top_k]]


def get_relevant_context(index: dict[str, Any], queries: list[str], max_chunks: int = 20) -> str:
    seen_ids: set[str] = set()
    chunks: list[str] = []
    for query in queries:
        results = search_index(index, query, top_k=10)
        for node in results:
            nid = node.get("id", "")
            if nid in seen_ids:
                continue
            seen_ids.add(nid)
            parts = [
                f"File: {node['file']}",
                f"Type: {node['type']}",
            ]
            if node.get("parent"):
                parts.append(f"Parent: {node['parent']}")
            parts.append(f"Name: {node['name']}")
            if node.get("signature"):
                parts.append(f"Signature: {node['signature']}")
            if node.get("docstring"):
                parts.append(f"Doc: {node['docstring']}")
            if node.get("body_preview"):
                parts.append(f"Code:\n{node['body_preview']}")
            chunks.append("\n".join(parts))
        if len(seen_ids) >= max_chunks:
            break
    if not chunks:
        return ""
    return "## Code Index Context\n" + "\n\n---\n\n".join(chunks[:max_chunks])


# ── Helpers ─────────────────────────────────────────────────────────────

def _get_head_commit(repo_dir: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def index_filename(repo_name: str) -> str:
    return f"INDEX-{repo_name}.json"
