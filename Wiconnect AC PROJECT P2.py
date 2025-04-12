import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt

# Title
st.set_page_config(page_title="Saudi AC Installation Dashboard", layout="wide")
st.title("📊 Saudi AC Installation Dashboard")

# Load Google Sheet
@st.cache_data
def load_data():
    url_sites = "https://docs.google.com/spreadsheets/d/1pZBg_lf8HakI6o2W1v8u1lUN2FGJn1Jc/export?format=csv&gid=622694975"
    url_installed = "https://docs.google.com/spreadsheets/d/1IeZVNb01-AMRuXjj9SZQyELTVr6iw5Vq4JsiN7PdZEs/export?format=csv&gid=1076079545"
    df_sites = pd.read_csv(url_sites)
    df_installed = pd.read_csv(url_installed)

    df_sites.columns = df_sites.columns.str.strip()
    df_installed.columns = df_installed.columns.str.strip()

    df_sites["Site ID"] = df_sites["Site ID"].astype(str).str.strip().str.upper()
    df_installed["Site ID"] = df_installed["Site ID"].astype(str).str.strip().str.upper()

    df = df_sites.merge(df_installed[["Site ID", "Installation Date"]], on="Site ID", how="left")
    df["Scope Status"] = df["Scope Status"].fillna("Open")
    df["Installation Date"] = pd.to_datetime(df["Installation Date"], errors="coerce")
    df["Status"] = df["Installation Date"].notna().map({True: "Installed", False: "Open"})
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df.dropna(subset=["Latitude", "Longitude"], inplace=True)

    return df

df = load_data()

# KPIs
total_sites = len(df)
installed_sites = (df["Status"] == "Installed").sum()
open_sites = (df["Status"] == "Open").sum()
progress = round(installed_sites / total_sites * 100, 2)
daily_rate = round(installed_sites / max((df["Installation Date"].max() - df["Installation Date"].min()).days + 1, 1), 2)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Sites", total_sites)
col2.metric("Installed", installed_sites)
col3.metric("Open", open_sites)
col4.metric("Progress %", f"{progress}%")
col5.metric("Daily Rate", f"{daily_rate} sites/day")

# Map
st.subheader("📍 Site Installation Map")
def get_color(status):
    return "green" if status == "Installed" else "red"

m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)
for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        color=get_color(row["Status"]),
        fill=True,
        fill_opacity=0.7,
        popup=f"{row['Site ID']} - {row['Status']}"
    ).add_to(m)
st_folium(m, width=1100)

# Chart
st.subheader("📈 Daily Installation Trend")
installed_df = df[df["Status"] == "Installed"]
daily_installs = installed_df["Installation Date"].value_counts().sort_index()
fig, ax = plt.subplots()
daily_installs.plot(kind="bar", ax=ax)
ax.set_xlabel("Date")
ax.set_ylabel("Sites Installed")
st.pyplot(fig)

# Download buttons
st.subheader("📥 Export Data")
buffer = BytesIO()
df.to_excel(buffer, index=False, engine="openpyxl")
st.download_button("Download Excel", buffer.getvalue(), file_name="installation_progress.xlsx", mime="application/vnd.ms-excel")

from xhtml2pdf import pisa
html_content = f"<h1>Installation Report</h1><p>Total Sites: {total_sites}, Installed: {installed_sites}, Open: {open_sites}, Progress: {progress}%</p>"
pdf = BytesIO()
pisa.CreatePDF(src=html_content, dest=pdf)
st.download_button("Download PDF", pdf.getvalue(), file_name="installation_report.pdf", mime="application/pdf")