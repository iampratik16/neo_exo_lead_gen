"""
Neo Eco Cleaning — Lead Generator
==================================
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel
from typing import List, Optional


class SearchRequest(BaseModel):
    """Trigger payload for a scraping run.

    Users can filter by business type and location. Selecting nothing
    (empty lists) is treated as "all" for that dimension.

    ``export_format`` controls whether the downloadable file is produced
    as .xlsx (Excel) or .csv.
    """

    dry_run: bool = False
    business_types: List[str] = []   # e.g. ["property_management", "estate_agent"]
    locations: List[str] = []         # e.g. ["Barnet, London", "Camden, London"]
    export_format: str = "xlsx"       # "xlsx" or "csv"


class Lead(BaseModel):
    """A single lead row — CRM-ready export format.

    Export column order (17 columns):
      Company Name | Email | Person | Primary_Designation |
      Company Description | Country | Industry | Website |
      Employees | Revenue | Founded | Company_Phone |
      Company_LinkedIn | Primary_Phone | LinkedIn |
      Alternate_Person | Alternate_Designation
    """

    # ---- Core identification ----
    business_name: str               # → "Company Name"
    email: str                       # → "Email"
    contact_person: str = ""         # → "Person"
    primary_designation: str = ""    # → "Primary_Designation" (role/title)

    # ---- Company info ----
    company_description: str = ""    # → "Company Description"
    country: str = "United Kingdom"  # → "Country"
    industry: str = ""               # → "Industry"
    website: str = ""                # → "Website"
    employees: str = ""              # → "Employees" (best-effort)
    revenue: str = ""                # → "Revenue" (best-effort)
    founded: str = ""                # → "Founded" (best-effort)

    # ---- Contact details ----
    company_phone: str = ""          # → "Company_Phone"
    company_linkedin: str = ""       # → "Company_LinkedIn"
    primary_phone: str = ""          # → "Primary_Phone"
    linkedin: str = ""               # → "LinkedIn"

    # ---- Alternate contact ----
    alternate_person: str = ""       # → "Alternate_Person"
    alternate_designation: str = ""  # → "Alternate_Designation"

    # ---- Internal scoring (not exported but used for UI/sorting) ----
    outreach_priority: str = "LOW"   # HIGH / MEDIUM / LOW
    icp_tier: str = ""               # "Tier 1 – Block Management" etc.
    category: str = ""               # "Property Management" or "Estate Agent"
    borough: str = ""                # London borough
    area_zone: str = ""              # "North London" / "West London" etc.
    google_maps_url: str = ""
    rating: str = ""
    review_count: int = 0
    address: str = ""
    notes: str = ""


class ScrapeProgress(BaseModel):
    """Real-time progress update pushed to the frontend."""

    status: str
    leads_found: int
    current_action: str
