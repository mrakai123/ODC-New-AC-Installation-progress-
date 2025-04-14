import streamlit as st
from streamlit_autorefresh import st_autorefresh

# --- إعداد الصفحة ---
st.set_page_config(page_title="ODC-AC Installation Dashboard", layout="wide")

# --- تحديث تلقائي كل 30 ثانية ---
refresh_interval = 30
count = st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")

# --- CSS مخصص لتجميل الواجهة ---
st.markdown("""
    <style>
        .main {
            background-color: #f9f9f9;
        }
        h1 {
            color: #1f5f8b;
            font-size: 36px;
        }
        .logo {
            display: block;
            margin-left: auto;
            margin-right: auto;
        }
        .kpi {
            font-size: 22px;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- شعارات واسم المشروع ---
col1, col2, col3 = st.columns([2, 6, 2])
with col1:
    st.image("wiconnect_logo.png", width=100)
with col2:
    st.markdown("<h1 style='text-align:center;'>📊 ODC-AC Installation Dashboard</h1>", unsafe_allow_html=True)
with col3:
    st.image("latis_logo.png", width=100)

# باقي المكتبات
import pandas as pd
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime
from zoneinfo import ZoneInfo

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
    df_merged = df_sites.merge(df_form[["Site ID", "Latitude", "Longitude", "Timestamp"]],
                               on="Site ID", how="left", suffixes=("", "_form"))
    df_merged["Status"] = df_merged["Timestamp"].apply(lambda x: "Installed" if pd.notnull(x) else "Open")
    df_merged["Latitude"] = df_merged["Latitude"].fillna(df_merged["Latitude_form"])
    df_merged["Longitude"] = df_merged["Longitude"].fillna(df_merged["Longitude_form"])
    df_merged["Installation Date"] = pd.to_datetime(df_merged["Timestamp"], errors="coerce")
    df_merged["Latitude"] = pd.to_numeric(df_merged["Latitude"], errors="coerce")
    df_merged["Longitude"] = pd.to_numeric(df_merged["Longitude"], errors="coerce")
    df_merged.dropna(subset=["Latitude", "Longitude"], inplace=True)
    return df_merged

df = load_data()
if df.empty:
    st.error("⚠️ No data loaded. Please check the Google Sheets links.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filter Options")
regions = df["Region"].dropna().unique().tolist() if "Region" in df.columns else []
status_filter = st.sidebar.multiselect("Select Status", ["Installed", "Open"], default=["Installed", "Open"])
region_filter = st.sidebar.multiselect("Select Region", regions, default=regions)
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

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📍 Total Sites", total_sites)
k2.metric("✅ Installed", installed_count)
k3.metric("❌ Open", open_count)
k4.metric("📊 Progress %", f"{progress}%")
k5.metric("📈 Daily Rate", f"{daily_rate} sites/day")

# --- Map ---
st.subheader("📍 Site Installation Map")
m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)
for _, row in filtered_df.iterrows():
    color = "green" if row["Status"] == "Installed" else "red"
    popup = f"Site ID: {row['Site ID']}<br>Status: {row['Status']}<br>Date: {row.get('Installation Date', 'N/A')}<br>Region: {row.get('Region', 'N/A')}"
    folium.CircleMarker(location=[row["Latitude"], row["Longitude"]], radius=6, popup=popup,
                        color=color, fill=True, fill_color=color, fill_opacity=0.8).add_to(m)
folium_static(m)

# --- Charts ---
st.subheader("📊 Status Distribution")
chart_type = st.radio("Chart Type", ["Pie", "Bar"], horizontal=True)
status_counts = filtered_df["Status"].value_counts()
fig, ax = plt.subplots()
if chart_type == "Pie":
    status_counts.plot.pie(autopct="%1.1f%%", colors=["green", "red"], ax=ax)
    ax.set_ylabel("")
else:
    status_counts.plot.bar(color=["green", "red"], ax=ax)
    ax.set_ylabel("Site Count")
st.pyplot(fig)

# --- Trend Chart ---
st.subheader("📈 Installation Trend")
trend = filtered_df[filtered_df["Status"] == "Installed"]
trend = trend.groupby(trend["Installation Date"].dt.date).size()
fig2, ax2 = plt.subplots()
trend.plot(ax=ax2)
ax2.set_ylabel("Installed Sites")
ax2.set_xlabel("Date")
st.pyplot(fig2)

# --- Export ---
st.markdown("### 📥 Export Options")
excel_buffer = BytesIO()
filtered_df.to_excel(excel_buffer, index=False)
st.download_button("⬇️ Download Excel", data=excel_buffer.getvalue(), file_name="installation_status.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

html_table = filtered_df[["Site ID", "Status", "Installation Date"]].to_html(index=False)
pdf_html = f"<html><body>{html_table}</body></html>"
b64 = base64.b64encode(pdf_html.encode()).decode()
st.markdown(f'<a href="data:text/html;base64,{b64}" download="installation_report.html">⬇️ Download PDF Report</a>', unsafe_allow_html=True)

# --- Footer ---
ksa_time = datetime.now(ZoneInfo("Asia/Riyadh"))
st.markdown("---")
st.markdown(f"<p style='text-align:center;'>⏰ Last Update: {ksa_time.strftime('%H:%M:%S')} | Refresh every {refresh_interval}s</p>", unsafe_allow_html=True)

remaining = refresh_interval - (count % refresh_interval)
color = "red" if remaining <= 10 else "black"
st.markdown(f"<p style='text-align:center; font-size:18px; color:{color};'>⏳ Refreshing in: {remaining} seconds</p>", unsafe_allow_html=True)
