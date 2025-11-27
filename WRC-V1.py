
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# URL of WRC results page
URL = "https://www.wrc.com/en/events/wrc-rally-saudi-arabia-2025/wrc-rally-saudi-arabia-results-2025"

def fetch_wrc_data():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract current and next SS info
        current_ss = soup.find("div", class_="current-stage")
        next_ss = soup.find("div", class_="next-stage")
        current_ss_info = current_ss.get_text(strip=True) if current_ss else "Unknown"
        next_ss_info = next_ss.get_text(strip=True) if next_ss else "Unknown"

        # Extract results table
        table = soup.find("table")
        if not table:
            return current_ss_info, next_ss_info, pd.DataFrame()

        rows = table.find_all("tr")
        data = []
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 6:
                data.append([
                    cols[0].get_text(strip=True),
                    cols[1].get_text(strip=True),
                    cols[2].get_text(strip=True),
                    cols[3].get_text(strip=True),
                    cols[4].get_text(strip=True),
                    cols[5].get_text(strip=True)
                ])

        df = pd.DataFrame(data, columns=["Position", "Driver", "Co-Driver", "Car", "Total Time", "Gap"])
        return current_ss_info, next_ss_info, df

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return "Unknown", "Unknown", pd.DataFrame()

# Streamlit UI
st.title("🏁 WRC Rally Saudi Arabia 2025 Results")
st.write("Live overall classification and stage info")

current_ss, next_ss, results_df = fetch_wrc_data()

st.subheader("Current Stage")
st.write(current_ss)

st.subheader("Next Stage")
st.write(next_ss)

if not results_df.empty:
    st.subheader("Overall Classification")
    st.dataframe(results_df)
else:
    st.warning("No results available at the moment.")

# Optional: Auto-refresh every X seconds
st.write("Page refreshes every 60 seconds.")
st.experimental_rerun()
