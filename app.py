#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import plotly.express as px
import random, unicodedata

st.set_page_config(page_title="WRC Live Simulation", layout="wide")
st.title("🏁 WRC Rally Saudi Arabia 2025 – Live Simulation Dashboard (Final)")

EWRC_URL = "https://www.ewrc-results.com/results/90029-rally-saudi-arabia-2025/"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
]
REFERER = "https://www.ewrc-results.com/"

# ✅ Base points (confirmed latest)
BASE_POINTS = {
    'Elfyn Evans': 289,
    'Sébastien Ogier': 284,
    'Kalle Rovanperä': 260,
    'Ott Tänak': 238,
    'Thierry Neuville': 176,
}

# Normalize names

def normalize_name(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize('NFKD', name)
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return n.strip().lower()

NAME_MAP = {normalize_name(k): k for k in BASE_POINTS.keys()}

st.sidebar.header("Nastavení")
fallback_refresh = st.sidebar.number_input("Fallback refresh (sekundy)", min_value=60, max_value=1800, value=300, step=30)

@st.cache_data(ttl=300)
def fetch_stage_table(url: str) -> pd.DataFrame:
    headers = {"User-Agent": random.choice(USER_AGENTS), "Referer": REFERER}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        st.error(f"Nepodařilo se načíst eWRC: {e}")
        st.info("Možné důvody selhání:")
        st.markdown("""
        - **403 Forbidden**: eWRC blokuje přímé požadavky bez správných hlaviček.
        - **Dynamické načítání**: Data se načítají přes JavaScript, který `requests` nevykoná.
        - **Změna struktury HTML**: Scraper nenajde očekávané elementy.
        - **IP blokace**: Opakované požadavky mohou být blokovány.
        """)
        return pd.DataFrame()
    soup = BeautifulSoup(r.text, 'html.parser')
    rows = []
    tables = soup.find_all('table')
    for tbl in tables:
        headers_row = [th.get_text(strip=True).lower() for th in tbl.find_all('th')]
        if not headers_row:
            continue
        if any('km' in h or 'length' in h for h in headers_row) and any('speed' in h for h in headers_row):
            for tr in tbl.find_all('tr')[1:]:
                tds = tr.find_all('td')
                if not tds:
                    continue
                cols = [td.get_text(strip=True) for td in tds]
                stage = cols[0] if len(cols) > 0 else None
                length_km = None
                for c in cols:
                    if 'km' in c:
                        try:
                            length_km = float(c.replace('km','').replace(',', '.').strip())
                            break
                        except:
                            pass
                start_time = None
                for c in cols:
                    if ':' in c and len(c) <= 5 and c.replace(':','').isdigit():
                        start_time = c
                        break
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

# Try scraping
stage_df = fetch_stage_table(EWRC_URL)

st.subheader("Data z eWRC – Stage Results")
if stage_df.empty:
    st.info("Nepodařilo se načíst data z eWRC. Můžeš nahrát CSV export z eWRC níže.")
    uploaded_file = st.file_uploader("Nahraj CSV soubor z eWRC", type=["csv"])
    if uploaded_file:
        try:
            stage_df = pd.read_csv(uploaded_file)
            st.success("CSV načteno.")
        except Exception as e:
            st.error(f"Chyba při načtení CSV: {e}")

if not stage_df.empty:
    st.dataframe(stage_df)

# ETA prediction
pred_df = stage_df.copy()

def parse_start_time(t: str):
    if not isinstance(t, str) or not t:
        return None
    try:
        today = datetime.now()
        dt = datetime.strptime(t, "%H:%M").replace(year=today.year, month=today.month, day=today.day)
        return dt
    except:
        return None

if not pred_df.empty:
    if 'start_time' in pred_df.columns:
        pred_df['start_dt'] = pred_df['start_time'].apply(parse_start_time)
        def to_float(x):
            try:
                return float(x)
            except:
                return None
        if 'length_km' in pred_df.columns:
            pred_df['length_km'] = pred_df['length_km'].apply(to_float)
        if 'avg_speed' in pred_df.columns:
            pred_df['avg_speed'] = pred_df['avg_speed'].apply(to_float)
        pred_df['duration_h'] = pred_df.apply(lambda r: (r['length_km']/r['avg_speed']) if (r.get('length_km') and r.get('avg_speed') and r['avg_speed']>0) else None, axis=1)
        pred_df['eta_finish'] = pred_df.apply(lambda r: (r['start_dt'] + timedelta(hours=r['duration_h'])) if (r.get('start_dt') and r.get('duration_h')) else None, axis=1)
        st.subheader("Predikované časy dojezdu (ETA)")
        show_cols = [c for c in ['stage','start_time','length_km','avg_speed','eta_finish'] if c in pred_df.columns]
        st.dataframe(pred_df[show_cols])
        next_eta = None
        if 'eta_finish' in pred_df.columns and not pred_df['eta_finish'].dropna().empty:
            future = pred_df[pred_df['eta_finish'] > datetime.now()]
            if not future.empty:
                next_eta = future['eta_finish'].min()
            else:
                next_eta = pred_df['eta_finish'].max()
        if next_eta:
            st.info(f"Další očekávaná aktualizace: {next_eta.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.info("ETA zatím nelze spočítat – chybí startovní časy nebo rychlosti.")

# Championship simulation
if 'base_points' not in st.session_state:
    st.session_state.base_points = BASE_POINTS.copy()
base_points = st.session_state.base_points.copy()

st.subheader("Základní bodové pořadí (eWRC)")
base_df = pd.DataFrame(sorted(base_points.items(), key=lambda x:x[1], reverse=True), columns=['Driver','Points'])
base_df['Rank'] = range(1, len(base_df)+1)
base_df = base_df[['Rank','Driver','Points']]
st.dataframe(base_df, use_container_width=True)

current_positions = ['Ott Tänak','Elfyn Evans','Sébastien Ogier','Kalle Rovanperä','Thierry Neuville']
rally_points = [25,17,15,12,10]

updated_norm = {normalize_name(k): v for k,v in base_points.items()}
for i, drv in enumerate(current_positions):
    n = normalize_name(drv)
    add = rally_points[i] if i < len(rally_points) else 0
    updated_norm[n] = updated_norm.get(n, 0) + add

updated = []
for n_key, pts in updated_norm.items():
    orig = NAME_MAP.get(n_key, n_key)
    updated.append((orig, int(pts)))

stand_df = pd.DataFrame(sorted(updated, key=lambda x:x[1], reverse=True), columns=['Driver','Points'])
stand_df['Rank'] = range(1, len(stand_df)+1)
stand_df = stand_df[['Rank','Driver','Points']]

st.subheader("Simulované pořadí šampionátu (po aktuálním pořadí v rally)")
st.dataframe(stand_df, use_container_width=True)
fig = px.bar(stand_df.sort_values('Rank'), x='Driver', y='Points', title='Porovnání bodů – simulace', text='Points')
fig.update_layout(height=420)
st.plotly_chart(fig, use_container_width=True)
