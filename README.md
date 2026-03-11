# app_gov — Companies House Annual Accounts Filing

Files micro-entity accounts for **CORSICA STREET 567 LIMITED** (10303807) directly to the Companies House XML Gateway.

You use this once a year. These instructions assume you've forgotten everything since last time.

---

## Quick Start

```bash
./start.sh
```

Open **http://localhost:4825** in your browser.

---

## What This App Does

1. You enter (or confirm) the balance sheet figures
2. It generates an iXBRL document (the legally required format)
3. It wraps that in a GovTalk XML envelope (the gateway's required wrapper)
4. It submits the package to the Companies House XML Gateway
5. You poll for the result (accept/reject) over the following days

The numbers for this company don't change year to year. The form comes pre-filled. You mainly just need to:
- Update the **accounting period dates** (e.g. 2026-08-01 to 2027-07-31)
- Set the **board approval date**
- Enter the **company authentication code**

---

## Before You File: Checklist

### 1. Check your credentials are set

You need three things:

| What | Where to get it | Env var |
|------|----------------|---------|
| **Presenter ID** | Companies House software filing registration | `CH_PRESENTER_ID` |
| **Presenter auth code** | Same registration | `CH_PRESENTER_AUTH` |
| **Company auth code** | Companies House sends this to the registered office annually | Entered in the form |

Set the presenter credentials before starting:

```bash
export CH_PRESENTER_ID="your_presenter_id"
export CH_PRESENTER_AUTH="your_presenter_auth_code"
./start.sh
```

If you haven't registered as a software filer yet, see the **Getting a Presenter ID** section below, or visit the **Setup Guide** page in the app (`/setup`).

### 2. Verify the gateway URL is reachable

The app submits to:

```
https://xmlgw.companieshouse.gov.uk/v1-0/xmlgw/Gateway
```

This is the **real, live** Companies House XML Gateway. All software filers use this same URL. You can verify it's up:

```bash
curl -s -o /dev/null -w "%{http_code}" https://xmlgw.companieshouse.gov.uk/v1-0/xmlgw/Gateway
```

You should get a response (likely `200` or `405`). If you get a connection error, check your internet.

### 3. Do a test submission first

The app defaults to **test mode**. When `CH_ENVIRONMENT` is not set to `live`, every submission includes `<GatewayTest>1</GatewayTest>` in the envelope, which tells Companies House this is a test — it won't be filed for real.

**Always do a test submission before your real one:**

```bash
# Test mode (default)
export CH_PRESENTER_ID="your_id"
export CH_PRESENTER_AUTH="your_auth"
./start.sh
```

1. Fill in the form, click **Validate & Preview**
2. Check the balance sheet summary is correct
3. Click **View iXBRL Document** — it should look like proper accounts
4. Click **View GovTalk Envelope** — verify the XML looks sane
5. Click **Submit Filing** — this sends to CH in test mode
6. Check the **Status** page for the gateway response

If the test comes back with no errors, you're ready for live.

### 4. Submit for real

```bash
export CH_ENVIRONMENT=live
export CH_PRESENTER_ID="your_id"
export CH_PRESENTER_AUTH="your_auth"
./start.sh
```

Then go through the same flow. The only difference is `GatewayTest` will be `0`.

---

## After Submitting

Companies House processes submissions **asynchronously**. It can take up to 5 working days.

1. Go to the **Status** page
2. Click **Poll for Status**
3. Possible results:
   - **PENDING** — still processing, check back later
   - **ACCEPT** — filed successfully
   - **REJECT** — rejected, check the rejection reason
   - **PARKED** — set aside for manual review by CH

If rejected, fix the issue and resubmit.

---

## The Balance Sheet (Reference)

These numbers have been the same every year:

| Line | Amount |
|------|--------|
| Fixed Assets | 20,199 |
| Current Assets | — |
| Net current assets | 0 |
| Total assets less current liabilities | 20,199 |
| Creditors: due after 1 year | (20,193) |
| Provisions | 0 |
| Accruals & deferred income | 0 |
| **Net assets** | **6** |
| **Capital and reserves** | **6** |

Average employees: 0 (both years)

If the numbers ever do change, just update them in the form.

---

## Pages

| URL | What it does |
|-----|-------------|
| `/` | Input form (pre-filled) |
| `/preview` | Validates and shows summary |
| `/ixbrl` | Raw iXBRL document (for inspection) |
| `/envelope` | Full GovTalk XML envelope (for inspection) |
| `/file` | Submits to CH gateway |
| `/status` | Shows submission result, poll button |
| `/setup` | Setup guide — how to get a Presenter ID |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CH_PRESENTER_ID` | _(none)_ | Your Companies House presenter ID |
| `CH_PRESENTER_AUTH` | _(none)_ | Your presenter authentication code |
| `CH_ENVIRONMENT` | `test` | Set to `live` for real filings |
| `CH_GATEWAY_URL` | `https://xmlgw.companieshouse.gov.uk/v1-0/xmlgw/Gateway` | Override only if CH changes the URL |
| `API_PORT` | `4825` | Port the app runs on |
| `SECRET_KEY` | `dev-key-change-me` | Flask session key |

---

## Getting a Presenter ID (First-Time Setup)

You need a Presenter ID and Authentication Code to submit filings. This is a one-time registration process.

### Step 1: Request a test account

Email **xml@companieshouse.gov.uk** with:
- Your name / organisation name
- Contact name
- Address
- Email address
- Phone number

They'll reply within a few working days with test credentials. Before emailing, you should have read the [technical interface specifications](https://www.gov.uk/government/publications/technical-interface-specifications-for-companies-house-software/important-information-for-software-developers-read-first) (this app already implements them).

### Step 2: Test your filing

Use the test credentials to do a test submission (the app defaults to test mode). Then email xml@companieshouse.gov.uk to tell them your test is ready for their review.

### Step 3: Get live credentials

Once testing is approved, apply for a live presenter account:

**For accounts-only filing (our case)** — apply online, near-instant:
https://find-and-update.company-information.service.gov.uk/presenter-account

- Sign in or create a Companies House account
- Provide name, address, business name or company number
- **Tick "software filing"** when asked
- Credentials issued almost immediately

**For fee-bearing filings (not needed for accounts)** — credit account form:
https://www.gov.uk/government/publications/apply-for-a-companies-house-credit-account
Email to chdfinance@companieshouse.gov.uk, takes up to 5 working days.

### Credential format

| Credential | Format |
|-----------|--------|
| Presenter ID | 11 chars. Starts/ends with `000` (credit) or starts with `E` + 10 digits (presenter-only) |
| Presenter Auth | 11 chars, uppercase letters + numbers (e.g. `AC75D45JUQA`) |
| Company Auth | 6 chars, alphanumeric. Posted to registered office annually |

### Key contacts

| Purpose | Email |
|---------|-------|
| Test accounts & XML technical queries | xml@companieshouse.gov.uk |
| Credit account applications | chdfinance@companieshouse.gov.uk |
| General enquiries | https://www.gov.uk/contact-companies-house |

The app also has a detailed **Setup Guide** page at `/setup` with all of this information.

---

## Troubleshooting

**"Presenter credentials not configured"** — Set `CH_PRESENTER_ID` and `CH_PRESENTER_AUTH` env vars before starting.

**"Balance sheet does not balance"** — Net assets must equal capital and reserves. Check your figures.

**Gateway returns errors** — Check the raw response on the Status page. Common issues:
- Invalid company auth code
- Wrong company number format (must be 8 chars)
- Schema validation failure in the iXBRL

**Can't reach the gateway** — Run the curl check above. The URL hasn't changed in years, but verify.

---

## How It Works (Technical)

The app generates an **iXBRL** (inline XBRL) document — this is an HTML page with embedded XBRL tags using the FRC FRS-102 taxonomy (which covers FRS 105 micro-entities). It then wraps that document (base64-encoded) inside a **GovTalk XML envelope** with a `FormSubmission` body, and POSTs it to the Companies House XML Gateway. Authentication uses CHMD5 (MD5 hashes of your presenter credentials).

This is the same mechanism that commercial filing software (FreeAgent, Xero, etc.) uses.
