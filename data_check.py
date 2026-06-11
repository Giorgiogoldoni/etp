#!/usr/bin/env python3
"""
data_check.py — Verifica disponibilità dati storici ETF WT
Trova la data più antica di quotazione per ogni ETF
Determina il periodo valido per il backtest
"""

import json, datetime, time, urllib.request
from pathlib import Path

def fetch_yahoo(ticker, days=3650):
    """Scarica dati da Yahoo Finance"""
    end = int(datetime.datetime.utcnow().timestamp())
    start = end - days * 86400
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?interval=1d&period1={start}&period2={end}&events=history")
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            result = data.get("chart", {}).get("result")
            if not result:
                time.sleep(2)
                continue
            ts = result[0]["timestamp"]
            q = result[0]["indicators"]["quote"][0]
            adj = result[0]["indicators"].get("adjclose", [{}])[0].get("adjclose", q["close"])
            dates = [datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d") for t in ts]
            closes = [float(v) if v else None for v in adj]
            valid = [(d, c) for d, c in zip(dates, closes) if c]
            if len(valid) < 60:
                return None, None, len(valid)
            return valid[0][0], valid[-1][0], len(valid)
        except Exception as e:
            time.sleep(2*attempt+1)
    return None, None, 0

# ETF Universe WT
UNIVERSO = [
    {"ticker": "WS5X.MI", "nome": "WT Euro Stoxx 50"},
    {"ticker": "WSPX.MI", "nome": "WT S&P 500"},
    {"ticker": "WNAS.MI", "nome": "WT Nasdaq-100"},
    {"ticker": "WWRD.MI", "nome": "WT World"},
    {"ticker": "WRTY.MI", "nome": "WT Russell 2000"},
    {"ticker": "WSPE.MI", "nome": "WT S&P 500 EUR Hedged"},
]

# Benchmark
BENCHMARK = "IWMO.MI"

print("=" * 80)
print("DATA CHECK — Verifica Disponibilità Storica ETF WT")
print("=" * 80)

data_map = {}
dates_inizio = []

# Check ETF WT
print("\n📊 ETF UNIVERSO WT:")
print("-" * 80)
for etf in UNIVERSO:
    ticker = etf["ticker"]
    nome = etf["nome"]
    print(f"\n  {ticker:<15} {nome:<35} ", end="", flush=True)
    
    first_date, last_date, n_days = fetch_yahoo(ticker, days=3650)
    
    if first_date:
        data_map[ticker] = {"first": first_date, "last": last_date, "days": n_days}
        dates_inizio.append(first_date)
        
        # Colore età ETF
        try:
            age_days = (datetime.datetime.now() - datetime.datetime.fromisoformat(first_date)).days
            age_years = age_days / 365.25
            if age_years < 1:
                marker = "⚠️  GIOVANE"
            elif age_years < 3:
                marker = "⚡ NUOVO"
            else:
                marker = "✅ MATURO"
        except:
            marker = "❌"
        
        print(f"{marker}")
        print(f"    → Primi dati: {first_date}  |  Ultimi: {last_date}  |  {n_days} giorni")
    else:
        print("❌ ERRORE")
        print(f"    → Dati insufficienti o ticker errato")
    
    time.sleep(0.3)

# Check Benchmark IWMO
print(f"\n📈 BENCHMARK:")
print("-" * 80)
print(f"  {BENCHMARK:<15} iShares MSCI World Momentum", end="", flush=True)
first_bm, last_bm, n_days_bm = fetch_yahoo(BENCHMARK, days=3650)
if first_bm:
    data_map[BENCHMARK] = {"first": first_bm, "last": last_bm, "days": n_days_bm}
    print(f" ✅")
    print(f"    → Primi dati: {first_bm}  |  Ultimi: {last_bm}  |  {n_days_bm} giorni")
else:
    print(f" ❌")

# Determina il periodo valido
print("\n" + "=" * 80)
print("📅 ANALISI PERIODO VALIDO PER BACKTEST")
print("=" * 80)

if dates_inizio:
    # Data più recente fra tutte le prime date (il vincolo)
    backtest_start = max(dates_inizio)
    print(f"\n✅ Data INIZIO backtest: {backtest_start}")
    print(f"   (Tutti gli ETF hanno dati da questa data in poi)")
    
    # Quanti giorni di storia
    try:
        days_available = (datetime.datetime.now() - datetime.datetime.fromisoformat(backtest_start)).days
        years_available = days_available / 365.25
        print(f"\n📊 Periodo disponibile: {days_available} giorni (~{years_available:.1f} anni)")
    except:
        print(f"\n📊 Periodo disponibile: Calcolo fallito")
    
    # Mostra timeline
    print(f"\n🗓️  TIMELINE ETF:")
    print("-" * 80)
    timeline = [(d, f"ETF {[e['ticker'] for e in UNIVERSO if data_map.get(e['ticker'], {}).get('first') == d][0] if d in [data_map.get(e['ticker'], {}).get('first') for e in UNIVERSO] else 'Benchmark'}") 
                for d in sorted(set(dates_inizio + ([first_bm] if first_bm else [])))]
    for date_str, etf_name in timeline:
        marker = "🔴" if date_str == backtest_start else "🟢"
        print(f"  {marker} {date_str}: {etf_name}")
    
    # Report finale
    print("\n" + "=" * 80)
    print("🎯 RACCOMANDAZIONE")
    print("=" * 80)
    print(f"""
Backtest dovrebbe iniziare da: {backtest_start}

ETF Critici (quotati dopo 2022-01-01):
""")
    
    for etf in UNIVERSO:
        ticker = etf["ticker"]
        if ticker in data_map:
            first = data_map[ticker]["first"]
            if first > "2022-01-01":
                print(f"  ⚠️  {ticker}: {first} (GIOVANE)")
    
    print(f"""
Periodo backtest: {backtest_start} → {datetime.date.today().isoformat()}
Durata: ~{years_available:.1f} anni

✅ PRONTO PER BACKTEST
""")
else:
    print("\n❌ Nessun dato disponibile!")

print("=" * 80)
