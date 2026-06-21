from pathlib import Path

from agent.indexer import (
    build_index,
    get_relevant_context,
    index_filename,
    search_index,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_index_filename():
    assert index_filename("SkyLink") == "INDEX-SkyLink.json"
    assert index_filename("nss-platform") == "INDEX-nss-platform.json"


def test_build_index_empty_dir(tmp_path):
    idx = build_index("test-repo", tmp_path)
    assert idx["repo"] == "test-repo"
    assert idx["nodes"] == []
    assert idx["edges"] == []
    assert idx["total_files"] == 0
    assert "built_at" in idx


def test_build_index_python_file(tmp_path):
    src = tmp_path / "hello.py"
    src.write_text(
        '"""Module docstring."""\n'
        "import os\n"
        "from pathlib import Path\n\n"
        "def greet(name: str) -> str:\n"
        '    """Say hello."""\n'
        "    return f'Hello {name}'\n\n"
        "class Calculator:\n"
        '    """A simple calculator."""\n'
        "    def add(self, a: int, b: int) -> int:\n"
        '        """Add two numbers."""\n'
        "        return a + b\n"
    )
    idx = build_index("py-repo", tmp_path)
    assert idx["total_files"] == 1
    node_ids = [n["id"] for n in idx["nodes"]]
    assert any("function:greet" in nid for nid in node_ids)
    assert any("class:Calculator" in nid for nid in node_ids)
    assert any("method:add" in nid for nid in node_ids)


def test_build_index_java_file(tmp_path):
    src = tmp_path / "Hello.java"
    src.write_text(
        "package com.example;\n\n"
        "import java.util.List;\n"
        "import java.util.Map;\n\n"
        "/** A greeting service. */\n"
        "public class Hello {\n"
        "    private String name;\n\n"
        "    public String greet(String input) {\n"
        '        return "Hello " + input;\n'
        "    }\n"
        "}\n"
    )
    idx = build_index("java-repo", tmp_path)
    assert idx["total_files"] == 1
    node_ids = [n["id"] for n in idx["nodes"]]
    assert any("class:Hello" in nid for nid in node_ids)
    assert any("method:greet" in nid for nid in node_ids)


def test_build_index_ts_file(tmp_path):
    src = tmp_path / "app.ts"
    src.write_text(
        'import { Component } from "react";\n\n'
        "/** App component. */\n"
        "class App extends Component {\n"
        "    render() {\n"
        '        return "<div />";\n'
        "    }\n"
        "}\n\n"
        "function bootstrap() {\n"
        "    return new App();\n"
        "}\n"
    )
    idx = build_index("ts-repo", tmp_path)
    assert idx["total_files"] == 1
    node_ids = [n["id"] for n in idx["nodes"]]
    assert any("class:App" in nid for nid in node_ids)
    assert any("function:bootstrap" in nid for nid in node_ids)


def test_build_index_skips_node_modules(tmp_path):
    (tmp_path / "node_modules" / "lib").mkdir(parents=True)
    (tmp_path / "node_modules" / "lib" / "big.js").write_text("var x = 1;")
    src = tmp_path / "index.js"
    src.write_text("function main() { return 42; }\n")

    idx = build_index("js-repo", tmp_path)
    assert idx["total_files"] == 1
    assert all("node_modules" not in n["file"] for n in idx["nodes"])


def test_search_index():
    idx = {
        "nodes": [
            {"id": "a.py:class:Foo", "file": "a.py", "type": "class",
             "name": "Foo", "docstring": "Main class", "signature": "",
             "body_preview": "class Foo:", "imports": ["os"], "children": [],
             "parents": []},
            {"id": "b.py:function:bar", "file": "b.py", "type": "function",
             "name": "bar", "docstring": "Helper", "signature": "",
             "body_preview": "def bar():", "imports": ["sys"], "children": [],
             "parents": []},
            {"id": "c.py:function:baz", "file": "c.py", "type": "function",
             "name": "baz", "docstring": "Another", "signature": "",
             "body_preview": "def baz():", "imports": [], "children": [],
             "parents": []},
        ],
    }

    results = search_index(idx, "foo")
    assert len(results) >= 1
    assert results[0]["name"] == "Foo"

    results = search_index(idx, "nonexistent")
    assert results == []


def test_get_relevant_context():
    idx = {
        "nodes": [
            {"id": "a.py:class:Foo", "file": "a.py", "type": "class",
             "name": "Foo", "docstring": "Main class", "signature": "class Foo",
             "body_preview": "class Foo:", "imports": [], "children": [],
             "parents": []},
        ],
    }
    ctx = get_relevant_context(idx, ["foo"])
    assert "Foo" in ctx
    assert "a.py" in ctx
    assert "Code Index Context" in ctx


def test_get_relevant_context_empty():
    assert get_relevant_context({"nodes": []}, ["foo"]) == ""


def test_build_index_multiple(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "def helper(): return 1\n"
    )
    (tmp_path / "src" / "utils.py").write_text(
        "class Util:\n    def run(self): pass\n"
    )
    idx = build_index("multi-repo", tmp_path)
    assert idx["total_files"] == 2
    assert len(idx["nodes"]) >= 3  # 1 function + 1 class + 1 method
