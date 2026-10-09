import re
src = open("pedal_adapter.py", encoding="utf-8-sig").read()
body_fn = src[src.index("def build():"):src.index('if __name__')]
lines = body_fn.splitlines()
out = []
for ln in lines:
    out.append(ln)
    m = re.match(r"^(\s+)body = ", ln)
    if m: out.append(f"{m.group(1)}print({ln.strip()[:60]!r}, round(body.volume), len(body.solids()), body.is_valid)")
code = src[:src.index("def build():")] + "\n".join(out) + "\nbuild()\n"
exec(compile(code, "trace", "exec"))



