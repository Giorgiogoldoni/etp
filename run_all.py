#!/usr/bin/env python3
"""
run_all.py — COMPASS ETP — lancia tutte le linee
"""
import subprocess, sys, datetime

LINEE = [
    ("Linea WT",       "linea_wt.py"),
    ("Linea 2",        "linea_2.py"),
    ("Linea 3",        "linea_3.py"),
    ("Linea Tematici", "linea_tematici.py"),
    ("Linea Full",     "linea_full.py"),
    ("IWMO Timing",    "linea_timing.py"),
]

def main():
    print(f"\n{'='*60}")
    print(f"COMPASS ETP — run_all — {datetime.date.today()}")
    print(f"{'='*60}\n")
    ok = []; err = []
    for nome, script in LINEE:
        print(f"\n{'─'*40}")
        print(f"▶ {nome} ({script})")
        print(f"{'─'*40}")
        try:
            result = subprocess.run(
                [sys.executable, script],
                check=True, capture_output=False
            )
            ok.append(nome)
            print(f"✅ {nome} completato")
        except subprocess.CalledProcessError as e:
            err.append(nome)
            print(f"❌ {nome} ERRORE: {e}")

    print(f"\n{'='*60}")
    print(f"RIEPILOGO: {len(ok)} OK — {len(err)} ERR")
    for n in ok:  print(f"  ✅ {n}")
    for n in err: print(f"  ❌ {n}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
