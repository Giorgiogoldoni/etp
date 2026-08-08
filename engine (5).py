#!/usr/bin/env python3
"""
engine.py — COMPASS ETP Engine v1.0
══════════════════════════════════════════════════════════════════════
Logica comune condivisa da tutte le linee:
  - Download dati Yahoo Finance
  - Indicatori: KAMA, ER, momentum multi-timeframe
  - Segnali uscita su IWMO (S1/S2/S3)
  - Score: mom6M×0.40 + mom3M×0.35 + mom1M×0.25 × ER × KAMA
  - Backtest ogni 10 giorni con pesi score^1.5
  - Peso minimo 1% memoria per score negativo
  - Short disattivato: nessuna linea apre posizioni short (quota confluisce in XEON)
Benchmark: IWMO.MI (+ VWCE.DE, IS3S.DE di confronto) — Backtest: 2024-01-01
"""

import json, math, datetime, time, urllib.request
from pathlib import Path
from collections import defaultdict

# ── CONFIGURAZIONE ────────────────────────────────────────────────────────────
BACKTEST_START   = "2026-01-01"
CAPITALE         = 100_000
BENCHMARK        = "IWMO.MI"
BENCHMARK2       = "VWCE.DE"
BENCHMARK3       = "IS3S.DE"  # iShares Edge MSCI World Value Factor (IWVL), quotato su Xetra in EUR
REBAL_DAYS       = 10
COOLDOWN_GIORNI  = 5    # giorni di borsa di esclusione per un ticker dopo un exit forzato
PESO_MEMORIA     = 1.0
PESO_EXP         = 1.5
SOGLIA_ROTAZIONE = 12

QUOTA_LONG  = {0: 1.00, 1: 0.70, 2: 0.30, 3: 0.00}
# Short disattivato: la quota un tempo destinata allo short confluisce in XEON
QUOTA_XEON  = {0: 0.00, 1: 0.30, 2: 0.70, 3: 1.00}

# ── DOWNLOAD ──────────────────────────────────────────────────────────────────
def fetch_yahoo(ticker, days=900):
    end   = int(datetime.datetime.utcnow().timestamp())
    start = end - days * 86400
    url   = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
             f"?interval=1d&period1={start}&period2={end}&events=history")
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            result = data.get("chart", {}).get("result")
            if not result: time.sleep(2); continue
            ts  = result[0]["timestamp"]
            q   = result[0]["indicators"]["quote"][0]
            adj = result[0]["indicators"].get("adjclose",[{}])[0].get("adjclose", q["close"])
            dates  = [datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d") for t in ts]
            closes = [float(v) if v else None for v in adj]
            valid  = [(d,c) for d,c in zip(dates,closes) if c]
            if len(valid) < 60: return None
            d,c = zip(*valid)
            return {"dates": list(d), "closes": list(c)}
        except Exception:
            time.sleep(2*attempt+1)
    return None

def closes_at(etf_data, ticker, target_date):
    d = etf_data.get(ticker)
    if not d: return []
    n = min(len(d["closes"]), len(d["dates"]))
    return [d["closes"][i] for i in range(n) if d["dates"][i] <= target_date]

def download_universo(tickers, label="", days=900):
    etf_data = {}
    ok = err = 0
    for i, t in enumerate(sorted(tickers), 1):
        d = fetch_yahoo(t, days=days)
        if d:
            etf_data[t] = d
            cl = d["closes"]
            m6 = round((cl[-1]-cl[-127])/cl[-127]*100,1) if len(cl)>127 and cl[-127] else None
            print(f"  [{i}/{len(tickers)}] {t}... OK mom6M={f'{m6:+.1f}%' if m6 else 'n.d.'}")
            ok += 1
        else:
            print(f"  [{i}/{len(tickers)}] {t}... ERR"); err += 1
        time.sleep(0.3)
    print(f"  {label}Download: {ok} OK, {err} ERR")
    return etf_data

# ── INDICATORI ────────────────────────────────────────────────────────────────
def calc_sma(closes, period):
    if len(closes) < period: return None
    return sum(closes[-period:]) / period

def calc_mom(closes, days):
    if len(closes) <= days: return None
    old = closes[-(days+1)]
    return round((closes[-1]-old)/old*100, 2) if old else None

def calc_er(closes, period=20):
    if len(closes) <= period: return 0.0
    direction  = abs(closes[-1]-closes[-period-1])
    volatility = sum(abs(closes[i]-closes[i-1]) for i in range(-period,0))
    return round(direction/volatility, 4) if volatility else 0.0

def calc_kama(closes, period=10, fast=2, slow=30):
    if len(closes) < period+2: return None, None, 0
    fsc = 2/(fast+1); ssc = 2/(slow+1)
    kama = closes[period]
    series = [kama]
    for i in range(period+1, len(closes)):
        d = abs(closes[i]-closes[i-period])
        v = sum(abs(closes[j]-closes[j-1]) for j in range(i-period+1,i+1))
        er = d/v if v else 0
        sc = (er*(fsc-ssc)+ssc)**2
        kama = kama + sc*(closes[i]-kama)
        series.append(kama)
    kn = series[-1]; kp = series[-2] if len(series)>=2 else kn
    kd = 1 if kn > kp*1.0001 else (-1 if kn < kp*0.9999 else 0)
    return round(kn,4), round(kp,4), kd

# ── SEGNALI IWMO ──────────────────────────────────────────────────────────────
def calc_segnali_iwmo(closes_iwmo):
    if not closes_iwmo or len(closes_iwmo) < 130:
        return 0, {"s1":False,"s2":False,"s3":False,"n_segnali":0,
                   "quota_long":1.0,"quota_xeon":0.0,
                   "quota_az_pct":100,"descrizione":"Dati insufficienti",
                   "mom1m_iwmo":None,"kama_iwmo":None,"kama_dir_iwmo":0,"price_iwmo":None}
    price = closes_iwmo[-1]
    m1    = calc_mom(closes_iwmo, 21)
    s1    = m1 is not None and m1 < 0
    kn, kp, kd = calc_kama(closes_iwmo)
    s2 = kn is not None and price < kn and kd < 0
    max60 = max(closes_iwmo[-60:]) if len(closes_iwmo)>=60 else None
    s3    = max60 is not None and price < max60*0.90
    pct   = round((max60-price)/max60*100,1) if max60 else None
    n = sum([s1,s2,s3])
    desc = []
    if m1 is not None: desc.append(f"S1{'✓' if s1 else '✗'} Mom1M={m1:+.1f}%")
    if kn: desc.append(f"S2{'✓' if s2 else '✗'} Prezzo={price:.2f} KAMA={kn:.2f}{'↑' if kd>0 else '↓' if kd<0 else '→'}")
    if pct is not None: desc.append(f"S3{'✓' if s3 else '✗'} -{pct:.1f}% da max60gg")
    return n, {"s1":s1,"s2":s2,"s3":s3,"n_segnali":n,
               "quota_long":QUOTA_LONG[min(n,3)],
               "quota_xeon":QUOTA_XEON[min(n,3)],"quota_az_pct":round(QUOTA_LONG[min(n,3)]*100),
               "mom1m_iwmo":round(m1,2) if m1 else None,"kama_iwmo":round(kn,4) if kn else None,
               "kama_dir_iwmo":kd,"price_iwmo":round(price,4),"descrizione":" | ".join(desc)}

def calc_momentum_universo(etf_data, universo_long, rdate):
    """
    Momentum medio (1 mese, stessa finestra di S1) dell'universo LONG proprio
    di una linea, calcolato alla data rdate. Segnale complementare a IWMO:
    verificato sui dati che coglie casi in cui IWMO è in ritardo o non
    rappresentativo dell'universo specifico della linea (leva/tematici/EM).
    Ritorna (mom_medio, n_titoli_usati) — None se dati insufficienti.
    """
    vals = []
    for etf in universo_long:
        cl = closes_at(etf_data, etf["ticker"], rdate)
        if len(cl) < 26: continue
        m = calc_mom(cl, 21)
        if m is not None: vals.append(m)
    if not vals: return None, 0
    return round(sum(vals)/len(vals), 2), len(vals)

# ── SCORE ─────────────────────────────────────────────────────────────────────
def calc_score(closes):
    if not closes or len(closes) < 130: return None, {}
    m6 = calc_mom(closes,126); m3 = calc_mom(closes,63); m1 = calc_mom(closes,21)
    if None in (m6,m3,m1): return None, {}
    score_base = m6*0.40 + m3*0.35 + m1*0.25
    er = calc_er(closes)
    mult_er = 1.15 if er>=0.6 else (0.85 if er<0.4 else 1.0)
    kn,_,kd = calc_kama(closes)
    price = closes[-1]
    if kn is None:            mult_kama = 1.0
    elif price>kn and kd>0:   mult_kama = 1.15
    elif price<kn:             mult_kama = 0.75
    else:                      mult_kama = 1.0
    sf = round(score_base*mult_er*mult_kama, 2)
    return sf, {
        "mom6m":round(m6,2),
        "mom3m":round(m3,2),
        "mom1m":round(m1,2),
        "er":round(er,3),"kama":round(kn,4) if kn else None,
        "kama_dir":kd,"mult_er":round(mult_er,2),"mult_kama":round(mult_kama,2),
    }

# ── AZIONE E COMMENTO ─────────────────────────────────────────────────────────
def genera_azione(ticker, score, comp_prec, data_ingresso):
    oggi = datetime.date.today()
    try:
        giorni = (oggi - datetime.date.fromisoformat(data_ingresso)).days if data_ingresso else None
    except: giorni = None
    prev = next((p for p in (comp_prec or []) if p["ticker"]==ticker), None)
    if not prev:
        return ("ACQUISTA", f"Nuovo ingresso — score {score:.0f}, momentum positivo" if score>=20
                else f"Nuovo ingresso — score {score:.0f}, monitora")
    delta = score - (prev.get("score") or 0)
    if delta >= 15:  return "RAFFORZA",   f"Score +{delta:.0f}pt — trend in accelerazione"
    if delta >= 5:   return "MANTIENI",   f"Score +{delta:.0f}pt — trend confermato"
    if delta >= -10: return "MANTIENI",   f"Score stabile (Δ{delta:+.0f}pt{f', {giorni}gg in ptf' if giorni else ''})"
    if delta >= -20: return "ATTENZIONE", f"Score {delta:.0f}pt — momentum in indebolimento"
    return "VENDI", f"Score {delta:.0f}pt — valuta uscita"

BANDA_TOLLERANZA_LEVA = 0.03   # 3%: riduce il whipsaw sugli ETF a leva (verificato: -24% exit, whipsaw 49%->39%)

def giorni_dopo_n(all_dates, data, n):
    """Ritorna la data che sta N giorni di borsa dopo 'data' nella lista all_dates."""
    try:
        idx = all_dates.index(data)
    except ValueError:
        posteriori = [d for d in all_dates if d >= data]
        if not posteriori: return data
        idx = all_dates.index(posteriori[0])
    j = min(idx + n, len(all_dates) - 1)
    return all_dates[j]


def cammina_periodo_con_exit(etf_data, composizione, data_inizio, data_fine,
                              capitale_iniziale, all_dates, cooldown_until):
    """
    Cammina giorno per giorno nel periodo (data_inizio, data_fine], applicando
    un exit forzato sulle posizioni LONG (non memoria/XEON) quando
    prezzo < KAMA e KAMA in discesa — stessa condizione simmetrica usata per
    il segnale S2 su IWMO, applicata al singolo titolo.
    Per gli ETF a leva (leva_2x/leva_3x) si applica una banda di tolleranza del
    3% sotto la KAMA prima di far scattare l'exit, per ridurre il whipsaw dovuto
    alla maggiore volatilità (verificato sui dati: dimezza il tasso di whipsaw).
    Il capitale liberato da un exit forzato confluisce nel rendimento di
    XEON.MI fino alla fine del periodo corrente.
    Aggiorna 'cooldown_until' in place. Ritorna (capitale_finale, eventi_exit).
    """
    giorni = [d for d in all_dates if data_inizio < d <= data_fine]
    if not giorni:
        return capitale_iniziale, []

    pesi = {c["ticker"]: c["peso"] / 100 for c in composizione}
    cat = {c["ticker"]: c.get("cat", "") for c in composizione}
    usciti = set()
    eventi = []
    capitale = capitale_iniziale

    prev_prices = {}
    for t in pesi:
        cl = closes_at(etf_data, t, data_inizio)
        if cl: prev_prices[t] = cl[-1]
    cl_x0 = closes_at(etf_data, "XEON.MI", data_inizio)
    prev_xeon = cl_x0[-1] if cl_x0 else None

    for giorno in giorni:
        cl_x = closes_at(etf_data, "XEON.MI", giorno)
        px_xeon = cl_x[-1] if cl_x else None
        r_xeon = (px_xeon - prev_xeon) / prev_xeon if (px_xeon and prev_xeon and prev_xeon > 0) else 0.0

        ret_giorno = 0.0
        for t, peso in pesi.items():
            if peso <= 0: continue
            if t in usciti or t == "XEON.MI":
                ret_giorno += peso * r_xeon
                continue
            cl = closes_at(etf_data, t, giorno)
            if not cl or len(cl) < 12:
                continue
            prezzo = cl[-1]
            pp = prev_prices.get(t)
            r = (prezzo - pp) / pp if (pp and pp > 0) else 0.0
            ret_giorno += peso * r
            prev_prices[t] = prezzo

            # Controllo exit forzato — solo posizioni long "vere" (non cash)
            if cat.get(t) != "monetario":
                kn, kp, kd = calc_kama(cl)
                banda = BANDA_TOLLERANZA_LEVA if cat.get(t) in ("leva_2x", "leva_3x") else 0.0
                soglia = kn * (1 - banda) if kn is not None else None
                if soglia is not None and kd is not None and prezzo < soglia and kd < 0:
                    usciti.add(t)
                    cooldown_until[t] = giorni_dopo_n(all_dates, giorno, COOLDOWN_GIORNI)
                    eventi.append({
                        "data": giorno, "ticker": t,
                        "prezzo": round(prezzo, 4), "kama": round(kn, 4),
                        "motivo": "Exit forzato: prezzo sotto KAMA con KAMA in discesa" +
                                  (f" (banda leva {banda*100:.0f}%)" if banda else ""),
                        "cooldown_fino": cooldown_until[t],
                    })

        if px_xeon: prev_xeon = px_xeon
        capitale = round(capitale * (1 + ret_giorno), 4)

    return capitale, eventi


# ── BACKTEST ──────────────────────────────────────────────────────────────────
def run_backtest(etf_data, universo_long, n_max,
                 backtest_start, oggi, label=""):
    all_dates = sorted(set(
        d for data in etf_data.values()
        for d in data.get("dates",[])
        if backtest_start <= d <= oggi
    ))
    rebal_dates = [all_dates[i] for i in range(0, len(all_dates), REBAL_DAYS)]
    if all_dates and all_dates[-1] not in rebal_dates:
        rebal_dates.append(all_dates[-1])

    versioni = []; comp_att = []; comp_prec = []
    capitale = float(CAPITALE); rendimenti = {}
    storia_segnali = []; data_ingresso_map = {}
    cooldown_until = {}; exit_forzati_log = []

    for idx, rdate in enumerate(rebal_dates):
        # Cammina il periodo appena concluso applicando gli exit forzati sui long
        if idx > 0 and comp_att and rebal_dates[idx-1] < rdate:
            prev_date = rebal_dates[idx-1]
            capitale_prima = capitale
            capitale, eventi_exit = cammina_periodo_con_exit(
                etf_data, comp_att, prev_date, rdate, capitale, all_dates, cooldown_until)
            rendimenti[rdate] = round((capitale/capitale_prima - 1) * 100, 4)
            if eventi_exit:
                exit_forzati_log.extend(eventi_exit)

        # Segnali IWMO
        cl_iwmo = closes_at(etf_data, BENCHMARK, rdate)
        n_seg, seg = calc_segnali_iwmo(cl_iwmo)
        ql = QUOTA_LONG[min(n_seg,3)]
        qx = QUOTA_XEON[min(n_seg,3)]

        # Segnale complementare: momentum medio dell'universo proprio della linea.
        # Se negativo, riduce ulteriormente la quota azionaria (dimezzata),
        # indipendentemente da cosa dice IWMO — copre i casi in cui IWMO è in
        # ritardo o non rappresentativo dell'universo specifico (leva/tematici/EM).
        mom_universo, n_mom = calc_momentum_universo(etf_data, universo_long, rdate)
        segnale_momentum_attivo = bool(mom_universo is not None and mom_universo < 0)
        if segnale_momentum_attivo:
            qx = qx + ql/2
            ql = ql/2
        seg["mom_universo"] = mom_universo
        seg["segnale_momentum_attivo"] = segnale_momentum_attivo
        storia_segnali.append({"data":rdate,**seg})

        # Score long
        cand_long = []
        for etf in universo_long:
            t = etf["ticker"]
            if cooldown_until.get(t, "") >= rdate:
                continue  # in cooldown dopo un exit forzato, non rieleggibile
            cl = closes_at(etf_data, t, rdate)
            if len(cl) < 200: continue  # richiesto per il filtro MM200 sotto (era 130)
            ma200 = calc_sma(cl, 200)
            if ma200 is None or cl[-1] <= ma200:
                continue  # filtro di ingresso: candidabile solo se prezzo > MM200
            sc, ind = calc_score(cl)
            if sc is None: continue
            cat = etf.get("cat","")
            if cat == "leva_3x": sc = round(sc / 3, 2)
            elif cat == "leva_2x": sc = round(sc / 2, 2)
            # Cap assoluto score — evita dominanza ETF leva con momentum estremo
            sc = min(sc, 40.0)
            peso_max = 15 if cat=="leva_3x" else (20 if cat=="leva_2x" else 100)
            cand_long.append({"ticker":t,"nome":etf.get("nome",t),"cat":cat,
                              "sub":etf.get("sub",""),"is_short":False,"score":sc,
                              "peso_max":peso_max,"price":cl[-1],**ind})

        # Bonus stabilità
        ticker_prec = {p["ticker"] for p in comp_att}
        for c in cand_long:
            if c["ticker"] in ticker_prec:
                c["score"] = round(c["score"] + SOGLIA_ROTAZIONE/2, 2)
                c["in_portafoglio"] = True
            else:
                c["in_portafoglio"] = False

        # Separa attivi da memoria
        cand_long.sort(key=lambda x: x["score"], reverse=True)
        top_long = [c for c in cand_long if c["score"]>0][:n_max]
        mem_long = [c for c in cand_long if c["score"]<=0]

        # Pesi long — score^1.5 proporzionale
        peso_mem_tot = len(mem_long) * PESO_MEMORIA
        peso_disp = max(0, 100.0 - peso_mem_tot) * ql  # quota disponibile per i long
        tot_wl = sum(max(0, c["score"])**PESO_EXP for c in top_long) or 1
        for c in top_long:
            c["peso"] = round(max(0, c["score"])**PESO_EXP / tot_wl * peso_disp, 2)
            # Cap per ETF a leva
            c["peso"] = min(c["peso"], c.get("peso_max", 100))
        # Rinormalizza dopo i cap per mantenere somma corretta
        tot_dopo_cap = sum(c["peso"] for c in top_long) or 1
        if tot_dopo_cap > 0 and abs(tot_dopo_cap - peso_disp) > 0.1:
            factor = peso_disp / tot_dopo_cap
            for c in top_long:
                c["peso"] = round(min(c["peso"] * factor, c.get("peso_max", 100)), 2)
        for c in mem_long:
            c["peso"] = round(PESO_MEMORIA * ql, 2)

        # XEON — copre sempre sia la quota difensiva (qx) sia l'eventuale residuo
        # non allocato in long per mancanza di candidati sufficienti (es. tutti
        # sotto MM200, o storico insufficiente): il capitale non deve mai restare
        # "in un buco" non investito da nessuna parte.
        peso_long_reale = sum(c["peso"] for c in top_long + mem_long)
        qx_effettiva = max(qx, 1 - peso_long_reale/100) if peso_long_reale < ql*100 else qx
        pos_xeon = []
        if qx_effettiva > 0:
            cl_x = closes_at(etf_data, "XEON.MI", rdate)
            pos_xeon = [{"ticker":"XEON.MI","nome":"Xtrackers EUR Overnight",
                         "cat":"monetario","sub":"CASH","is_short":False,"score":0,
                         "peso":round(qx_effettiva*100,2),"price":cl_x[-1] if cl_x else None,
                         "mom6m":None,"mom3m":None,"mom1m":None,"er":1.0,"kama":None,"kama_dir":0}]

        composizione = top_long + mem_long + pos_xeon

        # Rinormalizza pesi al 100%
        tot_p = sum(c["peso"] for c in composizione) or 1
        for c in composizione:
            c["peso"] = round(c["peso"]/tot_p*100, 2)

        # Data ingresso e prezzo ingresso
        ticker_ora = {c["ticker"] for c in composizione}
        for c in composizione:
            t = c["ticker"]
            if t not in data_ingresso_map or t not in {p["ticker"] for p in comp_att}:
                data_ingresso_map[t] = {"data":rdate, "price":c.get("price")}
            c["data_ingresso"]   = data_ingresso_map[t]["data"]
            c["prezzo_ingresso"] = data_ingresso_map[t]["price"]
            c["importo"]         = round(capitale * c["peso"]/100, 2)

        # Azione e commento
        for c in composizione:
            if c["ticker"] == "XEON.MI":
                c["azione"] = "CASH"
                c["commento"] = f"Protezione — {n_seg} segnale/i attivo"
            else:
                c["azione"], c["commento"] = genera_azione(
                    c["ticker"], c["score"], comp_prec, c.get("data_ingresso"))

        comp_prec = comp_att
        comp_att  = composizione
        versioni.append({"data":rdate,"n_segnali":n_seg,"segnali":seg,
                         "quota_az":round(ql*100),
                         "quota_xeon":round(qx*100),"composizione":composizione,
                         "capitale":round(capitale,2)})

    # ── Metriche ──────────────────────────────────────────────────────────────
    perf_tot = round((capitale-CAPITALE)/CAPITALE*100, 2)

    equity_mensile = []; cap_tmp = float(CAPITALE); months_seen = set()
    for rd, ret in sorted(rendimenti.items()):
        cap_tmp = round(cap_tmp*(1+ret/100), 2)
        m = rd[:7]
        if m not in months_seen:
            equity_mensile.append({"mese":m,"valore":cap_tmp}); months_seen.add(m)

    cap_s = [float(CAPITALE)] + [v["capitale"] for v in versioni]
    peak = cap_s[0]; mdd = 0
    for c in cap_s:
        if c > peak: peak = c
        dd = (c-peak)/peak*100
        if dd < mdd: mdd = dd

    rl = [rendimenti[d] for d in sorted(rendimenti)]

    def sharpe_n(rl, n, rf=0.03/52):
        if len(rl)<n: return None
        w=rl[-n:]; mr=sum(w)/len(w)-rf
        var=sum((r-sum(w)/len(w))**2 for r in w)/(len(w)-1) if len(w)>1 else 0
        std=math.sqrt(var) if var>0 else 0
        return round(mr/std*math.sqrt(52),2) if std>0 else None

    cap2 = [float(CAPITALE)]
    for d in sorted(rendimenti): cap2.append(cap2[-1]*(1+rendimenti[d]/100))
    peak=cap2[0]; dd_series=[]; dates_w=sorted(rendimenti.keys())
    for i,v in enumerate(cap2[1:]):
        if v>peak: peak=v
        dd_series.append({"data":dates_w[i],"dd":round((v-peak)/peak*100,3)})

    rolling_sh=[]; dates_s=sorted(rendimenti.keys())
    for i in range(13, len(rl)+1):
        w=rl[i-13:i]; rf=0.03/52; mr=sum(w)/len(w)-rf
        var=sum((r-sum(w)/len(w))**2 for r in w)/(len(w)-1) if len(w)>1 else 0
        std=math.sqrt(var) if var>0 else 0
        sh=round(mr/std*math.sqrt(52),3) if std>0 else 0
        rolling_sh.append({"data":dates_s[i-1] if i-1<len(dates_s) else None,"sharpe":sh})

    rpa=defaultdict(dict); prev_val=float(CAPITALE)
    for e in equity_mensile:
        anno,mese=e["mese"].split("-")
        rpa[anno][mese]=round((e["valore"]-prev_val)/prev_val*100,2); prev_val=e["valore"]
    rend_annuo={anno:round((math.prod(1+r/100 for r in mesi.values())-1)*100,2)
                for anno,mesi in rpa.items()}

    def calc_rend_bm(ticker):
        d=etf_data.get(ticker)
        if not d: return {},{}
        n=min(len(d["closes"]),len(d["dates"]))
        pairs=[(d["dates"][i],d["closes"][i]) for i in range(n) if d["dates"][i]>=backtest_start]
        if not pairs: return {},{}
        mc=defaultdict(list)
        for dt,cl in pairs: mc[dt[:7]].append(cl)
        mesi_ord=sorted(mc.keys()); rpa2=defaultdict(dict); ra2={}; prev=mc[mesi_ord[0]][0]
        for mese in mesi_ord:
            last=mc[mese][-1]; ret=round((last-prev)/prev*100,2) if prev else 0
            anno,m=mese.split("-"); rpa2[anno][m]=ret; prev=last
        for anno,mesi in rpa2.items():
            ra2[anno]=round((math.prod(1+r/100 for r in mesi.values())-1)*100,2)
        return dict(rpa2),ra2

    riw,riwa = calc_rend_bm(BENCHMARK)

    turnovers=[]
    for i in range(1,len(versioni)):
        pc={p["ticker"] for p in versioni[i-1].get("composizione",[])}
        cc={p["ticker"] for p in versioni[i].get("composizione",[])}
        changed=len(pc.symmetric_difference(cc)); tot=max(len(pc),len(cc))
        if tot>0: turnovers.append(changed/tot*100)
    turnover_medio=round(sum(turnovers)/len(turnovers),1) if turnovers else 0

    pps=defaultdict(list)
    for v in versioni:
        if v["data"] in rendimenti: pps[str(v["n_segnali"])].append(rendimenti[v["data"]])
    labels_step={"0":"100% long","1":"70% long","2":"30% long","3":"100% XEON"}
    perf_step={ns:{"media_sett":round(sum(r)/len(r),3),"n":len(r),
                   "positivi":sum(1 for x in r if x>0),"label":labels_step.get(ns,"")}
               for ns,r in pps.items()}

    storia_slim=[{k:v[k] for k in ["data","n_segnali","s1","s2","s3","quota_az_pct","descrizione"] if k in v}
                 for v in storia_segnali]

    return {
        "label":label,"backtest_start":backtest_start,
        "performance_totale_pct":perf_tot,
        "performance_totale_eur":round(capitale-CAPITALE,2),
        "capitale_attuale":round(capitale,2),
        "max_drawdown":round(mdd,2),
        "sharpe_6m":sharpe_n(rl,26),"sharpe_12m":sharpe_n(rl,52),
        "rolling_sharpe":rolling_sh,"drawdown_series":dd_series,
        "rend_per_anno":dict(rpa),"rend_annuo":rend_annuo,
        "rend_iwmo_mese":riw,"rend_iwmo_anno":riwa,
        "turnover_medio":turnover_medio,"perf_per_step":perf_step,
        "versioni":versioni,"composizione_corrente":comp_att,
        "data_ingresso_map":{t:v for t,v in data_ingresso_map.items()},
        "rendimenti":rendimenti,"equity_mensile":equity_mensile,
        "storia_segnali":storia_slim,"n_rebalancing":len(versioni),
        "n_etf_universo_long":len(universo_long),
        "segnali_oggi":storia_slim[-1] if storia_slim else {},
        "exit_forzati":exit_forzati_log,
        "cooldown_attivo":{t:d for t,d in cooldown_until.items() if d >= oggi},
    }

# ── UTILITÀ ───────────────────────────────────────────────────────────────────
def calc_bm_perf(ticker, etf_data, backtest_start):
    d=etf_data.get(ticker)
    if not d: return None
    p0=next((d["closes"][i] for i in range(len(d["dates"])) if d["dates"][i]>=backtest_start),None)
    p1=d["closes"][-1]
    return round((p1-p0)/p0*100,2) if p0 and p1 else None

def save_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,separators=(",",":"))
    print(f"  ✅ {path} ({Path(path).stat().st_size/1024:.0f} KB)")
