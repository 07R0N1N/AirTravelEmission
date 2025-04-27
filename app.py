import streamlit as st
import pandas as pd
import math
import io
import os
import altair as alt
import base64

# =======================
# Embed & Apply Custom Font to All Text & Headings
# =======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "fonts", "MyFont.otf")

def load_font_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

if os.path.exists(FONT_PATH):
    font_data = load_font_base64(FONT_PATH)
    st.markdown(f"""
    <style>
    @font-face {{
        font-family: 'MyFont';
        src: url(data:font/otf;base64,{font_data}) format('opentype');
    }}
    html, body, [class*="css"], .block-container {{
        font-family: 'MyFont', system-ui !important;
    }}
    </style>
    """, unsafe_allow_html=True)
else:
    st.warning("Custom font file not found at fonts/MyFont.otf. Using default font.")

# Emission factors (kg CO2e per passenger·km)
DOMESTIC_FACTOR = 0.03350 + 0.27257
INTERNATIONAL_FACTOR = 0.02162 + 0.17580

# Load and cache airport data
@st.cache_data
def load_airport_data(path: str = None) -> dict:
    if path is None:
        path = os.path.join(BASE_DIR, "data", "airports.csv")
    df = pd.read_csv(path, usecols=["iata_code", "latitude_deg", "longitude_deg", "iso_country"])
    df = df.dropna(subset=["iata_code"])
    df["iso_country"] = df["iso_country"].fillna("").astype(str).str.upper()
    df["iata_code"] = df["iata_code"].str.upper()
    return {row.iata_code: {"lat": row.latitude_deg, "lon": row.longitude_deg, "country": row.iso_country}
            for row in df.itertuples()}

airport_data = load_airport_data()

# Distance function (Haversine)
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Streamlit UI
st.markdown(
    "<h1 style='text-align:center'>Air Travel Emissions Tracker</h1>",
    unsafe_allow_html=True
)

# Single Lookup
st.markdown(
    "<h4 style='text-align:center;font-family:system-ui;'>Single Flight Lookup</h2>",
    unsafe_allow_html=True
)
col1, col2 = st.columns(2)
with col1:
    from_code = st.text_input("From IATA code", "").strip().upper()
with col2:
    to_code = st.text_input("To IATA code", "").strip().upper()

if st.button("Calculate Distance"):
    if not from_code or not to_code:
        st.warning("Please enter both From and To IATA codes.")
    elif from_code not in airport_data or to_code not in airport_data:
        missing = [c for c in (from_code, to_code) if c not in airport_data]
        st.error(f"Unknown IATA code(s): {', '.join(missing)}")
    else:
        a1 = airport_data[from_code]
        a2 = airport_data[to_code]
        distance = haversine(a1['lat'], a1['lon'], a2['lat'], a2['lon'])
        travel_type = "Domestic" if a1['country']=='IN' and a2['country']=='IN' else "International"
        emissions_t = distance * (DOMESTIC_FACTOR if travel_type=='Domestic' else INTERNATIONAL_FACTOR)
        st.success(
            f"Distance between {from_code} and {to_code}: {distance:.1f} km ({travel_type}) — Emissions: {emissions_t:.2f} kgCO₂e"
        )

# Bulk Upload & Insights
st.markdown(
    "<h2 style='text-align:center;font-family:system-ui;'>Upload Travel Data</h2>",
    unsafe_allow_html=True
)
uploaded_file = st.file_uploader("Upload an Excel file (.xlsx/.xls)", type=["xlsx", "xls"])
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [col.strip().lower() for col in df.columns]
        if 'route' in df.columns:
    # Ensure 'trips' exists and is integer
            if 'trips' in df.columns:
                df['trips'] = df['trips'].fillna(1).astype(int)
            else:
                df['trips'] = 1

            def compute_route_metrics(row):
                """
                Calculates distance and emissions for a dash-separated route
                using the correct factor *per leg* (domestic vs international).
                Returns:  [total_km, overall_travel_type, emissions_tCO2e]
                """
                codes = [c.strip().upper() for c in row["route"].split("-")]
                total_km     = 0.0           # accumulate distance
                total_em_kg  = 0.0           # accumulate emissions in kg
                all_domestic = True          # flips to False on first int’l leg

                for origin, dest in zip(codes, codes[1:]):
                    a1, a2 = airport_data.get(origin), airport_data.get(dest)
                    if not a1 or not a2:                     # unknown IATA code
                        return pd.Series([None, None, None])

                    leg_km = haversine(a1["lat"], a1["lon"], a2["lat"], a2["lon"])
                    total_km += leg_km

                    domestic_leg = (a1["country"] == "IN") and (a2["country"] == "IN")
                    factor       = DOMESTIC_FACTOR if domestic_leg else INTERNATIONAL_FACTOR
                    total_em_kg += leg_km * factor               # add this leg’s emissions

                    if not domestic_leg:
                        all_domestic = False

                travel_type = "Domestic" if all_domestic else "International"
                emissions_t = total_em_kg / 1000                 # kg → tonnes
                return pd.Series([total_km, travel_type, emissions_t])


            df[['distance_km', 'travel_type', 'emissions(tCO2e)']] = df.apply(compute_route_metrics, axis=1)

        elif not {'from', 'to'}.issubset(df.columns):
            st.error("Excel must contain 'from' and 'to' columns.")
        else:
            df['trips'] = df.get('trips', 1).fillna(1).astype(int)

            def compute_metrics(row):
                f, t = row['from'].strip().upper(), row['to'].strip().upper()
                if f in airport_data and t in airport_data:
                    a1, a2 = airport_data[f], airport_data[t]
                    dist = haversine(a1['lat'], a1['lon'], a2['lat'], a2['lon'])
                    tt = 'Domestic' if a1['country']=='IN' and a2['country']=='IN' else 'International'
                    em_t = dist * (DOMESTIC_FACTOR if tt=='Domestic' else INTERNATIONAL_FACTOR) * row['trips'] / 1000
                    return pd.Series([dist, tt, em_t])
                return pd.Series([None, None, None])

            df[['distance_km','travel_type','emissions(tCO2e)']] = df.apply(compute_metrics, axis=1)

        if 'route' not in df.columns:
            df['route'] = df['from'].str.upper() + '→' + df['to'].str.upper()

        # Summaries
        total_em = df['emissions(tCO2e)'].sum()
        dom_em = df.loc[df['travel_type']=='Domestic','emissions(tCO2e)'].sum()
        int_em = df.loc[df['travel_type']=='International','emissions(tCO2e)'].sum()
        total_dist = df['distance_km'].sum()
        dom_dist = df.loc[df['travel_type']=='Domestic','distance_km'].sum()
        int_dist = df.loc[df['travel_type']=='International','distance_km'].sum()
        total_trips = int(df['trips'].sum())
        dom_trips = int(df.loc[df['travel_type']=='Domestic','trips'].sum())
        int_trips = int(df.loc[df['travel_type']=='International','trips'].sum())

        st.subheader("Key Metrics")
        # Key Metrics rendered with custom MyFont via inline HTML and unique IDs
        c1, c2, c3 = st.columns(3)
        # Total Emissions
        c1.markdown(f"""
        <div id="metric-total-emissions" style="font-family: 'MyFont', system-ui;">
        <div id="metric-total-emissions-label" style="font-size:0.875rem; color:#ccc;">Total Emissions</div>
        <div id="metric-total-emissions-value" style="font-size:2rem;">{total_em:,.2f} tCO₂e</div>
        </div>
        """, unsafe_allow_html=True)
        # Domestic Emissions
        c2.markdown(f"""
        <div id="metric-domestic-emissions" style="font-family: 'MyFont', system-ui;">
        <div id="metric-domestic-emissions-label" style="font-size:0.875rem; color:#ccc;">Domestic Emissions</div>
        <div id="metric-domestic-emissions-value" style="font-size:2rem;">{dom_em:,.2f} tCO₂e</div>
        </div>
        """, unsafe_allow_html=True)
        # International Emissions
        c3.markdown(f"""
        <div id="metric-international-emissions" style="font-family: 'MyFont', system-ui;">
        <div id="metric-international-emissions-label" style="font-size:0.875rem; color:#ccc;">International Emissions</div>
        <div id="metric-international-emissions-value" style="font-size:2rem;">{int_em:,.2f} tCO₂e</div>
        </div>
        """, unsafe_allow_html=True)

        c4, c5, c6 = st.columns(3)
        # Total Distance
        c4.markdown(f"""
        <div id="metric-total-distance" style="font-family: 'MyFont', system-ui;">
        <div id="metric-total-distance-label" style="font-size:0.875rem; color:#ccc;">Total Distance</div>
        <div id="metric-total-distance-value" style="font-size:2rem;">{total_dist:,.0f} km</div>
        </div>
        """, unsafe_allow_html=True)
        # Domestic Distance
        c5.markdown(f"""
        <div id="metric-domestic-distance" style="font-family: 'MyFont', system-ui;">
        <div id="metric-domestic-distance-label" style="font-size:0.875rem; color:#ccc;">Total Distance(Domestice)</div>
        <div id="metric-domestic-distance-value" style="font-size:2rem;">{dom_dist:,.0f} km</div>
        </div>
        """, unsafe_allow_html=True)
        # International Distance
        c6.markdown(f"""
        <div id="metric-int-distance" style="font-family: 'MyFont', system-ui;">
        <div id="metric-int-distance-label" style="font-size:0.875rem; color:#ccc;">Total Distance(International)</div>
        <div id="metric-int-distance-value" style="font-size:2rem;">{int_dist:,.0f} km</div>
        </div>
        """, unsafe_allow_html=True)

        c7, c8, c9 = st.columns(3)
        # Total Trips
        c7.markdown(f"""
        <div id="metric-total-trips" style="font-family: 'MyFont', system-ui;">
        <div id="metric-total-trips-label" style="font-size:0.875rem; color:#ccc;">Total Trips</div>
        <div id="metric-total-trips-value" style="font-size:2rem;">{total_trips}</div>
        </div>
        """, unsafe_allow_html=True)
        # Domestic Trips
        c8.markdown(f"""
        <div id="metric-domestic-trips" style="font-family: 'MyFont', system-ui;">
        <div id="metric-domestic-trips-label" style="font-size:0.875rem; color:#ccc;">Domestic Trips</div>
        <div id="metric-domestic-trips-value" style="font-size:2rem;">{dom_trips}</div>
        </div>
        """, unsafe_allow_html=True)
        # International Trips
        c9.markdown(f"""
        <div id="metric-international-trips" style="font-family: 'MyFont', system-ui;">
        <div id="metric-international-trips-label" style="font-size:0.875rem; color:#ccc;">International Trips</div>
        <div id="metric-international-trips-value" style="font-size:2rem;">{int_trips}</div>
        </div>
        """, unsafe_allow_html=True)
        # Emissions Share Pie Chart (monochrome)
        st.subheader("Emissions Share: Domestic vs International")
        pie_df = pd.DataFrame({
            'Travel Type': ['Domestic','International'],
            'Emissions (tCO₂e)': [dom_em,int_em]
        })
        pie = alt.Chart(pie_df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta('Emissions (tCO₂e):Q'),
            color=alt.Color('Travel Type:N', scale=alt.Scale(domain=['Domestic','International'],range=['#FFFFFF','#888888'])),
            tooltip=['Travel Type:N','Emissions (tCO₂e):Q']
        )
        st.altair_chart(pie,use_container_width=True)
        # Insight with border & bulb icon
        max_row = df.loc[df['emissions(tCO2e)'].idxmax()]
        insight_route = max_row['route']
        em_val = max_row['emissions(tCO2e)']
        trips_val = int(max_row['trips'])
        reduction = em_val*0.10
        st.markdown(f"""
            <div style="border:1px solid #ccc;border-radius:10px;padding:15px;background:#444444;display:flex;align-items:center;">
                <span style="font-size:24px;margin-right:10px;">💡</span>
                <div>
                    <strong>Insight:</strong> Your most polluting route is <strong>{insight_route}</strong>,
                    generating <strong>{em_val:,.2f} tCO₂e</strong> over <strong>{trips_val}</strong> trips.
                    By reducing 10% of these trips via virtual meetings, you could cut
                    <strong>{reduction:,.2f} tCO₂e</strong> emissions.
                </div>
            </div><br>
        """,unsafe_allow_html=True)
        # Top 10 Polluting Routes (monochrome bar, descending)
        st.subheader("Top 10 Polluting Routes")
        top10 = df.groupby('route')['emissions(tCO2e)'].sum().reset_index().sort_values('emissions(tCO2e)',ascending=False).head(10)
        bar = alt.Chart(top10).mark_bar(color='#444444').encode(
            x=alt.X('emissions(tCO2e):Q',title='Emissions (tCO₂e)'),
            y=alt.Y('route:N',sort='-x',title='Route'),
            tooltip=['route:N','emissions(tCO2e):Q']
        )
        st.altair_chart(bar,use_container_width=True)
        
        st.dataframe(df)
        buf = io.BytesIO()
        df.to_excel(buf,index=False,engine='openpyxl')
        buf.seek(0)
        st.download_button("Download Results",data=buf,file_name="airport_insights.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Error processing file: {e}")
