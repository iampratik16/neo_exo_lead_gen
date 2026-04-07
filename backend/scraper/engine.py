"""
Bassi Clothing — Google Maps Lead Scraper Engine
=================================================
Two-pass architecture:
  Pass 1: Scroll Google Maps feed, collect all business metadata.
  Pass 2: Visit each website in a fresh page to extract emails & signals.

CRITICAL: Uses geolocation spoofing + Maps viewport coordinates to ensure
results come from the target country, not the user's physical location.
"""

import asyncio
import re
import urllib.parse
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, BrowserContext

from models import SearchRequest, Lead, ScrapeProgress


# ---------------------------------------------------------------------------
# Country → (latitude, longitude, zoom, Google Maps TLD/hl hint)
# Used to spoof geolocation and centre the Maps viewport.
# ---------------------------------------------------------------------------
COUNTRY_COORDS: Dict[str, Tuple[float, float, int]] = {
    "united kingdom":   (51.5074,  -0.1278,  10),
    "france":           (48.8566,   2.3522,  10),
    "germany":          (52.5200,  13.4050,  10),
    "netherlands":      (52.3676,   4.9041,  10),
    "italy":            (41.9028,  12.4964,  10),
    "spain":            (40.4168,  -3.7038,  10),
    "sweden":           (59.3293,  18.0686,  10),
    "denmark":          (55.6761,  12.5683,  10),
    "belgium":          (50.8503,   4.3517,  10),
    "ireland":          (53.3498,  -6.2603,  10),
    "austria":          (48.2082,  16.3738,  10),
    "switzerland":      (47.3769,   8.5417,  10),
    "portugal":         (38.7223,  -9.1393,  10),
    "norway":           (59.9139,  10.7522,  10),
    "finland":          (60.1699,  24.9384,  10),
    "poland":           (52.2297,  21.0122,  10),
    "czech republic":   (50.0755,  14.4378,  10),
    "hungary":          (47.4979,  19.0402,  10),
    "romania":          (44.4268,  26.1025,  10),
    "greece":           (37.9838,  23.7275,  10),
    "croatia":          (45.8150,  15.9819,  10),
    "slovakia":         (48.1486,  17.1077,  10),
    "slovenia":         (46.0569,  14.5058,  10),
    "estonia":          (59.4370,  24.7536,  10),
    "latvia":           (56.9496,  24.1052,  10),
    "lithuania":        (54.6872,  25.2797,  10),
    "luxembourg":       (49.6116,   6.1319,  10),
    "malta":            (35.8989,  14.5146,  10),
    "cyprus":           (35.1856,  33.3823,  10),
    "bulgaria":         (42.6977,  23.3219,  10),
}

# Major cities per country for better coverage
COUNTRY_CITIES: Dict[str, List[str]] = {
    "united kingdom":   ["London", "Manchester", "Birmingham"],
    "france":           ["Paris", "Lyon", "Marseille"],
    "germany":          ["Berlin", "Munich", "Hamburg"],
    "netherlands":      ["Amsterdam", "Rotterdam", "The Hague"],
    "italy":            ["Milan", "Rome", "Florence"],
    "spain":            ["Madrid", "Barcelona", "Valencia"],
    "sweden":           ["Stockholm", "Gothenburg", "Malmö"],
    "denmark":          ["Copenhagen", "Aarhus", "Odense"],
    "belgium":          ["Brussels", "Antwerp", "Ghent"],
    "ireland":          ["Dublin", "Cork", "Galway"],
    "austria":          ["Vienna", "Salzburg", "Graz"],
    "switzerland":      ["Zurich", "Geneva", "Basel"],
    "portugal":         ["Lisbon", "Porto", "Faro"],
    "norway":           ["Oslo", "Bergen", "Stavanger"],
    "finland":          ["Helsinki", "Tampere", "Turku"],
    "poland":           ["Warsaw", "Krakow", "Wroclaw"],
    "czech republic":   ["Prague", "Brno", "Ostrava"],
    "hungary":          ["Budapest", "Debrecen", "Szeged"],
    "romania":          ["Bucharest", "Cluj-Napoca", "Timisoara"],
    "greece":           ["Athens", "Thessaloniki", "Patras"],
    "croatia":          ["Zagreb", "Split", "Dubrovnik"],
    "slovakia":         ["Bratislava", "Košice", "Prešov"],
    "slovenia":         ["Ljubljana", "Maribor", "Celje"],
    "estonia":          ["Tallinn", "Tartu", "Narva"],
    "latvia":           ["Riga", "Daugavpils", "Liepāja"],
    "lithuania":        ["Vilnius", "Kaunas", "Klaipėda"],
    "luxembourg":       ["Luxembourg City"],
    "malta":            ["Valletta", "Sliema"],
    "cyprus":           ["Nicosia", "Limassol", "Larnaca"],
    "bulgaria":         ["Sofia", "Plovdiv", "Varna"],
}


# ---------------------------------------------------------------------------
# Dataclass for raw business data scraped from the Maps feed
# ---------------------------------------------------------------------------
@dataclass
class RawBusiness:
    name: str
    website: str
    phone: str
    maps_url: str
    country: str
    city: str
    rating: str = ""
    reviews: str = ""
    category: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# ICP category classification helpers
# ---------------------------------------------------------------------------
ICP_CATEGORIES = [
    "Fashion Retailers",
    "Clothing Brands",
    "Department Stores",
    "E-commerce Fashion Platforms",
    "Private Label Brands",
    "Sustainable Fashion Startups",
    "Luxury Fashion Brands",
    "Streetwear Brands",
    "Activewear / Sportswear Brands",
]

# keyword → category mapping (checked against lowered text)
_CATEGORY_RULES: List[Tuple[List[str], str]] = [
    (["department store", "department"], "Department Stores"),
    (["streetwear", "street wear", "urban wear", "skate"], "Streetwear Brands"),
    (["activewear", "sportswear", "athletic", "gym wear", "fitness apparel"], "Activewear / Sportswear Brands"),
    (["sustainable", "eco-friendly", "organic cotton", "fair trade", "ethical fashion"], "Sustainable Fashion Startups"),
    (["private label", "white label", "own brand manufacturing"], "Private Label Brands"),
    (["luxury", "haute couture", "premium fashion", "designer"], "Luxury Fashion Brands"),
    (["e-commerce", "ecommerce", "online store", "online shop", "online fashion", "webshop"], "E-commerce Fashion Platforms"),
    (["retailer", "retail", "fashion store", "clothing store", "boutique"], "Fashion Retailers"),
    (["brand", "clothing", "apparel", "fashion", "wear", "garment"], "Clothing Brands"),
]


def classify_business_category(about_text: str, maps_category: str) -> str:
    """Classify a business into one of the ICP categories."""
    combined = (about_text + " " + maps_category).lower()
    for keywords, category in _CATEGORY_RULES:
        if any(kw in combined for kw in keywords):
            return category
    return "Clothing Brands"  # sensible default for a Maps clothing search


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------
class LeadScraperEngine:
    """Orchestrates the full scrape-enrich-score pipeline."""

    RATE_LIMIT_DELAY = 2.0  # seconds between website visits

    def __init__(
        self,
        on_progress: Callable[[ScrapeProgress], None],
        on_lead: Callable[[Lead], None],
    ):
        self.on_progress = on_progress
        self.on_lead = on_lead
        self.leads_found = 0
        self.seen_domains: Set[str] = set()

    # ---- public entry point ------------------------------------------------
    async def run(self, request: SearchRequest) -> None:
        country_key = request.country.strip().lower()

        # Resolve geo coordinates for the target country
        coords = COUNTRY_COORDS.get(country_key)
        if not coords:
            # Fallback: use the country name directly, default to London coords
            coords = (51.5074, -0.1278, 10)

        lat, lng, zoom = coords

        # Build search locations: if user specified a city, use only that.
        # Otherwise, search the top 3 cities for better coverage.
        if request.city and request.city.strip():
            search_locations = [(request.city.strip(), request.country.strip())]
        else:
            cities = COUNTRY_CITIES.get(country_key, [request.country.strip()])
            search_locations = [(c, request.country.strip()) for c in cities]

        # Build query list
        company_types = request.company_types if request.company_types else [
            "mens clothing brand", "unisex fashion retailer", "menswear store"
        ]
        queries: List[Tuple[str, str, str]] = []  # (query, city, country)
        for city, country in search_locations:
            for ctype in company_types:
                queries.append((f"{ctype} in {city}, {country}", city, country))

        self._emit("scraping_maps", f"Preparing {len(queries)} search queries across {len(search_locations)} location(s)…")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            # --- Pass 1: collect raw business data from Maps ---------------
            all_raw: List[RawBusiness] = []
            maps_ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
                locale="en-GB",
                timezone_id="Europe/London",
                geolocation={"latitude": lat, "longitude": lng},
                permissions=["geolocation"],
            )
            maps_page = await maps_ctx.new_page()

            for query, city, country in queries:
                self._emit("scraping_maps", f"Searching: {query}")
                raw = await self._collect_from_maps(maps_page, query, city, country, lat, lng, zoom)
                all_raw.extend(raw)

            await maps_ctx.close()

            # Deduplicate by domain
            unique_raw: List[RawBusiness] = []
            for biz in all_raw:
                domain = self._domain(biz.website)
                if domain and domain not in self.seen_domains:
                    self.seen_domains.add(domain)
                    unique_raw.append(biz)

            self._emit(
                "enriching",
                f"Maps done. {len(all_raw)} total → {len(unique_raw)} unique businesses. Enriching…",
            )

            # --- Pass 2: enrich each business on its own page --------------
            enrich_ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )

            for idx, biz in enumerate(unique_raw, 1):
                self._emit(
                    "enriching",
                    f"[{idx}/{len(unique_raw)}] Enriching: {biz.name} ({biz.website})",
                )
                enrich_page = await enrich_ctx.new_page()
                try:
                    lead = await self._enrich(enrich_page, biz, request.min_score)
                    if lead:
                        self.leads_found += 1
                        self.on_lead(lead)
                except Exception as exc:
                    print(f"[enrich] Error on {biz.website}: {exc}")
                finally:
                    await enrich_page.close()
                await asyncio.sleep(self.RATE_LIMIT_DELAY)

            await enrich_ctx.close()
            await browser.close()

        self._emit(
            "completed",
            f"Done! {self.leads_found} qualified leads found.",
        )

    # ---- Pass 1 helpers ---------------------------------------------------
    async def _collect_from_maps(
        self, page: Page, query: str, city: str, country: str,
        lat: float, lng: float, zoom: int,
    ) -> List[RawBusiness]:
        """Open Google Maps centred on the target location and collect results."""
        results: List[RawBusiness] = []

        # Build a Maps URL with explicit viewport coordinates
        # Format: @lat,lng,zoom
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/maps/search/{encoded_query}/@{lat},{lng},{zoom}z?hl=en"

        try:
            await page.goto(url, timeout=60_000)
            await asyncio.sleep(5)

            # Dismiss cookie consent if present
            for btn_text in ["Accept all", "Reject all", "I agree"]:
                try:
                    btn = page.locator(f"button:has-text('{btn_text}')").first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await asyncio.sleep(1)
                        break
                except Exception:
                    pass

            # Wait for the results feed
            feed = page.locator('div[role="feed"]')
            try:
                await feed.wait_for(timeout=15_000)
            except Exception:
                print(f"[maps] No feed found for: {query}")
                return results

            # Scroll the feed 5 times to load more results
            for _ in range(5):
                await feed.evaluate("el => el.scrollTop = el.scrollHeight")
                await asyncio.sleep(2)

            # Collect every business card link
            links = await page.locator('a[href*="/maps/place/"]').all()
            self._emit("scraping_maps", f"Found {len(links)} listings for: {query}")

            for link in links:
                try:
                    name = await link.get_attribute("aria-label", timeout=3000)
                    href = await link.get_attribute("href", timeout=3000)
                    if not name or not href:
                        continue

                    # Click the listing to open the side panel
                    await link.click(timeout=5000)
                    await asyncio.sleep(2)

                    # Extract website
                    website = await self._extract_panel_field(
                        page, 'a[data-item-id="authority"]', "href"
                    )
                    if not website:
                        continue

                    # Extract phone
                    phone = await self._extract_panel_field(
                        page,
                        'button[data-item-id^="phone:tel:"]',
                        "aria-label",
                    )
                    if phone:
                        phone = (
                            phone.replace("Phone: ", "")
                            .replace("Phone number: ", "")
                            .strip()
                        )
                    else:
                        phone = "N/A"

                    # Extract full address from panel to verify location
                    address = await self._extract_panel_field(
                        page,
                        'button[data-item-id="address"]',
                        "aria-label",
                    )
                    if address:
                        address = address.replace("Address: ", "").strip()

                    # *** LOCATION FILTER ***
                    # Verify the business is actually in the target country
                    country_lower = country.lower()
                    address_lower = (address or "").lower()
                    maps_url_lower = (href or "").lower()

                    # Check if the country name appears in the address or maps URL
                    country_match = (
                        country_lower in address_lower
                        or city.lower() in address_lower
                        or country_lower in maps_url_lower
                        or city.lower() in maps_url_lower
                    )

                    # For "United Kingdom", also check for "UK", "England", "Scotland", "Wales"
                    if not country_match and country_lower == "united kingdom":
                        country_match = any(
                            kw in address_lower
                            for kw in ["uk", "england", "scotland", "wales", "london", "manchester", "birmingham"]
                        )

                    # For Denmark, also check for "Danmark"
                    if not country_match and country_lower == "denmark":
                        country_match = any(
                            kw in address_lower
                            for kw in ["denmark", "danmark", "copenhagen", "københavn", "aarhus", "odense"]
                        )

                    if not country_match and address:
                        # If we have an address but it doesn't match, skip this business
                        print(f"[maps] SKIPPED (wrong location): {name} — Address: {address}")
                        continue

                    # Extract rating
                    rating = ""
                    try:
                        rating_el = page.locator('div[role="img"][aria-label*="stars"]').first
                        rating = (await rating_el.get_attribute("aria-label", timeout=2000)) or ""
                    except Exception:
                        pass

                    # Extract the Google Maps "About" / description snippet
                    maps_description = ""
                    maps_category_text = ""
                    try:
                        # The category chip (e.g. "Clothing store") is usually the
                        # first button[jsaction] with category-like text near the top
                        cat_el = page.locator('button[jsaction*="category"]').first
                        maps_category_text = (await cat_el.text_content(timeout=2000)) or ""
                    except Exception:
                        pass

                    # Fallback: try to grab category from the panel heading area
                    if not maps_category_text:
                        try:
                            # Category text often appears near the business name
                            cat_spans = await page.locator('button.DkEaL').all()
                            if cat_spans:
                                maps_category_text = (await cat_spans[0].text_content(timeout=2000)) or ""
                        except Exception:
                            pass

                    # Try to extract the description / "About" text from panel
                    try:
                        # Google Maps puts the about text in various containers
                        about_selectors = [
                            'div.WeS02d.fontBodyMedium',   # common in 2025+ Maps
                            'div[class*="PYvSYb"]',        # some Maps versions use this
                            'div.rogA2c div.fontBodyMedium', # older variant
                        ]
                        for sel in about_selectors:
                            try:
                                about_el = page.locator(sel).first
                                txt = (await about_el.text_content(timeout=2000)) or ""
                                txt = txt.strip()
                                if txt and len(txt) > 15:
                                    maps_description = txt[:300]
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                    results.append(
                        RawBusiness(
                            name=name.strip(),
                            website=website.strip(),
                            phone=phone,
                            maps_url=href,
                            country=country,
                            city=city,
                            rating=rating,
                            category=maps_category_text.strip(),
                            description=maps_description,
                        )
                    )

                except Exception:
                    continue

        except Exception as exc:
            print(f"[maps] Fatal error for query '{query}': {exc}")

        return results

    @staticmethod
    async def _extract_panel_field(
        page: Page, selector: str, attribute: str
    ) -> Optional[str]:
        try:
            els = await page.locator(selector).all()
            if els:
                return await els[0].get_attribute(attribute, timeout=3000)
        except Exception:
            pass
        return None

    # ---- Pass 2: website enrichment ---------------------------------------
    async def _enrich(
        self, page: Page, biz: RawBusiness, min_score: int
    ) -> Optional[Lead]:
        """Visit the company website, extract emails & signals, score the lead."""
        emails: Set[str] = set()
        about_text = ""
        signals: List[str] = []

        # ----- Visit homepage -----
        try:
            await page.goto(biz.website, timeout=20_000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            about_text = soup.get_text(separator=" ").lower()

            # Extract emails from homepage HTML
            self._extract_emails(html, emails)

            # If no emails found on homepage, try /contact and /about pages
            if not emails:
                internal_links = soup.find_all("a", href=True)
                contact_pages = []
                for a in internal_links:
                    href_lower = a["href"].lower()
                    if any(
                        kw in href_lower
                        for kw in ["contact", "about", "team", "people", "impressum", "kontakt"]
                    ):
                        full = (
                            a["href"]
                            if a["href"].startswith("http")
                            else urllib.parse.urljoin(biz.website, a["href"])
                        )
                        contact_pages.append(full)

                # Visit up to 3 sub-pages
                for sub_url in list(set(contact_pages))[:3]:
                    try:
                        await page.goto(
                            sub_url, timeout=15_000, wait_until="domcontentloaded"
                        )
                        await asyncio.sleep(1)
                        sub_html = await page.content()
                        self._extract_emails(sub_html, emails)
                        sub_soup = BeautifulSoup(sub_html, "html.parser")
                        about_text += " " + sub_soup.get_text(separator=" ").lower()
                    except Exception:
                        pass

        except Exception as exc:
            print(f"[enrich] Could not load {biz.website}: {exc}")

        # ----- India sourcing signals -----
        sourcing_keywords = [
            "ethically sourced",
            "ethically made",
            "manufactured in",
            "supply chain",
            "private label",
            "production partner",
            "sustainab",
            "fair trade",
            "made in india",
        ]
        for kw in sourcing_keywords:
            if kw in about_text:
                signals.append(kw)

        # ----- ICP Scoring -----
        score = 3  # baseline: discovered via a relevant maps search query

        # Menswear & Unisex Focus Filter
        about_text_lower = about_text.lower()
        menswear_keywords = [
            "menswear", "men's wear", "mens clothing", "men's clothing",
            "unisex", "men's fashion", "mens fashion", "mens apparel", "men's apparel",
            "sweatshirt", "hoodie", "mercerized cotton", "t-shirt", "round neck",
            "polo neck", "trackpant", "shorts", "capri"
        ]
        womens_only_keywords = [
            "womenswear", "women's wear", "womens clothing", "women's clothing",
            "ladies fashion", "women's fashion", "womens fashion", "womens apparel"
        ]

        found_mens_products = [kw for kw in menswear_keywords if kw in about_text_lower]
        has_menswear = len(found_mens_products) > 0
        has_womenswear = any(kw in about_text_lower for kw in womens_only_keywords)

        if has_menswear:
            score += 2
        elif has_womenswear and not has_menswear:
            # Penalize heavily if it's strictly a women's brand
            score -= 5

        # +1 for location match (UK / major EU hub)
        location_keywords = [
            "london", "paris", "amsterdam", "berlin", "milan", "stockholm",
            "copenhagen", "brussels", "dublin", "vienna", "zurich", "lisbon",
            "oslo", "helsinki", "united kingdom", "uk", "denmark", "france",
            "germany", "netherlands", "italy", "spain", "sweden",
        ]
        if any(kw in biz.maps_url.lower() or kw in about_text for kw in location_keywords):
            score += 1

        # +2 if decision maker found
        dm_keywords = [
            "head of sourcing", "procurement", "buying manager",
            "ceo", "co-founder", "founder", "managing director",
            "operations director", "creative director",
        ]
        dm_found = any(kw in about_text for kw in dm_keywords)
        if dm_found:
            score += 2

        # +1 if ecommerce
        if any(kw in about_text for kw in ["add to cart", "add to bag", "shop now", "buy now", "køb nu", "tilføj til kurv"]):
            score += 1

        # +1 if sourcing signals
        if signals:
            score += 1

        # +1 if good rating
        if biz.rating and any(r in biz.rating for r in ["4.", "5 "]):
            score += 1

        # Clean emails
        clean_emails = sorted(
            {
                e
                for e in emails
                if not any(
                    junk in e
                    for junk in [
                        "sentry", "wix", "example", ".png", ".jpg",
                        ".jpeg", ".gif", ".svg", "cloudflare", "schema.org",
                    ]
                )
            }
        )
        if clean_emails:
            score += 1  # bonus for having a real email

        # Skip leads below threshold
        if score < min_score:
            return None

        tier = (
            "Tier 1 🔥" if score >= 7
            else ("Tier 2 ⏳" if score >= 4 else "Tier 3 ❄️")
        )

        # Format emails
        email_str = ", ".join(clean_emails) if clean_emails else "No email found"
        email_count = len(clean_emails)

        # ----- Business category classification -----
        biz_category = classify_business_category(about_text, biz.category)

        # ----- Build short description -----
        description = biz.description  # from Google Maps panel
        if not description or len(description) < 20:
            # Auto-generate a short description from website content
            description = self._generate_short_description(
                biz.name, biz_category, biz.city, biz.country,
                about_text, has_menswear, signals
            )

        return Lead(
            id=self.leads_found + 1,
            company_name=biz.name,
            description=description,
            business_category=biz_category,
            website=biz.website,
            country=biz.country,
            city=biz.city,
            google_maps_url=biz.maps_url,
            category=biz.category if biz.category else "Fashion / Clothing",
            employees_est="Unknown",
            icp_score=score,
            tier=tier,
            key_contact_name="Found on About page" if dm_found else "Not found",
            contact_role="Decision Maker detected" if dm_found else "N/A",
            linkedin_url="N/A",
            likely_email=email_str,
            phone=biz.phone,
            instagram="N/A",
            products_notes=", ".join(found_mens_products).title() if has_menswear else "Auto-classified from Maps search",
            india_sourcing_signals=", ".join(signals) if signals else "None detected",
            why_hot_lead=(
                f"Score {score}/10. {email_count} email(s) found. "
                + (f"Sourcing signals: {', '.join(signals[:3])}. " if signals else "")
                + f"{'Decision maker detected. ' if dm_found else ''}"
                + f"Rating: {biz.rating or 'N/A'}."
            ),
        )

    # ---- description generator ---------------------------------------------
    @staticmethod
    def _generate_short_description(
        name: str, category: str, city: str, country: str,
        about_text: str, has_menswear: bool, signals: List[str]
    ) -> str:
        """Auto-generate a concise business description when Maps didn't provide one."""
        parts = [f"{name} is a {category.lower()} based in {city}, {country}."]

        # Add product focus
        if has_menswear:
            parts.append("Offers menswear / unisex products.")

        # Add sourcing readiness hint
        if signals:
            parts.append(f"Sourcing signals: {', '.join(signals[:2])}.")

        # Add e-commerce hint
        ecom_keywords = ["add to cart", "add to bag", "shop now", "buy now"]
        if any(kw in about_text for kw in ecom_keywords):
            parts.append("Sells online via e-commerce.")

        return " ".join(parts)

    # ---- utilities --------------------------------------------------------
    @staticmethod
    def _extract_emails(html: str, output: Set[str]) -> None:
        """Find all email addresses in raw HTML."""
        pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
        for addr in re.findall(pattern, html):
            output.add(addr.lower())

    @staticmethod
    def _domain(url: str) -> Optional[str]:
        try:
            return urllib.parse.urlparse(url).netloc.replace("www.", "")
        except Exception:
            return None

    def _emit(self, status: str, action: str) -> None:
        self.on_progress(
            ScrapeProgress(
                status=status,
                leads_found=self.leads_found,
                current_action=action,
            )
        )
