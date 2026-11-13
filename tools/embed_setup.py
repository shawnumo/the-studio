"""Embed the Stop hook, its settings and the protocol section into src/index.html,
so the in-app setup prompt always matches this repo's own files.
Run from the repo root: python tools/embed_setup.py"""
import json, re, pathlib, sys
root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
read = lambda p: (root / p).read_text(encoding="utf-8").replace("\r\n", "\n")
hook = read(".claude/hooks/studio-check.cjs")
settings = read(".claude/settings.json")
claude = read("CLAUDE.md")
m = re.search(r"(## Studio protocol.*?)\n## Rules", claude, re.S)
protocol = m.group(1).strip().replace("the-studio", "{{NAME}}")
data = json.dumps({"hook": hook, "settings": settings, "protocol": protocol}, ensure_ascii=False).replace("</", "<\\/")
src = read("src/index.html")
new, n = re.subn(r"/\*SETUP_JSON\*/.*?/\*END_SETUP_JSON\*/", lambda _: "/*SETUP_JSON*/" + data + "/*END_SETUP_JSON*/", src, flags=re.S)
assert n == 1, n
(root / "src/index.html").write_text(new, encoding="utf-8", newline="\n")
print("embedded", len(data), "chars")
