import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import base64

# --- إعداد الصفحة ---
st.set_page_config(page_title="ODC-AC Installation Dashboard", layout="wide")
st_autorefresh(interval=30 * 1000, key="auto_refresh")

# --- تحميل البيانات ---
@st.cache_data(ttl=30)
def load_data():
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1pZBg_lf8HakI6o2W1v8u1lUN2FGJn1Jc/export?format=csv&gid=622694975"
        form_url = "https://docs.google.com/spreadsheets/d/1IeZVNb01-AMRuXjj9SZQyELTVr6iw5Vq4JsiN7PdZEs/export?format=csv&gid=1076079545"
        df_sites = pd.read_csv(sheet_url)
        df_form = pd.read_csv(form_url)
    except:
        return pd.DataFrame()

    df_sites.columns = df_sites.columns.str.strip()
    df_form.columns = df_form.columns.str.strip()

    if "Site ID" not in df_sites.columns or "Site ID" not in df_form.columns:
        return pd.DataFrame()

    df_sites["Site ID"] = df_sites["Site ID"].astype(str).str.strip().str.upper()
    df_form["Site ID"] = df_form["Site ID"].astype(str).str.strip().str.upper()

    df_merged = df_sites.merge(
        df_form[["Site ID", "Latitude", "Longitude", "Timestamp"]],
        on="Site ID", how="left", suffixes=("", "_form")
    )

    df_merged["Status"] = df_merged["Timestamp"].apply(lambda x: "Installed" if pd.notnull(x) else "Open")
    df_merged["Latitude"] = df_merged["Latitude"].fillna(df_merged["Latitude_form"])
    df_merged["Longitude"] = df_merged["Longitude"].fillna(df_merged["Longitude_form"])
    df_merged["Installation Date"] = pd.to_datetime(df_merged["Timestamp"], errors="coerce")
    df_merged.dropna(subset=["Latitude", "Longitude"], inplace=True)
    return df_merged

# --- البيانات ---
df = load_data()
if df.empty:
    st.error("⚠️ No data loaded. Please check the Google Sheets links or data structure.")
    st.stop()

# --- الفلاتر الجانبية ---
st.sidebar.header("🔍 Filter Options")
regions = df["Region"].dropna().unique().tolist() if "Region" in df.columns else []
status_filter = st.sidebar.multiselect("Select Status", options=["Installed", "Open"], default=["Installed", "Open"])
region_filter = st.sidebar.multiselect("Select Region", options=regions, default=regions)
date_range = st.sidebar.date_input("Installation Date Range", [])

filtered_df = df[df["Status"].isin(status_filter)]
if region_filter:
    filtered_df = filtered_df[filtered_df["Region"].isin(region_filter)]
if date_range and len(date_range) == 2:
    filtered_df = filtered_df[
        filtered_df["Installation Date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))
    ]

# --- KPIs ---
total_sites = len(filtered_df)
installed_count = (filtered_df["Status"] == "Installed").sum()
open_count = (filtered_df["Status"] == "Open").sum()
progress = round((installed_count / total_sites) * 100, 2) if total_sites else 0
installed_dates = pd.to_datetime(filtered_df[filtered_df["Status"] == "Installed"]["Installation Date"], errors="coerce")
days_span = (installed_dates.max() - installed_dates.min()).days or 1 if not installed_dates.empty else 1
daily_rate = round(installed_count / days_span, 2) if days_span else 0

# --- الرأس ---
st.markdown("""
    <style>
    .big-font { font-size:28px !important; text-align:center; }
    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    st.image("wiconnect_logo.png", width=130)
with col2:
    st.markdown("<h1 class='big-font'>📊 ODC-AC Installation Dashboard</h1>", unsafe_allow_html=True)
with col3:
    st.image("latis_logo.png", width=130)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Sites", total_sites)
kpi2.metric("Installed", installed_count)
kpi3.metric("Open", open_count)
kpi4.metric("Progress %", f"{progress}%")
kpi5.metric("Daily Rate", f"{daily_rate} sites/day")

# --- الخريطة ---
st.subheader("📍 Site Installation Map")
m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)
for _, row in filtered_df.iterrows():
    color = "green" if row["Status"] == "Installed" else "red"
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        popup=f"Site ID: {row['Site ID']}<br>Status: {row['Status']}<br>Region: {row.get('Region', 'N/A')}",
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8
    ).add_to(m)
folium_static(m)

# --- الرسوم البيانية ---
st.subheader("📊 Status Distribution")
pie_chart = px.pie(filtered_df, names="Status", title="Installation Status", color_discrete_sequence=px.colors.sequential.RdBu)
st.plotly_chart(pie_chart, use_container_width=True)

st.subheader("📈 Installation Trend")
trend_data = filtered_df[filtered_df["Status"] == "Installed"].copy()
trend_data = trend_data.groupby(trend_data["Installation Date"].dt.date).size().reset_index(name="Installations")
line_chart = px.line(trend_data, x="Installation Date", y="Installations", markers=True)
st.plotly_chart(line_chart, use_container_width=True)

# --- التصدير ---
st.markdown("### 📥 Export Options")
excel_buffer = BytesIO()
filtered_df.to_excel(excel_buffer, index=False)
st.download_button("⬇️ Download Excel", data=excel_buffer.getvalue(), file_name="installation_status.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

html_table = filtered_df[["Site ID", "Status", "Installation Date"]].to_html(index=False)
pdf_html = f"<html><body>{html_table}</body></html>"
b64 = base64.b64encode(pdf_html.encode()).decode()
st.markdown(f'<a href="data:text/html;base64,{b64}" download="installation_report.html">⬇️ Download PDF Report</a>', unsafe_allow_html=True)

# --- الوقت ---
ksa_time = datetime.now(ZoneInfo("Asia/Riyadh"))
st.markdown(f"<p style='text-align: center;'>⏰ Last updated: {ksa_time.strftime('%H:%M:%S')} KSA</p>", unsafe_allow_html=True)
