#!/usr/bin/env python3
"""
linea_wt.py — Linea WisdomTree v1.0
6 ETF WisdomTree — pesi dinamici score^1.5 — peso minimo 1% memoria
Benchmark: IWMO.MI
"""
import json, datetime
from pathlib import Path
from engine import (fetch_yahoo, download_universo, run_backtest,
                    calc_bm_perf, save_json, BACKTEST_START, BENCHMARK, BENCHMARK2)

BASE_DIR = Path(__file__).parent
OUT_FILE = BASE_DIR / "data" / "linea_wt.json"

UNIVERSO_LONG = [
    {"ticker":"WS5X.MI","nome":"WT Euro Stoxx 50",             "cat":"az_europa","sub":"EU"},
    {"ticker":"WWRD.MI","nome":"WT World",                      "cat":"az_globale","sub":"GLOBAL"},
    {"ticker":"WRTY.MI","nome":"WT Russell 2000 Efficient Core","cat":"az_usa",   "sub":"US_SMALL"},
    {"ticker":"WNAS.MI","nome":"WT Nasdaq-100",                 "cat":"az_usa",   "sub":"TECH"},
    {"ticker":"WSPE.MI","nome":"WT S&P 500 EUR Hedged",         "cat":"az_usa",   "sub":"US_EUR"},
    {"ticker":"WSPX.MI","nome":"WT S&P 500",                    "cat":"az_usa",   "sub":"US"},
]

UNIVERSO_SHORT = [
    {"ticker":"3USS.MI","nome":"WT S&P 500 3x Short",    "cat":"short","sub":"SHORT_US"},
    {"ticker":"SC3S.MI","nome":"S&P 500 3x Short",       "cat":"short","sub":"SHORT_US"},
    {"ticker":"3EUS.MI","nome":"Euro Stoxx 50 3x Short", "cat":"short","sub":"SHORT_EU"},
    {"ticker":"3M7S.MI","nome":"MSCI G7 3x Short",       "cat":"short","sub":"SHORT_G7"},
]

def main():
    oggi = datetime.date.today().isoformat()
    print(f"Linea WT v1.0 — {oggi}")

    run_number = 1
    if OUT_FILE.exists():
        try: run_number = json.loads(OUT_FILE.read_text()).get("run_number",0)+1
        except: pass

    tickers = (set(e["ticker"] for e in UNIVERSO_LONG) |
               set(e["ticker"] for e in UNIVERSO_SHORT) |
               {BENCHMARK, BENCHMARK2, "XEON.MI"})
    print(f"\n[1/3] Download {len(tickers)} ticker...")
    etf_data = download_universo(tickers, label="WT ")

    print(f"\n[2/3] Backtest Linea WT (da {BACKTEST_START})...")
    risultato = run_backtest(
        etf_data, UNIVERSO_LONG, UNIVERSO_SHORT,
        n_max=6, backtest_start=BACKTEST_START, oggi=oggi, label="Linea WT",
        abilita_short=False
    )
    print(f"  Perf: {risultato['performance_totale_pct']:+.1f}% | MDD: {risultato['max_drawdown']:.1f}% | Turnover: {risultato['turnover_medio']:.0f}%")

    print(f"\n[3/3] Benchmark...")
    bm1 = calc_bm_perf(BENCHMARK,  etf_data, BACKTEST_START)
    bm2 = calc_bm_perf(BENCHMARK2, etf_data, BACKTEST_START)
    op1 = round(risultato["performance_totale_pct"]-bm1,2) if bm1 else None
    op2 = round(risultato["performance_totale_pct"]-bm2,2) if bm2 else None
    if bm1: print(f"  IWMO: {bm1:+.1f}% | Outperf: {op1:+.1f}pp")

    output = {
        "generated":    datetime.datetime.utcnow().isoformat(),
        "version":      "linea_wt_1.0",
        "run_number":   run_number,
        "linea":        "WT",
        "descrizione":  "6 ETF WisdomTree — pesi dinamici — benchmark IWMO",
        "benchmark":    BENCHMARK, "benchmark2": BENCHMARK2,
        "benchmark_perf":  bm1, "benchmark2_perf": bm2,
        "outperformance":  op1, "outperformance2":  op2,
        "batte_benchmark": risultato["performance_totale_pct"] > bm1 if bm1 else None,
        **risultato,
    }
    save_json(output, OUT_FILE)
    print(f"\n  Portafoglio corrente:")
    for p in risultato["composizione_corrente"]:
        print(f"  {p['ticker']:<14} {p['peso']:>5.1f}% | score={p.get('score',0):.0f} | {p.get('azione','')} — {p.get('commento','')[:50]}")

if __name__ == "__main__":
    main()
