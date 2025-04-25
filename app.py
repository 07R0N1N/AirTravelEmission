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
        font-family: 'MyFont', sans-serif !important;
    }}
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {{
        font-family: sans-serif !important;
    }}
    [data-testid="metric-container"] *,
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {{
        font-family: 'MyFont', sans-serif !important;
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
st.title("Airport Distance, Travel Type & Emissions Dashboard")

# Single Lookup
st.header("Single IATA Lookup")
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
st.header("Bulk Excel Upload & Insights")
uploaded_file = st.file_uploader("Upload an Excel file (.xlsx/.xls)", type=["xlsx", "xls"])
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [col.strip().lower() for col in df.columns]
        if not {'from', 'to'}.issubset(df.columns):
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

            df[['distance_km','travel_type','with WTT']] = df.apply(compute_metrics, axis=1)

            # Summaries
            total_em = df['with WTT'].sum()
            dom_em = df.loc[df['travel_type']=='Domestic','with WTT'].sum()
            int_em = df.loc[df['travel_type']=='International','with WTT'].sum()
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
            <div id="metric-total-emissions" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-total-emissions-label" style="font-size:0.875rem; color:#ccc;">Total Emissions</div>
            <div id="metric-total-emissions-value" style="font-size:2rem;">{total_em/1000:,.2f} tCO₂e</div>
            </div>
            """, unsafe_allow_html=True)
            # Domestic Emissions
            c2.markdown(f"""
            <div id="metric-domestic-emissions" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-domestic-emissions-label" style="font-size:0.875rem; color:#ccc;">Domestic Emissions</div>
            <div id="metric-domestic-emissions-value" style="font-size:2rem;">{dom_em/1000:,.2f} tCO₂e</div>
            </div>
            """, unsafe_allow_html=True)
            # International Emissions
            c3.markdown(f"""
            <div id="metric-international-emissions" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-international-emissions-label" style="font-size:0.875rem; color:#ccc;">International Emiss.</div>
            <div id="metric-international-emissions-value" style="font-size:2rem;">{int_em/1000:,.2f} tCO₂e</div>
            </div>
            """, unsafe_allow_html=True)

            c4, c5, c6 = st.columns(3)
            # Total Distance
            c4.markdown(f"""
            <div id="metric-total-distance" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-total-distance-label" style="font-size:0.875rem; color:#ccc;">Total Distance</div>
            <div id="metric-total-distance-value" style="font-size:2rem;">{total_dist:,.0f} km</div>
            </div>
            """, unsafe_allow_html=True)
            # Domestic Distance
            c5.markdown(f"""
            <div id="metric-domestic-distance" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-domestic-distance-label" style="font-size:0.875rem; color:#ccc;">Dom. Distance</div>
            <div id="metric-domestic-distance-value" style="font-size:2rem;">{dom_dist:,.0f} km</div>
            </div>
            """, unsafe_allow_html=True)
            # International Distance
            c6.markdown(f"""
            <div id="metric-int-distance" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-int-distance-label" style="font-size:0.875rem; color:#ccc;">Int. Distance</div>
            <div id="metric-int-distance-value" style="font-size:2rem;">{int_dist:,.0f} km</div>
            </div>
            """, unsafe_allow_html=True)

            c7, c8, c9 = st.columns(3)
            # Total Trips
            c7.markdown(f"""
            <div id="metric-total-trips" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-total-trips-label" style="font-size:0.875rem; color:#ccc;">Total Trips</div>
            <div id="metric-total-trips-value" style="font-size:2rem;">{total_trips}</div>
            </div>
            """, unsafe_allow_html=True)
            # Domestic Trips
            c8.markdown(f"""
            <div id="metric-domestic-trips" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-domestic-trips-label" style="font-size:0.875rem; color:#ccc;">Domestic Trips</div>
            <div id="metric-domestic-trips-value" style="font-size:2rem;">{dom_trips}</div>
            </div>
            """, unsafe_allow_html=True)
            # International Trips
            c9.markdown(f"""
            <div id="metric-international-trips" style="font-family: 'MyFont', sans-serif;">
            <div id="metric-international-trips-label" style="font-size:0.875rem; color:#ccc;">Intl. Trips</div>
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
            max_row = df.loc[df['with WTT'].idxmax()]
            route = max_row['from'].strip().upper()+'→'+max_row['to'].strip().upper()
            em_val = max_row['with WTT']
            trips_val = int(max_row['trips'])
            reduction = em_val*0.10
            st.markdown(f"""
                <div style="border:1px solid #ccc;border-radius:10px;padding:15px;background:#444444;display:flex;align-items:center;">
                    <span style="font-size:24px;margin-right:10px;">💡</span>
                    <div>
                        <strong>Insight:</strong> Your most polluting route is <strong>{route}</strong>,
                        generating <strong>{em_val:,.2f} tCO₂e</strong> over <strong>{trips_val}</strong> trips.
                        By reducing 10% of these trips via virtual meetings, you could cut
                        <strong>{reduction:,.2f} tCO₂e</strong> emissions.
                    </div>
                </div><br>
            """,unsafe_allow_html=True)
            # Top 10 Polluting Routes (monochrome bar, descending)
            st.subheader("Top 10 Polluting Routes")
            df['route'] = df['from'].str.upper()+'→'+df['to'].str.upper()
            top10 = df.groupby('route')['with WTT'].sum().reset_index().sort_values('with WTT',ascending=False).head(10)
            bar = alt.Chart(top10).mark_bar(color='#444444').encode(
                x=alt.X('with WTT:Q',title='Emissions (tCO₂e)'),
                y=alt.Y('route:N',sort='-x',title='Route'),
                tooltip=['route:N','with WTT:Q']
            )
            st.altair_chart(bar,use_container_width=True)

            # Table & download
            st.dataframe(df)
            buf = io.BytesIO()
            df.to_excel(buf,index=False,engine='openpyxl')
            buf.seek(0)
            st.download_button("Download Results",data=buf,file_name="airport_insights.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Error processing file: {e}")
