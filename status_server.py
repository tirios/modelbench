# -*- coding: utf-8 -*-
"""Live benchmark status page.

    python status_server.py          then open http://localhost:5090

Reads only files this benchmark already writes, plus the LM Studio HTTP API.
Nothing here drives the benchmark; it is a window, not a control panel, so it
cannot perturb a run in progress. Standard library only.
"""
import http.server
import json
import os
import re
import socketserver
import time
import urllib.request

PORT = 5090
HERE = os.path.dirname(os.path.abspath(__file__))
LMS = "http://100.107.137.12:1234/api/v0/models"

ARMS = [
    ("qwen38", "Qwen3.8-27B", "local", "the model under test"),
    ("qwen36", "Qwen3.6-27B", "local", "currently installed baseline"),
    ("opus5", "Opus 5", "cloud", ""),
    ("sonnet5", "Sonnet 5", "cloud", ""),
    ("haiku45", "Haiku 4.5", "cloud", ""),
]
CATS = ["code", "reason", "format", "hallucination", "longctx", "hardcode"]
CAT_LABEL = {"code": "coding", "reason": "reasoning", "format": "format",
             "hallucination": "hallucination", "longctx": "long ctx",
             "hardcode": "hard coding"}
TOTAL_TASKS = 27

LINE_RE = re.compile(r"\[(\d+)/(\d+)\]\s+(\S+)\s+\.\.\.(.*)$")
SCORE_RE = re.compile(r"score\s+([0-9.]+)")
TPS_RE = re.compile(r"@\s+([0-9.]+)\s+tok/s")


def _load(path):
    try:
        with open(os.path.join(HERE, path), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def arm_state(key):
    """Merge the easy-tier and hard-tier result files for one arm."""
    merged = {}
    for p in (f"results_{key}.json", f"results_hard_{key}.json"):
        d = _load(p)
        if not d:
            continue
        for r in d.get("results", []):
            merged[r["task"]] = r
    if not merged:
        return None
    rows = list(merged.values())
    by_cat = {}
    for c in CATS:
        v = [r["score"] for r in rows if r.get("cat") == c]
        by_cat[c] = {"n": len(v), "mean": (sum(v) / len(v)) if v else None}
    scored = [r["score"] for r in rows]
    tps = [r["tok_per_s"] for r in rows if r.get("tok_per_s")]
    tok = [r["completion_tokens"] for r in rows if r.get("completion_tokens")]
    fails = [{"task": r["task"], "score": r["score"],
              "detail": (r.get("detail") or "")[:90],
              "truncated": bool(r.get("truncated"))}
             for r in rows if r["score"] < 1.0]
    return {
        "done": len(rows),
        "total": TOTAL_TASKS,
        "passed": sum(1 for s in scored if s >= 1.0),
        "mean": sum(scored) / len(scored),
        "by_cat": by_cat,
        "tok_per_s": (sum(tps) / len(tps)) if tps else None,
        "avg_out_tokens": (sum(tok) / len(tok)) if tok else None,
        "failures": fails,
    }


def current_job():
    """Progress comes from the results files, not the run logs.

    run_local.py rewrites its results JSON after every single task, so the file
    is an accurate live counter even when a run was started without redirecting
    its stdout to a log. Logs are consulted only for the name of the task
    currently in flight, which the JSON cannot know.
    """
    best, best_m = None, 0
    for f in os.listdir(HERE):
        if not (f.startswith("results_") and f.endswith(".json")):
            continue
        m = os.path.getmtime(os.path.join(HERE, f))
        if m > best_m:
            best, best_m = f, m
    if not best:
        return None
    d = _load(best)
    if not d:
        return None
    stem = best[len("results_"):-len(".json")]
    hard = stem.startswith("hard_")
    key = stem[len("hard_"):] if hard else stem
    label = {"qwen38": "Qwen3.8-27B", "qwen36": "Qwen3.6-27B", "opus5": "Opus 5",
             "sonnet5": "Sonnet 5", "haiku45": "Haiku 4.5"}.get(key, key)
    rows = d.get("results", [])
    total = 8 if hard else 19
    age = time.time() - best_m
    recent = [{"i": i + 1, "task": r["task"], "score": r["score"],
               "tok_per_s": r.get("tok_per_s"),
               "truncated": bool(r.get("truncated"))}
              for i, r in enumerate(rows)][-6:]
    # The task in flight is the one after the last written result.
    in_flight = age < 600 and len(rows) < total
    return {
        "log": best,
        "model": label,
        "tier": "hard coding" if hard else "main battery",
        "index": len(rows) + (1 if in_flight else 0),
        "of": total,
        "task": ("working on task %d" % (len(rows) + 1)) if in_flight else
                (rows[-1]["task"] if rows else "-"),
        "in_flight": in_flight,
        "seconds_since_output": round(age, 1),
        "stale": age > 900 and len(rows) < total,
        "finished": len(rows) >= total,
        "elapsed_s": d.get("elapsed_s"),
        "recent": recent,
    }


def box_state():
    try:
        with urllib.request.urlopen(LMS, timeout=6) as r:
            data = json.load(r)
        loaded = [m for m in data.get("data", []) if m.get("state") == "loaded"]
        return {"reachable": True,
                "loaded": [{"id": m["id"], "ctx": m.get("max_context_length"),
                            "quant": m.get("quantization")} for m in loaded],
                "n_indexed": len(data.get("data", []))}
    except Exception as e:
        return {"reachable": False, "error": type(e).__name__}


def snapshot():
    arms = []
    for key, label, where, note in ARMS:
        st = arm_state(key)
        arms.append({"key": key, "label": label, "where": where, "note": note,
                     "state": st})
    return {"arms": arms, "job": current_job(), "box": box_state(),
            "generated": time.strftime("%H:%M:%S")}


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Qwen3.8 benchmark status</title>
<style>
:root{--bg:#fbfbfa;--fg:#1a1a19;--dim:#6b6b68;--line:#e3e3e0;--card:#fff;
      --ok:#2f7d5d;--warn:#b8791f;--bad:#b5442f;--accent:#3b5bdb;}
@media (prefers-color-scheme:dark){:root{--bg:#131314;--fg:#ececea;--dim:#98989a;
      --line:#2b2b2d;--card:#1b1b1d;--ok:#5bbd91;--warn:#e0a44a;--bad:#e0705a;--accent:#7f9cf5;}}
*{box-sizing:border-box}
body{margin:0;padding:28px 22px 60px;background:var(--bg);color:var(--fg);
     font:15px/1.5 ui-sans-serif,-apple-system,"Segoe UI",system-ui,sans-serif;}
.wrap{max-width:1020px;margin:0 auto}
h1{font-size:19px;font-weight:600;margin:0 0 2px}
.sub{color:var(--dim);font-size:13px;margin-bottom:24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
      padding:16px 18px;margin-bottom:16px}
.k{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.06em;
   margin-bottom:10px;font-weight:600}
table{width:100%;border-collapse:collapse}
th{text-align:right;font-weight:500;color:var(--dim);font-size:12px;padding:6px 8px;
   border-bottom:1px solid var(--line)}
th:first-child{text-align:left}
td{padding:8px;border-bottom:1px solid var(--line);text-align:right;
   font-variant-numeric:tabular-nums}
td:first-child{text-align:left}
tr:last-child td{border-bottom:none}
.name{font-weight:600}
.tag{font-size:11px;color:var(--dim);font-weight:400;margin-left:7px}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;
     margin-top:6px;width:150px;margin-left:auto}
.bar i{display:block;height:100%;background:var(--accent)}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.big{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums}
.row{display:flex;gap:26px;flex-wrap:wrap;align-items:baseline}
.pulse{display:inline-block;width:8px;height:8px;border-radius:50%;
       background:var(--ok);margin-right:7px;animation:p 1.6s ease-in-out infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}
.idle{background:var(--dim);animation:none}
.stale{background:var(--warn);animation:none}
code{font:12px ui-monospace,Consolas,monospace;color:var(--dim)}
.fail{font-size:12.5px;padding:3px 0;color:var(--dim)}
.fail b{color:var(--bad);font-weight:600}
.scroll{overflow-x:auto}
</style></head><body><div class="wrap">
<h1>Qwen3.8-27B benchmark</h1>
<div class="sub">Local model on tpml-1 against Opus 5, Sonnet 5 and Haiku 4.5.
27 gated tasks each. Refreshes every 5 seconds.</div>
<div id="app">loading…</div>
<div class="sub" style="margin-top:20px">updated <span id="ts">—</span></div>
</div>
<script>
const pct = (a,b) => b ? Math.round(100*a/b) : 0;
const f2 = v => v==null ? "—" : v.toFixed(2);
function render(d){
  let h = "";
  const j = d.job;
  if (j){
    const cls = j.finished ? "pulse idle" : (j.stale ? "pulse stale" : "pulse");
    const what = j.finished ? "finished" : (j.stale ? "no output for "+j.seconds_since_output+"s" : "running");
    h += `<div class="card"><div class="k">current job</div>
      <div class="row"><div><span class="${cls}"></span><span class="name">${j.model}</span>
      <span class="tag">${j.tier}</span></div>
      <div class="big">${j.index}<span class="tag">of ${j.of}</span></div>
      <div><code>${j.task}</code></div>
      <div class="tag">${what}</div></div>
      <div class="bar" style="margin-left:0;width:100%"><i style="width:${pct(j.finished?j.of:j.index-1,j.of)}%"></i></div>`;
    if (j.recent && j.recent.length){
      h += `<div style="margin-top:12px">`;
      for (const r of j.recent.slice().reverse()){
        const s = r.score==null ? '<span class="tag">in flight…</span>'
          : `<b class="${r.score>=1?'ok':(r.score>0?'warn':'bad')}">${f2(r.score)}</b>`;
        h += `<div class="fail"><code>${r.task}</code> ${s}` +
             (r.tok_per_s?` <span class="tag">${r.tok_per_s} tok/s</span>`:``) +
             (r.truncated?` <b>TRUNCATED</b>`:``) + `</div>`;
      }
      h += `</div>`;
    }
    h += `</div>`;
  }
  h += `<div class="card"><div class="k">overall</div><div class="scroll"><table><tr>
    <th>model</th><th>done</th><th>passed</th><th>mean</th>`;
  for (const c of ${JSON.stringify(CATS_JS)}) h += `<th>${c}</th>`;
  h += `<th>tok/s</th></tr>`;
  for (const a of d.arms){
    const s = a.state;
    if (!s){ h += `<tr><td class="name">${a.label}<span class="tag">${a.where}</span></td>
      <td colspan="9" class="tag" style="text-align:left">not started</td></tr>`; continue; }
    h += `<tr><td class="name">${a.label}<span class="tag">${a.note||a.where}</span></td>
      <td>${s.done}/${s.total}<div class="bar"><i style="width:${pct(s.done,s.total)}%"></i></div></td>
      <td>${s.passed}</td>
      <td class="${s.mean>=0.99?'ok':(s.mean>=0.85?'warn':'bad')}"><b>${f2(s.mean)}</b></td>`;
    for (const c of Object.keys(s.by_cat)){
      const v = s.by_cat[c];
      h += `<td>${v.n? f2(v.mean) : '<span class="tag">—</span>'}</td>`;
    }
    h += `<td>${s.tok_per_s? Math.round(s.tok_per_s) : '<span class="tag">—</span>'}</td></tr>`;
  }
  h += `</table></div></div>`;
  h += `<div class="card"><div class="k">failures so far</div>`;
  let any = false;
  for (const a of d.arms){
    if (!a.state || !a.state.failures.length) continue;
    any = true;
    h += `<div style="margin-bottom:9px"><div class="name" style="font-size:13px">${a.label}</div>`;
    for (const f of a.state.failures)
      h += `<div class="fail"><code>${f.task}</code> <b>${f2(f.score)}</b>` +
           (f.truncated?` <b>TRUNCATED</b>`:``) + ` <span class="tag">${f.detail}</span></div>`;
    h += `</div>`;
  }
  if (!any) h += `<div class="tag">none</div>`;
  h += `</div>`;
  const b = d.box;
  h += `<div class="card"><div class="k">tpml-1</div>`;
  if (!b.reachable) h += `<div class="fail"><b>unreachable</b> <span class="tag">${b.error}</span></div>`;
  else if (!b.loaded.length) h += `<div class="tag">reachable, ${b.n_indexed} models indexed, none loaded</div>`;
  else for (const m of b.loaded)
    h += `<div class="fail"><span class="pulse"></span><code>${m.id}</code>
          <span class="tag">${m.quant||''} · max ${m.ctx} ctx</span></div>`;
  h += `</div>`;
  document.getElementById("app").innerHTML = h;
  document.getElementById("ts").textContent = d.generated;
}
async function tick(){
  try{ render(await (await fetch("/api/status",{cache:"no-store"})).json()); }
  catch(e){ document.getElementById("ts").textContent = "server not responding"; }
}
tick(); setInterval(tick, 5000);
</script></body></html>"""

PAGE = PAGE.replace("${JSON.stringify(CATS_JS)}",
                    json.dumps([CAT_LABEL[c] for c in CATS]))


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/status"):
            body = json.dumps(snapshot()).encode()
            ctype = "application/json"
        else:
            body = PAGE.encode()
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print(f"benchmark status on http://localhost:{PORT}")
    Server(("127.0.0.1", PORT), Handler).serve_forever()
