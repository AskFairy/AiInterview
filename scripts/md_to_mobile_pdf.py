#!/usr/bin/env python3
"""Convert Markdown to mobile-friendly PDF via HTML + Chrome headless."""

import argparse
import subprocess
import sys
from pathlib import Path

MOBILE_CSS = """
<style>
  @page {
    size: A5 portrait;
    margin: 14mm 12mm 16mm 12mm;
  }
  * { box-sizing: border-box; }
  html {
    -webkit-text-size-adjust: 100%;
  }
  body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
      "Noto Sans CJK SC", sans-serif;
    font-size: 11.5pt;
    line-height: 1.65;
    color: #1a1a1a;
    max-width: 100%;
    margin: 0;
    padding: 0;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  h1 {
    font-size: 17pt;
    line-height: 1.35;
    margin: 0 0 0.6em;
    padding-bottom: 0.35em;
    border-bottom: 2px solid #2563eb;
    color: #0f172a;
  }
  h2 {
    font-size: 14pt;
    margin: 1.2em 0 0.5em;
    color: #1e3a5f;
    page-break-after: avoid;
  }
  h3 {
    font-size: 12.5pt;
    margin: 1em 0 0.4em;
    color: #334155;
    page-break-after: avoid;
  }
  p, li {
    margin: 0.45em 0;
  }
  ul, ol {
    padding-left: 1.25em;
    margin: 0.5em 0;
  }
  li { margin: 0.25em 0; }
  strong { color: #0f172a; }
  hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.2em 0;
  }
  blockquote {
    margin: 0.8em 0;
    padding: 0.6em 0.9em;
    border-left: 3px solid #2563eb;
    background: #f8fafc;
    color: #334155;
    font-size: 10.5pt;
  }
  code {
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 0.9em;
    background: #f1f5f9;
    padding: 0.1em 0.35em;
    border-radius: 3px;
    word-break: break-all;
  }
  pre {
    font-size: 9pt;
    line-height: 1.45;
    background: #f8fafc;
    padding: 0.75em;
    border-radius: 6px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
    line-height: 1.45;
    margin: 0.8em 0;
    page-break-inside: auto;
  }
  thead { display: table-header-group; }
  tr { page-break-inside: avoid; page-break-after: auto; }
  th, td {
    border: 1px solid #cbd5e1;
    padding: 0.45em 0.5em;
    text-align: left;
    vertical-align: top;
    word-break: break-word;
  }
  th {
    background: #eff6ff;
    font-weight: 600;
    color: #1e3a5f;
  }
  tr:nth-child(even) td { background: #fafafa; }
  a {
    color: #2563eb;
    text-decoration: none;
    word-break: break-all;
  }
  .meta {
    font-size: 9.5pt;
    color: #64748b;
    margin-bottom: 1em;
    line-height: 1.5;
  }
  .footer-note {
    margin-top: 2em;
    padding-top: 0.8em;
    border-top: 1px solid #e2e8f0;
    font-size: 9pt;
    color: #94a3b8;
    text-align: center;
  }
</style>
"""

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_chrome() -> str:
    for path in CHROME_PATHS:
        if Path(path).exists():
            return path
    raise FileNotFoundError("未找到 Chrome/Chromium，无法生成 PDF")


def md_to_html(md_path: Path, html_path: Path) -> None:
    cmd = [
        "pandoc",
        str(md_path),
        "-f",
        "markdown",
        "-t",
        "html5",
        "--standalone",
        "-o",
        str(html_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def inject_mobile_styles(html_path: Path) -> None:
    content = html_path.read_text(encoding="utf-8")
    if "</head>" in content:
        content = content.replace("</head>", MOBILE_CSS + "\n</head>", 1)
    else:
        content = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\">{MOBILE_CSS}</head><body>{content}</body></html>"
    html_path.write_text(content, encoding="utf-8")


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = find_chrome()
    html_uri = html_path.resolve().as_uri()
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={pdf_path.resolve()}",
        "--print-to-pdf-no-header",
        html_uri,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not pdf_path.exists():
        raise RuntimeError(
            f"Chrome 生成 PDF 失败:\n{result.stderr or result.stdout}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown → 手机阅读友好 PDF")
    parser.add_argument("input_md", type=Path, help="输入 Markdown 文件")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="输出 PDF 路径（默认同名 .pdf）",
    )
    args = parser.parse_args()

    md_path = args.input_md.resolve()
    if not md_path.exists():
        print(f"文件不存在: {md_path}", file=sys.stderr)
        return 1

    pdf_path = (args.output or md_path.with_suffix(".pdf")).resolve()
    html_path = pdf_path.with_suffix(".html")

    try:
        md_to_html(md_path, html_path)
        inject_mobile_styles(html_path)
        html_to_pdf(html_path, pdf_path)
        print(f"已生成: {pdf_path}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"pandoc 失败: {e.stderr}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
