#!/usr/bin/env python3
"""
linea_tematici.py — Linea Tematici v1.0
14 ETF tematici ad alto momentum: semis, AI, difesa, EM, commodity, gold...
Benchmark: IWMO.MI
"""
import json, datetime
from pathlib import Path
from engine import (download_universo, run_backtest, calc_bm_perf,
                    save_json, BACKTEST_START, BENCHMARK, BENCHMARK2, BENCHMARK3)

BASE_DIR = Path(__file__).parent
OUT_FILE = BASE_DIR / "data" / "linea_tematici.json"

UNIVERSO_LONG = [
    {"ticker":"SMH.MI",  "nome":"VanEck Semiconductor",          "cat":"tematico","sub":"SEMIS"},
    {"ticker":"IART.DE", "nome":"iShares AI Innovation",         "cat":"tematico","sub":"AI"},
    {"ticker":"VAPX.MI", "nome":"Vanguard Dev Asia Pacific",     "cat":"az_em",   "sub":"ASIA_PAC"},
    {"ticker":"AXEE.MI", "nome":"iShares Asia ex Japan Enhanced","cat":"az_em",   "sub":"ASIA_F"},
    {"ticker":"EMEE.MI", "nome":"iShares EM Enhanced Active",    "cat":"az_em",   "sub":"EM_F"},
    {"ticker":"IS3N.DE", "nome":"iShares MSCI EM Small Cap",     "cat":"az_em",   "sub":"EM_SMALL"},
    {"ticker":"DFNS.MI", "nome":"VanEck Defense",                "cat":"tematico","sub":"DEFENSE"},
    {"ticker":"CRUD.MI", "nome":"WT WTI Crude Oil",              "cat":"tematico","sub":"CRUDE"},
    {"ticker":"PHAU.MI", "nome":"WT Physical Gold",              "cat":"tematico","sub":"GOLD"},
    {"ticker":"COPA.MI", "nome":"WT Copper",                     "cat":"tematico","sub":"MATERIALS"},
    {"ticker":"RARE.MI", "nome":"VanEck Rare Earth",             "cat":"tematico","sub":"MATERIALS"},
    {"ticker":"IFFF.MI", "nome":"iShares MSCI Global Financials","cat":"tematico","sub":"FINANCIAL"},
    {"ticker":"AIGA.MI", "nome":"WT Agriculture",                "cat":"tematico","sub":"COMMODITY"},
    {"ticker":"CMOD.MI", "nome":"iShares Commodity",             "cat":"tematico","sub":"COMMODITY"},
]

def main():
    oggi = datetime.date.today().isoformat()
    print(f"Linea Tematici v1.0 — {oggi}")

    run_number = 1
    if OUT_FILE.exists():
        try: run_number = json.loads(OUT_FILE.read_text()).get("run_number",0)+1
        except: pass

    tickers = (set(e["ticker"] for e in UNIVERSO_LONG) |
               {BENCHMARK, BENCHMARK2, BENCHMARK3, "XEON.MI"})
    print(f"\n[1/3] Download {len(tickers)} ticker...")
    etf_data = download_universo(tickers, label="TEM ")

    print(f"\n[2/3] Backtest Linea Tematici (da {BACKTEST_START})...")
    risultato = run_backtest(
        etf_data, UNIVERSO_LONG,
        n_max=8, backtest_start=BACKTEST_START, oggi=oggi, label="Linea Tematici"
    )
    print(f"  Perf: {risultato['performance_totale_pct']:+.1f}% | MDD: {risultato['max_drawdown']:.1f}%")

    print(f"\n[3/3] Benchmark...")
    bm1 = calc_bm_perf(BENCHMARK,  etf_data, BACKTEST_START)
    bm2 = calc_bm_perf(BENCHMARK2, etf_data, BACKTEST_START)
    bm3 = calc_bm_perf(BENCHMARK3, etf_data, BACKTEST_START)
    op1 = round(risultato["performance_totale_pct"]-bm1,2) if bm1 else None
    op2 = round(risultato["performance_totale_pct"]-bm2,2) if bm2 else None
    op3 = round(risultato["performance_totale_pct"]-bm3,2) if bm3 else None
    if bm1: print(f"  IWMO: {bm1:+.1f}% | Outperf: {op1:+.1f}pp")

    output = {
        "generated":   datetime.datetime.utcnow().isoformat(),
        "version":     "linea_tematici_1.0", "run_number": run_number,
        "linea":       "Tematici",
        "descrizione": "14 ETF tematici ad alto momentum — benchmark IWMO (short disattivato)",
        "benchmark":   BENCHMARK, "benchmark2": BENCHMARK2, "benchmark3": BENCHMARK3,
        "benchmark_perf": bm1, "benchmark2_perf": bm2, "benchmark3_perf": bm3,
        "outperformance": op1, "outperformance2": op2, "outperformance3": op3,
        "batte_benchmark": risultato["performance_totale_pct"]>bm1 if bm1 else None,
        **risultato,
    }
    save_json(output, OUT_FILE)

if __name__ == "__main__":
    main()
