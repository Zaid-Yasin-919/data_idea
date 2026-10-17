-- ============================================================================
-- Indian Business, Corporate & Public Procurement Intelligence Schema (SQLite)
-- Universal Raw Data Layer: Organizations, Directors, Tenders, Items, and Plants
-- Sector-Agnostic: Handles all industries, ministries, and enterprise categories
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. ORGANIZATIONS (Master Entity Directory: MCA Companies, Gov Bodies, MSMEs)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                             -- Legal or Department name
    entity_type TEXT CHECK(entity_type IN (
        'private_limited', 'public_limited', 'llp', 'one_person_company',
        'government_body', 'public_sector_undertaking', 'msme_unit', 
        'proprietorship', 'partnership', 'society_trust', 'other'
    )) DEFAULT 'other',
    
    -- Universal Business Identifiers
    cin TEXT UNIQUE,                                -- MCA Corporate Identification Number
    gstin TEXT UNIQUE,                              -- Goods & Services Tax Identification Number
    pan TEXT,                                       -- Income Tax PAN
    udyam_number TEXT UNIQUE,                       -- MSME Udyam Registration Number
    
    -- Industrial Classification (NIC / MCA)
    nic_code TEXT,                                  -- National Industrial Classification code (2 to 5 digit)
    industrial_classification TEXT,                 -- e.g. "Manufacturing (Metals)", "Business Services", "Trading"
    business_activity_description TEXT,             -- Main objects / business description
    
    -- Geography & Registered Office
    registered_address TEXT,
    city TEXT,
    district TEXT,
    state TEXT,
    pincode TEXT,
    
    -- Contact Points
    email TEXT,
    phone TEXT,
    website TEXT,
    
    -- Corporate Financials & Status (from MCA / CDM)
    incorporation_date DATE,
    authorized_capital REAL,
    paid_up_capital REAL,
    company_status TEXT DEFAULT 'Active',           -- 'Active', 'Dormant', 'Strike Off', 'Under Liquidation'
    roc_code TEXT,                                  -- e.g. 'RoC-Delhi', 'RoC-Kanpur', 'RoC-Mumbai'
    
    -- Data Source Tracking
    source_origin TEXT DEFAULT 'unknown',           -- 'mca', 'gem', 'udyam', 'data_gov_in'
    raw_metadata JSON,                              -- Complete untouched metadata from source
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_org_name ON organizations(name);
CREATE INDEX IF NOT EXISTS idx_org_state_dist ON organizations(state, district);
CREATE INDEX IF NOT EXISTS idx_org_classification ON organizations(industrial_classification);
CREATE INDEX IF NOT EXISTS idx_org_nic ON organizations(nic_code);
CREATE INDEX IF NOT EXISTS idx_org_status ON organizations(company_status);

-- ----------------------------------------------------------------------------
-- 2. DIRECTORS & OFFICERS (Key Management Personnel & Signatories)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS directors_officers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    designation TEXT,                               -- 'Director', 'Managing Director', 'Designated Partner'
    din TEXT,                                       -- Director Identification Number (from MCA)
    pan TEXT,
    phone TEXT,
    email TEXT,
    appointment_date DATE,
    cessation_date DATE,
    is_active INTEGER DEFAULT 1,                    -- 1 for active, 0 for resigned/inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_officer_org ON directors_officers(organization_id);
CREATE INDEX IF NOT EXISTS idx_officer_din ON directors_officers(din);
CREATE INDEX IF NOT EXISTS idx_officer_name ON directors_officers(name);

-- ----------------------------------------------------------------------------
-- 3. TENDERS & PROCUREMENT BIDS (GeM, CPPP, State Portals, Defence, Railways)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,                        -- Issuing buyer / ministry / PSU
    source TEXT NOT NULL CHECK(source IN (
        'gem', 'cppp', 'state_procurement', 'railways', 'defence', 'other'
    )),
    bid_number TEXT NOT NULL,                       -- e.g. "GEM/2026/B/8120709" or CPPP Tender ID
    title TEXT NOT NULL,
    description TEXT,
    
    bid_type TEXT CHECK(bid_type IN (
        'goods', 'services', 'works', 'custom_bid', 'reverse_auction', 'other'
    )) DEFAULT 'goods',
    
    -- Values & Currency
    estimated_value REAL,
    currency TEXT DEFAULT 'INR',
    
    -- Procurement Schedule
    publishing_date TIMESTAMP,
    closing_date TIMESTAMP,                         -- Submission deadline
    opening_date TIMESTAMP,                         -- Bid opening date
    
    -- Current Lifecycle Status
    status TEXT CHECK(status IN (
        'active', 'under_evaluation', 'awarded', 'cancelled', 'retendered', 'closed'
    )) DEFAULT 'active',
    
    -- Location & Links
    consignee_location TEXT,                        -- Delivery city/state
    document_url TEXT,                              -- Direct tender/BOQ download link
    raw_payload JSON,                               -- Verbatim JSON payload from scraper
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenders_source_bid ON tenders(source, bid_number);
CREATE INDEX IF NOT EXISTS idx_tenders_closing ON tenders(closing_date);
CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status);
CREATE INDEX IF NOT EXISTS idx_tenders_org ON tenders(organization_id);

-- ----------------------------------------------------------------------------
-- 4. TENDER_ITEMS (Granular Products, Materials & Services Requested)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tender_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,                        -- e.g. "Desktop Computers", "Brass Strips", "PVC Pipes"
    item_category TEXT,                             -- Broad sector / category
    specifications TEXT,                            -- Technical parameters / BOQ notes
    quantity REAL,
    unit TEXT DEFAULT 'units',                      -- 'pieces', 'kg', 'metric_ton', 'meters', 'sets', etc.
    estimated_unit_price REAL,
    total_estimated_value REAL,
    raw_item_payload JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tender_items_tender ON tender_items(tender_id);
CREATE INDEX IF NOT EXISTS idx_tender_items_category ON tender_items(item_category);
CREATE INDEX IF NOT EXISTS idx_tender_items_name ON tender_items(item_name);

-- ----------------------------------------------------------------------------
-- 5. INDUSTRIAL_PLANTS (Physical Factories, MSME Units & Industrial Footprints)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS industrial_plants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,                        -- Owning entity
    unit_name TEXT NOT NULL,                        -- Plant or unit name
    plant_type TEXT CHECK(plant_type IN (
        'manufacturing', 'assembly', 'processing', 'warehouse', 'service_unit', 'other'
    )) DEFAULT 'manufacturing',
    
    enterprise_category TEXT CHECK(enterprise_category IN (
        'micro', 'small', 'medium', 'large', 'unclassified'
    )) DEFAULT 'unclassified',
    
    -- Physical Location
    address TEXT,
    industrial_area TEXT,                           -- e.g. "RIICO Industrial Area", "MIDC", "UPSIDC"
    district TEXT,
    state TEXT,
    pincode TEXT,
    
    -- Operational Metrics (from Udyam / Factory License)
    major_activity TEXT,                            -- e.g. "Manufacturing of Metal Products"
    nic_code TEXT,
    investment_in_machinery_lakhs REAL,
    annual_turnover_lakhs REAL,
    date_of_commencement DATE,
    
    raw_payload JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plants_org ON industrial_plants(organization_id);
CREATE INDEX IF NOT EXISTS idx_plants_state_dist ON industrial_plants(state, district);
CREATE INDEX IF NOT EXISTS idx_plants_nic ON industrial_plants(nic_code);
CREATE INDEX IF NOT EXISTS idx_plants_category ON industrial_plants(enterprise_category);
