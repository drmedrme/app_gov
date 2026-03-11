"""iXBRL generator for micro-entity accounts (FRS 105).

Generates an inline XBRL document using the FRC FRS-102 taxonomy
(FRS 105 micro-entities use a subset of FRS 102).

iXBRL 1.0 namespace: http://www.xbrl.org/2008/inlineXBRL
Entity scheme: http://www.companieshouse.gov.uk/
Taxonomy prefixes: uk-bus, uk-core
"""

from lxml import etree

# Taxonomy year — update when new taxonomy suite is required
TAXONOMY_YEAR = "2024-01-01"
SCHEMA_HREF = f"https://xbrl.frc.org.uk/FRS-102/{TAXONOMY_YEAR}/FRS-102-{TAXONOMY_YEAR}.xsd"

# Namespaces
H = "{http://www.w3.org/1999/xhtml}"
IX = "{http://www.xbrl.org/2008/inlineXBRL}"
XBRLI = "{http://www.xbrl.org/2003/instance}"
LINK = "{http://www.xbrl.org/2003/linkbase}"
XLINK = "{http://www.w3.org/1999/xlink}"

NSMAP = {
    None: "http://www.w3.org/1999/xhtml",
    "ix": "http://www.xbrl.org/2008/inlineXBRL",
    "xbrli": "http://www.xbrl.org/2003/instance",
    "xbrldi": "http://xbrl.org/2006/xbrldi",
    "link": "http://www.xbrl.org/2003/linkbase",
    "xlink": "http://www.w3.org/1999/xlink",
    "iso4217": "http://www.xbrl.org/2003/iso4217",
    "ixt": "http://www.xbrl.org/inlineXBRL/transformation/2010-04-20",
    "uk-bus": f"http://xbrl.frc.org.uk/cd/{TAXONOMY_YEAR}/business",
    "uk-core": f"http://xbrl.frc.org.uk/fr/{TAXONOMY_YEAR}/core",
    "uk-direp": f"http://xbrl.frc.org.uk/reports/{TAXONOMY_YEAR}/direp",
    "uk-geo": f"http://xbrl.frc.org.uk/cd/{TAXONOMY_YEAR}/countries",
}

# Context IDs
CTX_CUR = "current-period-end"
CTX_PRI = "prior-period-end"
CTX_DUR = "current-period"
CTX_PRI_DUR = "prior-period"


def generate_ixbrl(a: dict) -> str:
    """Generate iXBRL from accounts dict. Returns UTF-8 XML string."""

    root = etree.Element(f"{H}html", nsmap=NSMAP)

    # HEAD
    head = _el(root, "head")

    # ix:header goes inside <head> per iXBRL spec
    ix_header = etree.SubElement(head, f"{IX}header")

    # References
    ix_refs = etree.SubElement(ix_header, f"{IX}references")
    etree.SubElement(
        ix_refs, f"{LINK}schemaRef",
        {f"{XLINK}type": "simple", f"{XLINK}href": SCHEMA_HREF},
    )

    # Resources (contexts and units)
    resources = etree.SubElement(ix_header, f"{IX}resources")

    _ctx_instant(resources, CTX_CUR, a["company_number"], a["period_end"])
    if a.get("prior_period_end"):
        _ctx_instant(resources, CTX_PRI, a["company_number"], a["prior_period_end"])
    _ctx_duration(resources, CTX_DUR, a["company_number"], a["period_start"], a["period_end"])
    if a.get("prior_period_end"):
        # Prior period duration
        _ctx_duration(resources, CTX_PRI_DUR, a["company_number"],
                      _prior_start(a["period_start"]), a["prior_period_end"])

    # Units
    unit_gbp = etree.SubElement(resources, f"{XBRLI}unit", id="GBP")
    m = etree.SubElement(unit_gbp, f"{XBRLI}measure")
    m.text = "iso4217:GBP"

    unit_pure = etree.SubElement(resources, f"{XBRLI}unit", id="pure")
    mp = etree.SubElement(unit_pure, f"{XBRLI}measure")
    mp.text = "xbrli:pure"

    title = _el(head, "title")
    title.text = f"Accounts - {a['company_name']}"
    style = _el(head, "style")
    style.text = CSS

    # BODY
    body = _el(root, "body")

    # Hidden tagged facts
    hidden_div = _el(body, "div", style="display:none")
    _nonnumeric(hidden_div, "uk-bus:EntityCurrentLegalOrRegisteredName", CTX_DUR, a["company_name"])
    _nonnumeric(hidden_div, "uk-bus:UKCompaniesHouseRegisteredNumber", CTX_DUR, a["company_number"])
    _nonnumeric(hidden_div, "uk-bus:StartDateForPeriodCoveredByReport", CTX_DUR, a["period_start"])
    _nonnumeric(hidden_div, "uk-bus:EndDateForPeriodCoveredByReport", CTX_DUR, a["period_end"])
    _nonnumeric(hidden_div, "uk-bus:BalanceSheetDate", CTX_DUR, a["period_end"])
    _nonnumeric(hidden_div, "uk-bus:AccountsStatusAuditedOrUnaudited", CTX_DUR, "Unaudited")
    _nonnumeric(hidden_div, "uk-bus:AccountingStandardsApplied", CTX_DUR, "Micro-entities")
    _nonnumeric(hidden_div, "uk-bus:LegalFormOfEntity", CTX_DUR, "Private Limited Company")
    _nonnumeric(hidden_div, "uk-bus:DateApprovalAccounts", CTX_DUR, a.get("approval_date", ""))
    _nonnumeric(hidden_div, "uk-bus:NameEntityOfficer", CTX_DUR, a["director_name"])
    _nonnumeric(hidden_div, "uk-bus:EntityOfficerRole", CTX_DUR, "Director")
    _nonnumeric(hidden_div, "uk-core:DirectorSigningAccounts", CTX_DUR, a["director_name"])

    # === VISIBLE DOCUMENT ===

    # Title page
    hdr = _el(body, "div", **{"class": "header-info"})
    _el(hdr, "p", text=f"Registered Number {a['company_number']}")
    _el(hdr, "h1", text=a["company_name"])
    _el(hdr, "p", text="Micro-entity Accounts")
    _el(hdr, "p", text=_fmt(a["period_end"]))

    _el(body, "div", style="page-break-before: always;")

    # Balance sheet header
    bs_hdr = _el(body, "div", **{"class": "bs-header"})
    _el(bs_hdr, "span", text=a["company_name"], **{"class": "bold"})
    _el(bs_hdr, "span", text=f"Registered Number {a['company_number']}", **{"class": "right bold"})
    _el(body, "h2", text=f"Micro-entity Balance Sheet as at {_fmt(a['period_end'])}")

    has_prior = bool(a.get("prior_period_end"))
    yr_cur = a["period_end"][:4]
    yr_pri = a["prior_period_end"][:4] if has_prior else ""

    # Balance sheet table
    table = _el(body, "table")

    # Column headers
    tr = _el(table, "tr")
    _el(tr, "td")
    _el(tr, "td", text="Notes", **{"class": "notes"})
    _el(tr, "th", text=yr_cur, **{"class": "amt"})
    if has_prior:
        _el(tr, "th", text=yr_pri, **{"class": "amt"})
    tr2 = _el(table, "tr")
    _el(tr2, "td"); _el(tr2, "td")
    _el(tr2, "td", text="\u00a3", **{"class": "amt"})
    if has_prior:
        _el(tr2, "td", text="\u00a3", **{"class": "amt"})

    # Rows
    _row(table, "Fixed Assets", "uk-core:FixedAssets", a["fixed_assets"], a.get("prior_fixed_assets"), has_prior, bold=True)
    _row(table, "Current Assets", "uk-core:CurrentAssets", a["current_assets"], a.get("prior_current_assets"), has_prior, bold=True, dash0=True)
    _row(table, "Prepayments and accrued income", None, 0, 0, has_prior, dash0=True)
    _row(table, "Net current assets (liabilities)", "uk-core:NetCurrentAssetsLiabilities", a.get("net_current_assets", 0), a.get("prior_net_current_assets", 0), has_prior, bold=True, line="top")
    _row(table, "Total assets less current liabilities", "uk-core:TotalAssetsLessCurrentLiabilities", a["total_assets_less_current_liabilities"], a.get("prior_total_assets_less_current_liabilities"), has_prior, bold=True, line="top")
    _row(table, "Creditors: amounts falling due after more than one year", "uk-core:Creditors-AmountsFallingDueAfterMoreThanOneYear", a["creditors_after_one_year"], a.get("prior_creditors_after_one_year"), has_prior, bold=True, negate=True)
    _row(table, "Provisions for liabilities", "uk-core:ProvisionsForLiabilities", a.get("provisions", 0), a.get("prior_provisions", 0), has_prior)
    _row(table, "Accruals and deferred income", "uk-core:AccrualsAndDeferredIncome", a.get("accruals_deferred_income", 0), a.get("prior_accruals_deferred_income", 0), has_prior)
    _row(table, "Total net assets (liabilities)", "uk-core:NetAssetsLiabilities", a["net_assets"], a.get("prior_net_assets"), has_prior, bold=True, line="top")
    _row(table, "Capital and reserves", "uk-core:Equity", a["capital_and_reserves"], a.get("prior_capital_and_reserves"), has_prior, bold=True, line="double")

    # Statements
    stmts = _el(body, "div", **{"class": "stmts"})
    for text in [
        f"For the year ending {_fmt(a['period_end'])} the company was entitled to exemption under section 477 of the Companies Act 2006 relating to small companies.",
        "The members have not required the company to obtain an audit in accordance with section 476 of the Companies Act 2006.",
        "The directors acknowledge their responsibilities for complying with the requirements of the Companies Act 2006 with respect to accounting records and the preparation of accounts.",
        "The accounts have been prepared in accordance with the micro-entity provisions and delivered in accordance with the provisions applicable to companies subject to the small companies regime.",
    ]:
        _el(stmts, "p", text=text)

    # Approval
    appr = _el(body, "div", **{"class": "approval"})
    _el(appr, "p", text=f"Approved by the Board on {_fmt(a.get('approval_date', ''))}")
    _el(appr, "p")
    _el(appr, "p", text="And signed on their behalf by:")
    _el(appr, "p", text=f"{a['director_name']}, Director", **{"class": "bold"})

    # Notes page
    _el(body, "div", style="page-break-before: always;")
    notes_hdr = _el(body, "div", **{"class": "bs-header"})
    _el(notes_hdr, "span", text=a["company_name"], **{"class": "bold"})
    _el(notes_hdr, "span", text=f"Registered Number {a['company_number']}", **{"class": "right bold"})
    _el(body, "h2", text=f"Notes to the Micro-entity Accounts for the period ended {_fmt(a['period_end'])}")

    _el(body, "h3", text="1    Employees")
    et = _el(body, "table", **{"class": "emp"})
    tr = _el(et, "tr")
    _el(tr, "td"); _el(tr, "th", text=yr_cur, **{"class": "amt"})
    if has_prior:
        _el(tr, "th", text=yr_pri, **{"class": "amt"})
    tr2 = _el(et, "tr")
    _el(tr2, "td", text="Average number of employees during the period")
    td = _el(tr2, "td", **{"class": "amt"})
    _num(td, "uk-bus:AverageNumberEmployeesDuringPeriod", CTX_DUR, a.get("avg_employees", 0), unit="pure")
    if has_prior:
        td2 = _el(tr2, "td", **{"class": "amt"})
        _num(td2, "uk-bus:AverageNumberEmployeesDuringPeriod", CTX_PRI_DUR, a.get("prior_avg_employees", 0), unit="pure")

    # Delivery statement
    _el(body, "p", text=(
        "This document was delivered using electronic communications and authenticated in accordance "
        "with the registrar's rules relating to electronic form, authentication and manner of delivery "
        "under section 1072 of the Companies Act 2006."
    ), **{"class": "delivery"})

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")


# --- Helpers ---

def _el(parent, tag, text=None, style=None, **attrs):
    elem = etree.SubElement(parent, f"{H}{tag}")
    if "class" in attrs:
        elem.set("class", attrs.pop("class"))
    for k, v in attrs.items():
        elem.set(k, v)
    if style:
        elem.set("style", style)
    if text:
        elem.text = text
    return elem


def _ctx_instant(parent, ctx_id, co_num, date_str):
    ctx = etree.SubElement(parent, f"{XBRLI}context", id=ctx_id)
    ent = etree.SubElement(ctx, f"{XBRLI}entity")
    ident = etree.SubElement(ent, f"{XBRLI}identifier", scheme="http://www.companieshouse.gov.uk/")
    ident.text = co_num
    per = etree.SubElement(ctx, f"{XBRLI}period")
    inst = etree.SubElement(per, f"{XBRLI}instant")
    inst.text = str(date_str)


def _ctx_duration(parent, ctx_id, co_num, start, end):
    ctx = etree.SubElement(parent, f"{XBRLI}context", id=ctx_id)
    ent = etree.SubElement(ctx, f"{XBRLI}entity")
    ident = etree.SubElement(ent, f"{XBRLI}identifier", scheme="http://www.companieshouse.gov.uk/")
    ident.text = co_num
    per = etree.SubElement(ctx, f"{XBRLI}period")
    sd = etree.SubElement(per, f"{XBRLI}startDate")
    sd.text = str(start)
    ed = etree.SubElement(per, f"{XBRLI}endDate")
    ed.text = str(end)


def _nonnumeric(parent, name, ctx, value):
    elem = etree.SubElement(parent, f"{IX}nonNumeric", name=name, contextRef=ctx)
    elem.text = str(value)


def _num(parent, name, ctx, value, unit="GBP", decimals="0"):
    elem = etree.SubElement(
        parent, f"{IX}nonFraction",
        name=name, contextRef=ctx, unitRef=unit, decimals=decimals,
        format="ixt:numdotdecimal",
    )
    elem.text = str(value)
    return elem


def _row(table, label, tag, cur, pri, has_prior, bold=False, negate=False, dash0=False, line=None):
    tr = _el(table, "tr")
    if line == "top":
        tr.set("class", "line-top")
    elif line == "double":
        tr.set("class", "line-double")

    td_l = _el(tr, "td")
    if bold:
        b = _el(td_l, "b")
        b.text = label
    else:
        td_l.text = label

    _el(tr, "td")  # notes

    cur_v = cur or 0
    td_c = _el(tr, "td", **{"class": "amt"})
    if tag:
        if dash0 and cur_v == 0:
            ix = _num(td_c, tag, CTX_CUR, 0); ix.text = "-"
        elif negate and cur_v:
            ix = _num(td_c, tag, CTX_CUR, cur_v); ix.set("sign", "-"); ix.text = f"({cur_v:,})"
        else:
            ix = _num(td_c, tag, CTX_CUR, cur_v); ix.text = f"{cur_v:,}"
    else:
        td_c.text = "-" if (dash0 and cur_v == 0) else f"{cur_v:,}"

    if has_prior:
        pri_v = pri if pri is not None else 0
        td_p = _el(tr, "td", **{"class": "amt"})
        if tag:
            if dash0 and pri_v == 0:
                ix = _num(td_p, tag, CTX_PRI, 0); ix.text = "-"
            elif negate and pri_v:
                ix = _num(td_p, tag, CTX_PRI, pri_v); ix.set("sign", "-"); ix.text = f"({pri_v:,})"
            else:
                ix = _num(td_p, tag, CTX_PRI, pri_v); ix.text = f"{pri_v:,}"
        else:
            td_p.text = "-" if (dash0 and pri_v == 0) else f"{pri_v:,}"


def _fmt(d):
    if not d:
        return ""
    try:
        parts = str(d).split("-")
        months = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
        return f"{int(parts[2])} {months[int(parts[1])-1]} {parts[0]}"
    except (IndexError, ValueError):
        return str(d)


def _prior_start(period_start: str) -> str:
    """Compute the prior period start (1 year before period_start)."""
    try:
        parts = period_start.split("-")
        return f"{int(parts[0])-1}-{parts[1]}-{parts[2]}"
    except (IndexError, ValueError):
        return period_start


CSS = """
body { font-family: "Times New Roman", Times, serif; max-width: 800px; margin: 0 auto; padding: 40px; font-size: 11pt; color: #000; }
h1 { font-size: 14pt; text-align: center; margin: 5px 0; }
h2 { font-size: 12pt; text-align: center; margin: 15px 0 10px; }
h3 { font-size: 11pt; margin: 15px 0 5px; }
.header-info { text-align: center; margin-bottom: 40px; }
.header-info p { margin: 5px 0; }
.bs-header { display: flex; justify-content: space-between; margin-bottom: 5px; }
.bold { font-weight: bold; }
.right { text-align: right; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; }
td, th { padding: 3px 8px; vertical-align: top; }
.amt { text-align: right; width: 80px; }
.notes { width: 40px; text-align: center; font-style: italic; }
.line-top td.amt { border-top: 1px solid #000; }
.line-double td.amt { border-top: 3px double #000; }
.stmts { margin-top: 20px; }
.stmts p { margin: 8px 0; }
.stmts p::before { content: "\\2022  "; }
.approval { margin-top: 20px; }
.delivery { margin-top: 30px; font-size: 10pt; }
.emp { width: auto; }
.emp td, .emp th { padding: 3px 20px 3px 0; }
"""
