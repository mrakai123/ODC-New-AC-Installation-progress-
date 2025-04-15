import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
from io import BytesIO
import base64
from datetime import datetime
from zoneinfo import ZoneInfo

# --- إعداد الصفحة ---
st.set_page_config(page_title="ODC-AC Installation Dashboard", layout="wide")
refresh_interval = 30
st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")

# --- العناوين والشعارات ---
st.markdown("""
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <img src='https://i.ibb.co/S6ZwJYt/wiconnect-logo.png' width='150'>
        <h1 style='text-align: center; color: #007ACC;'>📊 ODC-AC Installation Dashboard</h1>
        <img src='https://i.ibb.co/Ycjgfdm/latis-logo.png' width='120'>
    </div>
""", unsafe_allow_html=True)

# --- تحميل البيانات ---
@st.cache_data(ttl=30)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1pZBg_lf8HakI6o2W1v8u1lUN2FGJn1Jc/export?format=csv&gid=622694975"
    form_url = "https://docs.google.com/spreadsheets/d/1IeZVNb01-AMRuXjj9SZQyELTVr6iw5Vq4JsiN7PdZEs/export?format=csv&gid=1076079545"
    try:
        df_sites = pd.read_csv(sheet_url)
        df_form = pd.read_csv(form_url)
        df_sites.columns = df_sites.columns.str.strip()
        df_form.columns = df_form.columns.str.strip()
        df_sites["Site ID"] = df_sites["Site ID"].astype(str).str.strip().str.upper()
        df_form["Site ID"] = df_form["Site ID"].astype(str).str.strip().str.upper()
        df = df_sites.merge(df_form[["Site ID", "Latitude", "Longitude", "Timestamp"]], on="Site ID", how="left")
        df["Status"] = df["Timestamp"].apply(lambda x: "Installed" if pd.notnull(x) else "Open")
        df["Installation Date"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
        df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
        df.dropna(subset=["Latitude", "Longitude"], inplace=True)
        return df
    except:
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.error("⚠️ No data loaded. Please check the Google Sheets links or structure.")
    st.stop()

# --- الفلاتر ---
st.sidebar.header("🔍 Filter Options")
regions = df["Region"].dropna().unique().tolist() if "Region" in df.columns else []
status_filter = st.sidebar.multiselect("Select Status", ["Installed", "Open"], default=["Installed", "Open"])
region_filter = st.sidebar.multiselect("Select Region", options=regions, default=regions)
date_range = st.sidebar.date_input("Installation Date Range", [])

filtered_df = df[df["Status"].isin(status_filter)]
if region_filter:
    filtered_df = filtered_df[filtered_df["Region"].isin(region_filter)]
if date_range and len(date_range) == 2:
    filtered_df = filtered_df[filtered_df["Installation Date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))]

# --- KPIs ---
st.markdown("""
    <style>
        .kpi-container {
            display: flex;
            justify-content: space-around;
            padding: 20px 0;
        }
        .kpi {
            background-color: #f0f8ff;
            border-radius: 15px;
            padding: 20px;
            width: 18%;
            text-align: center;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }
        .kpi h2 { color: #007ACC; margin-bottom: 10px; }
        .kpi p { font-size: 22px; font-weight: bold; }
    </style>
    <div class='kpi-container'>
        <div class='kpi'><h2>Total Sites</h2><p>{}</p></div>
        <div class='kpi'><h2>Installed</h2><p>{}</p></div>
        <div class='kpi'><h2>Open</h2><p>{}</p></div>
        <div class='kpi'><h2>Progress %</h2><p>{}%</p></div>
        <div class='kpi'><h2>Daily Rate</h2><p>{} sites/day</p></div>
    </div>
""".format(
    len(filtered_df),
    (filtered_df["Status"] == "Installed").sum(),
    (filtered_df["Status"] == "Open").sum(),
    round((filtered_df["Status"] == "Installed").sum() / len(filtered_df) * 100, 2) if len(filtered_df) else 0,
    round((filtered_df["Status"] == "Installed").sum() / max((filtered_df["Installation Date"].max() - filtered_df["Installation Date"].min()).days, 1), 2)
), unsafe_allow_html=True)

# --- Map ---
st.subheader("📍 Site Installation Map")
m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)
for _, row in filtered_df.iterrows():
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=5,
        popup=f"{row['Site ID']} - {row['Status']}",
        color="green" if row["Status"] == "Installed" else "red",
        fill=True,
        fill_opacity=0.7
    ).add_to(m)
folium_static(m)

# --- Charts ---
st.subheader("📊 Status Distribution")
fig_status = px.pie(filtered_df, names="Status", title="Status Breakdown", hole=0.4, color_discrete_sequence=["green", "red"])
st.plotly_chart(fig_status, use_container_width=True)

st.subheader("📈 Installation Trend")
df_trend = filtered_df[filtered_df["Status"] == "Installed"].groupby(filtered_df["Installation Date"].dt.date).size().reset_index(name="Installed")
fig_trend = px.line(df_trend, x="Installation Date", y="Installed", markers=True, title="Daily Installation")
st.plotly_chart(fig_trend, use_container_width=True)

# --- Export ---
st.markdown("### 📥 Export Options")
excel_buffer = BytesIO()
filtered_df.to_excel(excel_buffer, index=False)
st.download_button("⬇️ Download Excel", data=excel_buffer.getvalue(), file_name="installation_status.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

html_table = filtered_df[["Site ID", "Status", "Installation Date"]].to_html(index=False)
pdf_html = f"<html><body>{html_table}</body></html>"
b64 = base64.b64encode(pdf_html.encode()).decode()
st.markdown(f'<a href="data:text/html;base64,{b64}" download="installation_report.html">⬇️ Download PDF Report</a>', unsafe_allow_html=True)

# --- التذييل ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Powered by Mohammed Alfadhel</p>", unsafe_allow_html=True)

ksa_time = datetime.now(ZoneInfo("Asia/Riyadh"))
st.markdown(f"<p style='text-align: center;'>⏰ آخر تحديث: {ksa_time.strftime('%H:%M:%S')} - تحديث تلقائي كل {refresh_interval} ثانية</p>", unsafe_allow_html=True)
