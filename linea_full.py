#!/usr/bin/env python3
"""
linea_full.py — Linea Full v1.0
~53 ETF long. Top 15 dinamici per score. Short disattivato.
Benchmark: IWMO.MI
"""
import json, datetime
from pathlib import Path
from engine import (download_universo, run_backtest, calc_bm_perf,
                    save_json, BACKTEST_START, BENCHMARK, BENCHMARK2, BENCHMARK3)

BASE_DIR = Path(__file__).parent
OUT_FILE = BASE_DIR / "data" / "linea_full.json"

UNIVERSO_LONG = [
    # ── Azionario Globale ──────────────────────────────────────────────────
    {"ticker":"WWRD.MI","nome":"WT World",                        "cat":"az_globale","sub":"GLOBAL"},
    {"ticker":"SWDA.MI","nome":"iShares Core MSCI World",         "cat":"az_globale","sub":"GLOBAL"},
    {"ticker":"VWCE.DE","nome":"Vanguard FTSE All-World",         "cat":"az_globale","sub":"GLOBAL"},
    {"ticker":"XDWT.MI","nome":"Xtrackers MSCI World Swap",       "cat":"az_globale","sub":"GLOBAL"},
    {"ticker":"IWMO.MI","nome":"iShares MSCI World Momentum",     "cat":"az_globale","sub":"GLOBAL_MOM"},
    {"ticker":"IWQU.MI","nome":"iShares MSCI World Quality",      "cat":"az_globale","sub":"GLOBAL_F"},
    {"ticker":"WOEE.DE","nome":"iShares World Enhanced Active",   "cat":"az_globale","sub":"GLOBAL_F"},
    {"ticker":"IFSW.MI","nome":"iShares STOXX World Multifactor", "cat":"az_globale","sub":"GLOBAL_F"},
    {"ticker":"JPGL.MI","nome":"JPMorgan Global Multi-Factor",    "cat":"az_globale","sub":"GLOBAL_F"},
    {"ticker":"FCRN.DE","nome":"iShares World Factor Rotation",   "cat":"az_globale","sub":"GLOBAL_F"},
    {"ticker":"NTSX.MI","nome":"WT US Efficient Core",            "cat":"az_globale","sub":"GLOBAL_EC"},
    {"ticker":"NTSG.MI","nome":"WT Global Efficient Core",        "cat":"az_globale","sub":"GLOBAL_EC"},
    {"ticker":"IBCZ.DE","nome":"iShares STOXX World MF",          "cat":"az_globale","sub":"GLOBAL_F"},
    # ── Azionario Europa ───────────────────────────────────────────────────
    {"ticker":"WS5X.MI","nome":"WT Euro Stoxx 50",                "cat":"az_europa","sub":"EU"},
    {"ticker":"SMEA.MI","nome":"iShares Europe Small Cap",        "cat":"az_europa","sub":"EU_SMALL"},
    {"ticker":"EXX5.DE","nome":"iShares EURO STOXX 50",           "cat":"az_europa","sub":"EU"},
    {"ticker":"EXV1.DE","nome":"iShares STOXX Europe 600",        "cat":"az_europa","sub":"EU"},
    {"ticker":"EUEE.DE","nome":"iShares Europe Enhanced Active",  "cat":"az_europa","sub":"EU_F"},
    {"ticker":"IEMO.MI","nome":"iShares MSCI Europe Momentum",    "cat":"az_europa","sub":"EU_MOM"},
    {"ticker":"IEQU.MI","nome":"iShares MSCI Europe Quality",     "cat":"az_europa","sub":"EU_F"},
    {"ticker":"EXXW.DE","nome":"iShares MSCI Europe",             "cat":"az_europa","sub":"EU"},
    # ── Azionario USA ──────────────────────────────────────────────────────
    {"ticker":"WSPX.MI","nome":"WT S&P 500",                      "cat":"az_usa","sub":"US"},
    {"ticker":"WSPE.MI","nome":"WT S&P 500 EUR Hedged",           "cat":"az_usa","sub":"US_EUR"},
    {"ticker":"WNAS.MI","nome":"WT Nasdaq-100",                   "cat":"az_usa","sub":"TECH"},
    {"ticker":"WRTY.MI","nome":"WT Russell 2000 Efficient Core",  "cat":"az_usa","sub":"US_SMALL"},
    {"ticker":"CSSPX.MI","nome":"iShares Core S&P 500",           "cat":"az_usa","sub":"US"},
    {"ticker":"USEE.DE","nome":"iShares US Enhanced Active",      "cat":"az_usa","sub":"US_F"},
    {"ticker":"QDVB.DE","nome":"iShares MSCI USA Quality",        "cat":"az_usa","sub":"US_F"},
    {"ticker":"XUTC.MI","nome":"Xtrackers MSCI USA IT",           "cat":"az_usa","sub":"TECH"},
    # ── Azionario EM/Asia ──────────────────────────────────────────────────
    {"ticker":"VFEM.MI","nome":"Vanguard FTSE EM",                "cat":"az_em","sub":"EM_BROAD"},
    {"ticker":"EIMI.MI","nome":"iShares MSCI EM",                 "cat":"az_em","sub":"EM_CORE"},
    {"ticker":"DXJF.MI","nome":"WisdomTree Japan EUR Hedged",     "cat":"az_em","sub":"JAPAN"},
    {"ticker":"XCHA.MI","nome":"iShares China",                   "cat":"az_em","sub":"CHINA"},
    {"ticker":"XASX.DE","nome":"iShares Asia Pacific",            "cat":"az_em","sub":"ASIA_PAC"},
    {"ticker":"EMEE.MI","nome":"iShares EM Enhanced Active",      "cat":"az_em","sub":"EM_F"},
    {"ticker":"AXEE.MI","nome":"iShares Asia ex Japan Enhanced",  "cat":"az_em","sub":"ASIA_F"},
    {"ticker":"IS3N.DE","nome":"iShares MSCI EM Small Cap",       "cat":"az_em","sub":"EM_SMALL"},
    {"ticker":"VAPX.MI","nome":"Vanguard Dev Asia Pacific",       "cat":"az_em","sub":"ASIA_PAC"},
    {"ticker":"JPNH.MI","nome":"Amundi MSCI Japan EUR Hdg",       "cat":"az_em","sub":"JAPAN"},
    {"ticker":"NTSZ.MI","nome":"WT EM Efficient Core",            "cat":"az_em","sub":"EM_EC"},
    # ── Tematici ───────────────────────────────────────────────────────────
    {"ticker":"SMH.MI", "nome":"VanEck Semiconductor",            "cat":"tematico","sub":"SEMIS"},
    {"ticker":"IART.DE","nome":"iShares AI Innovation",           "cat":"tematico","sub":"AI"},
    {"ticker":"DFNS.MI","nome":"VanEck Defense",                  "cat":"tematico","sub":"DEFENSE"},
    {"ticker":"PHAU.MI","nome":"WT Physical Gold",                "cat":"tematico","sub":"GOLD"},
    {"ticker":"CRUD.MI","nome":"WT WTI Crude Oil",                "cat":"tematico","sub":"CRUDE"},
    {"ticker":"COPA.MI","nome":"WT Copper",                       "cat":"tematico","sub":"MATERIALS"},
    {"ticker":"RARE.MI","nome":"VanEck Rare Earth",               "cat":"tematico","sub":"MATERIALS"},
    {"ticker":"CMOD.MI","nome":"iShares Commodity",               "cat":"tematico","sub":"COMMODITY"},
    {"ticker":"AIGA.MI","nome":"WT Agriculture",                  "cat":"tematico","sub":"COMMODITY"},
    {"ticker":"IFFF.MI","nome":"iShares MSCI Global Financials",  "cat":"tematico","sub":"FINANCIAL"},
    # ── Leva 2x ────────────────────────────────────────────────────────────
    {"ticker":"2TRV.MI","nome":"WT Travel 2x Lev",                "cat":"leva_2x","sub":"TRAVEL"},
    {"ticker":"2CAR.MI","nome":"WT Automobiles 2x Lev",                "cat":"leva_2x","sub":"AUTO"},
    # ── Leva 3x long ───────────────────────────────────────────────────────
    {"ticker":"3EDF.MI","nome":"WT Aerospace & Defence 3x Lev",                   "cat":"leva_3x","sub":"AERO_DEF"},
    {"ticker":"3EUL.MI","nome":"WT Euro Stoxx 50 3x Lev",         "cat":"leva_3x","sub":"EU_LEV"},
    {"ticker":"3BAL.MI","nome":"WT Banks 3x Lev",                   "cat":"leva_3x","sub":"BANKS"},
    {"ticker":"3DEL.MI","nome":"WT DAX 3x Lev",         "cat":"leva_3x","sub":"DAX_LEV"},
    {"ticker":"3ITL.MI","nome":"WT Italy 3x Lev",                 "cat":"leva_3x","sub":"IT_LEV"},
    {"ticker":"3USL.MI","nome":"WT S&P 500 3x Lev",               "cat":"leva_3x","sub":"US_LEV"},
    {"ticker":"QQQ3.MI","nome":"WT Nasdaq 3x Lev",                "cat":"leva_3x","sub":"NAS_LEV"},
    {"ticker":"3MG7.MI","nome":"WT MSCI G7 3x Lev",               "cat":"leva_3x","sub":"G7_LEV"},
    {"ticker":"3SEM.MI","nome":"WT Semiconductor 3x Lev",               "cat":"leva_3x","sub":"SEMI_LEV"},
    {"ticker":"3NVD.MI","nome":"Leverage Shares 3x NVIDIA",       "cat":"leva_3x","sub":"LEVA_TEMA"},
]

def main():
    oggi = datetime.date.today().isoformat()
    print(f"Linea Full v1.0 — {oggi}")

    run_number = 1
    if OUT_FILE.exists():
        try: run_number = json.loads(OUT_FILE.read_text()).get("run_number",0)+1
        except: pass

    tickers = (set(e["ticker"] for e in UNIVERSO_LONG) |
               {BENCHMARK, BENCHMARK2, BENCHMARK3, "XEON.MI"})
    print(f"\n[1/3] Download {len(tickers)} ticker...")
    etf_data = download_universo(tickers, label="FULL ")

    print(f"\n[2/3] Backtest Linea Full (da {BACKTEST_START})...")
    risultato = run_backtest(
        etf_data, UNIVERSO_LONG,
        n_max=15, backtest_start=BACKTEST_START, oggi=oggi, label="Linea Full"
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
        "version":     "linea_full_1.0", "run_number": run_number,
        "linea":       "Full",
        "descrizione": f"{len(UNIVERSO_LONG)} ETF long — top 15 dinamici — benchmark IWMO (short disattivato)",
        "benchmark":   BENCHMARK, "benchmark2": BENCHMARK2, "benchmark3": BENCHMARK3,
        "benchmark_perf": bm1, "benchmark2_perf": bm2, "benchmark3_perf": bm3,
        "outperformance": op1, "outperformance2": op2, "outperformance3": op3,
        "batte_benchmark": risultato["performance_totale_pct"]>bm1 if bm1 else None,
        **risultato,
    }
    save_json(output, OUT_FILE)

if __name__ == "__main__":
    main()
