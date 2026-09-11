#!/usr/bin/env python3
"""
Zero-terminal control surface for screener-eval, for a non-technical Mac user.

Stdlib only (http.server + threading + subprocess + json) — no Flask, no
external web framework. Binds 127.0.0.1 only. Launched by ../Screener.command,
which creates/activates the .venv this runs under (so `import yaml` below is
fine — PyYAML is already a hard dependency of the scripts this UI drives, per
requirements.txt, and is installed into that same .venv before this file ever
imports).

Endpoints (JSON in/out unless noted):
    GET  /                       the single-page UI
    GET  /api/keys               masked key status
    POST /api/keys/save          {anthropic?, openai?} -> writes .env (mode 600)
    POST /api/keys/check         starts a job: run_screen.py --preflight
    GET  /api/jds/count          how many indexed JDs have local text
    GET  /api/pilot/recommendation   parsed reps recommendation from latest pilot report
    POST /api/estimate/pilot     {reps} -> projected cost text for `make pilot`
    POST /api/estimate/full      {reps} -> projected cost text for a full run
    POST /api/run/pilot          {reps, mock} -> starts pilot job
    POST /api/run/full           {ablation, reps, mock} -> starts full-run job
    GET  /api/results            list results/<run_id> dirs
    POST /api/run/analyze        {run_id} -> starts analyze job
    GET  /api/status             current job status
    GET  /api/log?offset=N       job log tail since offset
    POST /api/job/stop           terminate the running job
    GET  /api/reports            list reports/*.md, newest first
    GET  /api/report?name=X      rendered-HTML + raw text of one report
    GET  /api/report/download?name=X   raw .md file
    POST /api/bundle             {run_id} -> zips a results bundle to ~/Downloads
    GET  /api/bundle/file?name=X download the zip just built
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import yaml

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
HOST = "127.0.0.1"
PORT = 8765
ALLOWED_HOSTS = {"127.0.0.1:8765", "localhost:8765", "127.0.0.1", "localhost"}
ALLOWED_ORIGINS = {"null", "http://127.0.0.1:8765", "http://localhost:8765"}

PY = sys.executable  # the venv python this server itself is running under

# ---------------------------------------------------------------------------
# .env handling
# ---------------------------------------------------------------------------

KEY_NAMES = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]


def read_env() -> dict:
    vals = {k: "" for k in KEY_NAMES}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k in vals:
                vals[k] = v.strip()
    return vals


class EnvValueError(ValueError):
    """Raised when a value passed to write_env() is unsafe to store in .env
    (would let a caller inject an extra line — a bogus key, or a control
    line — into the file)."""


def write_env(updates: dict):
    """Merge updates (only non-None/non-empty values overwrite) into .env,
    preserving any other lines already there, and chmod it 600. Raises
    EnvValueError if any value contains a newline/carriage return, which
    would otherwise let a POST body smuggle extra lines into .env."""
    current = read_env()
    for k, v in updates.items():
        if v:  # blank in the form means "leave unchanged"
            if not isinstance(v, str):
                raise EnvValueError(f"{k}: value must be a string")
            v = v.strip()
            if "\n" in v or "\r" in v:
                raise EnvValueError(f"{k}: value must not contain newlines")
            current[k] = v

    existing_lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    seen = set()
    out_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in current:
                out_lines.append(f"{k}={current[k]}")
                seen.add(k)
                continue
        out_lines.append(line)
    for k in KEY_NAMES:
        if k not in seen:
            out_lines.append(f"{k}={current[k]}")

    ENV_PATH.write_text("\n".join(out_lines) + "\n")
    os.chmod(ENV_PATH, 0o600)


def mask(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 4:
        return "*" * len(v)
    return "*" * (len(v) - 4) + v[-4:]


# ---------------------------------------------------------------------------
# Config helpers (cost projections)
# ---------------------------------------------------------------------------

def load_cfg():
    return yaml.safe_load((ROOT / "config" / "config.yaml").read_text())


def count_jds_with_text():
    idx = yaml.safe_load((ROOT / "jds" / "index.yaml").read_text())["jds"]
    return sum(1 for e in idx if (ROOT / "jds" / "text" / f"{e['jd_id']}.txt").exists())


AVG_IN_TOKENS = 900
AVG_OUT_TOKENS = 160


def per_call_cost(model_cfg):
    return (AVG_IN_TOKENS / 1_000_000 * model_cfg["price_input_per_1m"]) + (
        AVG_OUT_TOKENS / 1_000_000 * model_cfg["price_output_per_1m"]
    )


def estimate_pilot(reps):
    cfg = load_cfg()
    lines = [f"Pilot: {reps} reps x {len(cfg['models'])} models, condition A only "
              f"(~{AVG_IN_TOKENS} in / ~{AVG_OUT_TOKENS} out tokens/call, rough estimate):"]
    total = 0.0
    for m in cfg["models"]:
        pc = per_call_cost(m)
        model_total = pc * reps
        total += model_total
        lines.append(f"  {m['key']}: {reps} calls x ${pc:.5f} = ${model_total:.4f}")
    lines.append(f"Projected total: ${total:.4f}")
    return total, "\n".join(lines)


def estimate_full(reps, n_ablations=1):
    cfg = load_cfg()
    n_jds = count_jds_with_text()
    n_models = len(cfg["models"])
    calls_per_model = n_jds * n_ablations * reps * 2  # A + B
    lines = [f"Full run: {n_jds} JDs x {n_models} models x {n_ablations} ablation(s) x "
              f"{reps} reps x 2 conditions ({calls_per_model * n_models} calls total):"]
    total = 0.0
    for m in cfg["models"]:
        pc = per_call_cost(m)
        model_total = pc * calls_per_model
        total += model_total
        lines.append(f"  {m['key']}: {calls_per_model} calls x ${pc:.5f} = ${model_total:.4f}")
    lines.append(f"Projected total: ${total:.4f}")
    return total, n_jds, "\n".join(lines)


def latest_real_run_id():
    """Newest results/real-* run dir, for the "Resume last run" checkbox.
    real-* run ids are UTC timestamps (YYYYMMDDTHHMMSSZ) so lexicographic
    order is chronological order."""
    results_dir = ROOT / "results"
    if not results_dir.exists():
        return None
    candidates = sorted(p.name for p in results_dir.iterdir() if p.is_dir() and p.name.startswith("real-"))
    return candidates[-1] if candidates else None


def latest_pilot_recommendation():
    reports_dir = ROOT / "reports"
    candidates = sorted(reports_dir.glob("pilot_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in candidates:
        m = re.search(r"Recommended rep count for a real run \(max across models\): \*\*(\d+)\*\*",
                       p.read_text())
        if m:
            return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Single-job runner
# ---------------------------------------------------------------------------

class JobManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.name = None
        self.log = ""
        self.status = "idle"  # idle | running | finished
        self.exit_code = None
        self._reader_thread = None

    def start(self, name, steps):
        """steps: list of arg-list commands run in sequence, stop on first failure."""
        with self.lock:
            if self.status == "running":
                return False, "a job is already running"
            self.proc = None
            self.name = name
            self.log = ""
            self.status = "running"
            self.exit_code = None
        self._reader_thread = threading.Thread(target=self._run_steps, args=(steps,), daemon=True)
        self._reader_thread.start()
        return True, "started"

    def _append(self, text):
        with self.lock:
            self.log += text

    def _run_steps(self, steps):
        final_code = 0
        for cmd in steps:
            self._append(f"$ {' '.join(cmd)}\n")
            try:
                proc = subprocess.Popen(
                    cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
            except Exception as e:  # noqa: BLE001
                self._append(f"[error launching command: {e}]\n")
                final_code = 1
                break
            with self.lock:
                self.proc = proc
            for line in proc.stdout:
                self._append(line)
            proc.wait()
            with self.lock:
                self.proc = None
            if proc.returncode != 0:
                final_code = proc.returncode
                self._append(f"\n[step exited {proc.returncode} — stopping]\n")
                break
        with self.lock:
            self.status = "finished"
            self.exit_code = final_code

    def stop(self):
        with self.lock:
            proc = self.proc
        if not proc:
            return False
        try:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:  # noqa: BLE001
            pass
        self._append("\n[stopped by user]\n")
        with self.lock:
            self.status = "finished"
            self.exit_code = -1
        return True

    def state(self):
        with self.lock:
            return {"status": self.status, "name": self.name, "exit_code": self.exit_code}

    def log_since(self, offset):
        with self.lock:
            text = self.log[offset:]
            new_offset = len(self.log)
        return text, new_offset


jobs = JobManager()

# ---------------------------------------------------------------------------
# Minimal markdown -> HTML (headings, bold, inline code, tables, lists)
# ---------------------------------------------------------------------------

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inline_md(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def render_markdown(text):
    lines = text.splitlines()
    out = []
    i = 0
    in_ul = in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            close_lists()
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_lists()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline_md(m.group(2))}</h{level}>")
            i += 1
            continue

        if re.match(r"^\|.*\|$", stripped) and i + 1 < len(lines) and re.match(
                r"^\|?[\s:|-]+\|?$", lines[i + 1].strip()):
            close_lists()
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            out.append("<table><thead><tr>" +
                        "".join(f"<th>{inline_md(c)}</th>" for c in header_cells) +
                        "</tr></thead><tbody>")
            i += 2
            while i < len(lines) and re.match(r"^\|.*\|$", lines[i].strip()):
                row_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in row_cells) + "</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline_md(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_md(m.group(1))}</li>")
            i += 1
            continue

        if stripped == "---":
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        close_lists()
        # collapse trailing double-space "hard break" markdown into <br>
        para_line = re.sub(r"\s{2,}$", "<br>", stripped)
        out.append(f"<p>{inline_md(para_line)}</p>")
        i += 1

    close_lists()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------

INDEX_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Screener</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #fafafa; color: #111; margin: 0; padding: 0; }
  header { padding: 16px 24px; border-bottom: 1px solid #ddd; background: #fff; }
  header h1 { font-size: 18px; margin: 0; }
  header p { margin: 4px 0 0; color: #666; font-size: 13px; }
  nav { display: flex; gap: 4px; padding: 0 24px; background: #fff; border-bottom: 1px solid #ddd; }
  nav button { border: none; background: none; padding: 12px 14px; font-size: 14px; cursor: pointer;
               border-bottom: 2px solid transparent; color: #555; }
  nav button.active { color: #111; border-bottom-color: #111; font-weight: 600; }
  main { max-width: 780px; margin: 0 auto; padding: 24px; }
  section { display: none; }
  section.active { display: block; }
  h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .03em; color: #444; margin: 24px 0 8px; }
  h2:first-child { margin-top: 0; }
  .card { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin-bottom: 16px; }
  label { display: block; font-size: 13px; color: #333; margin-bottom: 4px; }
  input[type=password], input[type=text], input[type=number], select {
      width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;
      margin-bottom: 12px; font-family: inherit; }
  button.btn { background: #111; color: #fff; border: none; padding: 9px 16px; border-radius: 4px;
        font-size: 14px; cursor: pointer; margin-right: 8px; }
  button.btn.secondary { background: #fff; color: #111; border: 1px solid #ccc; }
  button.btn.danger { background: #b00020; }
  button.btn:disabled { opacity: .5; cursor: not-allowed; }
  pre#log { background: #111; color: #ddd; padding: 12px; border-radius: 6px; height: 360px;
        overflow-y: auto; white-space: pre-wrap; word-break: break-word; font-size: 12px;
        font-family: ui-monospace, Menlo, monospace; }
  .status-line { font-size: 13px; color: #444; margin-bottom: 10px; }
  .status-line.running { color: #a15c00; }
  .status-line.finished-ok { color: #146c2e; }
  .status-line.finished-err { color: #b00020; }
  .muted { color: #777; font-size: 13px; }
  .estimate { background: #f4f4f4; border: 1px solid #ddd; border-radius: 4px; padding: 10px;
        font-size: 13px; white-space: pre-wrap; font-family: ui-monospace, Menlo, monospace;
        margin-bottom: 10px; display: none; }
  ul.reports { list-style: none; padding: 0; margin: 0; }
  ul.reports li { padding: 8px 0; border-bottom: 1px solid #eee; display: flex;
        justify-content: space-between; align-items: center; }
  ul.reports a.report-link { cursor: pointer; color: #111; text-decoration: underline; }
  #reportView h1, #reportView h2, #reportView h3 { margin-top: 18px; }
  #reportView table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; }
  #reportView th, #reportView td { border: 1px solid #ddd; padding: 5px 8px; text-align: left; }
  .row { display: flex; gap: 8px; align-items: flex-end; flex-wrap: wrap; }
  .row > div { flex: 1; min-width: 140px; }
  .small { font-size: 12px; color: #888; }
</style>
</head>
<body>
<header>
  <h1>Screener</h1>
  <p>screener-eval control panel — no Terminal needed.</p>
</header>
<nav>
  <button data-tab="keys" class="active">Keys</button>
  <button data-tab="run">Run</button>
  <button data-tab="log">Log</button>
  <button data-tab="reports">Reports</button>
</nav>
<main>

<section id="tab-keys" class="active">
  <h2>API keys</h2>
  <div class="card">
    <label>Anthropic API key</label>
    <input type="password" id="anthropicKey" placeholder="paste key or leave blank to keep current">
    <label>OpenAI API key</label>
    <input type="password" id="openaiKey" placeholder="paste key or leave blank to keep current">
    <div class="small" id="keyStatus"></div>
    <br>
    <button class="btn" id="saveKeysBtn">Save</button>
    <button class="btn secondary" id="checkKeysBtn">Check keys</button>
  </div>
</section>

<section id="tab-run">
  <h2>Pilot</h2>
  <div class="card">
    <p class="muted">One real job description, both models, N repeated calls each — sizes the
    rep count for a full run before you spend more.</p>
    <div class="row">
      <div><label>Reps</label><input type="number" id="pilotReps" value="10" min="1"></div>
    </div>
    <div class="estimate" id="pilotEstimate"></div>
    <button class="btn" id="pilotBtn">Run pilot</button>
  </div>

  <h2>Full run</h2>
  <div class="card">
    <div class="row">
      <div>
        <label>Ablation</label>
        <select id="fullAblation">
          <option value="institution_swap">institution_swap</option>
          <option value="evidence_links">evidence_links</option>
        </select>
      </div>
      <div><label>Reps</label><input type="number" id="fullReps" value="5" min="1"></div>
    </div>
    <p class="muted" id="jdCountLine"></p>
    <label style="display:flex; align-items:center; gap:6px; font-size:13px; margin-bottom:12px;">
      <!-- No `checked` attribute: defaults OFF on every page load, so a plain
           click of "Run full" always starts a new run at the ablation/reps
           chosen above — resuming is opt-in, never accidental. -->
      <input type="checkbox" id="resumeLastRun" style="width:auto; margin:0;">
      Resume last run instead (continues the newest interrupted <code>real-*</code> run — skips
      the ablation/reps above and any calls it already completed)
    </label>
    <div class="estimate" id="fullEstimate"></div>
    <button class="btn" id="fullBtn">Run full</button>
  </div>

  <h2>Analyze</h2>
  <div class="card">
    <label>Run</label>
    <select id="analyzeRunId"></select>
    <button class="btn" id="analyzeBtn">Analyze</button>
  </div>
</section>

<section id="tab-log">
  <h2>Job log</h2>
  <div class="status-line" id="statusLine">idle</div>
  <div class="small" id="etaLine" style="margin-bottom:8px;"></div>
  <button class="btn danger" id="stopBtn" disabled>Stop</button>
  <pre id="log"></pre>
</section>

<section id="tab-reports">
  <h2>Reports</h2>
  <div class="card">
    <div class="row">
      <div>
        <label>Download results bundle for run</label>
        <select id="bundleRunId"></select>
      </div>
    </div>
    <button class="btn secondary" id="bundleBtn">Download results bundle</button>
    <span class="small" id="bundleStatus"></span>
  </div>
  <div class="card">
    <ul class="reports" id="reportList"></ul>
  </div>
  <div class="card" id="reportViewCard" style="display:none">
    <a id="reportDownload" class="small" href="#" download>Download raw file</a>
    <div id="reportView"></div>
  </div>
</section>

</main>
<script>
const MOCK = new URLSearchParams(location.search).get('mock') === '1';

function $(id) { return document.getElementById(id); }

document.querySelectorAll('nav button').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('main section').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    $('tab-' + b.dataset.tab).classList.add('active');
  });
});

async function api(path, opts) {
  const res = await fetch(path, opts);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch (e) { data = { error: text }; }
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

// ---------- Keys ----------
async function loadKeys() {
  const d = await api('/api/keys');
  $('anthropicKey').placeholder = d.anthropic_masked ? d.anthropic_masked + ' (saved)' : 'paste key';
  $('openaiKey').placeholder = d.openai_masked ? d.openai_masked + ' (saved)' : 'paste key';
  $('keyStatus').textContent = (d.anthropic_masked ? 'Anthropic key set. ' : 'Anthropic key not set. ') +
                                (d.openai_masked ? 'OpenAI key set.' : 'OpenAI key not set.');
}
$('saveKeysBtn').onclick = async () => {
  await api('/api/keys/save', { method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ anthropic: $('anthropicKey').value, openai: $('openaiKey').value }) });
  $('anthropicKey').value = ''; $('openaiKey').value = '';
  await loadKeys();
  alert('Saved.');
};
$('checkKeysBtn').onclick = async () => {
  await startJob('/api/keys/check', {});
  switchToLog();
};

function switchToLog() {
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('main section').forEach(x => x.classList.remove('active'));
  document.querySelector('nav button[data-tab=log]').classList.add('active');
  $('tab-log').classList.add('active');
}

async function startJob(path, body) {
  try {
    await api(path, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  } catch (e) {
    alert('Could not start: ' + e.message);
  }
}

// ---------- Run tab ----------
let pilotArmed = false, fullArmed = false;

$('pilotBtn').onclick = async () => {
  const reps = parseInt($('pilotReps').value || '10', 10);
  if (!pilotArmed) {
    const d = await api('/api/estimate/pilot', { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ reps }) });
    $('pilotEstimate').style.display = 'block';
    $('pilotEstimate').textContent = d.text;
    $('pilotBtn').textContent = 'Confirm — run pilot now';
    pilotArmed = true;
    return;
  }
  pilotArmed = false;
  $('pilotBtn').textContent = 'Run pilot';
  $('pilotEstimate').style.display = 'none';
  await startJob('/api/run/pilot', { reps, mock: MOCK });
  switchToLog();
};

$('fullBtn').onclick = async () => {
  const resume = $('resumeLastRun').checked;
  const reps = parseInt($('fullReps').value || '5', 10);
  const ablation = $('fullAblation').value;
  if (resume) {
    // No estimate step for resume — it continues an already-costed run, not a new one.
    await startJob('/api/run/full', { resume: true, mock: MOCK });
    switchToLog();
    return;
  }
  if (!fullArmed) {
    const d = await api('/api/estimate/full', { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ reps, ablation }) });
    $('fullEstimate').style.display = 'block';
    $('fullEstimate').textContent = d.text;
    $('fullBtn').textContent = 'Confirm — run full now';
    fullArmed = true;
    return;
  }
  fullArmed = false;
  $('fullBtn').textContent = 'Run full';
  $('fullEstimate').style.display = 'none';
  await startJob('/api/run/full', { reps, ablation, mock: MOCK });
  switchToLog();
};

$('analyzeBtn').onclick = async () => {
  const runId = $('analyzeRunId').value;
  if (!runId) { alert('No run selected'); return; }
  await startJob('/api/run/analyze', { run_id: runId });
  switchToLog();
};

async function loadJdCount() {
  const d = await api('/api/jds/count');
  $('jdCountLine').textContent = d.count + ' job description(s) with text available locally.';
}
async function loadPilotRecommendation() {
  const d = await api('/api/pilot/recommendation');
  if (d.reps) $('fullReps').value = d.reps;
}
async function loadResultsList() {
  const d = await api('/api/results');
  for (const sel of [$('analyzeRunId'), $('bundleRunId')]) {
    sel.innerHTML = '';
    d.run_ids.forEach(r => {
      const o = document.createElement('option'); o.value = r; o.textContent = r; sel.appendChild(o);
    });
  }
}

// ---------- Log tab ----------
let logOffset = 0;
let fullLog = '';
$('stopBtn').onclick = async () => { await api('/api/job/stop', { method: 'POST' }); };

async function pollLog() {
  try {
    const s = await api('/api/status');
    const line = $('statusLine');
    if (s.status === 'running') {
      line.textContent = 'running: ' + s.name;
      line.className = 'status-line running';
      $('stopBtn').disabled = false;
    } else if (s.status === 'finished') {
      line.textContent = (s.name || 'job') + ' finished (exit code ' + s.exit_code + ')';
      line.className = 'status-line ' + (s.exit_code === 0 ? 'finished-ok' : 'finished-err');
      $('stopBtn').disabled = true;
      if (s.exit_code === 0) { loadResultsList(); loadReportsList(); }
    } else {
      line.textContent = 'idle';
      line.className = 'status-line';
      $('stopBtn').disabled = true;
    }
    const d = await api('/api/log?offset=' + logOffset);
    if (d.text) {
      const pre = $('log');
      const atBottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 20;
      pre.textContent += d.text;
      fullLog += d.text;
      logOffset = d.offset;
      if (atBottom) pre.scrollTop = pre.scrollHeight;
      // scripts/run_screen.py prints "[progress] done/total done, elapsed Xs, rate Y/min, ETA Zs"
      // every 20 completed calls — surface the latest one above the raw log.
      const matches = fullLog.match(/\[progress\].*/g);
      $('etaLine').textContent = matches ? matches[matches.length - 1] : '';
    }
  } catch (e) { /* server not ready yet */ }
  setTimeout(pollLog, 1000);
}

// ---------- Reports tab ----------
async function loadReportsList() {
  const d = await api('/api/reports');
  const ul = $('reportList');
  ul.innerHTML = '';
  d.reports.forEach(r => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.className = 'report-link';
    a.textContent = r.name;
    a.onclick = () => openReport(r.name);
    const span = document.createElement('span');
    span.className = 'small';
    span.textContent = r.mtime;
    li.appendChild(a); li.appendChild(span);
    ul.appendChild(li);
  });
}
async function openReport(name) {
  const d = await api('/api/report?name=' + encodeURIComponent(name));
  $('reportViewCard').style.display = 'block';
  $('reportView').innerHTML = d.html;
  $('reportDownload').href = '/api/report/download?name=' + encodeURIComponent(name);
}
$('bundleBtn').onclick = async () => {
  const runId = $('bundleRunId').value;
  $('bundleStatus').textContent = 'Building...';
  try {
    const d = await api('/api/bundle', { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ run_id: runId }) });
    $('bundleStatus').innerHTML = 'Saved to ' + d.path + ' — <a href="/api/bundle/file?name=' +
      encodeURIComponent(d.filename) + '">download</a>';
  } catch (e) {
    $('bundleStatus').textContent = 'Failed: ' + e.message;
  }
};

loadKeys();
loadJdCount();
loadPilotRecommendation();
loadResultsList();
loadReportsList();
pollLog();
</script>
</body></html>
"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "ScreenerUI/1.0"

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return host in ALLOWED_HOSTS

    def _origin_ok(self):
        """CSRF guard for POSTs: a same-origin browser request either omits
        Origin (older browsers, same-origin GET-turned-POST navigations) or
        sends 'null' (sandboxed contexts) or our own origin. Anything else —
        a cross-origin page's fetch()/form POST — is rejected. Falls back to
        Referer when Origin is absent, since some clients send only that."""
        origin = self.headers.get("Origin")
        if origin is not None:
            return origin in ALLOWED_ORIGINS
        referer = self.headers.get("Referer")
        if referer is not None:
            return any(referer == a or referer.startswith(a + "/") for a in ALLOWED_ORIGINS if a != "null")
        return True

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, code=200):
        body = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text_file(self, data: bytes, filename: str, content_type="text/plain"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode())
        except Exception:  # noqa: BLE001
            return {}

    def do_GET(self):
        if not self._host_ok():
            self._send_json({"error": "forbidden host"}, 403)
            return
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/":
            self._send_html(INDEX_HTML)
        elif path == "/api/keys":
            env = read_env()
            self._send_json({
                "anthropic_masked": mask(env["ANTHROPIC_API_KEY"]),
                "openai_masked": mask(env["OPENAI_API_KEY"]),
            })
        elif path == "/api/jds/count":
            self._send_json({"count": count_jds_with_text()})
        elif path == "/api/pilot/recommendation":
            self._send_json({"reps": latest_pilot_recommendation()})
        elif path == "/api/results":
            results_dir = ROOT / "results"
            run_ids = sorted([p.name for p in results_dir.iterdir() if p.is_dir()]) if results_dir.exists() else []
            self._send_json({"run_ids": run_ids})
        elif path == "/api/status":
            self._send_json(jobs.state())
        elif path == "/api/log":
            offset = int(qs.get("offset", ["0"])[0])
            text, new_offset = jobs.log_since(offset)
            self._send_json({"text": text, "offset": new_offset})
        elif path == "/api/reports":
            reports_dir = ROOT / "reports"
            items = []
            if reports_dir.exists():
                for p in sorted(reports_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
                    items.append({"name": p.name,
                                  "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
            self._send_json({"reports": items})
        elif path == "/api/report":
            name = qs.get("name", [""])[0]
            safe = Path(name).name  # no traversal
            fp = ROOT / "reports" / safe
            if not fp.exists() or fp.suffix != ".md":
                self._send_json({"error": "not found"}, 404)
                return
            text = fp.read_text()
            self._send_json({"html": render_markdown(text), "raw": text})
        elif path == "/api/report/download":
            name = qs.get("name", [""])[0]
            safe = Path(name).name
            fp = ROOT / "reports" / safe
            if not fp.exists():
                self._send_json({"error": "not found"}, 404)
                return
            self._send_text_file(fp.read_bytes(), safe, "text/markdown")
        elif path == "/api/bundle/file":
            name = qs.get("name", [""])[0]
            safe = Path(name).name
            fp = Path.home() / "Downloads" / safe
            if not fp.exists():
                self._send_json({"error": "not found"}, 404)
                return
            self._send_text_file(fp.read_bytes(), safe, "application/zip")
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._host_ok():
            self._send_json({"error": "forbidden host"}, 403)
            return
        if not self._origin_ok():
            self._send_json({"error": "forbidden origin"}, 403)
            return
        path = urlparse(self.path).path
        body = self._read_json_body()

        if path == "/api/keys/save":
            try:
                write_env({"ANTHROPIC_API_KEY": body.get("anthropic", ""),
                           "OPENAI_API_KEY": body.get("openai", "")})
            except EnvValueError as e:
                self._send_json({"error": str(e)}, 400)
                return
            self._send_json({"ok": True})

        elif path == "/api/keys/check":
            ok, msg = jobs.start("check keys", [[PY, "scripts/run_screen.py", "--preflight"]])
            self._send_json({"ok": ok, "message": msg}, 200 if ok else 409)

        elif path == "/api/estimate/pilot":
            reps = int(body.get("reps", 10))
            total, text = estimate_pilot(reps)
            self._send_json({"total": total, "text": text})

        elif path == "/api/estimate/full":
            reps = int(body.get("reps", 5))
            total, n_jds, text = estimate_full(reps)
            self._send_json({"total": total, "n_jds": n_jds, "text": text})

        elif path == "/api/run/pilot":
            reps = int(body.get("reps", 10))
            mock = bool(body.get("mock")) or bool(os.environ.get("MOCK"))
            cmd = [PY, "analysis/pilot.py", "--jd", "anthropic-pm-beneficial-deployments-001",
                   "--reps", str(reps)]
            if mock:
                cmd.append("--mock")
            ok, msg = jobs.start("pilot", [[PY, "scripts/make_variants.py"], cmd])
            self._send_json({"ok": ok, "message": msg}, 200 if ok else 409)

        elif path == "/api/run/full":
            mock = bool(body.get("mock")) or bool(os.environ.get("MOCK"))
            concurrency = load_cfg().get("run", {}).get("concurrency", 8)

            if bool(body.get("resume")):
                run_id = latest_real_run_id()
                if not run_id:
                    self._send_json({"error": "no previous real run (results/real-*) found to resume"}, 400)
                    return
                cmd = [PY, "scripts/run_screen.py", "--resume", run_id, "--concurrency", str(concurrency)]
                ok, msg = jobs.start(f"resume {run_id}", [cmd])
                self._send_json({"ok": ok, "message": msg, "run_id": run_id}, 200 if ok else 409)
                return

            reps = int(body.get("reps", 5))
            ablation = body.get("ablation", "institution_swap")
            if ablation not in ("institution_swap", "evidence_links"):
                self._send_json({"error": "invalid ablation"}, 400)
                return
            cmd = [PY, "scripts/run_screen.py", "--reps", str(reps), "--ablation", ablation,
                   "--concurrency", str(concurrency)]
            if mock:
                cmd.append("--mock")
            ok, msg = jobs.start("full run", [cmd])
            self._send_json({"ok": ok, "message": msg}, 200 if ok else 409)

        elif path == "/api/run/analyze":
            run_id = body.get("run_id", "")
            safe = Path(run_id).name
            if not safe or not (ROOT / "results" / safe).exists():
                self._send_json({"error": "unknown run_id"}, 400)
                return
            ok, msg = jobs.start("analyze", [[PY, "analysis/analyze.py", safe]])
            self._send_json({"ok": ok, "message": msg}, 200 if ok else 409)

        elif path == "/api/job/stop":
            stopped = jobs.stop()
            self._send_json({"stopped": stopped})

        elif path == "/api/bundle":
            run_id = body.get("run_id", "")
            safe = Path(run_id).name
            run_dir = ROOT / "results" / safe
            downloads = Path.home() / "Downloads"
            downloads.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"screener-eval-results-{date_str}.zip"
            zpath = downloads / filename
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
                reports_dir = ROOT / "reports"
                if reports_dir.exists():
                    for p in reports_dir.glob("*.md"):
                        zf.write(p, arcname=str(Path("reports") / p.name))
                if run_dir.exists():
                    for fname in ("manifest.json", "calls.jsonl"):
                        fp = run_dir / fname
                        if fp.exists():
                            zf.write(fp, arcname=str(Path("results") / safe / fname))
            self._send_json({"ok": True, "path": str(zpath), "filename": filename})

        else:
            self._send_json({"error": "not found"}, 404)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Screener UI listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
