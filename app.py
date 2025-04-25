import streamlit as st
import pandas as pd
import math
import io
import os

# Emission factors (kg CO2e per passenger·km)
DOMESTIC_FACTOR = 0.03350 + 0.27257  # Domestic: avg passenger.km factors summed
INTERNATIONAL_FACTOR = 0.02162 + 0.17580  # International: avg passenger.km factors summed

# 1. Load and cache airport data with country information
def load_airport_data(path: str = None) -> dict:
    @st.cache_data
    def _load(path):
        if path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "data", "airports.csv")
        df = pd.read_csv(
            path,
            usecols=["iata_code", "latitude_deg", "longitude_deg", "iso_country"]
        )
        df = df.dropna(subset=["iata_code"])
        df["iso_country"] = df["iso_country"].fillna("").astype(str).str.upper()
        df["iata_code"] = df["iata_code"].str.upper()
        airport_data = {}
        for row in df.itertuples():
            airport_data[row.iata_code] = {
                "lat": row.latitude_deg,
                "lon": row.longitude_deg,
                "country": row.iso_country
            }
        return airport_data
    return _load(path)

airport_data = load_airport_data()

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
st.title("Airport Distance, Travel Type & Emissions Calculator")

# --- Single lookup ---
st.header("Single IATA Lookup")
col1, col2 = st.columns(2)
with col1:
    from_code = st.text_input("From IATA code", "").strip().upper()
with col2:
    to_code = st.text_input("To IATA code", "").strip().upper()

if st.button("Calculate Distance"):
    missing = [code for code in [from_code, to_code] if code and code not in airport_data]
    if missing:
        st.error(f"Unknown IATA code(s): {', '.join(missing)}")
    elif not from_code or not to_code:
        st.warning("Please enter both From and To IATA codes.")
    else:
        a1 = airport_data[from_code]
        a2 = airport_data[to_code]
        distance = haversine(a1['lat'], a1['lon'], a2['lat'], a2['lon'])
        travel_type = (
            "Domestic" if a1['country'] == "IN" and a2['country'] == "IN" else "International"
        )
        factor = DOMESTIC_FACTOR if travel_type == "Domestic" else INTERNATIONAL_FACTOR
        emissions = distance * factor
        st.success(
            f"Distance between {from_code} and {to_code}: {distance:.1f} km ({travel_type}) — Emissions: {emissions:.1f} kgCO2e"
        )

# --- Bulk upload ---
st.header("Bulk Excel Upload")
uploaded_file = st.file_uploader("Upload an Excel file (.xlsx/.xls)", type=["xlsx", "xls"])
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [col.strip().lower() for col in df.columns]
        if not {'from', 'to'}.issubset(df.columns):
            st.error("Excel must contain 'from' and 'to' columns.")
        else:
            # Compute distance per row
            def compute_distance(row):
                f = str(row['from']).strip().upper()
                t = str(row['to']).strip().upper()
                if f in airport_data and t in airport_data:
                    a1 = airport_data[f]
                    a2 = airport_data[t]
                    return haversine(a1['lat'], a1['lon'], a2['lat'], a2['lon'])
                return None

            # Determine travel type per row
            def compute_travel_type(row):
                f = str(row['from']).strip().upper()
                t = str(row['to']).strip().upper()
                if f in airport_data and t in airport_data:
                    a1 = airport_data[f]
                    a2 = airport_data[t]
                    return "Domestic" if a1['country'] == "IN" and a2['country'] == "IN" else "International"
                return None

            # Compute emissions including trips if present
            def compute_emissions(row):
                d = row.get('distance_km')
                t = row.get('travel_type')
                trips = int(row['trips']) if 'trips' in row and pd.notna(row['trips']) else 1
                if pd.notna(d) and t:
                    factor = DOMESTIC_FACTOR if t == "Domestic" else INTERNATIONAL_FACTOR
                    return d * factor * trips/1000
                return None

            df['distance_km'] = df.apply(compute_distance, axis=1)
            df['travel_type'] = df.apply(compute_travel_type, axis=1)
            df['Emissions (tCO2e)'] = df.apply(compute_emissions, axis=1)

            st.dataframe(df)

            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            towrite.seek(0)
            st.download_button(
                label="Download Results",
                data=towrite,
                file_name="airport_results_with_wtt.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error processing file: {e}")
