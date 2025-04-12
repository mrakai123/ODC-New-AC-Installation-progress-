
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
from io import BytesIO
import base64

st.set_page_config(page_title="Saudi AC Installation Dashboard", layout="wide")
st.title("📊 Saudi AC Installation Dashboard")

@st.cache_data
def load_data():
    project_url = "https://docs.google.com/spreadsheets/d/1pZBg_lf8HakI6o2W1v8u1lUN2FGJn1Jc/export?format=csv"
    form_url = "https://docs.google.com/spreadsheets/d/1IeZVNb01-AMRuXjj9SZQyELTVr6iw5Vq4JsiN7PdZEs/export?format=csv"

    df_sites = pd.read_csv(project_url)
    df_sites.columns = df_sites.columns.str.strip()

    if "Site ID" not in df_sites.columns:
        st.error("❌ 'Site ID' not found in project sheet.")
        return pd.DataFrame()

    df_sites["Site ID"] = df_sites["Site ID"].astype(str).str.strip().str.upper()

    df_form = pd.read_csv(form_url)
    df_form.columns = df_form.columns.str.strip()
    df_form["Site ID"] = df_form["Site ID"].astype(str).str.strip().str.upper()

    # فقط التركيب الذي يخص المواقع الجديدة
    df_form_filtered = df_form[df_form["Site ID"].isin(df_sites["Site ID"])]

    # دمج بيانات الفورم في مواقع المشروع فقط
    df_sites = df_sites.merge(
        df_form_filtered[["Site ID", "Latitude", "Longitude", "Timestamp"]],
        on="Site ID",
        how="left"
    )

    df_sites["Status"] = df_sites["Timestamp"].apply(lambda x: "Installed" if pd.notnull(x) else "Open")
    df_sites["Latitude"] = df_sites["Latitude"].fillna(df_sites["Latitude_y"])
    df_sites["Longitude"] = df_sites["Longitude"].fillna(df_sites["Longitude_y"])
    df_sites["Installation Date"] = df_sites["Timestamp"].fillna("")

    df_sites["Latitude"] = pd.to_numeric(df_sites["Latitude"], errors="coerce")
    df_sites["Longitude"] = pd.to_numeric(df_sites["Longitude"], errors="coerce")
    df_sites.dropna(subset=["Latitude", "Longitude"], inplace=True)

    return df_sites

df = load_data()

if not df.empty:
    total_sites = len(df)
    installed_count = (df["Status"] == "Installed").sum()
    open_count = (df["Status"] == "Open").sum()
    progress = round((installed_count / total_sites) * 100, 2) if total_sites else 0

    installed_dates = pd.to_datetime(df[df["Status"] == "Installed"]["Installation Date"], errors="coerce")
    days_span = (installed_dates.max() - installed_dates.min()).days or 1 if not installed_dates.empty else 0
    daily_rate = round(installed_count / days_span, 2) if days_span else 0

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Total Sites", total_sites)
    kpi2.metric("Installed", installed_count)
    kpi3.metric("Open", open_count)
    kpi4.metric("Progress %", f"{progress}%")
    kpi5.metric("Daily Rate", f"{daily_rate} sites/day")

    st.markdown("---")

    st.subheader("📍 Site Installation Map")
    m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)
    for _, row in df.iterrows():
        color = "green" if row["Status"] == "Installed" else "red"
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6,
            popup=f"Site ID: {row['Site ID']}<br>Status: {row['Status']}<br>Installation Date: {row['Installation Date']}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
        ).add_to(m)
    folium_static(m)

    st.subheader("📊 Installation Status Distribution")
    fig1, ax1 = plt.subplots()
    df["Status"].value_counts().plot.pie(autopct="%1.1f%%", colors=["green", "red"], ax=ax1)
    ax1.set_ylabel("")
    st.pyplot(fig1)

    st.subheader("📈 Daily Installation Trend")
    trend_df = df[df["Status"] == "Installed"].copy()
    trend_df["Installation Date"] = pd.to_datetime(trend_df["Installation Date"], errors="coerce")
    trend = trend_df.groupby(trend_df["Installation Date"].dt.date).size()
    fig2, ax2 = plt.subplots()
    trend.plot(ax=ax2)
    ax2.set_ylabel("Sites Installed")
    ax2.set_xlabel("Date")
    st.pyplot(fig2)

    st.markdown("### 📥 Export Data")
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_data = excel_buffer.getvalue()

    st.download_button("⬇️ Download Excel", data=excel_data, file_name="installation_status.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    df_sample_html = df[["Site ID", "Status", "Installation Date"]].to_html(index=False)
    pdf_html = f"<html><body>{df_sample_html}</body></html>"
    b64 = base64.b64encode(pdf_html.encode()).decode()
    st.markdown(f'<a href="data:text/html;base64,{b64}" download="installation_report.html">⬇️ Download PDF Report</a>', unsafe_allow_html=True)
