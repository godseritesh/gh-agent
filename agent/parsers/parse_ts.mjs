#!/usr/bin/env node
// ts-morph based TypeScript/JavaScript parser for the AST indexer.
// Usage: node parse_ts.mjs <repo_dir>
// Outputs JSON with {nodes: [...]} to stdout.

import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative, extname } from "path";

const SKIP_DIRS = new Set([
  "node_modules", "dist", "build", ".git", ".next", "__pycache__",
  "target", ".hg", ".svn",
]);
const EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx"]);

let tsMorph;
try {
  tsMorph = await import("ts-morph");
} catch {
  // ts-morph not installed, fall back to regex output
  console.log(JSON.stringify({ nodes: [] }));
  process.exit(0);
}

const rootDir = process.argv[2];
if (!rootDir) {
  console.error("Usage: node parse_ts.mjs <repo_dir>");
  process.exit(1);
}

const nodes = [];
const project = new tsMorph.Project({ skipAddingFilesFromTsConfig: true });

function walkDir(dir) {
  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!SKIP_DIRS.has(entry.name) && !entry.name.startsWith(".")) {
          walkDir(fullPath);
        }
      } else if (entry.isFile() && EXTENSIONS.has(extname(entry.name).toLowerCase())) {
        processFile(fullPath);
      }
    }
  } catch {}
}

function processFile(filePath) {
  try {
    const rel = relative(rootDir, filePath).replace(/\\/g, "/");
    const source = readFileSync(filePath, "utf-8");

    // Extract imports
    const imports = [];
    const importRegex = /^import\s+(?:\{[^}]*\}\s+from\s+)?['"]([^'"]+)['"]/gm;
    let m;
    while ((m = importRegex.exec(source)) !== null) {
      imports.push(m[1]);
    }

    // Try ts-morph parsing
    try {
      const sf = project.addSourceFileAtPath(filePath);
      if (!sf) return;

      // Classes
      for (const cls of sf.getClasses()) {
        const name = cls.getName() || "Unknown";
        const start = cls.getStartLineNumber();
        const end = cls.getEndLineNumber();
        const doc = cls.getJsDocs().map((d) => d.getDescription()).join(" ") || "";
        const bases = cls.getBaseClass() ? [cls.getBaseClass().getName() || ""] : [];
        const methods = [];
        const methodNodes = [];

        for (const method of cls.getMethods()) {
          const mname = method.getName();
          methods.push(mname);
          const msig = method.getSignature().getText() || mname;
          methodNodes.push({
            id: `${rel}:method:${mname}`,
            file: rel,
            type: "method",
            name: mname,
            signature: msig,
            parent: name,
            line_start: method.getStartLineNumber(),
            line_end: method.getEndLineNumber(),
            docstring: method.getJsDocs().map((d) => d.getDescription()).join(" "),
            body_preview: method.getText().split("\n").slice(0, 20).join("\n"),
          });
        }

        nodes.push({
          id: `${rel}:class:${name}`,
          file: rel,
          type: "class",
          name,
          signature: cls.getText().split("\n")[0] || name,
          line_start: start,
          line_end: end,
          docstring: doc,
          body_preview: cls.getText().split("\n").slice(0, 20).join("\n"),
          imports: [...imports],
          children: methods,
          parents: bases,
        });
        nodes.push(...methodNodes);
      }

      // Top-level functions
      for (const func of sf.getFunctions()) {
        const name = func.getName() || "Anonymous";
        nodes.push({
          id: `${rel}:function:${name}`,
          file: rel,
          type: "function",
          name,
          signature: func.getText().split("\n")[0] || name,
          line_start: func.getStartLineNumber(),
          line_end: func.getEndLineNumber(),
          docstring: func.getJsDocs().map((d) => d.getDescription()).join(" "),
          body_preview: func.getText().split("\n").slice(0, 20).join("\n"),
          imports: [...imports],
          children: [],
          parents: [],
        });
      }
    } catch {
      // ts-morph parse error — skip silently
    }
  } catch {}
}

walkDir(rootDir);
console.log(JSON.stringify({ nodes }));
