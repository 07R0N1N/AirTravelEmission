#Air Travel Emissions Tracker

A Streamlit web‑app that lets you calculate flight distances and carbon emissions for single trips or bulk itineraries. Upload an Excel sheet and instantly get key metrics, interactive charts, downloadable results, and an insight into your most polluting route.

✈️ Features

Capability

Details

Single‑Route Lookup

Enter two IATA codes → distance, travel type, emissions.

Bulk Upload

Accepts two templates: 1. From / To / Trips 2. Route / Trips (dash‑separated multi‑leg e.g. TRV-BLR-JFK)

Per‑Leg Factors

Domestic legs use ±0.30607 kg/km, international legs ±0.19742 kg/km.

Key Metrics

Total distance, emissions, trips + domestic / international splits.

Charts

• Pie: domestic vs international share  • Bar: top‑10 polluting routes

Insight Card

Highlights worst emitting route and 10 % reduction potential.

Download

One‑click export of enriched results to Excel.

🏗 Setup

# 1 Clone & enter repo
$ git clone https://github.com/<your‑org>/air‑travel‑emissions.git
$ cd air‑travel‑emissions

# 2 Create virtual env (optional)
$ python -m venv .venv && source .venv/bin/activate  # Linux/macOS
# or  .venv\Scripts\Activate   # Windows

# 3 Install dependencies
$ pip install -r requirements.txt

### requirements.txt (minimum)

streamlit>=1.29
pandas
altair
openpyxl

🚀 Running Locally

$ streamlit run app.py

Visit http://localhost:8501 in your browser.

Tip: place airports.csv in data/ (or change the path in load_airport_data).

🗃 Excel Templates

### Template A – Point‑to‑Point

from

to

trips (optional)

AGR

JFK

1000

### Template B – Multi‑Leg Route

route (dash‑separated)

trips (optional)

TRV‑BLR‑JFK

1

If trips is omitted the app assumes 1.

🖼 Screenshots



🌐 Deploying to Streamlit Community Cloud

Push this repo to GitHub.

In Streamlit Cloud → New app → pick the repo & app.py.

Add your custom font file under fonts/ if desired.The app auto‑redeploys on every git push.

✍️ Customization

Emission factors – edit DOMESTIC_FACTOR & INTERNATIONAL_FACTOR in app.py.

Per‑leg country rule – currently anything outside IN marks a leg as international. Adapt in compute_route_metrics() if needed.

Styling – update the <style> block at the top of app.py or move it to a standalone CSS file.

🗒 License

MIT – see LICENSE.

🙏 Credits

Airport data from openflights.org (CC‑BY‑SA).

CO₂ emission factors based on DEFRA 2023 guidelines.
