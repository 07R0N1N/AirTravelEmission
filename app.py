import streamlit as st
import pandas as pd
import math
import io

# 1. Load and cache airport data
@st.cache_data
def load_airport_data(path: str = "data/airports.csv") -> dict:
    df = pd.read_csv(path, usecols=["iata_code", "latitude_deg", "longitude_deg"] )
    df = df.dropna(subset=["iata_code"])
    df["iata_code"] = df["iata_code"].str.upper()
    return {row.iata_code: (row.latitude_deg, row.longitude_deg) for row in df.itertuples()}

airport_coords = load_airport_data()

# 2. Distance function (Haversine)
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  # Earth radius in kilometers
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 3. Streamlit UI
st.title("Airport Distance Calculator")

# Single lookup section
st.header("Single IATA Lookup")
col1, col2 = st.columns(2)
with col1:
    from_code = st.text_input("From IATA code", "").strip().upper()
with col2:
    to_code = st.text_input("To IATA code", "").strip().upper()

if st.button("Calculate Distance"):
    if from_code in airport_coords and to_code in airport_coords:
        lat1, lon1 = airport_coords[from_code]
        lat2, lon2 = airport_coords[to_code]
        distance = haversine(lat1, lon1, lat2, lon2)
        st.success(f"Distance between {from_code} and {to_code}: {distance:.1f} km")
    else:
        missing = [code for code in [from_code, to_code] if code not in airport_coords]
        st.error(f"Unknown IATA code(s): {', '.join(missing)}")

# Bulk upload section
st.header("Bulk Excel Upload")
uploaded_file = st.file_uploader("Upload an Excel file (.xlsx/.xls)", type=["xlsx", "xls"])
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        # Normalize column names
        df.columns = [col.strip().lower() for col in df.columns]
        if not {'from', 'to'}.issubset(df.columns):
            st.error("Excel must contain 'from' and 'to' columns.")
        else:
            # Compute distances
            def compute_distance(row):
                f = str(row['from']).strip().upper()
                t = str(row['to']).strip().upper()
                if f in airport_coords and t in airport_coords:
                    lat1, lon1 = airport_coords[f]
                    lat2, lon2 = airport_coords[t]
                    return haversine(lat1, lon1, lat2, lon2)
                return None

            df['distance_km'] = df.apply(compute_distance, axis=1)
            st.dataframe(df)

            # Prepare download
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            towrite.seek(0)
            st.download_button(
                label="Download Results",
                data=towrite,
                file_name="airport_distances.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error processing file: {e}")
