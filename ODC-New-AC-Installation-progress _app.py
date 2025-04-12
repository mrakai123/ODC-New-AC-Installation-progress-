
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from io import BytesIO
import base64

st.set_page_config(layout="wide")
st.title("📊 Saudi AC Installation Dashboard")

@st.cache_data(ttl=86400)
def load_data():
    form_url = "https://docs.google.com/spreadsheets/d/1IeZVNb01-AMRuXjj9SZQyELTVr6iw5Vq4JsiN7PdZEs/gviz/tq?tqx=out:csv&sheet=Project Progress"
    project_url = "https://docs.google.com/spreadsheets/d/1pZBg_lf8HakI6o2W1v8u1lUN2FGJn1Jc/gviz/tq?tqx=out:csv&sheet=Tracking Sheet"

    df_installed = pd.read_csv(form_url)
    df_sites = pd.read_csv(project_url)

    df_installed.columns = df_installed.columns.str.strip()
    df_sites.columns = df_sites.columns.str.strip()

    df_installed["Site ID"] = df_installed["Site ID"].astype(str).str.upper().str.strip()
    df_sites["Site ID"] = df_sites["Site ID"].astype(str).str.upper().str.strip()

    df_sites["Latitude"] = pd.to_numeric(df_sites.get("Latitude"), errors="coerce")
    df_sites["Longitude"] = pd.to_numeric(df_sites.get("Longitude"), errors="coerce")
    df_sites.dropna(subset=["Latitude", "Longitude"], inplace=True)

    df_sites["Status"] = df_sites["Site ID"].apply(lambda x: "INSTALLED" if x in df_installed["Site ID"].values else "OPEN")
    df_sites["Installation Date"] = df_sites["Site ID"].map(
        df_installed.set_index("Site ID").get("Installation Date", pd.Series())
    )

    return df_sites

df = load_data()

total_sites = len(df)
installed = len(df[df["Status"] == "INSTALLED"])
open_sites = len(df[df["Status"] == "OPEN"])
progress = round((installed / total_sites) * 100, 2) if total_sites else 0

df["Installation Date"] = pd.to_datetime(df["Installation Date"], errors='coerce')
daily_rate = installed / df["Installation Date"].nunique() if installed else 0

st.markdown("### 📊 Saudi AC Installation Dashboard")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Sites", total_sites)
col2.metric("Installed", installed)
col3.metric("Open", open_sites)
col4.metric("Progress %", f"{progress}%")
col5.metric("Daily Rate", f"{daily_rate:.2f} sites/day")

st.markdown("### 📍 Site Installation Map")
m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)

def get_color(status):
    return "green" if status == "INSTALLED" else "red"

for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=5,
        color=get_color(row["Status"]),
        fill=True,
        fill_opacity=0.7,
        popup=f"Site: {row['Site ID']}<br>Status: {row['Status']}<br>Date: {row['Installation Date']}",
    ).add_to(m)

st_folium(m, width=1000, height=500)

st.markdown("### 📋 Detailed Site Table")
st.dataframe(df[["Site ID", "Region", "Status", "Installation Date"]])

excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False)
b64_excel = base64.b64encode(excel_buffer.getvalue()).decode()
href = f'<a href="data:application/octet-stream;base64,{b64_excel}" download="project_progress.xlsx">📥 Download Excel Data</a>'
st.markdown(href, unsafe_allow_html=True)
