#!/usr/bin/env python3
"""
linea_3.py — Linea 3 v1.0
22 ETF: WT 6 + leva 2x 4 + leva 3x 7 + short 3x 10
Short entrano solo con segnali KAMA attivi.
Benchmark: IWMO.MI
"""
import json, datetime
from pathlib import Path
from engine import (download_universo, run_backtest, calc_bm_perf,
                    save_json, BACKTEST_START, BENCHMARK, BENCHMARK2)

BASE_DIR = Path(__file__).parent
OUT_FILE = BASE_DIR / "data" / "linea_3.json"

UNIVERSO_LONG = [
    # WisdomTree base
    {"ticker":"WS5X.MI","nome":"WT Euro Stoxx 50",             "cat":"az_europa","sub":"EU"},
    {"ticker":"WWRD.MI","nome":"WT World",                      "cat":"az_globale","sub":"GLOBAL"},
    {"ticker":"WRTY.MI","nome":"WT Russell 2000 Efficient Core","cat":"az_usa",   "sub":"US_SMALL"},
    {"ticker":"WNAS.MI","nome":"WT Nasdaq-100",                 "cat":"az_usa",   "sub":"TECH"},
    {"ticker":"WSPE.MI","nome":"WT S&P 500 EUR Hedged",         "cat":"az_usa",   "sub":"US_EUR"},
    {"ticker":"WSPX.MI","nome":"WT S&P 500",                    "cat":"az_usa",   "sub":"US"},
    # Leva 2x
    {"ticker":"2TRV.MI","nome":"WT Travel 2x Lev",              "cat":"leva_2x",  "sub":"TRAVEL"},
    {"ticker":"2CAR.MI","nome":"WT Carbon 2x Lev",              "cat":"leva_2x",  "sub":"CARBON"},
    {"ticker":"2OIG.MI","nome":"WT Oil & Gas 2x Lev",           "cat":"leva_2x",  "sub":"OIL_GAS"},
    {"ticker":"2STR.MI","nome":"WT Storage 2x Lev",             "cat":"leva_2x",  "sub":"STORAGE"},
    # Leva 3x long
    {"ticker":"3EDF.MI","nome":"WT EDF 3x Lev",                 "cat":"leva_3x",  "sub":"EDF"},
    {"ticker":"3EUL.MI","nome":"WT Euro Stoxx 50 3x Lev",       "cat":"leva_3x",  "sub":"EU_LEV"},
    {"ticker":"3BAL.MI","nome":"WT BAT 3x Lev",                 "cat":"leva_3x",  "sub":"BAT"},
    {"ticker":"3USL.MI","nome":"WT S&P 500 3x Lev",             "cat":"leva_3x",  "sub":"US_LEV"},
    {"ticker":"QQQ3.MI","nome":"WT Nasdaq 3x Lev",              "cat":"leva_3x",  "sub":"NAS_LEV"},
    {"ticker":"3MG7.MI","nome":"WT MSCI G7 3x Lev",             "cat":"leva_3x",  "sub":"G7_LEV"},
    {"ticker":"3SEM.MI","nome":"WT MSCI EM 3x Lev",             "cat":"leva_3x",  "sub":"EM_LEV"},
]

UNIVERSO_SHORT = [
    {"ticker":"3EDS.MI","nome":"WT EDF 3x Short",           "cat":"short","sub":"SHORT_EDF"},
    {"ticker":"3EUS.MI","nome":"WT Euro Stoxx 50 3x Short",  "cat":"short","sub":"SHORT_EU"},
    {"ticker":"3BAS.MI","nome":"WT BAT 3x Short",            "cat":"short","sub":"SHORT_BAT"},
    {"ticker":"3DEL.MI","nome":"WT Deutsche Bank 3x Lev",    "cat":"leva_3x","sub":"DB_LEV"},
    {"ticker":"3DES.MI","nome":"WT Deutsche Bank 3x Short",  "cat":"short","sub":"SHORT_DB"},
    {"ticker":"3ITL.MI","nome":"WT Italy 3x Lev",            "cat":"leva_3x","sub":"IT_LEV"},
    {"ticker":"3ITS.MI","nome":"WT Italy 3x Short",          "cat":"short","sub":"SHORT_IT"},
    {"ticker":"3USS.MI","nome":"WT S&P 500 3x Short",        "cat":"short","sub":"SHORT_US"},
    {"ticker":"SC3S.MI","nome":"S&P 500 3x Short",           "cat":"short","sub":"SHORT_US"},
    {"ticker":"3M7S.MI","nome":"WT MSCI G7 3x Short",        "cat":"short","sub":"SHORT_G7"},
]

def main():
    oggi = datetime.date.today().isoformat()
    print(f"Linea 3 v1.0 — {oggi}")

    run_number = 1
    if OUT_FILE.exists():
        try: run_number = json.loads(OUT_FILE.read_text()).get("run_number",0)+1
        except: pass

    tickers = (set(e["ticker"] for e in UNIVERSO_LONG) |
               set(e["ticker"] for e in UNIVERSO_SHORT) |
               {BENCHMARK, BENCHMARK2, "XEON.MI"})
    print(f"\n[1/3] Download {len(tickers)} ticker...")
    etf_data = download_universo(tickers, label="L3 ")

    print(f"\n[2/3] Backtest Linea 3 (da {BACKTEST_START})...")
    risultato = run_backtest(
        etf_data, UNIVERSO_LONG, UNIVERSO_SHORT,
        n_max=10, backtest_start=BACKTEST_START, oggi=oggi, label="Linea 3"
    )
    print(f"  Perf: {risultato['performance_totale_pct']:+.1f}% | MDD: {risultato['max_drawdown']:.1f}%")

    print(f"\n[3/3] Benchmark...")
    bm1 = calc_bm_perf(BENCHMARK,  etf_data, BACKTEST_START)
    bm2 = calc_bm_perf(BENCHMARK2, etf_data, BACKTEST_START)
    op1 = round(risultato["performance_totale_pct"]-bm1,2) if bm1 else None
    op2 = round(risultato["performance_totale_pct"]-bm2,2) if bm2 else None
    if bm1: print(f"  IWMO: {bm1:+.1f}% | Outperf: {op1:+.1f}pp")

    output = {
        "generated":   datetime.datetime.utcnow().isoformat(),
        "version":     "linea_3_1.0", "run_number": run_number,
        "linea":       "3",
        "descrizione": "WT 6 + leva 2x 4 + leva 3x 7 + short 3x 10 — benchmark IWMO",
        "benchmark":   BENCHMARK, "benchmark2": BENCHMARK2,
        "benchmark_perf": bm1, "benchmark2_perf": bm2,
        "outperformance": op1, "outperformance2": op2,
        "batte_benchmark": risultato["performance_totale_pct"]>bm1 if bm1 else None,
        **risultato,
    }
    save_json(output, OUT_FILE)

if __name__ == "__main__":
    main()
