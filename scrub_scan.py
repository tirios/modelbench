# -*- coding: utf-8 -*-
"""Pre-publish scan: does anything in this folder carry content that must not leave?

Run before pushing to any remote, and before flipping the repo public.

The scan is self-testing. A detector that cannot fire is worse than no detector,
because it reports "clean" with the same words either way. So `--selftest` plants
each pattern's own canary in a temporary file and fails loudly if any pattern
misses its own bait.

    python scrub_scan.py --selftest     # prove the detector fires
    python scrub_scan.py                # scan this folder
"""
import argparse
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

SKIP_DIRS = {".git", "__pycache__", ".venv", "agent_scratch"}
SKIP_FILES = {"scrub_scan.py"}          # this file names the patterns it hunts
TEXT_EXT = {".py", ".json", ".md", ".txt", ".html", ".yml", ".yaml", ".cfg", ".log"}

# (label, regex, canary that MUST trigger it)
PATTERNS = [
    ("partner name",
     re.compile(r"\bSASI\b"),
     "the SASI wind tunnel"),
    ("absolute user path",
     re.compile(r"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+"),
     r"C:\Users\someone\thing"),
    ("session uuid",
     re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
     "8eea26cb-3376-42ff-abc6-b4e568ebbb4a"),
    ("api key / token",
     re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"),
     "sk-abcdefghijklmnopqrstuvwxyz"),
    ("private key block",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
     "-----BEGIN OPENSSH PRIVATE KEY-----"),
    ("tunnel/rider data hint",
     re.compile(r"\b(CdA|rider_id|run_id)\s*[=:]\s*[0-9.]+"),
     "CdA = 0.213"),
]


def walk():
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn in SKIP_FILES:
                continue
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            yield os.path.join(root, fn)


def scan_text(text, path, hits):
    for label, rx, _ in PATTERNS:
        for m in rx.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append((label, os.path.relpath(path, HERE), line, m.group(0)[:60]))


def selftest():
    """Every pattern must fire on its own canary. Fails loudly if one cannot."""
    print("SELFTEST: planting one canary per pattern\n")
    dead = []
    for label, rx, canary in PATTERNS:
        fired = bool(rx.search(canary))
        print("  %-24s %s" % (label, "FIRES" if fired else "DEAD -- pattern cannot match its own bait"))
        if not fired:
            dead.append(label)
    # and the whole pipeline end to end, through a real file on disk
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "canary.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(c for _, _, c in PATTERNS))
        hits = []
        scan_text(open(p, encoding="utf-8").read(), p, hits)
    labels_hit = {h[0] for h in hits}
    missing = [lab for lab, _, _ in PATTERNS if lab not in labels_hit]
    print("\n  end-to-end: %d/%d patterns fired through a real file"
          % (len(labels_hit), len(PATTERNS)))
    if missing:
        print("  MISSING:", ", ".join(missing))
    ok = not dead and not missing
    print("\nSELFTEST", "PASSED -- the detector can fire" if ok else "FAILED")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    hits = []
    n = 0
    for path in walk():
        n += 1
        try:
            scan_text(open(path, encoding="utf-8", errors="replace").read(), path, hits)
        except Exception as e:
            print("  unreadable: %s (%s)" % (path, type(e).__name__))
    print("scanned %d text files under %s\n" % (n, HERE))
    if not hits:
        print("no matches. NOTE: this is only meaningful if --selftest passes.")
        return 0
    by_label = {}
    for label, rel, line, frag in hits:
        by_label.setdefault(label, []).append((rel, line, frag))
    for label, rows in sorted(by_label.items()):
        print("%s  (%d)" % (label, len(rows)))
        for rel, line, frag in rows[:12]:
            print("    %s:%d  %s" % (rel, line, frag))
        if len(rows) > 12:
            print("    ... and %d more" % (len(rows) - 12))
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
