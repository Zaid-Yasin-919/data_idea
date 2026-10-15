-- ============================================================================
-- Moradabad B2B Matchmaking — Demand & Intent Database Schema
-- Focus: Organizations (Buyers/Gov), Officers/Directors, Intent Signals, & Items
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. ORGANIZATIONS (Master entity for buyers, government bodies, corporates)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                             -- Legal or Department name
    org_type TEXT CHECK(org_type IN (
        'government_body', 'private_limited', 'public_limited', 
        'llp', 'proprietorship', 'partnership', 'wholesaler', 'other'
    )) DEFAULT 'other',
    
    -- Identifiers
    cin TEXT UNIQUE,                                -- MCA Corporate Identification Number
    gst_number TEXT UNIQUE,                         -- GSTIN
    pan TEXT,                                       -- Permanent Account Number
    udyam_reg_number TEXT UNIQUE,                   -- MSME Udyam Registration Number
    
    -- Industrial Classification
    industrial_classification TEXT,                 -- MCA Industry / NIC Code
    business_activity TEXT,                         -- e.g. "Manufacturing (Metals)", "Trading"
    
    -- Address & Geography
    address TEXT,
    city TEXT,
    district TEXT,
    state TEXT,
    pincode TEXT,
    
    -- Direct Contact Details
    phone TEXT,
    email TEXT,
    website TEXT,
    
    -- Financials / Registration Info (from MCA)
    incorporation_date DATE,
    authorized_capital REAL,
    paid_up_capital REAL,
    company_status TEXT DEFAULT 'Active',           -- 'Active', 'Dormant', 'Strike Off'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_org_name ON organizations(name);
CREATE INDEX IF NOT EXISTS idx_org_state_city ON organizations(state, city);
CREATE INDEX IF NOT EXISTS idx_org_classification ON organizations(industrial_classification);

-- ----------------------------------------------------------------------------
-- 2. ORGANIZATION_OFFICERS (Directors, Signatories, Procurement Officers)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organization_officers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    designation TEXT,                               -- 'Director', 'Managing Director', 'Purchase Manager'
    din TEXT,                                       -- Director Identification Number (from MCA)
    phone TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_officer_org ON organization_officers(organization_id);
CREATE INDEX IF NOT EXISTS idx_officer_din ON organization_officers(din);

-- ----------------------------------------------------------------------------
-- 3. INTENT_SIGNALS (Events: GeM Tenders, MCA Incorp, Import Shipments)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS intent_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,                        -- Linked organization if identified
    source TEXT NOT NULL CHECK(source IN (
        'gem', 'cppp', 'mca', 'udyam', 'exim', 'manual'
    )),
    source_ref_id TEXT NOT NULL,                    -- e.g. "GEM/2026/B/8120709" or MCA CIN / URN
    title TEXT,                                     -- Headline summary
    
    signal_type TEXT CHECK(signal_type IN (
        'tender_bid', 'new_incorporation', 'import_shipment', 'msme_registration'
    )) DEFAULT 'tender_bid',
    
    -- Lead Qualification Pipeline
    signal_status TEXT CHECK(signal_status IN (
        'detected', 'analyzed', 'call_queued', 'verified_buyer', 'disqualified', 'closed'
    )) DEFAULT 'detected',
    
    intent_score REAL DEFAULT 0.5,                 -- 0.0 (irrelevant) to 1.0 (exact Moradabad fit)
    
    -- Timelines
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_date TIMESTAMP,                       -- Tender publish date or incorporation date
    closing_date TIMESTAMP,                         -- Tender submission deadline
    
    source_url TEXT,                                -- Link to GeM tender document or MCA page
    raw_payload JSON,                               -- Full verbatim JSON dump from scraper
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL
);

-- Unique index prevents duplicate signals across runs
CREATE UNIQUE INDEX IF NOT EXISTS idx_signal_source_ref ON intent_signals(source, source_ref_id);
CREATE INDEX IF NOT EXISTS idx_signal_status ON intent_signals(signal_status);
CREATE INDEX IF NOT EXISTS idx_signal_score ON intent_signals(intent_score DESC);

-- ----------------------------------------------------------------------------
-- 4. SIGNAL_ITEMS (Granular products / line items demanded in a signal)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS signal_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    item_title TEXT NOT NULL,                       -- e.g. "BRASS STRIPS 1.00 mm"
    category TEXT CHECK(category IN (
        'trophy_memento', 'statue_figure', 'home_decor', 
        'hardware_fitting', 'raw_material_metal', 'gifting', 'other'
    )) DEFAULT 'other',
    
    material TEXT CHECK(material IN (
        'brass', 'aluminium', 'iron', 'copper', 'metal_alloy', 'non_metal', 'unknown'
    )) DEFAULT 'unknown',
    
    quantity INTEGER,
    unit TEXT DEFAULT 'pieces',                     -- 'pieces', 'sets', 'kg', 'nos'
    estimated_budget REAL,
    specifications TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signal_id) REFERENCES intent_signals(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_item_category ON signal_items(category);
CREATE INDEX IF NOT EXISTS idx_item_material ON signal_items(material);

-- ----------------------------------------------------------------------------
-- 5. QUALIFICATION_CALLS (Audit log of buyer verification calls)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS qualification_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    signal_id INTEGER,
    contacted_person TEXT,
    phone_dialed TEXT NOT NULL,
    call_outcome TEXT CHECK(call_outcome IN (
        'verified_ready_to_buy', 'verified_future_requirement', 
        'procuring_elsewhere', 'no_requirement', 'unreachable', 'wrong_number'
    )) NOT NULL,
    verified_budget REAL,
    verified_timeline TEXT,
    notes TEXT,
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
    FOREIGN KEY (signal_id) REFERENCES intent_signals(id) ON DELETE SET NULL
);
