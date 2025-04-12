
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from io import BytesIO
import base64

st.set_page_config(page_title="Saudi AC Installation Dashboard", layout="wide")

@st.cache_data(ttl=86400)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1IeZVNb01-AMRuXjj9SZQyELTVr6iw5Vq4JsiN7PdZEs/export?format=csv&gid=1076079545"
    df = pd.read_csv(sheet_url)
    df.columns = df.columns.str.strip()

    # Normalize columns
    df = df.rename(columns=lambda x: x.strip())
    if "Site ID" not in df.columns:
        raise KeyError("'Site ID' column not found in the Google Sheet")

    df["Site ID"] = df["Site ID"].astype(str).str.strip().str.upper()
    df["Scope Status"] = df["Scope Status"].astype(str).str.lower()
    df["Installation Date"] = pd.to_datetime(df["Installation Date"], errors="coerce")

    # Filter rows with valid Lat/Lon if exist
    if "Latitude" in df.columns and "Longitude" in df.columns:
        df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
        df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
        df = df.dropna(subset=["Latitude", "Longitude"])

    return df

df = load_data()

# Metrics
total_sites = len(df)
installed_sites = df[df["Scope Status"] == "installed"]
installed_count = len(installed_sites)
open_count = total_sites - installed_count
progress_percent = round((installed_count / total_sites) * 100, 2) if total_sites > 0 else 0

# Daily rate
if not installed_sites["Installation Date"].isna().all():
    installed_sites = installed_sites.dropna(subset=["Installation Date"])
    if len(installed_sites) > 0:
        date_range = installed_sites["Installation Date"].max() - installed_sites["Installation Date"].min()
        daily_rate = round(installed_count / date_range.days, 2) if date_range.days > 0 else installed_count
    else:
        daily_rate = 0
else:
    daily_rate = 0

st.title("📊 Saudi AC Installation Dashboard")
st.markdown("")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Sites", total_sites)
col2.metric("Installed", installed_count)
col3.metric("Open", open_count)
col4.metric("Progress %", f"{progress_percent}%")
col5.metric("Daily Rate", f"{daily_rate} sites/day")

# Map
st.subheader("📍 Site Installation Map")
if "Latitude" in df.columns and "Longitude" in df.columns:
    m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)
    for _, row in df.iterrows():
        status = row["Scope Status"]
        color = "green" if status == "installed" else "red"
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=row["Site ID"]
        ).add_to(m)
    st_folium(m, width=1000, height=500)
else:
    st.warning("Latitude and Longitude data not found.")

# Chart: Installed Over Time
st.subheader("📈 Installation Trend")
if not installed_sites.empty:
    trend = installed_sites.groupby(installed_sites["Installation Date"].dt.date).size()
    fig, ax = plt.subplots()
    trend.plot(kind="line", marker="o", ax=ax)
    ax.set_xlabel("Date")
    ax.set_ylabel("Installed Sites")
    ax.set_title("Daily Installation Trend")
    st.pyplot(fig)
else:
    st.info("No installation data available.")

# Export Buttons
st.subheader("📥 Export Data")

excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False)
excel_buffer.seek(0)
b64_excel = base64.b64encode(excel_buffer.read()).decode()
st.download_button("📊 Download Excel", f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}", file_name="ac_installation_data.xlsx")

pdf_placeholder = st.empty()
st.caption("📌 PDF download feature is not supported in Streamlit Cloud directly.")
