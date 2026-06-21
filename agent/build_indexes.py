"""Build AST-aware code indexes for all active repos."""
from __future__ import annotations

import json
from pathlib import Path

from agent.config import AgentConfig
from agent.indexer import build_index, index_filename
from agent.scanner import clone_or_pull

ORG = "godseritesh"
WORKSPACE = Path("/tmp/agent-repos")
config = AgentConfig.load(".agent-config.yaml")

for repo_name in config.active_repos:
    print(f"\n=== Indexing {repo_name} ===")
    try:
        clone_dir = clone_or_pull(ORG, repo_name, WORKSPACE)
        index = build_index(repo_name, clone_dir)
        outfile = index_filename(repo_name)
        Path(outfile).write_text(json.dumps(index, indent=2), encoding="utf-8")
        print(f'  {len(index["nodes"])} chunks from {index["total_files"]} files')
    except Exception as e:
        print(f"  FAILED: {e}")
