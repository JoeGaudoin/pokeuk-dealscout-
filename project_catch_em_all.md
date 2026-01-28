This technical specification serves as the blueprint for **"PokeUK DealScout,"** a real-time arbitrage platform designed to identify undervalued Pokémon TCG opportunities across the UK market.

---

## **1\. Project Overview**

**Objective:** A high-frequency web dashboard that aggregates "Buy It Now" listings from major UK marketplaces and compares them against current market rates to highlight "deals."

**Frequency:** 60-second refresh cycles for primary sources.

**Target Market:** United Kingdom (£ GBP, local shipping).

---

## **2\. System Architecture**

The platform operates on a **Distributed Worker Architecture** to handle multiple scraping and API tasks concurrently without slowing down the user interface.

| Layer | Component | Description |
| :---- | :---- | :---- |
| **Data Ingestion** | Python / Playwright | Custom scrapers for retail sites and API consumers for eBay. |
| **Logic Engine** | FastAPI | Calculates the **Deal Score** and applies the **Keyword Blacklist**. |
| **Data Storage** | PostgreSQL / Redis | Stores card metadata (Postgres) and live deals (Redis). |
| **User Interface** | Next.js | A reactive frontend with filters for sets, price, and condition. |

---

## **3\. Marketplace Connectivity**

To achieve a "marketplace of all deals," the system must integrate three distinct types of UK sources:

### **A. API-Driven (Real-time)**

* **eBay UK (Site ID 3):** Primary source for secondary market deals. Uses the **Browse API** to find "Newly Listed" items.  
* **Pokémon TCG API:** Used as the master reference for card images and set IDs.

### **B. Marketplace Scraping (High Margin)**

* **Cardmarket (UK Sellers):** Monitoring "Price Trend" vs. "Low" for UK-located listings.  
* **Vinted & FB Marketplace:** Requires a **Headless Browser (Playwright)** to monitor for "bundle" keywords like *"Old Pokemon Cards"* or *"Binder Collection."*

### **C. Retail Monitoring (Clearance)**

* **Magic Madhouse / Chaos Cards:** Scrapes the "Singles" and "Sale" pages for price drops or mispriced stock.

---

## **4\. Operational Logic & Data Integrity**

### **The "Deal Score" Calculation**

A deal is only valid if it remains profitable after UK-specific costs.

$$Deal Score \= \\frac{MarketValue \- (ListingPrice \+ Shipping \+ PlatformFees)}{MarketValue} \\times 100$$

### **Keyword Blacklist (The "Fake Filter")**

To maintain the North Star of "high-quality deals," the following keywords trigger an **automatic discard**:

* **Proxies/Fakes:** proxy, replica, reprint, handmade, tribute, non-official.  
* **Low-Value Noise:** mystery bundle, unsearched, energy cards, code cards.  
* **Visual Red Flags:** Any listing titled with **"Digital Card"** or **"TCG Online Code."**

---

## **5\. UI/UX Requirements**

* **Live Ticker:** A sidebar showing "Just Found" deals within the last 5 minutes.  
* **Set Filtering:** A multi-select dropdown to focus on specific eras (e.g., *WotC Vintage*, *Sword & Shield Chase*, *2025/2026 Mega Evolutions*).  
* **Direct Action:** A "Buy Now" button that deep-links directly to the marketplace listing.  
* **Price Floor/Ceiling:** Ability to filter out any card under £10 to avoid bulk-listing clutter.

---

## **6\. Implementation Challenges**

1. **Bot Detection:** UK retailers use Cloudflare. The system must use **Rotating Proxies** (UK-based) to avoid being blocked.  
2. **Price Normalization:** Converting "eBay Sold" (historical) and "Cardmarket Low" (current) into a single "True Market Value" for the UK.  
3. **Condition Matching:** Using OCR (Optical Character Recognition) to read listing titles for terms like NM (Near Mint) or LP (Lightly Played) to ensure the price comparison is "like-for-like."

