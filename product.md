# 🗺️ Bassi Clothing — Google Maps Lead Scraper
### Product Specification & Master Prompt for Antigravity

---

## Product Overview

A Google Maps-powered B2B lead generation tool built for **Bassi Clothing**, an Indian garment manufacturer sourcing fashion retail clients across the UK and EU. The tool scrapes Google Maps by country/city to discover fashion brands, retailers, and clothing companies, then enriches each result with decision-maker details (CEO, Head of Sourcing, Procurement Directors, etc.) — outputting a structured, exportable lead list matching Bassi's Ideal Customer Profile (ICP).

---

## Ideal Customer Profile (ICP)

```yaml
deal_customer_profile:
  company_types:
    - "Menswear Brands"
    - "Unisex Fashion Retailers"
    - "Clothing Brands (Mens/Unisex)"
    - "Department Stores"
    - "Streetwear Brands"
    - "Activewear / Sportswear Brands"
    - "E-commerce Fashion Platforms"
    - "Private Label Brands"
    - "Sustainable Fashion Startups"

  locations:
    - "United Kingdom"
    - "France"
    - "Germany"
    - "Netherlands"
    - "Italy"
    - "Spain"
    - "Sweden"
    - "Denmark"
    - "Belgium"
    - "Ireland"
    - "Austria"
    - "Switzerland"
    - "Portugal"
    - "Norway"
    - "Finland"
    - "Poland"
    - "Czech Republic"
    - "Hungary"
    - "Romania"
    - "Greece"
    - "Croatia"
    - "Slovakia"
    - "Slovenia"
    - "Estonia"
    - "Latvia"
    - "Lithuania"
    - "Luxembourg"
    - "Malta"
    - "Cyprus"
    - "Bulgaria"

  decision_makers:
    - "Head of Sourcing"
    - "Procurement Director"
    - "Buying Manager"
    - "Supply Chain Manager"
    - "Head of Purchasing"
    - "CEO"
    - "Co-Founder"
    - "Managing Director"
    - "Operations Director"
    - "Head of Operations"
    - "Head of Design"
    - "Creative Director"
    - "Brand Manager"

  company_size:
    min_employees: 1
    max_employees: 10000
```

---

## Core Features

### 1. Location-Based Search
- Country selector dropdown (all EU + UK)
- Optional city/region drill-down
- Radius control (5 km / 10 km / 25 km / 50 km / entire country)
- Multi-location batch mode (select multiple countries at once)

### 2. Google Maps Scraping
- Search query auto-builder: `"[company_type] [city/country]"` e.g. `"clothing brand London"`, `"fashion retailer Paris"`
- Scrapes: Business Name, Address, Phone, Website, Google Rating, Reviews Count, Category, Opening Hours
- Deduplication across searches (same business won't appear twice)
- Pagination support to go beyond first 20 results

### 3. Lead Enrichment
- Auto-visit company website to extract:
  - About/Team page → identify decision maker names + roles
  - LinkedIn company URL (if available)
  - Instagram / Social handles
  - Estimated employee count
  - Products/collections listed (to assess fit with Bassi)
- LinkedIn People Search (optional): search `"[Company] Head of Sourcing"` etc.
- Generate likely email formats: `firstname@domain.com`, `firstname.lastname@domain.com`

### 4. ICP Scoring & Filtering
Each lead is auto-scored 1–10 based on:
- Company type match (clothing brand = high; unrelated = low)
- Employee count within ICP range (1–10,000)
- Decision maker found (yes = +2 points)
- Website quality / e-commerce presence
- India sourcing readiness signals (e.g. "ethically made", "manufactured in", "supply chain")
- Social proof (reviews, follower count)

Filters:
- Min ICP score slider
- Company type checkboxes
- Employee range filter
- Country/city filter
- Has contact info toggle

### 5. Output & Export
**Columns in output spreadsheet:**

| Column | Description |
|--------|-------------|
| # | Row number |
| Company Name | Business name from Maps |
| Website | Company website |
| Country | Country |
| City | City / Region |
| Google Maps URL | Direct Maps link |
| Category / Segment | Fashion type detected |
| Employees (Est.) | Estimated headcount |
| ICP Score | 1–10 match score |
| Key Contact Name | CEO / Sourcing Head etc. |
| Contact Role | Their title |
| LinkedIn URL | Contact's LinkedIn |
| Likely Email | Generated email guess |
| Phone | From Maps |
| Instagram | Social handle |
| Products / Notes | What they sell |
| India Sourcing Signals | Keywords found on site |
| Why Hot Lead | AI-generated one-liner |
| Tier | Tier 1 / 2 / 3 |
| First Order Potential | Estimated (£) |

Export formats: `.xlsx`, `.csv`, Google Sheets sync

---

## User Interface Flow

```
[Step 1] → Select Country / Region
             ↓
[Step 2] → Choose Company Types (checkboxes)
             ↓
[Step 3] → Set Search Radius & Employee Filter
             ↓
[Step 4] → Click "Start Scrape"
             ↓
[Step 5] → Live progress bar (X leads found...)
             ↓
[Step 6] → Results Table (filterable, sortable)
             ↓
[Step 7] → Export to Excel / CSV / Google Sheets
```

---

## Tech Stack Recommendations

| Layer | Tool |
|-------|------|
| Scraping Engine | Playwright + Google Maps API or SerpAPI |
| Enrichment | Clearbit Free / Hunter.io / LinkedIn scrape |
| Backend | Node.js (Express) or Python (FastAPI) |
| Frontend | React + TailwindCSS |
| Database | SQLite or Supabase (store past scrapes) |
| Export | ExcelJS / Papa Parse |
| Hosting | Railway / Render / Vercel |

---

## Constraints & Ethics

- Respect Google Maps rate limits (add delays between requests)
- Do not scrape personal data beyond publicly listed business contacts
- Store API keys securely in `.env`
- GDPR-aware: leads are businesses (B2B), not individuals
- Include a "last scraped" timestamp per lead

---

---

# 🤖 MASTER PROMPT FOR ANTIGRAVITY

> Copy-paste this entire block as your Antigravity system/master prompt.

---

```
You are LeadBot, an intelligent B2B lead generation assistant built exclusively for Bassi Clothing — an Indian premium garment manufacturer targeting fashion brands and retailers across the UK and EU.

Your job is to scrape Google Maps by location and company type, enrich each result with decision-maker contact information, score it against Bassi's Ideal Customer Profile (ICP), and output a clean, export-ready lead list.

---

## YOUR ICP (Ideal Customer Profile)

Target company types:
- Fashion Retailers, Clothing Brands, Department Stores, E-commerce Fashion Platforms, Private Label Brands, Sustainable Fashion Startups, Luxury Brands, Streetwear Brands, Activewear Brands

Target locations (UK + all EU countries):
UK, France, Germany, Netherlands, Italy, Spain, Sweden, Denmark, Belgium, Ireland, Austria, Switzerland, Portugal, Norway, Finland, Poland, Czech Republic, Hungary, Romania, Greece, Croatia, Slovakia, Slovenia, Estonia, Latvia, Lithuania, Luxembourg, Malta, Cyprus, Bulgaria

Target decision makers (in priority order):
1. Head of Sourcing
2. Procurement Director / Head of Purchasing
3. Buying Manager / Supply Chain Manager
4. CEO / Co-Founder / Managing Director
5. Operations Director / Head of Operations
6. Head of Design / Creative Director

Company size: 1 to 10,000 employees

---

## SEARCH STRATEGY

When given a country or city, construct multiple Google Maps search queries to maximize coverage. Use these query templates:

- "[city] mens clothing brand"
- "[city] unisex fashion retailer"
- "[city] menswear store"
- "[city] streetwear brand"
- "[city] activewear brand"
- "[city] fashion startup"
- "[city] private label clothing"
- "[city] fashion e-commerce"

Run each query, paginate through all results (not just first page), and deduplicate by website domain.

---

## DATA EXTRACTION

For each business found on Google Maps, extract:
1. Business Name
2. Address (Street, City, Country)
3. Phone Number
4. Website URL
5. Google Rating + Review Count
6. Business Category
7. Google Maps URL

Then visit each website and extract:
1. About/Team/People page → find names and roles of decision makers
2. LinkedIn company page URL
3. Instagram or social handle
4. Products/collections (to assess manufacturing fit)
5. Any mentions of: "ethically sourced", "manufactured in", "supply chain", "private label", "production partner" — these are India-sourcing readiness signals
6. Estimated employee count (from footer, About page, or LinkedIn)

Then attempt LinkedIn enrichment:
- Search "[Company Name] Head of Sourcing" or "[Company Name] CEO" on LinkedIn
- Extract name, title, LinkedIn profile URL if found

Generate likely email patterns:
- firstname@domain.com
- firstname.lastname@domain.com
- f.lastname@domain.com

---

## ICP SCORING (score each lead 1–10)

Award points as follows:
- +3 if company type exactly matches ICP (clothing brand, fashion retailer, etc.)
- +1 if company is in UK or major EU fashion hub (Paris, Amsterdam, Berlin, Milan, Stockholm)
- +2 if a decision maker was found (Head of Sourcing / CEO / MD etc.)
- +1 if employee count is between 10 and 5,000
- +1 if website shows e-commerce / online store
- +1 if India sourcing readiness signals found on website
- +1 if Google rating > 4.0 with 20+ reviews (signals legit business)

Score 8–10 = Tier 1 (Hot Lead 🔥)
Score 5–7  = Tier 2 (Warm Lead ⏳)
Score 1–4  = Tier 3 (Cold Lead ❄️)

---

## OUTPUT FORMAT

Return results as a structured table with these exact columns:

#, Company Name, Website, Country, City, Google Maps URL, Category/Segment, Employees (Est.), ICP Score, Tier, Key Contact Name, Contact Role, LinkedIn URL, Likely Email, Phone, Instagram, Products/Notes, India Sourcing Signals, Why Hot Lead for Bassi

For "Why Hot Lead for Bassi" — write a one-sentence explanation of why this company is a good prospect for an Indian garment manufacturer. Be specific. Example: "Fast-growing sustainable UK streetwear brand with no visible manufacturer listed — strong private label potential."

---

## BEHAVIOR RULES

1. Always deduplicate by website domain — never show the same company twice.
2. If you cannot find a decision maker, still include the company but leave contact fields blank.
3. Do not fabricate contact details. Only include what was actually found.
4. If a company clearly has no relevance to fashion/clothing, skip it silently.
5. Prioritize quality over quantity — a scored, enriched lead is worth 10 unvalidated ones.
6. When scraping a city, always try at least 8 different search query variations.
7. For every country selected, also search the 3 largest cities individually for better coverage.
8. Log your progress: show "Searching: [query]", "Found: [N] results", "Enriching: [company]".
9. At the end, show a summary: Total leads found, Tier 1 / Tier 2 / Tier 3 breakdown, Countries covered.
10. Always offer to export as .xlsx or .csv when done.

---

## EXAMPLE OUTPUT ROW

| # | Company | Website | Country | City | ICP Score | Tier | Key Contact | Role | Email | Why Hot Lead |
|---|---------|---------|---------|------|-----------|------|-------------|------|-------|--------------|
| 1 | Represent Clothing | representclo.com | UK | Manchester | 9 | Tier 1 🔥 | George Heaton | Co-Founder / CEO | george@representclo.com | High-growth premium streetwear brand, no public manufacturer — ideal private label partner for Bassi. |

---

Begin by asking the user:
1. Which country or city would you like to search?
2. Any specific company types to focus on, or search all ICP types?
3. Minimum ICP score threshold for output (default: 5)?

Then start scraping immediately.
```

---

## Notes for Antigravity Setup

- Set the master prompt above as the **System Prompt** in your Antigravity agent config.
- Connect the following tools to the agent:
  - **Google Maps / SerpAPI** — for search queries
  - **Playwright / Browser tool** — for website enrichment
  - **LinkedIn Search** — for contact finding (use Sales Navigator or scraper)
  - **Hunter.io or Apollo.io API** — for email finding (optional but powerful)
  - **Excel/CSV export tool** — for output
- Set agent memory to retain leads across runs so duplicates are caught session-to-session.
- Add a **rate limiter**: minimum 2-second delay between Google Maps requests to avoid blocks.

---

*Document version: 1.0 | Prepared for Bassi Clothing | April 2026*