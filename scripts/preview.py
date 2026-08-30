#!/usr/bin/env python3
"""Self-contained Markdown documentation preview server.

Renders every Markdown file in the repository root as GitHub-flavored HTML and
serves it over HTTP. This is the "application" for this documentation-only
repository: it lets contributors preview the KeyToKey guides locally exactly as
they change them, without pushing to GitHub first.

Usage:
    python3 scripts/preview.py [--host HOST] [--port PORT]
"""

from __future__ import annotations

import argparse
import html
import http.server
import pathlib
import socketserver
import urllib.parse

import markdown

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

MARKDOWN_EXTENSIONS = [
    "extra",          # tables, fenced code, attr_list, etc.
    "sane_lists",
    "toc",
    "codehilite",
    "admonition",
]

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="page">
  <nav class="sidebar">
    <div class="brand">syhwi docs</div>
    {nav}
  </nav>
  <main class="markdown-body">
    {body}
  </main>
</div>
</body>
</html>
"""

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP",
    Helvetica, Arial, sans-serif;
  background: #f6f8fa;
  color: #1f2328;
}
.page { display: flex; min-height: 100vh; }
.sidebar {
  width: 260px;
  flex: 0 0 260px;
  background: #24292f;
  color: #d0d7de;
  padding: 20px 16px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}
.sidebar .brand {
  font-weight: 700;
  font-size: 18px;
  color: #fff;
  margin-bottom: 16px;
  letter-spacing: 0.3px;
}
.sidebar a {
  display: block;
  padding: 8px 10px;
  color: #d0d7de;
  text-decoration: none;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 2px;
}
.sidebar a:hover { background: #32383f; color: #fff; }
.sidebar a.active { background: #388bfd; color: #fff; }
main.markdown-body {
  flex: 1 1 auto;
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 48px 80px;
  background: #fff;
  line-height: 1.6;
}
.markdown-body h1, .markdown-body h2 {
  border-bottom: 1px solid #d8dee4;
  padding-bottom: .3em;
  margin-top: 1.6em;
}
.markdown-body h1 { font-size: 2em; }
.markdown-body img {
  max-width: 100%;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
  margin: 8px 0;
}
.markdown-body code {
  background: rgba(175,184,193,.2);
  padding: .2em .4em;
  border-radius: 6px;
  font-size: 85%;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.markdown-body pre {
  background: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow: auto;
}
.markdown-body pre code { background: none; padding: 0; }
.markdown-body a { color: #0969da; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body table { border-collapse: collapse; margin: 12px 0; }
.markdown-body th, .markdown-body td {
  border: 1px solid #d0d7de;
  padding: 6px 13px;
}
.markdown-body th { background: #f6f8fa; }
.markdown-body blockquote {
  color: #57606a;
  border-left: .25em solid #d0d7de;
  padding: 0 1em;
  margin: 0 0 16px;
}
@media (max-width: 768px) {
  .page { flex-direction: column; }
  .sidebar { width: 100%; height: auto; position: static; }
  main.markdown-body { padding: 24px 20px 60px; }
}
"""


def list_docs() -> list[pathlib.Path]:
    """Return sorted Markdown files in the repository root."""
    return sorted(REPO_ROOT.glob("*.md"), key=lambda p: p.name.lower())


def build_nav(active: str) -> str:
    links = []
    for doc in list_docs():
        cls = "active" if doc.name == active else ""
        href = "/" + urllib.parse.quote(doc.name)
        links.append(
            f'<a class="{cls}" href="{href}">{html.escape(doc.name)}</a>'
        )
    return "\n    ".join(links)


def render_doc(doc: pathlib.Path) -> str:
    md = markdown.Markdown(extensions=MARKDOWN_EXTENSIONS)
    body = md.convert(doc.read_text(encoding="utf-8"))
    return PAGE_TEMPLATE.format(
        title=doc.name,
        css=CSS,
        nav=build_nav(doc.name),
        body=body,
    )


def render_index() -> str:
    docs = list_docs()
    if docs:
        items = "\n".join(
            f'<li><a href="/{urllib.parse.quote(d.name)}">{html.escape(d.name)}</a></li>'
            for d in docs
        )
        body = f"<h1>Documentation</h1>\n<ul>\n{items}\n</ul>"
    else:
        body = "<h1>Documentation</h1>\n<p>No Markdown files found.</p>"
    return PAGE_TEMPLATE.format(
        title="Documentation",
        css=CSS,
        nav=build_nav(""),
        body=body,
    )


class Handler(http.server.BaseHTTPRequestHandler):
    def _send_html(self, content: str, status: int = 200) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if path in ("/", "/index.html"):
            self._send_html(render_index())
            return
        name = path.lstrip("/")
        target = REPO_ROOT / name
        if (
            name.endswith(".md")
            and target.resolve().parent == REPO_ROOT
            and target.exists()
        ):
            self._send_html(render_doc(target))
            return
        self._send_html("<h1>404 Not Found</h1>", status=404)

    def log_message(self, fmt: str, *args) -> None:
        print("[preview] " + (fmt % args))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    docs = [d.name for d in list_docs()]
    print(f"[preview] serving {len(docs)} doc(s) from {REPO_ROOT}: {docs}")
    print(f"[preview] listening on http://{args.host}:{args.port}")

    class ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableServer((args.host, args.port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("[preview] shutting down")


if __name__ == "__main__":
    main()
