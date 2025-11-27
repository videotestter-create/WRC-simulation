#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="WRC Live Simulation", layout="wide")
st.title("🏁 WRC Rally Saudi Arabia 2025 – Live Simulation Dashboard")

# --- CONFIGURATION ---
EWRC_URL = "https://www.ewRC-results.com/results/90029-rally-saudi-arabia-2025/"  # case-insensitive
FALLBACK_REFRESH_SEC = 300  # 5 minutes fallback

st.sidebar.header("Nastavení")
fallback = st.sidebar.number_input("Fallback refresh (sekundy)", min_value=60, max_value=1800, value=FALLBACK_REFRESH_SEC, step=30)

@st.cache_data(ttl=300)
def fetch_stage_table(url: str) -> pd.DataFrame:
    """Scrape eWRC stage results page and return a table with stage, length, start, avg_speed."""
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except Exception as e:
        st.error(f"Nepodařilo se načíst eWRC: {e}")
        return pd.DataFrame()
    soup = BeautifulSoup(r.text, 'html.parser')

    rows = []
    # eWRC struktura se může lišit – pokusíme se najít tabulku se stage results
    tables = soup.find_all('table')
    for tbl in tables:
        headers = [th.get_text(strip=True).lower() for th in tbl.find_all('th')]
        if not headers:
            continue
        # heuristika: tabulka obsahuje délku (km) a průměrnou rychlost
        if any('km' in h or 'length' in h for h in headers) and any('speed' in h for h in headers):
            for tr in tbl.find_all('tr')[1:]:
                tds = tr.find_all('td')
                if not tds:
                    continue
                cols = [td.get_text(strip=True) for td in tds]
                # best effort mapping
                stage = cols[0] if len(cols) > 0 else None
                # try extract length (km)
                length_km = None
                for c in cols:
                    if 'km' in c:
                        try:
                            length_km = float(c.replace('km','').replace(',', '.').strip())
                            break
                        except:
                            pass
                # start time may be like 20:35
                start_time = None
                for c in cols:
                    if ':' in c and len(c) <= 5 and c.replace(':','').isdigit():
                        start_time = c
                        break
                # avg speed (last numeric in row)
                avg_speed = None
                for c in reversed(cols):
                    try:
                        avg_speed = float(c.replace('km/h','').replace(',', '.').strip())
                        break
                    except:
                        continue
                rows.append({'stage': stage, 'length_km': length_km, 'start_time': start_time, 'avg_speed': avg_speed})
            break
    return pd.DataFrame(rows)

stage_df = fetch_stage_table(EWRC_URL)

st.subheader("Data z eWRC – Stage Results")
if stage_df.empty:
    st.warning("Tabulka etap nebyla nalezena. Ověř prosím, že stránka eWRC obsahuje sekci Stage Results.")
else:
    st.dataframe(stage_df)

# --- Predikce dojezdů podle průměrné rychlosti ---
pred_df = stage_df.copy()

def parse_start_time(t: str) -> datetime | None:
    if not t:
        return None
    try:
        # předpoklad: dnešní datum, čas HH:MM místní
        today = datetime.now()
        dt = datetime.strptime(t, "%H:%M").replace(year=today.year, month=today.month, day=today.day)
        return dt
    except:
        return None

pred_df['start_dt'] = pred_df['start_time'].apply(parse_start_time)
pred_df['duration_h'] = pred_df.apply(lambda r: (r['length_km']/r['avg_speed']) if (r['length_km'] and r['avg_speed'] and r['avg_speed']>0) else None, axis=1)
pred_df['eta_finish'] = pred_df.apply(lambda r: (r['start_dt'] + timedelta(hours=r['duration_h'])) if (r['start_dt'] and r['duration_h']) else None, axis=1)

st.subheader("Predikované časy dojezdu (ETA)")
st.dataframe(pred_df[['stage','start_time','length_km','avg_speed','eta_finish']])

# --- Určení nejbližšího očekávaného dojezdu ---
next_eta = None
if not pred_df['eta_finish'].dropna().empty:
    future = pred_df[pred_df['eta_finish'] > datetime.now()]
    if not future.empty:
        next_eta = future['eta_finish'].min()
    else:
        next_eta = pred_df['eta_finish'].max()

if next_eta:
    st.info(f"Další očekávaná aktualizace: {next_eta.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.info("ETA zatím nelze spočítat – chybí startovní časy nebo rychlosti.")

# --- Simulace bodů šampionátu (aktuální pořadí v rally je třeba napojit na live timing) ---
championship_points = {
    'Elfyn Evans': 243,
    'Sébastien Ogier': 240,
    'Kalle Rovanperä': 232,
    'Ott Tänak': 210,
    'Thierry Neuville': 205,
}

# TODO: Napojit na live pořadí z eWRC nebo WRC.com – dočasně příklad
current_positions = ['Ott Tänak','Elfyn Evans','Sébastien Ogier','Kalle Rovanperä','Thierry Neuville']
rally_points = [25,17,15,12,10]

updated = championship_points.copy()
for i, drv in enumerate(current_positions):
    updated[drv] = updated.get(drv,0) + rally_points[i]

stand_df = pd.DataFrame(sorted(updated.items(), key=lambda x:x[1], reverse=True), columns=['Driver','Points'])

st.subheader("Simulované pořadí šampionátu (pokud rally skončí aktuálním stavem)")
st.table(stand_df)

fig = px.bar(stand_df, x='Driver', y='Points', title='Porovnání bodů', text='Points')
fig.update_layout(height=400)
st.plotly_chart(fig, use_container_width=True)

# --- Auto-refresh logika ---
# Streamlit nemá cron, ale lze vynutit rerun pomocí st.experimental_rerun v kombinaci s javascriptem/Meta refresh
# Zde zobrazíme countdown do next_eta a doporučení ručního reloadu.
if next_eta:
    seconds_to_eta = (next_eta - datetime.now()).total_seconds()
    if seconds_to_eta > 0:
        st.sidebar.success(f"Automatický refresh doporučen za ~{int(seconds_to_eta)} s")
    else:
        st.sidebar.warning("Etapa by měla být v cíli – obnov stránku (Ctrl+R) pro nové výsledky.")
else:
    st.sidebar.info(f"Fallback refresh: každých {fallback} s")
