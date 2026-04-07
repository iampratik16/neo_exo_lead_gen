from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    country: str
    city: Optional[str] = None
    company_types: List[str]
    radius_km: int = 25
    min_score: int = 5

class Lead(BaseModel):
    id: int
    company_name: str
    description: str
    business_category: str
    website: str
    country: str
    city: str
    google_maps_url: str
    category: str
    employees_est: str
    icp_score: int
    tier: str
    key_contact_name: str
    contact_role: str
    linkedin_url: str
    likely_email: str
    phone: str
    instagram: str
    products_notes: str
    india_sourcing_signals: str
    why_hot_lead: str

class ScrapeProgress(BaseModel):
    status: str
    leads_found: int
    current_action: str
