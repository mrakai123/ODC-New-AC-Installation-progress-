
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from io import BytesIO
import requests

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
        .logo-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .logo-container img {
            height: 60px;
        }
    </style>
    <div class="logo-container">
        <img src="https://i.imgur.com/Gc1HpVq.png" alt="WiConnect Logo">
        <h1>ODC-AC Installation Dashboard</h1>
        <img src="https://i.imgur.com/zHx9Arl.png" alt="LATIS Logo">
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("**Prepared by: Mohammed Alfadhel**")

# Load Excel from GitHub using requests
url = "https://raw.githubusercontent.com/mrakai123/ODC-AC-Installation-progress-/main/ODC-AC%20Installation%20progress%2002-March-25%20_.xlsx"
response = requests.get(url)
data = BytesIO(response.content)
df_sites = pd.read_excel(data, sheet_name="Tracking Sheet")

# Simulated Installed Site Names (to be fetched from Google Sheet in future)
installed_sites = [
    "RIY0001", "RIY0005", "RIY0020"
]

# Status logic
df_sites["Status"] = df_sites["Site Name"].apply(
    lambda x: "Installed" if str(x).strip() in installed_sites else "Open"
)

# Marker color function
def get_marker_color(status):
    return "green" if status == "Installed" else "red"

# Map creation
m = folium.Map(location=[23.8859, 45.0792], zoom_start=6)
for i in range(len(df_sites)):
    site_name = df_sites.loc[i, "Site Name"]
    lat = df_sites.loc[i, "Latitude"]
    lon = df_sites.loc[i, "Longitude"]
    status = df_sites.loc[i, "Status"]
    folium.Marker(
        location=[lat, lon],
        popup=f"{site_name} - {status}",
        icon=folium.Icon(color=get_marker_color(status))
    ).add_to(m)

# Display map in Streamlit
st_data = st_folium(m, width=1100)

# Export buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("📥 Download Excel"):
        excel_io = BytesIO()
        df_sites.to_excel(excel_io, index=False)
        st.download_button("Download Excel File", data=excel_io.getvalue(), file_name="site_status.xlsx")

with col2:
    if st.button("📥 Download PDF"):
        st.info("🔧 PDF Export will be enabled in final deployment.")
