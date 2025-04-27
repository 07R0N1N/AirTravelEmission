# Air Travel Emissions Tracker

A Streamlit web‑app that lets you calculate flight distances and carbon emissions for single trips **or** bulk itineraries. Upload an Excel sheet and instantly get key metrics, interactive charts, downloadable results, and an insight into your most polluting route.

---

## ✈️ Features

| Capability | Details |
|-------------|---------|
| **Single‑Route Lookup** | Enter two IATA codes → distance, travel type, emissions. |
| **Bulk Upload** | Accepts two templates: <br>1. **From / To / Trips** <br>2. **Route / Trips** (dash‑separated multi‑leg e.g. `TRV-BLR-JFK`) |
| **Per‑Leg Factors** | Domestic legs use ±0.30607 kg/km, international legs ±0.19742 kg/km. |
| **Key Metrics** | Total distance, emissions, trips + domestic / international splits. |
| **Charts** | • Pie: domestic vs international share  <br>• Bar: top‑10 polluting routes |
| **Insight Card** | Highlights worst emitting route and 10 % reduction potential. |
| **Download** | One‑click export of enriched results to Excel. |

---

## 🏗 Setup

```bash
# 1 Clone & enter repo
$ git clone https://github.com/<your‑org>/air‑travel‑emissions.git
$ cd air‑travel‑emissions

# 2 Create virtual env (optional)
$ python -m venv .venv && source .venv/bin/activate  # Linux/macOS
# or  .venv\Scripts\Activate   # Windows

# 3 Install dependencies
$ pip install -r requirements.txt
```

### requirements.txt (minimum)
```
streamlit>=1.29
pandas
altair
openpyxl
```

---

## 🚀 Running Locally

```bash
$ streamlit run app.py
```
Visit `http://localhost:8501` in your browser.

> **Tip:** place `airports.csv` in `data/` (or change the path in `load_airport_data`).

---

## 🗃 Excel Templates

### Template A – Point‑to‑Point
| from | to  | trips (optional) |
|------|-----|------------------|
| AGR  | JFK | 1000 |

### Template B – Multi‑Leg Route
| route (dash‑separated) | trips (optional) |
|------------------------|------------------|
| TRV‑BLR‑JFK            | 1 |

If **trips** is omitted the app assumes `1`.

---


## 🌐 Deploying to Streamlit Community Cloud
1. Push this repo to GitHub.  
2. In Streamlit Cloud → **New app** → pick the repo & `app.py`.  
3. Add your custom font file under `fonts/` if desired.  
The app auto‑redeploys on every git push.

---

## ✍️ Customization
* **Emission factors** – edit `DOMESTIC_FACTOR` & `INTERNATIONAL_FACTOR` in `app.py`.
* **Per‑leg country rule** – currently anything outside `IN` marks a leg as international. Adapt in `compute_route_metrics()` if needed.
* **Styling** – update the `<style>` block at the top of `app.py` or move it to a standalone CSS file.

---

## 📐 Distance Calculation
We compute great‑circle distance between airports using the **Haversine formula**:

```
 d = 2R * asin( sqrt( sin²(Δφ/2) + cos φ₁ · cos φ₂ · sin²(Δλ/2) ) )
 where R = 6 371 km
```

* φ = latitude, λ = longitude in **radians**  
* Δφ, Δλ are the differences between the two points.

This yields an accurate great‑circle distance, suitable for estimating flight path length and CO₂e. See `haversine()` in **app.py** for the implementation.

---

## 🗒 License
MIT – see [`LICENSE`](LICENSE).

---

## 🙏 Credits
* Airport data from https://ourairports.com/data/.
* CO₂ emission factors based on DEFRA 2024 guidelines.

