#!/usr/bin/env python3
"""
linea_timing.py — IWMO Timing v1.0
Solo IWMO.MI. Uscita progressiva su XEON con segnali KAMA (short disattivato).
La strategia più semplice e diretta per battere IWMO nel lungo periodo.
Benchmark: IWMO.MI
"""
import json, math, datetime, time
from pathlib import Path
from collections import defaultdict
from engine import (fetch_yahoo, closes_at, calc_segnali_iwmo, calc_score,
                    calc_kama, calc_er, calc_mom, genera_azione,
                    save_json, calc_bm_perf,
                    cammina_periodo_con_exit, COOLDOWN_GIORNI,
                    BACKTEST_START, BENCHMARK, BENCHMARK2, CAPITALE,
                    REBAL_DAYS, QUOTA_LONG, QUOTA_SHORT, QUOTA_XEON)

BASE_DIR = Path(__file__).parent
OUT_FILE = BASE_DIR / "data" / "linea_timing.json"

UNIVERSO_SHORT = [
    {"ticker":"3USS.MI","nome":"WT S&P 500 3x Short",   "cat":"short","sub":"SHORT_US"},
    {"ticker":"SC3S.MI","nome":"S&P 500 3x Short",      "cat":"short","sub":"SHORT_US"},
    {"ticker":"3EUS.MI","nome":"Euro Stoxx 50 3x Short","cat":"short","sub":"SHORT_EU"},
    {"ticker":"3M7S.MI","nome":"MSCI G7 3x Short",      "cat":"short","sub":"SHORT_G7"},
]

def run_backtest_timing(etf_data, backtest_start, oggi):
    all_dates = sorted(set(
        d for data in etf_data.values()
        for d in data.get("dates",[])
        if backtest_start <= d <= oggi
    ))
    rebal_dates = [all_dates[i] for i in range(0,len(all_dates),REBAL_DAYS)]
    if all_dates and all_dates[-1] not in rebal_dates:
        rebal_dates.append(all_dates[-1])

    versioni=[]; comp_att=[]; capitale=float(CAPITALE); rendimenti={}
    storia_segnali=[]; data_ing_map={}
    cooldown_until={}; exit_forzati_log=[]

    for idx, rdate in enumerate(rebal_dates):
        # Cammina il periodo appena concluso applicando l'exit forzato su IWMO
        if idx > 0 and comp_att and rebal_dates[idx-1] < rdate:
            prev_date = rebal_dates[idx-1]
            capitale_prima = capitale
            capitale, eventi_exit = cammina_periodo_con_exit(
                etf_data, comp_att, prev_date, rdate, capitale, all_dates,
                cooldown_until, short_return_bug=False)
            rendimenti[rdate] = round((capitale/capitale_prima - 1) * 100, 4)
            if eventi_exit:
                exit_forzati_log.extend(eventi_exit)

        cl_iwmo = closes_at(etf_data, BENCHMARK, rdate)
        n_seg, seg = calc_segnali_iwmo(cl_iwmo)
        storia_segnali.append({"data":rdate,**seg})
        ql=QUOTA_LONG[min(n_seg,3)]; qs=QUOTA_SHORT[min(n_seg,3)]; qx=QUOTA_XEON[min(n_seg,3)]
        qx = qx + qs; qs = 0.0   # short disattivato: quota confluisce in XEON

        # In cooldown dopo un exit forzato: IWMO resta fuori, la sua quota va in XEON
        if cooldown_until.get(BENCHMARK, "") >= rdate:
            qx = qx + ql
            ql = 0.0

        composizione = []

        # IWMO long
        if ql > 0 and cl_iwmo:
            kn,_,kd = calc_kama(cl_iwmo)
            er = calc_er(cl_iwmo)
            composizione.append({
                "ticker":"IWMO.MI","nome":"iShares MSCI World Momentum",
                "cat":"az_globale","sub":"GLOBAL_MOM","is_short":False,
                "peso":round(ql*100,2),"score":55,"price":cl_iwmo[-1],
                "mom6m":calc_mom(cl_iwmo,126),"mom3m":calc_mom(cl_iwmo,63),
                "mom1m":calc_mom(cl_iwmo,21),"er":round(er,3),
                "kama":round(kn,4) if kn else None,"kama_dir":kd,
            })

        # Short disattivato — vedi qs=0 sopra; blocco mantenuto ma inerte per riuso futuro
        top_short = []
        if qs > 0 and n_seg > 0:
            cand_short=[]
            for etf in UNIVERSO_SHORT:
                t=etf["ticker"]; cl=closes_at(etf_data,t,rdate)
                if len(cl)<60: continue
                sc,ind=calc_score(cl,is_short=True)
                if sc is None: continue
                cand_short.append({"ticker":t,"nome":etf["nome"],"cat":"short",
                                   "sub":etf["sub"],"is_short":True,"score":sc,
                                   "price":cl[-1],**ind})
            cand_short.sort(key=lambda x:x["score"],reverse=True)
            top_short=[c for c in cand_short if c["score"]>0][:2]
            tot_ws=sum(c["score"]**1.5 for c in top_short) or 1
            for c in top_short:
                c["peso"]=round(c["score"]**1.5/tot_ws*qs*100,2)
            composizione.extend(top_short)

        # XEON
        if qx > 0:
            cl_x=closes_at(etf_data,"XEON.MI",rdate)
            composizione.append({
                "ticker":"XEON.MI","nome":"Xtrackers EUR Overnight",
                "cat":"monetario","sub":"CASH","is_short":False,
                "peso":round(qx*100,2),"score":0,
                "price":cl_x[-1] if cl_x else None,
                "mom6m":None,"mom3m":None,"mom1m":None,"er":1.0,"kama":None,"kama_dir":0,
            })

        # Rinormalizza
        tot_p=sum(c["peso"] for c in composizione) or 1
        for c in composizione: c["peso"]=round(c["peso"]/tot_p*100,2)

        # Data ingresso
        ticker_prec={p["ticker"] for p in comp_att}
        for c in composizione:
            t=c["ticker"]
            if t not in data_ing_map or t not in ticker_prec:
                data_ing_map[t]={"data":rdate,"price":c.get("price")}
            c["data_ingresso"]=data_ing_map[t]["data"]
            c["prezzo_ingresso"]=data_ing_map[t]["price"]
            c["importo"]=round(capitale*c["peso"]/100,2)

        # Azione
        for c in composizione:
            if c["ticker"]=="XEON.MI":
                c["azione"]="CASH"; c["commento"]=f"Protezione — {n_seg} segnale/i"
            elif c["ticker"]==BENCHMARK:
                c["azione"]="MANTIENI" if n_seg==0 else "RIDUCI"
                lv=["100% IWMO — nessun segnale","70% IWMO — S1 attivo",
                    "30% IWMO — 2 segnali","0% IWMO — uscita totale"]
                c["commento"]=lv[min(n_seg,3)]
            else:
                c["azione"]="SHORT"; c["commento"]=f"Short attivo — {n_seg} segnali IWMO"

        comp_att=composizione
        versioni.append({"data":rdate,"n_segnali":n_seg,"segnali":seg,
                         "quota_iwmo":round(ql*100),"quota_short":round(qs*100),
                         "quota_xeon":round(qx*100),"composizione":composizione,
                         "capitale":round(capitale,2)})

    # Metriche
    perf_tot=round((capitale-CAPITALE)/CAPITALE*100,2)
    equity_mensile=[]; cap_tmp=float(CAPITALE); ms=set()
    for rd,ret in sorted(rendimenti.items()):
        cap_tmp=round(cap_tmp*(1+ret/100),2); m=rd[:7]
        if m not in ms: equity_mensile.append({"mese":m,"valore":cap_tmp}); ms.add(m)

    cap_s=[float(CAPITALE)]+[v["capitale"] for v in versioni]
    peak=cap_s[0]; mdd=0
    for c in cap_s:
        if c>peak: peak=c
        dd=(c-peak)/peak*100
        if dd<mdd: mdd=dd

    rl=[rendimenti[d] for d in sorted(rendimenti)]
    def sh(rl,n,rf=0.03/52):
        if len(rl)<n: return None
        w=rl[-n:]; mr=sum(w)/len(w)-rf
        var=sum((r-sum(w)/len(w))**2 for r in w)/(len(w)-1) if len(w)>1 else 0
        std=math.sqrt(var) if var>0 else 0
        return round(mr/std*math.sqrt(52),2) if std>0 else None

    cap2=[float(CAPITALE)]
    for d in sorted(rendimenti): cap2.append(cap2[-1]*(1+rendimenti[d]/100))
    peak=cap2[0]; dd_series=[]; dw=sorted(rendimenti.keys())
    for i,v in enumerate(cap2[1:]):
        if v>peak: peak=v
        dd_series.append({"data":dw[i],"dd":round((v-peak)/peak*100,3)})

    rolling_sh=[]; ds=sorted(rendimenti.keys())
    for i in range(13,len(rl)+1):
        w=rl[i-13:i]; rf=0.03/52; mr=sum(w)/len(w)-rf
        var=sum((r-sum(w)/len(w))**2 for r in w)/(len(w)-1) if len(w)>1 else 0
        std=math.sqrt(var) if var>0 else 0
        rolling_sh.append({"data":ds[i-1] if i-1<len(ds) else None,
                           "sharpe":round(mr/std*math.sqrt(52),3) if std>0 else 0})

    rpa=defaultdict(dict); prev_val=float(CAPITALE)
    for e in equity_mensile:
        a,m=e["mese"].split("-")
        rpa[a][m]=round((e["valore"]-prev_val)/prev_val*100,2); prev_val=e["valore"]
    ra={a:round((math.prod(1+r/100 for r in ms.values())-1)*100,2) for a,ms in rpa.items()}

    def rend_bm(ticker):
        d=etf_data.get(ticker)
        if not d: return {},{}
        n=min(len(d["closes"]),len(d["dates"]))
        pairs=[(d["dates"][i],d["closes"][i]) for i in range(n) if d["dates"][i]>=backtest_start]
        if not pairs: return {},{}
        mc=defaultdict(list)
        for dt,cl in pairs: mc[dt[:7]].append(cl)
        mo=sorted(mc.keys()); rpa2=defaultdict(dict); ra2={}; prev=mc[mo[0]][0]
        for mese in mo:
            last=mc[mese][-1]; ret=round((last-prev)/prev*100,2) if prev else 0
            a,m=mese.split("-"); rpa2[a][m]=ret; prev=last
        for a,ms in rpa2.items():
            ra2[a]=round((math.prod(1+r/100 for r in ms.values())-1)*100,2)
        return dict(rpa2),ra2

    riw,riwa=rend_bm(BENCHMARK)
    pps=defaultdict(list)
    for v in versioni:
        if v["data"] in rendimenti: pps[str(v["n_segnali"])].append(rendimenti[v["data"]])
    perf_step={ns:{"media_sett":round(sum(r)/len(r),3),"n":len(r),
                   "positivi":sum(1 for x in r if x>0),
                   "label":["100% IWMO","70% IWMO","30% IWMO","100% XEON"][min(int(ns),3)]}
               for ns,r in pps.items()}
    storia_slim=[{k:v[k] for k in ["data","n_segnali","s1","s2","s3","quota_az_pct","descrizione"] if k in v}
                 for v in storia_segnali]

    return {
        "performance_totale_pct":perf_tot,"performance_totale_eur":round(capitale-CAPITALE,2),
        "capitale_attuale":round(capitale,2),"max_drawdown":round(mdd,2),
        "sharpe_6m":sh(rl,26),"sharpe_12m":sh(rl,52),
        "rolling_sharpe":rolling_sh,"drawdown_series":dd_series,
        "rend_per_anno":dict(rpa),"rend_annuo":ra,
        "rend_iwmo_mese":riw,"rend_iwmo_anno":riwa,
        "turnover_medio":0,"perf_per_step":perf_step,
        "versioni":versioni,"composizione_corrente":comp_att,
        "data_ingresso_map":{t:v for t,v in data_ing_map.items()},
        "rendimenti":rendimenti,"equity_mensile":equity_mensile,
        "storia_segnali":storia_slim,"n_rebalancing":len(versioni),
        "segnali_oggi":storia_slim[-1] if storia_slim else {},
        "exit_forzati":exit_forzati_log,
        "cooldown_attivo":{t:d for t,d in cooldown_until.items() if d >= oggi},
    }

def main():
    oggi=datetime.date.today().isoformat()
    print(f"IWMO Timing v1.0 — {oggi}")

    run_number=1
    if OUT_FILE.exists():
        try: run_number=json.loads(OUT_FILE.read_text()).get("run_number",0)+1
        except: pass

    tickers=({BENCHMARK,BENCHMARK2,"XEON.MI"} |
             {e["ticker"] for e in UNIVERSO_SHORT})
    print(f"\n[1/3] Download {len(tickers)} ticker...")
    etf_data={}
    for t in sorted(tickers):
        d=fetch_yahoo(t,days=900)
        if d: etf_data[t]=d; print(f"  {t}... OK")
        else: print(f"  {t}... ERR")
        time.sleep(0.3)

    cl_iwmo=closes_at(etf_data,BENCHMARK,oggi)
    n_seg,seg=calc_segnali_iwmo(cl_iwmo)
    print(f"\n  Segnali IWMO: {n_seg}/3 | {seg['descrizione']}")

    print(f"\n[2/3] Backtest IWMO Timing (da {BACKTEST_START})...")
    risultato=run_backtest_timing(etf_data,BACKTEST_START,oggi)
    print(f"  Perf: {risultato['performance_totale_pct']:+.1f}% | MDD: {risultato['max_drawdown']:.1f}%")

    print(f"\n[3/3] Benchmark...")
    bm1=calc_bm_perf(BENCHMARK,etf_data,BACKTEST_START)
    bm2=calc_bm_perf(BENCHMARK2,etf_data,BACKTEST_START)
    op1=round(risultato["performance_totale_pct"]-bm1,2) if bm1 else None
    op2=round(risultato["performance_totale_pct"]-bm2,2) if bm2 else None
    if bm1: print(f"  IWMO: {bm1:+.1f}% | Outperf: {op1:+.1f}pp")

    output={
        "generated":datetime.datetime.utcnow().isoformat(),
        "version":"linea_timing_1.0","run_number":run_number,
        "linea":"Timing","descrizione":"Solo IWMO + XEON con segnali KAMA (short disattivato)",
        "benchmark":BENCHMARK,"benchmark2":BENCHMARK2,
        "benchmark_perf":bm1,"benchmark2_perf":bm2,
        "outperformance":op1,"outperformance2":op2,
        "batte_benchmark":risultato["performance_totale_pct"]>bm1 if bm1 else None,
        **risultato,
    }
    save_json(output,OUT_FILE)
    print(f"\n  Posizione: {seg['quota_az_pct']}% IWMO | {round((QUOTA_SHORT[min(n_seg,3)]+QUOTA_XEON[min(n_seg,3)])*100)}% XEON (short disattivato)")

if __name__=="__main__":
    main()
