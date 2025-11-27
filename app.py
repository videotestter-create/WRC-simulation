
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import plotly.express as px
import random

st.set_page_config(page_title="WRC Live Simulation", layout="wide")
st.title("🏁 WRC Rally Saudi Arabia 2025 – Live Simulation Dashboard")

EWRC_URL = "https://www.ewrc-results.com/results/90029-rally-saudi-arabia-2025/"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]
REFERER = "https://www.ewrc-results.com/"

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
    st.warning("Nepodařilo se načíst data z eWRC. Nahraj CSV export z eWRC níže.")
    uploaded_file = st.file_uploader("Nahraj CSV soubor z eWRC", type=["csv"])
    if uploaded_file:
        stage_df = pd.read_csv(uploaded_file)
        st.success("CSV načteno.")

if not stage_df.empty:
    st.dataframe(stage_df)

    # Predikce ETA
    pred_df = stage_df.copy()

    def parse_start_time(t: str):
        if not t:
            return None
        try:
            today = datetime.now()
            dt = datetime.strptime(t, "%H:%M").replace(year=today.year, month=today.month, day=today.day)
            return dt
        except:
            return None

    if 'start_time' in pred_df.columns:
        pred_df['start_dt'] = pred_df['start_time'].apply(parse_start_time)
        pred_df['duration_h'] = pred_df.apply(lambda r: (r['length_km']/r['avg_speed']) if (r.get('length_km') and r.get('avg_speed') and r['avg_speed']>0) else None, axis=1)
        pred_df['eta_finish'] = pred_df.apply(lambda r: (r['start_dt'] + timedelta(hours=r['duration_h'])) if (r.get('start_dt') and r.get('duration_h')) else None, axis=1)

        st.subheader("Predikované časy dojezdu (ETA)")
        st.dataframe(pred_df[['stage','start_time','length_km','avg_speed','eta_finish']])

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

# Simulace bodů
championship_points = {
    'Elfyn Evans': 243,
    'Sébastien Ogier': 240,
    'Kalle Rovanperä': 232,
    'Ott Tänak': 210,
    'Thierry Neuville': 205,
}
current_positions = ['Ott Tänak','Elfyn Evans','Sébastien Ogier','Kalle Rovanperä','Thierry Neuville']
rally_points = [25,17,15,12,10]
updated = championship_points.copy()
for i, drv in enumerate(current_positions):
    updated[drv] = updated.get(drv,0) + rally_points[i]
stand_df = pd.DataFrame(sorted(updated.items(), key=lambda x:x[1], reverse=True), columns=['Driver','Points'])

st.subheader("Simulované pořadí šampionátu")
st.table(stand_df)
fig = px.bar(stand_df, x='Driver', y='Points', title='Porovnání bodů', text='Points')
fig.update_layout(height=400)
st.plotly_chart(fig, use_container_width=True)
