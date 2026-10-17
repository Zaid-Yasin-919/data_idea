from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Organization:
    """Master entity model for corporate and government buyers/suppliers."""
    name: str
    id: Optional[int] = None
    entity_type: str = "other"
    cin: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    udyam_number: Optional[str] = None
    nic_code: Optional[str] = None
    industrial_classification: Optional[str] = None
    business_activity_description: Optional[str] = None
    registered_address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    company_status: str = "Active"
    source_origin: str = "unknown"
    raw_metadata: Optional[Dict[str, Any]] = None


@dataclass
class TenderItem:
    """Granular product or service line item demanded within a tender."""
    item_name: str
    id: Optional[int] = None
    tender_id: Optional[int] = None
    item_category: Optional[str] = None
    specifications: Optional[str] = None
    quantity: Optional[float] = None
    unit: str = "units"
    estimated_unit_price: Optional[float] = None
    total_estimated_value: Optional[float] = None
    raw_item_payload: Optional[Dict[str, Any]] = None


@dataclass
class Tender:
    """Public procurement bid / tender entity."""
    source: str
    bid_number: str
    title: str
    id: Optional[int] = None
    organization_id: Optional[int] = None
    description: Optional[str] = None
    bid_type: str = "goods"
    estimated_value: Optional[float] = None
    currency: str = "INR"
    publishing_date: Optional[str] = None
    closing_date: Optional[str] = None
    opening_date: Optional[str] = None
    status: str = "active"
    consignee_location: Optional[str] = None
    document_url: Optional[str] = None
    items: List[TenderItem] = field(default_factory=list)
    raw_payload: Optional[Dict[str, Any]] = None


@dataclass
class IndustrialPlant:
    """Physical manufacturing unit or industrial plant location."""
    unit_name: str
    id: Optional[int] = None
    organization_id: Optional[int] = None
    plant_type: str = "manufacturing"
    enterprise_category: str = "unclassified"
    address: Optional[str] = None
    industrial_area: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    major_activity: Optional[str] = None
    nic_code: Optional[str] = None
    investment_in_machinery_lakhs: Optional[float] = None
    annual_turnover_lakhs: Optional[float] = None
    date_of_commencement: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

