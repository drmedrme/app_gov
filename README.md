# app_gov — Companies House XML Gateway Filing Application

A Flask application that generates iXBRL accounts and submits them directly to the Companies House XML Gateway. Currently files micro-entity annual accounts for **CORSICA STREET 567 LIMITED** (10303807), with potential to become a multi-company SaaS filing platform.

---

## What We Built

This application handles the entire Companies House annual accounts filing workflow:

1. **Form entry** — pre-filled balance sheet figures (these don't change year to year for this company)
2. **iXBRL generation** — produces a compliant inline XBRL document using the FRC FRS-102 taxonomy (covering FRS 105 micro-entities)
3. **GovTalk envelope** — wraps the base64-encoded iXBRL in a v1.0 GovTalk XML envelope with CHMD5 authentication
4. **Gateway submission** — POSTs to the Companies House XML Gateway at `https://xmlgw.companieshouse.gov.uk/v1-0/xmlgw/Gateway`
5. **Status polling** — checks submission status (ACCEPT/REJECT/PENDING/PARKED) and acknowledges receipt

This is the same XML Gateway mechanism used by commercial filing software such as FreeAgent, Xero, and TaxCalc.

### Application Files

| File | Purpose |
|------|---------|
| `app.py` | Flask web app on port 4825, routes, form handling, pre-filled defaults |
| `ixbrl.py` | iXBRL document generator (FRS-102 taxonomy 2024, uk-bus/uk-core prefixes) |
| `govtalk.py` | GovTalk v1.0 envelope builder with CHMD5 auth and FormSubmission body |
| `gateway.py` | HTTP client: submit, poll (GetSubmissionStatus), acknowledge (GetStatusAck) |
| `start.sh` | Instance-agnostic startup script |
| `templates/` | Jinja2 templates: form, preview, status, setup guide (all extend base.html) |

### Pages

| URL | What it does |
|-----|-------------|
| `/` | Input form (pre-filled with company defaults) |
| `/preview` | Validates and shows balance sheet summary |
| `/ixbrl` | Raw iXBRL document (for inspection) |
| `/envelope` | Full GovTalk XML envelope (for inspection) |
| `/file` | Submits to CH gateway |
| `/status` | Shows submission result, poll/acknowledge buttons |
| `/setup` | Setup guide for Presenter ID registration |
| `/submissions` | Submission history |

---

## How We Got Here — Development Timeline (12 March 2026)

The application was developed and tested against the live Companies House XML Gateway in a single day, working directly with **Karolina** (Relationship Manager, Companies House XML Gateway team).

### The Process

1. **Requested a test account** by emailing xml@companieshouse.gov.uk with name, address, email, and phone number (per the [technical interface specifications](https://www.gov.uk/government/publications/technical-interface-specifications-for-companies-house-software/important-information-for-software-developers-read-first))

2. **Received test credentials** from Karolina within hours:
   - Test Presenter ID: `66666533000`
   - Authentication Value: `8VOFKGTEH5M`
   - Test Flag: `1`
   - Test Package Reference: `0012`

3. **Encountered and resolved a 502 Authorisation Failure**. Key lessons learned from Karolina's guidance:
   - The `md5#` prefix must NOT be included in the SenderID or Value fields — just the raw MD5 hash
   - Test submissions must use **dummy company data** (8-digit company number, 6-character auth code), not real company details
   - Submission numbers must be **unique and incremental** — non-unique numbers result in immediate rejection

4. **First successful test submission accepted** — Karolina reviewed and confirmed all business rules passed. She recommended improving the iXBRL rendering:
   - Hidden notes at the top of the document should not be visible
   - Information should be properly structured and spread across separate pages
   - Referenced the Companies House micro-entity account examples for expected layout standards

5. **Second submission accepted** after layout improvements based on her feedback. Karolina confirmed: *"the micro-entity accounts now look much better and have been successfully accepted"*

6. **Next steps discussed** — Gerald asked about adding dormant accounts and confirmation statements. Karolina offered to provide direction on the relevant schemas and documentation.

### Key Technical Discoveries (from the Karolina correspondence)

These are hard-won details not obvious from the documentation:

| Detail | What We Learned |
|--------|----------------|
| **MD5 auth format** | Raw hash only — no `md5#` prefix. E.g. `<SenderID>9ea9c2343ed0cc104375c93e7990b179</SenderID>` |
| **Test data** | Use dummy company number (8 digits) and auth code (6 chars), not real company details |
| **Submission numbers** | Must be unique AND incremental — duplicates cause immediate rejection |
| **Envelope version** | 1.0 (NOT 2.0) |
| **GovTalk namespace** | `http://www.govtalk.gov.uk/schemas/govtalk/govtalkheader` (NOT CM/envelope) |
| **Class** | `Accounts` (capitalised, not uppercase) |
| **TransactionID** | Uppercase hex `[0-9A-F]`, max 32 characters |
| **FormSubmission namespace** | `http://xmlgw.companieshouse.gov.uk/Header` (v2-11 schema) |
| **iXBRL rendering** | Must follow CH micro-entity layout standards — notes hidden, properly paginated |

---

## Reference Documents

### Companies House Technical Specifications

- **[Important information for software developers - read first](https://www.gov.uk/government/publications/technical-interface-specifications-for-companies-house-software/important-information-for-software-developers-read-first)** — The primary developer guide. Covers test account setup, 502 error resolution checklist, authentication requirements, and filing procedures. This was the starting point for the entire project and was referenced throughout the email exchange with Karolina.

- **[XML Gateway Schema Status](http://xmlgw.companieshouse.gov.uk/SchemaStatus)** — Current versions of all XML Gateway input schemas, including accounts, confirmation statements, and other filing types.

- **[XML Gateway Interface Specification](https://xmlgw.companieshouse.gov.uk/iface.shtml)** — Technical details of the GovTalk envelope format and gateway interaction model.

- **[Companies House XML Gateway Forum](https://xmlforum.companieshouse.gov.uk/)** — Developer forum for XML Gateway questions, including dedicated sections for confirmation statements and accounts.

### XBRL Sample Documents (from Companies House)

These sample documents were provided by Companies House and used as reference during development:

- **`XBRLsample.pdf`** — A full XBRL instance document showing the traditional (non-inline) XBRL format. Demonstrates the complete taxonomy structure including: balance sheet items (`pt:TangibleFixedAssets`, `pt:Debtors`, etc.), accounting policies, depreciation rates, director shareholdings, equity details, creditor breakdowns, and fixed asset movement schedules. Uses the `ae:` (accounts entity) and `pt:` (primary taxonomy) namespace prefixes with context references for current and prior year periods.

- **`inlineXBRLsample.pdf`** — An inline XBRL (iXBRL) document showing the format our application generates. This is an HTML page with embedded XBRL tags (`ix:nonNumeric`, `ix:nonFraction`) that is both human-readable in a browser and machine-parseable by XBRL processors. Shows the dormant company accounts layout including: title page, balance sheet with `ix:nonFraction` tagged figures, statutory statements (section 480 exemption, audit exemption, directors' responsibilities, small companies regime), and board approval section. Uses `uk-gaap-cd-bus:` and `uk-gaap-pt:` namespace prefixes. This was the primary format reference for our iXBRL generator.

### Companies House Contacts

| Purpose | Contact |
|---------|---------|
| XML Gateway test accounts and technical queries | xml@companieshouse.gov.uk |
| General customer care | customercare@companieshouse.gov.uk |
| Credit account applications | chdfinance@companieshouse.gov.uk |
| Changes to UK company law updates | https://changestoukcompanylaw.campaign.gov.uk/changes-at-a-glance/ |
| Companies House email updates | https://public.govdelivery.com/accounts/UKCH/subscriber/new |

---

## The Balance Sheet (Reference)

These numbers have been the same every year for this company:

| Line | Amount |
|------|--------|
| Fixed Assets | 20,199 |
| Current Assets | -- |
| Net current assets | 0 |
| Total assets less current liabilities | 20,199 |
| Creditors: due after 1 year | (20,193) |
| Provisions | 0 |
| Accruals & deferred income | 0 |
| **Net assets** | **6** |
| **Capital and reserves** | **6** |

Average employees: 0 (both years). If the numbers ever change, update them in the form.

---

## Quick Start

```bash
export CH_PRESENTER_ID="your_presenter_id"
export CH_PRESENTER_AUTH="your_presenter_auth_code"
./start.sh
```

Open **http://localhost:4825** in your browser.

The app defaults to **test mode** (`GatewayTest=1`). Set `CH_ENVIRONMENT=live` for real filings.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CH_PRESENTER_ID` | _(none)_ | Your Companies House presenter ID |
| `CH_PRESENTER_AUTH` | _(none)_ | Your presenter authentication code |
| `CH_ENVIRONMENT` | `test` | Set to `live` for real filings |
| `CH_GATEWAY_URL` | `https://xmlgw.companieshouse.gov.uk/v1-0/xmlgw/Gateway` | Override only if CH changes the URL |
| `CH_PACKAGE_REF` | `0012` | Package reference (test=0012, live=your assigned ref) |
| `API_PORT` | `4825` | Port the app runs on |
| `SECRET_KEY` | `dev-key-change-me` | Flask session key |

---

## Filing Workflow

### Test Submission

1. Set presenter credentials and start the app
2. Fill in/confirm the form (dates, board approval date, company auth code)
3. Click **Validate & Preview** — check the balance sheet summary
4. Click **View iXBRL Document** — verify it looks like proper accounts
5. Click **Submit Filing** — sends to CH in test mode
6. Check **Status** page — poll for gateway response

### Live Submission

```bash
export CH_ENVIRONMENT=live
export CH_PRESENTER_ID="your_id"
export CH_PRESENTER_AUTH="your_auth"
export CH_PACKAGE_REF="your_live_package_ref"
./start.sh
```

Same flow as test. The only difference is `GatewayTest` will be `0`.

### After Submitting

Companies House processes submissions asynchronously (up to 5 working days):

| Status | Meaning |
|--------|---------|
| **PENDING** | Still processing, check back later |
| **ACCEPT** | Filed successfully |
| **REJECT** | Rejected — check the rejection reason and resubmit |
| **PARKED** | Set aside for manual review by CH |

---

## Opportunity: SaaS Filing Platform

### The Market

- **~4.9 million** active companies on the UK Companies House register
- **~96%** qualify as micro-entities (~4.7 million companies)
- Every company must file annual accounts — every year, without exception
- The free HMRC/Companies House joint filing portal (CATO) **shuts down 31 March 2026**
- Under ECCTA 2023, mandatory software-only iXBRL filing for accounts is planned (originally April 2027, currently under review with 21-month notice commitment)

This is a massive forced migration. Millions of directors who currently use a free government form will need commercial software.

### Competitor Landscape

| Provider | Price | Notes |
|----------|-------|-------|
| TinyTax | £20-50/yr | Micro-entity focused, CT600 + CH accounts |
| TaxCalc | ~£200/yr | Full-featured, 12 returns, used by accountants |
| Microfiler | £285/filing | Accountant-assisted |
| Accountants | £300-500+ | Per filing, full service |
| Inform Direct | ~£40-100/yr | Company secretarial + filing |

A simple, focused micro-entity filing tool could charge **£25-40 per filing** or **£30-60/yr subscription**.

### Revenue Potential

| Customers | Price/yr | Annual Revenue |
|-----------|----------|---------------|
| 1,000 | £30 | £30K |
| 10,000 | £30 | £300K |
| 50,000 | £40 | £2M |
| 100,000 | £40 | £4M |

At typical SaaS valuations of 5-10x ARR, even modest traction would value the platform at **£1.5M-£40M**.

### What We'd Need to Build

**Phase 1 — Multi-company accounts filing:**
- Multi-tenant support (arbitrary companies, not hardcoded)
- User authentication and Stripe billing
- Dormant company accounts (simplest filing type, huge segment)

**Phase 2 — Full annual compliance:**
- Confirmation statements (CS01) via XML Gateway — same GovTalk envelope, different body schema. Karolina has offered guidance on the relevant schemas
- CT600 corporation tax returns via HMRC (the killer feature — bundling accounts + tax)

**Phase 3 — Extended filing types:**
- Small company accounts (larger balance sheet, more detail)
- LLP accounts
- Company changes (registered office, directors, PSCs)

### Competitive Advantages

1. **Regulatory tailwind** — the government is forcing every company onto software
2. **Simplicity** — most micro-entity directors want to click a button once a year, not learn TaxCalc
3. **Low cost to serve** — filing is just XML over HTTP, minimal infrastructure
4. **Sticky revenue** — companies must file every year, churn is naturally low
5. **Existing gateway integration** — we already have working, CH-approved XML Gateway code
6. **Direct relationship with CH XML team** — Karolina has reviewed and accepted our submissions

---

## Planning: Taking This to Production

This section captures the architectural decisions and trade-offs considered before building out the product. Two approaches were evaluated: a full SaaS with user accounts, and a simpler stateless filing service.

### Decision 1: Stateless Filing vs Full SaaS

#### Option A — Stateless Filing Service (recommended starting point)

The simplest viable product. No user accounts, no database, no stored data:

```
User visits site
    → enters company details + balance sheet figures
        → pays via Stripe Checkout (£25-35)
            → app generates iXBRL + GovTalk envelope
                → submits to CH gateway
                    → shows confirmation + transaction ID
                        → user leaves
                            → nothing stored
```

What this eliminates:

| No longer needed | Why |
|------------------|-----|
| User accounts + login | No data to protect behind auth |
| PostgreSQL database | Nothing to store |
| Django ORM + migrations | No models |
| Password reset flows | No passwords |
| GDPR data subject requests | You don't hold personal data |
| Database backups | No database |
| Encrypted credential storage | User enters presenter creds each time |

The user fills in a form, pays, it files, they get a transaction ID. Companies House has the record. There is no need to keep a copy.

**Handling the status poll:** Companies House doesn't give instant accept/reject. The user gets a transaction ID and can return to a `/status?txn=ABC123` page to poll CH on demand. No data stored — the app just proxies the poll request to CH in real time using the credentials they re-enter.

**What you lose vs full SaaS:**

| Feature | Stateless | Full SaaS |
|---------|-----------|-----------|
| Repeat filing convenience | User re-enters everything each year | Pre-filled from last year |
| Filing history | User keeps their own transaction IDs | Stored in their account |
| Multiple companies | File one at a time | Dashboard showing all |
| Automatic status checking | User polls manually | Email notifications |

For micro-entity directors filing once a year, the stateless model is probably fine. They spend 5 minutes, pay, file, note the transaction ID, done.

**This version could ship in days, not weeks.** The current Flask app is 90% of the way there.

#### Option B — Full SaaS with User Accounts

If the product grows and users want convenience (pre-filled forms, filing history, multiple companies), this is the upgrade path. See "Decision 2" below for the framework choice.

### Decision 2: Framework Choice (if building full SaaS)

#### Why Django over Flask (for the full SaaS)

The current app is Flask, which was the right choice for a single-company tool. For a multi-tenant SaaS, Django provides critical features out of the box that Flask requires bolting on:

| What SaaS needs | Flask | Django |
|----------------|-------|--------|
| User auth (signup, login, password reset) | Wire up Flask-Login + Flask-Mail + Flask-Security | Built in |
| Database ORM + migrations | Add SQLAlchemy + Alembic | Built in |
| Admin panel (view users, filings, debug) | Build from scratch | Built in — and excellent |
| Form validation | Add WTForms | Built in |
| CSRF protection | Add Flask-WTF | Built in |
| Session handling | Basic | Built in, database-backed |

With Flask you'd install 8-10 extensions and wire them together. Django gives all of it integrated and tested.

#### Why NOT React / Next.js / SPA

This product is form-based workflows. A user logs in, picks a company, fills in dates, clicks submit, checks back later. There is no need for a single-page app.

- Two codebases (API + frontend) means double the maintenance and deployment complexity
- Django templates with HTMX gives all needed interactivity (live validation, status polling) with 10% of the complexity
- The frontend would look modern using Tailwind CSS + daisyUI component library — the framework choice doesn't constrain the visual design at all

#### Why NOT FastAPI

FastAPI is great for building APIs, but this is a web application with forms and pages. FastAPI would require building the entire frontend separately.

#### The full SaaS stack would be:

```
Django 5.x          — web framework, auth, ORM, admin, forms
PostgreSQL           — database (users, companies, filings, submissions)
Celery + Redis       — background tasks (polling CH gateway for status)
Stripe               — billing
HTMX                 — interactivity without a JS framework
Tailwind CSS         — modern UI without writing custom CSS
gunicorn + nginx     — production serving
```

#### What moves unchanged from the current app

The three core modules are framework-agnostic Python with no Flask dependency:

- **`ixbrl.py`** — takes a dict of figures, returns iXBRL HTML string
- **`govtalk.py`** — takes credentials + iXBRL, returns XML envelope
- **`gateway.py`** — takes XML, POSTs to CH, returns result dict

These become utility modules that Django views (or Flask routes) call. The hard part is already done.

#### Django model structure (full SaaS only)

```python
User              — email, password (Django built-in)
Company           — user (FK), name, number, auth_code, sic_codes, defaults
PresenterAccount  — user (FK), presenter_id, auth_code (encrypted)
Filing            — company (FK), period_start, period_end, figures (JSON), status
Submission        — filing (FK), transaction_id, envelope_xml, response_xml,
                    status (pending/accepted/rejected), submitted_at
```

### Decision 3: Payments

#### Stripe is the right choice

Lowest fees, best developer experience, Django/Flask libraries exist, handles Apple Pay / Google Pay / cards. PCI compliant without touching card data.

| Provider | Fees | Notes |
|----------|------|-------|
| **Stripe** | 1.5% + 20p (UK cards) | Best developer experience, you handle VAT |
| GoCardless | 1% + 20p | Direct Debit, slower clearing |
| Paddle | 5% + 50p | They handle VAT — they're merchant of record |
| Lemon Squeezy | 5% + 50p | Same merchant-of-record model |

At £30 per filing, Stripe keeps £29.35. You don't need to register for VAT until £90K revenue (~3,000 filings). By then you can afford an accountant or switch to Paddle.

#### Payment model

**Pay-per-filing** is the simplest starting point. Freemium works well: let anyone fill in the form and preview the iXBRL for free. Charge only when they click "Submit to Companies House". This removes friction and lets users see the product works before paying.

#### Companies House fees

Annual accounts filing with Companies House is **free** — CH charges nothing to receive them. Confirmation statements cost **£50** (paid to CH separately). So the pricing for users is purely your software fee:

| What they pay | To whom | For what |
|---------------|---------|----------|
| £0 | Companies House | Accounts filing (free) |
| £50 | Companies House | Confirmation statement fee (if applicable) |
| £25-35 | Your app | Software fee to generate and file |

For the XML Gateway, CH fees for fee-bearing filings (like confirmation statements) are charged via a **Companies House credit account** linked to the presenter ID — not by card at time of filing. Each user would need their own presenter account with CH, and CH invoices them monthly.

### Decision 4: Hosting

#### Railway (recommended)

Fully managed platform. No server security to handle — they manage SSL, OS patches, DDoS protection, firewall rules, and database backups. You just `git push` and it deploys.

| Concern | Railway | DIY on a VPS |
|---------|---------|-------------|
| SSL certificates | Automatic | You set up Let's Encrypt |
| OS security patches | They handle it | You run updates |
| DDoS protection | Built in | You configure it |
| Database backups | Automatic | You set up cron jobs |
| Firewall rules | Managed | You configure them |
| Zero-day vulnerabilities | Their problem | Your problem at 2am |
| Deployment | `git push` | You manage deploy scripts |

Cost: ~$15/month (app $5 + PostgreSQL $5 + Redis $5). Cheaper than DigitalOcean's managed equivalent (~$42/month).

#### Data location: Amsterdam is fine

Railway's European region is Amsterdam (Netherlands). There is no UK data centre. However:

- The UK and EU have mutual **data adequacy decisions** (renewed December 2025, valid until 2031)
- Data flows freely between UK and Netherlands — no legal issue
- The data being stored (company names, numbers, balance sheet figures) is **public information on the Companies House register** anyway
- Privacy policy simply states: *"Data is hosted in the European Economic Area (Netherlands) in compliance with UK GDPR and the EU-UK adequacy decision"*

If using the stateless model, this is even less of a concern — you're not storing any data at all.

#### Alternatives considered

| Provider | UK data centre? | Notes |
|----------|----------------|-------|
| DigitalOcean | Yes (London) | App Platform ~$42/month, or DIY droplet ~$6/month |
| Railway | No (Amsterdam) | Fully managed, ~$15/month |
| AWS | Yes (London) | Overkill for this stage |
| Hetzner | No (Germany) | Cheap VPS but no UK region, DIY security |

#### For the stateless model, Railway is ideal

No database to manage, minimal infrastructure, auto-deploys on push. The app is essentially just Flask + Stripe + the three core modules.

### Decision 5: Build Locally, Deploy When Ready

Development happens on the current local machine. The entire app is code in a git repo. Deploying is pushing that repo to a host:

```
1. Build locally              ← localhost, iterate and test
2. Push to GitHub             ← private repo (already set up)
3. Connect Railway            ← auto-deploys on push to main
4. Point a domain at it       ← e.g. filemyaccounts.co.uk
5. Add Stripe live keys       ← switch from test to live
6. Go live
```

Everything transfers automatically — Django/Flask code, templates, core modules. Environment variables (credentials, Stripe keys) are set on the host, not in code.

### Recommended Path Forward

**Start with the stateless Flask model.** It's the fastest to ship and the current codebase is almost there:

1. Remove hardcoded company defaults — make the form blank for any company
2. Add presenter credentials fields to the form
3. Add Stripe Checkout before the submit step
4. Add a status-check page that takes a transaction ID and polls CH on demand
5. Style with Tailwind CSS for a modern look
6. Deploy to Railway

If traction proves the market, upgrade to the full Django SaaS with user accounts, pre-filled forms, filing history, and additional filing types (dormant accounts, confirmation statements, CT600).

### Filing Types to Add

#### Confirmation Statements (CS01)

Can be filed via the same XML Gateway using the `ConfirmationStatement-v1-3` or `ConfirmationAndVerificationStatement-v1-0` schema. Uses the same GovTalk envelope, same auth, same poll/acknowledge cycle — only the body changes. For a simple "no changes" filing (the majority of micro-entities year to year), the XML payload is much simpler than iXBRL accounts. Karolina at Companies House has offered to provide guidance on the relevant schemas. Note: confirmation statements are not subject to the mandatory software-only filing requirement — they can still be filed via WebFiling.

#### Dormant Company Accounts

The simplest accounts filing type. Huge segment of the market. Same iXBRL format but with minimal figures (typically just share capital). The `inlineXBRLsample.pdf` reference document shows exactly this format.

#### CT600 Corporation Tax Returns (future)

Filed with HMRC (not Companies House) but this is the killer feature. The free CATO joint filing portal shuts down 31 March 2026, forcing every company onto commercial software for CT600 filing. Bundling accounts + tax return would be the strongest product offering.

---

## Getting a Presenter ID (First-Time Setup)

### Step 1: Request a test account

Email **xml@companieshouse.gov.uk** with your name, organisation, address (including postcode), email, and phone number. Reference the [technical interface specifications](https://www.gov.uk/government/publications/technical-interface-specifications-for-companies-house-software/important-information-for-software-developers-read-first).

They'll reply within a few working days with test credentials.

### Step 2: Test your filing

Use the test credentials to submit a test. Then email xml@companieshouse.gov.uk to tell them your test is ready for review.

### Step 3: Get live credentials

**For accounts-only filing** — apply online (near-instant):
https://find-and-update.company-information.service.gov.uk/presenter-account

**For fee-bearing filings** — credit account form:
https://www.gov.uk/government/publications/apply-for-a-companies-house-credit-account

### Credential Format

| Credential | Format |
|-----------|--------|
| Presenter ID | 11 chars. Starts/ends with `000` (credit) or starts with `E` + 10 digits (presenter-only) |
| Presenter Auth | 11 chars, uppercase letters + numbers |
| Company Auth | 6 chars, alphanumeric. Posted to registered office annually |

---

## Troubleshooting

**502 Authorisation Failure** — The most common error during development. Check:
- SenderID and Value contain raw MD5 hashes (no `md5#` prefix)
- Method is `clear`
- Test flag is `1` for test submissions
- Package reference is `0012` for test
- Presenter ID and auth code are correct

**Submission rejected as duplicate** — Submission numbers must be unique and incremental. The app tracks these in `.submission_number`.

**Balance sheet does not balance** — Net assets must equal capital and reserves.

**iXBRL rendering feedback** — CH expects properly structured pages: title page, balance sheet, notes/statements. Hidden elements should not be visible. Review the Companies House micro-entity examples for expected layout.
