# Moradabad Brass & Handicrafts — B2B Lead & Intent Pipeline

An automated data pipeline and matchmaking system designed to identify high-intent domestic buyers (wholesalers, gifting agencies, corporate procurement, interior designers) and connect them with verified brass and metal handicraft manufacturers in **Moradabad, Uttar Pradesh**.

---

## 🎯 The Core Concept

- **The Problem:** Moradabad workshops are squeezed by middlemen, exporters, and junk inquiries on horizontal platforms (IndiaMART, TradeIndia). Buyers struggle to verify authentic manufacturers and avoid payment risks.
- **The Solution:** 
  1. Detect real-time buying signals from public procurement, new company incorporations, and trade data.
  2. Qualify intent through phone verification.
  3. Pre-match verified local manufacturers to ready-to-buy clients.

For the comprehensive strategy, see [business_model.md](business_model.md).

---

## 🏛️ Target Data Sources

| Source | Target Signal | Ingestion Method |
| :--- | :--- | :--- |
| **GeM (`gem.gov.in`) / CPPP** | Active government bids for brass trophies, mementos, corporate gifts | Procurement scraper / RSS / Aggregators |
| **MCA (`mca.gov.in`) / CDM** | Newly incorporated gifting, décor, and retail companies | Master data dumps / Open government data |
| **MSME Udyam Dashboard** | Sectoral & district-level manufacturing expansion trends | Periodic dashboard / data.gov.in feeds |
| **Trade Data (HSN 8306)** | Importers of metal statuettes/decor (domestic substitution) | Exim customs databases |

---

## 🛠️ Project Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Git

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Zaid-Yasin-919/data_idea.git
cd data_idea

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Scraper
```bash
python scraper.py
```
Outputs are written in structured JSON format to the `data/` directory (ignored by git).

---

## 📂 Project Structure

```text
├── README.md              # Project overview and guide
├── business_model.md      # Full strategic business plan & GTM
├── requirements.txt       # Python dependencies
├── scraper.py             # Feasibility scraper for gov portals
├── .gitignore             # Ignored paths (venv, data, logs, env)
└── data/                  # Output JSON scrapes (local only)
```

---

## 🚀 Current Status & Roadmap

- [x] Initial cluster defined (Moradabad brass & metal crafts)
- [x] Business model and unit economics drafted
- [x] Git repository configured
- [x] Feasibility scraper v1/v2 implemented
- [ ] Evaluate headless browser automation (Playwright) for JS-rendered government portals (GeM & MCA)
- [ ] Implement robust tender keyword filtering (`brass`, `trophy`, `memento`)
- [ ] In-person supplier discovery & validation interviews (10 manufacturers)

