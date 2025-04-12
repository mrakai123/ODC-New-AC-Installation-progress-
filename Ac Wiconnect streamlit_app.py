
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from io import BytesIO
import base64

# Title
st.set_page_config(layout="wide")
st.title("📊 Saudi AC Installation Dashboard")

# Load data
@st.cache_data(ttl=86400)
def load_data():
    # Project Progress sheet only
    form_url = "https://docs.google.com/spreadsheets/d/1IeZVNb01-AMRuXjj9SZQyELTVr6iw5Vq4JsiN7PdZEs/gviz/tq?tqx=out:csv&sheet=Project Progress"
    project_url = "https://docs.google.com/spreadsheets/d/1pZBg_lf8HakI6o2W1v8u1lUN2FGJn1Jc/export?format=csv&gid=622694975"

    df_installed = pd.read_csv(form_url)
df_installed = df_installed.copy()
df_installed.columns = df_installed.columns.str.strip()
df_installed = df_installed.loc[:, ~df_installed.columns.duplicated()].copy()
    df_sites = pd.read_csv(project_url)
df_sites = df_sites.copy()
df_sites.columns = df_sites.columns.str.strip()
df_sites = df_sites.loc[:, ~df_sites.columns.duplicated()].copy()

    df_sites.columns = df_sites.columns.str.strip()
    df_installed.columns = df_installed.columns.str.strip()

    df_sites["Site ID"] = df_sites["Site ID"].astype(str).str.strip().str.upper()
    df_installed["Site ID"] = df_installed["Site ID"].astype(str).str.strip().str.upper()

    df = pd.merge(df_sites, df_installed[["Site ID", "Latitude", "Longitude", "Timestamp"]], on="Site ID", how="left")

    df["Scope Status"] = df["Scope Status"].str.strip().str.lower()
    df["Installation Status"] = df["Count Of Installed ACs"].apply(lambda x: "INSTALLED" if x >= 1 else "open")

    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    df["Installation Date"] = pd.to_datetime(df["Timestamp"], errors="coerce").dt.date
    return df

df = load_data()

# KPIs
total_sites = len(df)
installed = df["Installation Status"].str.upper().eq("INSTALLED").sum()
open_sites = df["Installation Status"].str.lower().eq("open").sum()
progress = round((installed / total_sites) * 100, 2) if total_sites else 0

start_date = df["Installation Date"].dropna().min()
today = datetime.today().date()
days_passed = (today - start_date).days if start_date else 0
daily_rate = round(installed / days_passed, 2) if days_passed else 0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Sites", total_sites)
kpi2.metric("Installed", installed)
kpi3.metric("Open", open_sites)
kpi4.metric("Progress %", f"{progress}%")
kpi5.metric("Daily Rate", f"{daily_rate} sites/day")

# Map
st.subheader("📍 Site Installation Map")

def get_color(scope_status, install_status):
    if str(scope_status).lower() == "open":
        return "red"
    elif str(install_status).strip().upper() == "INSTALLED":
        return "green"
    return "gray"

m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)

for _, row in df.iterrows():
    if "Latitude" in row and "Longitude" in row and pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f'Site ID: {row["Site ID"]} | Status: {row["Installation Status"]}',
            icon=folium.Icon(color=get_color(row["Scope Status"], row["Installation Status"]))
        ).add_to(m)

st_data = st_folium(m, width=1100, height=500)

# Chart
st.subheader("📊 Installation Status Distribution")
st.bar_chart(df["Installation Status"].value_counts())

# Trend
st.subheader("📈 Daily Installation Trend")
trend = df[df["Installation Status"] == "INSTALLED"].groupby("Installation Date").size()
st.line_chart(trend)

# Download buttons
st.subheader("📥 Export Data")
excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False, engine='openpyxl')
excel_data = excel_buffer.getvalue()
b64 = base64.b64encode(excel_data).decode()
href = f'<a href="data:application/octet-stream;base64,{b64}" download="Saudi_AC_Installation_Progress.xlsx">📥 Download Excel File</a>'
st.markdown(href, unsafe_allow_html=True)
