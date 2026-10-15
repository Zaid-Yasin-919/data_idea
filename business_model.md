# B2B Buyer–Seller Matchmaking: Moradabad Brass & Metal Handicrafts

## 1. One-line summary
An intent-driven matchmaking service that connects Moradabad brass and metal handicraft manufacturers with verified, ready-to-buy domestic buyers. Sellers pay; buyers use it free. A data pipeline finds buyer intent, and people on the ground verify it and close deals.

## 2. The problem

**Manufacturers (Moradabad units)**
- Much of the cluster's output goes through exporters; many smaller units do job work for them and have few direct domestic buyers
- Depend on the same few traders and exporters, who squeeze margins
- Can't afford the time or travel to build new distribution
- Pay for directory subscriptions (IndiaMART, TradeIndia) and get junk or recycled inquiries

**Buyers (traders, gifting firms, décor brands, new businesses)**
- Searching gives 50 sellers; checking who is genuine, capable, and fairly priced takes days
- Fear of losing advance payments to unreliable suppliers
- Buying through Delhi traders means paying an extra margin
- Small buyers struggle with high minimum order quantities and lack of credit

## 3. The solution
1. **Detect intent** from public and licensed data signals (automated pipeline)
2. **Verify** the need with a call
3. **Match** 2–3 suitable, pre-verified Moradabad sellers
4. **Introduce** both sides warmly on WhatsApp
5. **Follow up** until the deal closes; support the deal afterward
6. **Feed outcomes back** into the pipeline to improve lead scoring

Human verification on both sides is the core value. Anyone can buy a list; few qualify the leads.

## 4. Target market

### Starting cluster: Moradabad
- India's major brass and metal handicraft hub, large and fragmented
- Close to the founder's base in Bijnor, allowing frequent visits and local references
- Products: brass, aluminium, and iron décor, statuettes, gifting items, trophies, mementos, home and hospitality décor

Later clusters to expand into: Aligarh (locks, hardware), Meerut (sports goods), Khurja (ceramics), Firozabad (glass).

### Demand side: priority buyers
1. **Delhi gift and décor wholesalers** (Sadar Bazar and similar markets). They buy in volume, buy repeatedly, act fast, and constantly need new manufacturers and product lines.
2. **Corporate gifting companies**, especially before Diwali and year-end
3. **D2C and home décor brands** that need manufacturers
4. **Hotels, hospitality, and interior design firms**
5. **Buyers importing similar products** (e.g. from China) who could switch to a domestic source
6. **Out-of-state distributors and retailers** who can't visit Moradabad in person
7. **Government buyers** via GeM tenders for mementos, trophies, and décor

**Not a priority:** established small shops with fixed suppliers. Discovery isn't their problem.

### Seasonality
Domestic demand peaks around Diwali, corporate gifting cycles, and the wedding season. Time the first big buyer push before these.

## 5. Team

| Role | Who | Responsibilities | When |
|---|---|---|---|
| **Founder: data, pipeline & product** | You | Intent pipeline, seller database, matching system, tooling. Personally join the first 10–20 seller and buyer conversations. | Day 1 |
| **Sales / BD co-founder or early partner** | Someone from Moradabad, Bijnor, or the handicraft trade | Sit with workshop owners, sign sellers, close buyers, own relationships. Equity, not only salary. **Most important hire.** | Day 1 (or as early as possible) |
| **Field person, Moradabad** | Local, ideally from a family in the trade | Onboard units, product photos, samples, capacity and legitimacy checks | Month 1–4 |
| **Caller / operations** | Hindi-speaking, can be remote/part-time at first | Verify buyer intent by phone, follow-ups, keep records clean | Around month 3 |
| **Outside help** | Freelancers | Part-time CA (GST, accounts); photographer for a few days to build catalogs | As needed |

**No developer hire early.** The founder builds the pipeline; operations run on WhatsApp and sheets until sellers renew.

## 6. Revenue model
- **Sellers pay; buyers are free.** Buyers in India rarely pay for supplier contacts.
- **Primary:** monthly plan for a set number of verified buyer leads
- **Alternative:** per-qualified-lead fee
- **Trial:** first 3–5 leads free so sellers can judge quality
- **Collect fees upfront.** Never rely on small businesses honestly reporting commissions after a deal.

Seller pitch (Hinglish):
> "Aapko sirf woh buyer milenge jinko abhi maal chahiye, aur paisa tabhi jab order lage."
> ("You'll only get buyers who need goods right now, and you only pay when an order is placed.")

Moradabad angle: lead with **direct domestic buyers**, an alternative to depending only on exporters and traders.

## 7. Data and intent pipeline (founder's domain)

### Signal sources

| Signal | Source | Status |
|---|---|---|
| Government tenders for brass items, trophies, mementos, décor | GeM, state tender portals | Public; collect gently, rate-limited |
| Import substitution | Import shipment data filtered by **HSN 8306** (base-metal ornaments, statuettes, photo frames) | Buy from licensed providers |
| New gifting, décor, hospitality, interior firms | MCA company data; GST/new registrations via licensed vendors | Public/licensed; don't bulk-scrape the GST portal |
| Procurement hiring | Job posts for purchase roles at hotels, gifting firms, décor brands | Public |
| New D2C décor brands | Their websites and marketplace listings | Public; respect site terms |
| Seasonal triggers | Diwali, corporate gifting, wedding season | Planning calendar |

### Pipeline stages
1. **Ingest** each source on a schedule
2. **Clean and deduplicate**
3. **Resolve entities:** the same company found via GST, MCA, and its website becomes one record
4. **Enrich:** category, location, size
5. **Score intent:** recency, fit with Moradabad products, signal strength
6. **Push top leads** to the caller's verification queue
7. **Log outcomes** (verified / matched / deal / no deal) and feed them back to improve scoring

### Seller-side data
Structured seller profiles (see Section 8) with product tags, capacity, minimum order quantity, and price bands, so matching can be automated.

### Build discipline
Early on, data is not the bottleneck; closing sellers and getting buyer feedback is. Start with **2–3 signal sources** and spreadsheet-level tooling, prove that sellers renew, then automate whatever slows you down most.

### Avoid
- Scraping IndiaMART, JustDial, TradeIndia (prohibited by their terms, with IT Act liability risk)
- Bulk-scraping the GST portal (captcha-protected, meant for one-off checks)
- Bought contact lists from leaked databases

### Compliance
Follow the DPDP Act. Business information (company names, GST numbers, tenders) is mostly fine. Proprietors' phone numbers are personal data, so get consent before adding people to your system and offer an easy opt-out. Get a legal review before scaling.

## 8. What to maintain

| Record | Contents | Why it matters |
|---|---|---|
| **Seller profiles** | Product photos, materials and finishes (brass, aluminium, iron), price ranges, minimum order quantity, monthly capacity, lead time, GST number, export experience | Good photos sell handicrafts; structured data enables matching |
| **Buyer pipeline** | Lead source, verification status, product need, quantity, timeline | Drives the caller's daily work |
| **Match log** | Who was introduced to whom, deal outcome, feedback from both sides | Proves lead quality at renewal time; trains scoring |
| **Subscriptions & invoices** | Who paid, renewal dates, GST invoices | Cash collection |
| **Consent records** | Who agreed to receive messages | DPDP compliance |

**Tools:** WhatsApp Business (with product catalogs), Google Sheets or Airtable, Razorpay (subscriptions), Zoho Books or Tally (accounts).

## 9. Disintermediation strategy
Assume most repeat orders will go direct. Build so it doesn't matter:
- **Charge for leads, not deals.** Sellers always need new buyers.
- **Stay useful after the introduction:** credit or delayed payment through an NBFC partner, payment protection, logistics, and dispute handling
- **Pool demand:** combine small buyers' orders into bulk orders for better prices and lower minimum quantities
- Don't count on hiding contact numbers; they get exchanged on the first call.

## 10. Buyer value proposition
Lead with what buyers actually want, not "we'll find you a supplier":
- Direct-from-workshop prices instead of trader margins
- Credit (buy now, pay in 30 days)
- Lower minimum order quantities through pooling
- Verified sellers, so advances are safe
- A shortlist with photos and quotes, delivered quickly

## 11. Go-to-market

### Supply onboarding (Moradabad)
- **In person for the first 20–30 sellers**, led by the sales partner with the founder attending early meetings
- Enter through the local exporters' association or EPCH (Export Promotion Council for Handicrafts) for credibility
- Use Bijnor and family references
- Ask each owner for two referrals
- Verify capacity, quality, and legitimacy on site; photograph products

### Demand onboarding
- Walk into Delhi gift and décor wholesale markets; follow up on WhatsApp
- Use pipeline signals for gifting firms, décor brands, hospitality, importers, and tenders

### Deal facilitation
- WhatsApp group with both sides + a call
- Accompany the buyer on workshop visits for the first few large deals

### Scaling
- Field person handles ongoing onboarding and verification in Moradabad
- Callers added as lead volume grows
- Automate pipeline stages only after sellers are renewing
- Add the next cluster once Moradabad is working

## 12. Competition
| Player | Model | Your edge |
|---|---|---|
| IndiaMART, TradeIndia | Horizontal listings, seller subscriptions | Verified, high-intent leads instead of junk inquiries |
| Udaan, Jumbotail, Moglix, OfBusiness, Zetwerk | Category-specific transactions and supply | Deep Moradabad focus and local, face-to-face trust |
| JustDial, Google Maps | Local discovery | Matching and verification, not just listings |
| Exporters and traders | Intermediaries for Moradabad output | Direct domestic buyers for workshops |
| ONDC | Open network protocols | Possible distribution channel later |

## 13. Key risks
| Risk | Mitigation |
|---|---|
| No strong sales partner | Make this the first hire; offer equity |
| Over-building tech before validation | 2–3 signal sources, sheets first, automate later |
| Cold start (no buyers without sellers, and vice versa) | Hand-onboard Moradabad supply first |
| Disintermediation | Per-lead pricing and post-introduction services (Section 9) |
| Price-sensitive, slow-paying SMBs | Upfront fees, free trial to prove quality |
| Seasonal demand swings | Time pushes before Diwali, gifting, and wedding seasons; add hospitality and tenders for steadier demand |
| Data and legal exposure | Public and licensed sources only, consent, legal review |

## 14. Validation plan (before spending on data or tech)
1. Interview **10 Moradabad manufacturers** (founder attends):
   - How do you find new buyers today? How much goes through exporters?
   - What do you pay for directories or agents, and is it worth it?
   - Would you pay a monthly fee for verified domestic buyer leads? How much?
2. Interview **10–20 buyers** (Delhi wholesalers, gifting firms, décor brands):
   - How did you find your current suppliers?
   - What went wrong with your last supplier?
   - Would credit, lower minimum orders, or workshop-direct prices make you switch?
3. Build a minimal pipeline on **2–3 signal sources** and check how many leads verify as real.
4. Manually deliver 5–10 matches using WhatsApp + spreadsheet.
5. **Success test:** at least 3 sellers willing to pay for a second month.

## 15. Open decisions
- [x] Starting cluster: **Moradabad**
- [ ] Sales / BD partner: who, and equity split
- [ ] Monthly plan price and number of leads included
- [ ] First 2–3 signal sources to build
- [ ] Data vendors for MCA / registration / shipment data
- [ ] NBFC or credit partner (for later)
