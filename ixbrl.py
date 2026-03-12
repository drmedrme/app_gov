"""iXBRL generator for micro-entity accounts (FRS 105).

Generates an inline XBRL document using the FRC FRS-102 taxonomy
(FRS 105 micro-entities use a subset of FRS 102).

Structure follows the Companies House WebFiling iXBRL sample:
  - ix:header wrapped in <div class="hidden"> in <body>
  - ix:hidden for non-visible tagged facts
  - div.titlepage.accountspage.pagebreak for cover page
  - div.accountspage for balance sheet and notes pages
  - Statements as <ol> with ix:nonNumeric inline

iXBRL 1.0 namespace: http://www.xbrl.org/2008/inlineXBRL
Entity scheme: http://www.companieshouse.gov.uk/
Taxonomy prefixes: uk-bus, uk-core, uk-direp
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
    "ixt": "http://www.xbrl.org/inlineXBRL/transformation/2015-02-26",
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
    _el(head, "meta", name="generator", content="Companies House Filing App")
    meta_ct = _el(head, "meta")
    meta_ct.set("http-equiv", "Content-Type")
    meta_ct.set("content", "text/html; charset=UTF-8")

    title = _el(head, "title")
    title.text = f"Micro-Entity Accounts - {a['company_name']}"
    style = _el(head, "style")
    style.set("type", "text/css")
    style.text = CSS

    # BODY
    body = _el(root, "body")

    # ix:header wrapped in hidden div — per CH WebFiling sample pattern
    hidden_div = _el(body, "div", **{"class": "hidden"})
    ix_header = etree.SubElement(hidden_div, f"{IX}header")

    # ix:hidden — non-visible tagged facts
    ix_hidden = etree.SubElement(ix_header, f"{IX}hidden")
    _nonnumeric(ix_hidden, "uk-bus:EntityCurrentLegalOrRegisteredName", CTX_DUR, a["company_name"])
    _nonnumeric(ix_hidden, "uk-bus:UKCompaniesHouseRegisteredNumber", CTX_DUR, a["company_number"])
    _nonnumeric(ix_hidden, "uk-bus:StartDateForPeriodCoveredByReport", CTX_CUR, a["period_start"])
    _nonnumeric(ix_hidden, "uk-bus:EndDateForPeriodCoveredByReport", CTX_CUR, a["period_end"])
    _nonnumeric(ix_hidden, "uk-bus:BalanceSheetDate", CTX_CUR, a["period_end"])

    # Dimensional facts (required by CH business rules)
    _nonnumeric(ix_hidden, "uk-bus:AccountingStandardsApplied", "dim-accounting-standards", "")
    _nonnumeric(ix_hidden, "uk-bus:AccountsStatusAuditedOrUnaudited", "dim-accounts-status", "")
    _nonnumeric(ix_hidden, "uk-bus:AccountsType", "dim-accounts-type", "")
    _nonnumeric(ix_hidden, "uk-bus:EntityTradingStatus", CTX_DUR, "")
    _nonnumeric(ix_hidden, "uk-bus:EntityDormantTruefalse", CTX_DUR, "false")

    # Date of approval and director signing (uk-core)
    _nonnumeric(ix_hidden, "uk-core:DateAuthorisationFinancialStatementsForIssue", CTX_CUR, a.get("approval_date", ""))
    _nonnumeric(ix_hidden, "uk-core:DirectorSigningFinancialStatements", CTX_DUR, "")

    # Required statements (uk-direp) — also tagged inline in the visible statements section
    _nonnumeric(ix_hidden, "uk-direp:StatementThatAccountsHaveBeenPreparedInAccordanceWithProvisionsSmallCompaniesRegime", CTX_DUR,
                "The accounts have been prepared in accordance with the micro-entity provisions and delivered in accordance with the provisions applicable to companies subject to the small companies regime.")
    _nonnumeric(ix_hidden, "uk-direp:StatementThatCompanyEntitledToExemptionFromAuditUnderSection477CompaniesAct2006RelatingToSmallCompanies", CTX_DUR,
                "For the year the company was entitled to exemption under section 477 of the Companies Act 2006 relating to small companies.")
    _nonnumeric(ix_hidden, "uk-direp:StatementThatDirectorsAcknowledgeTheirResponsibilitiesUnderCompaniesAct", CTX_DUR,
                "The directors acknowledge their responsibilities for complying with the requirements of the Companies Act 2006 with respect to accounting records and the preparation of accounts.")
    _nonnumeric(ix_hidden, "uk-direp:StatementThatMembersHaveNotRequiredCompanyToObtainAnAudit", CTX_DUR,
                "The members have not required the company to obtain an audit in accordance with section 476 of the Companies Act 2006.")

    # ix:references
    ix_refs = etree.SubElement(ix_header, f"{IX}references")
    etree.SubElement(
        ix_refs, f"{LINK}schemaRef",
        {f"{XLINK}type": "simple", f"{XLINK}href": SCHEMA_HREF},
    )

    # ix:resources (contexts and units)
    resources = etree.SubElement(ix_header, f"{IX}resources")

    _ctx_instant(resources, CTX_CUR, a["company_number"], a["period_end"])
    if a.get("prior_period_end"):
        _ctx_instant(resources, CTX_PRI, a["company_number"], a["prior_period_end"])
    _ctx_duration(resources, CTX_DUR, a["company_number"], a["period_start"], a["period_end"])
    if a.get("prior_period_end"):
        _ctx_duration(resources, CTX_PRI_DUR, a["company_number"],
                      _prior_start(a["period_start"]), a["prior_period_end"])

    # Dimensional contexts for required hypercube elements
    BUS_NS = f"http://xbrl.frc.org.uk/cd/{TAXONOMY_YEAR}/business"
    _ctx_dim_duration(resources, "dim-accounting-standards", a["company_number"],
                      a["period_start"], a["period_end"],
                      BUS_NS, "AccountingStandardsDimension", "Micro-entities")
    _ctx_dim_duration(resources, "dim-accounts-status", a["company_number"],
                      a["period_start"], a["period_end"],
                      BUS_NS, "AccountsStatusDimension", "AuditExempt-NoAccountantsReport")
    _ctx_dim_duration(resources, "dim-accounts-type", a["company_number"],
                      a["period_start"], a["period_end"],
                      BUS_NS, "AccountsTypeDimension", "FullAccounts")

    # Units
    unit_gbp = etree.SubElement(resources, f"{XBRLI}unit", id="GBP")
    m = etree.SubElement(unit_gbp, f"{XBRLI}measure")
    m.text = "iso4217:GBP"

    unit_pure = etree.SubElement(resources, f"{XBRLI}unit", id="pure")
    mp = etree.SubElement(unit_pure, f"{XBRLI}measure")
    mp.text = "xbrli:pure"

    # === VISIBLE DOCUMENT ===

    has_prior = bool(a.get("prior_period_end"))
    yr_cur = a["period_end"][:4]
    yr_pri = a["prior_period_end"][:4] if has_prior else ""

    # --- PAGE 1: Title/Cover page ---
    cover = _el(body, "div", **{"class": "titlepage accountspage pagebreak"})
    _el(cover, "p", text=f"Registered Number {a['company_number']}")
    _el(cover, "p", text=a["company_name"])
    _el(cover, "p", text="Unaudited Micro-Entity Accounts")
    _el(cover, "p", text=_fmt(a["period_end"]))

    # --- PAGE 2: Balance Sheet ---
    bs_page = _el(body, "div", **{"class": "accountspage"})

    # Page header
    pg_hdr = _el(bs_page, "div", **{"class": "accountsheader"})
    h2 = _el(pg_hdr, "h2")
    h2.text = a["company_name"] + " "
    span_right = _el(h2, "span", text=f"Registered Number {a['company_number']}", **{"class": "right"})

    # Balance sheet
    bs_div = _el(bs_page, "div", id="balancesheet")
    _el(bs_div, "h2", text=f"Micro-Entity Balance Sheet as at {_fmt(a['period_end'])}", **{"class": "middle"})

    table = _el(bs_div, "table")

    # Column headers
    tr = _el(table, "tr")
    _el(tr, "th")
    _el(tr, "th", text=yr_cur, **{"class": "figure"})
    if has_prior:
        _el(tr, "th", text=yr_pri, **{"class": "figure"})
    tr2 = _el(table, "tr")
    _el(tr2, "th")
    _el(tr2, "th", text="\u00a3", **{"class": "figure"})
    if has_prior:
        _el(tr2, "th", text="\u00a3", **{"class": "figure"})

    # Balance sheet rows
    _row(table, "Fixed Assets", "uk-core:FixedAssets", a["fixed_assets"], a.get("prior_fixed_assets"), has_prior, bold=True)
    _row(table, "Current Assets", "uk-core:CurrentAssets", a["current_assets"], a.get("prior_current_assets"), has_prior, bold=True, dash0=True)
    _row(table, "Prepayments and accrued income", None, 0, 0, has_prior, dash0=True, indent=True)
    _row(table, "Net current assets (liabilities)", "uk-core:NetCurrentAssetsLiabilities", a.get("net_current_assets", 0), a.get("prior_net_current_assets", 0), has_prior, bold=True, line="top")
    _row(table, "Total assets less current liabilities", "uk-core:TotalAssetsLessCurrentLiabilities", a["total_assets_less_current_liabilities"], a.get("prior_total_assets_less_current_liabilities"), has_prior, bold=True, line="top")
    _row(table, "Creditors: amounts falling due after more than one year", "uk-core:Creditors", a["creditors_after_one_year"], a.get("prior_creditors_after_one_year"), has_prior, negate=True, indent=True)
    _row(table, "Provisions for liabilities", "uk-core:Provisions", a.get("provisions", 0), a.get("prior_provisions", 0), has_prior, indent=True)
    _row(table, "Accruals and deferred income", "uk-core:AccruedLiabilitiesDeferredIncome", a.get("accruals_deferred_income", 0), a.get("prior_accruals_deferred_income", 0), has_prior, indent=True)
    _row(table, "Total net assets (liabilities)", "uk-core:NetAssetsLiabilities", a["net_assets"], a.get("prior_net_assets"), has_prior, bold=True, line="top")
    _row(table, "Capital and reserves", "uk-core:Equity", a["capital_and_reserves"], a.get("prior_capital_and_reserves"), has_prior, bold=True, line="total")

    # Statements — ordered list per CH sample
    stmts_div = _el(bs_page, "div", id="statements")
    _el(stmts_div, "h3", text="STATEMENTS")
    ol = _el(stmts_div, "ol")
    for text in [
        f"For the year ending {_fmt(a['period_end'])} the company was entitled to exemption under section 477 of the Companies Act 2006 relating to small companies.",
        "The members have not required the company to obtain an audit in accordance with section 476 of the Companies Act 2006.",
        "The directors acknowledge their responsibilities for complying with the requirements of the Companies Act 2006 with respect to accounting records and the preparation of accounts.",
        "The accounts have been prepared in accordance with the micro-entity provisions and delivered in accordance with the provisions applicable to companies subject to the small companies regime.",
    ]:
        _el(ol, "li", text=text)

    # Approval
    appr_div = _el(bs_page, "div", id="approval")
    _el(appr_div, "p", text=f"Approved by the Board on {_fmt(a.get('approval_date', ''))}")
    p_sign = _el(appr_div, "p", text="And signed on their behalf by:")
    etree.SubElement(p_sign, f"{H}br")
    span_officer = _el(p_sign, "span", text=f"{a['director_name']}, Director", **{"class": "officername"})

    # --- PAGE 3: Notes ---
    _el(body, "div", **{"class": "pagebreak"})
    notes_page = _el(body, "div", **{"class": "accountspage"})

    pg_hdr2 = _el(notes_page, "div", **{"class": "accountsheader"})
    h2n = _el(pg_hdr2, "h2")
    h2n.text = a["company_name"] + " "
    _el(h2n, "span", text=f"Registered Number {a['company_number']}", **{"class": "right"})

    _el(notes_page, "h2", text=f"Notes to the Micro-Entity Accounts for the Year Ended {_fmt(a['period_end'])}", **{"class": "middle"})

    _el(notes_page, "h3", text="1    Employees")
    et = _el(notes_page, "table", **{"class": "emp"})
    tr = _el(et, "tr")
    _el(tr, "td"); _el(tr, "th", text=yr_cur, **{"class": "figure"})
    if has_prior:
        _el(tr, "th", text=yr_pri, **{"class": "figure"})
    tr2 = _el(et, "tr")
    _el(tr2, "td", text="Average number of employees during the period")
    td = _el(tr2, "td", **{"class": "figure"})
    _num(td, "uk-core:AverageNumberEmployeesDuringPeriod", CTX_DUR, a.get("avg_employees", 0), unit="pure")
    if has_prior:
        td2 = _el(tr2, "td", **{"class": "figure"})
        _num(td2, "uk-core:AverageNumberEmployeesDuringPeriod", CTX_PRI_DUR, a.get("prior_avg_employees", 0), unit="pure")

    # Delivery statement
    _el(notes_page, "p", text=(
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


def _ctx_dim_duration(parent, ctx_id, co_num, start, end, dim_ns, dim_name, member_name):
    """Create a duration context with an explicit dimension member in the segment."""
    XBRLDI = "{http://xbrl.org/2006/xbrldi}"
    ctx = etree.SubElement(parent, f"{XBRLI}context", id=ctx_id)
    ent = etree.SubElement(ctx, f"{XBRLI}entity")
    ident = etree.SubElement(ent, f"{XBRLI}identifier", scheme="http://www.companieshouse.gov.uk/")
    ident.text = co_num
    segment = etree.SubElement(ent, f"{XBRLI}segment")
    explicit = etree.SubElement(segment, f"{XBRLDI}explicitMember",
                                dimension=f"uk-bus:{dim_name}")
    explicit.text = f"uk-bus:{member_name}"
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


def _render_amount(parent, tag, ctx, value, negate=False, dash0=False):
    """Render an ix:nonFraction with proper numdotdecimal formatting.

    - dash0: display 0 as '-' but use '0' as the fact value
    - negate: display with parentheses but use positive number with sign='-'
    """
    if dash0 and value == 0:
        # Display '-' but the ix element must contain a valid number
        parent.text = "-"
        # Tag with 0 in a hidden span
        span = _el(parent, "span", style="display:none")
        _num(span, tag, ctx, 0)
    elif negate and value:
        # Display '(20,193)' — put '(' before, number inside ix, ')' after
        parent.text = "("
        ix = _num(parent, tag, ctx, value)
        ix.set("sign", "-")
        ix.text = f"{value:,}"
        ix.tail = ")"
    else:
        ix = _num(parent, tag, ctx, value)
        ix.text = f"{value:,}"


def _row(table, label, tag, cur, pri, has_prior, bold=False, negate=False, dash0=False, line=None, indent=False):
    tr = _el(table, "tr")
    if line == "top":
        tr.set("class", "separator")
    elif line == "total":
        tr.set("class", "separator")

    td_l = _el(tr, "th")
    if indent:
        td_l.set("class", "indent normal")
    elif bold:
        pass  # th is bold by default
    else:
        td_l.set("class", "normal")
    td_l.text = label

    cur_v = cur or 0
    td_c = _el(tr, "td", **{"class": "figure" + (" total" if line == "total" else "")})
    if tag:
        _render_amount(td_c, tag, CTX_CUR, cur_v, negate, dash0)
    else:
        td_c.text = "-" if (dash0 and cur_v == 0) else f"{cur_v:,}"

    if has_prior:
        pri_v = pri if pri is not None else 0
        td_p = _el(tr, "td", **{"class": "figure" + (" total" if line == "total" else "")})
        if tag:
            _render_amount(td_p, tag, CTX_PRI, pri_v, negate, dash0)
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
body { font-family: "Times New Roman", Times, Serif; }
tr, td, th, tbody { padding: 0px; margin: 0px; }
.hidden { display: none; }
div.pagebreak { page-break-after: always; }
div.accountspage { width: 100%; }
div.titlepage { font-weight: bold; margin-top: 5em; text-align: center; }
div.accountsheader { font-weight: bold; width: 100%; display: block; }
span.right { float: right; width: 30%; text-align: right; }
#balancesheet { width: 100%; display: block; padding-top: 1cm; }
#balancesheet table { width: 80%; border-collapse: collapse; margin-left: 10%; }
#balancesheet th { text-align: left; }
#balancesheet .indent { padding-left: 1cm; }
#balancesheet .figure { text-align: right; }
#balancesheet .total { font-weight: bold; border-color: black; border-top-width: 1px; border-bottom-width: 2px; border-style: solid none solid none; }
h1 { font-size: 100%; font-weight: bold; color: black; }
h2 { font-size: 100%; font-weight: bold; margin: 1em 0 1em 0; }
h2.middle { text-align: center; }
h3 { font-size: 100%; font-weight: bold; margin: 0.5em 0; }
span.officername { font-weight: bold; }
th.normal { font-weight: normal; }
#balancesheet tr.separator th { margin-top: 0.8em; }
#balancesheet tr.separator td { border-top: 1px solid black; }
#statements ol { list-style-type: lower-alpha; }
.delivery { margin-top: 2em; font-size: 90%; font-style: italic; }
.emp { width: auto; margin-top: 0.5em; }
.emp td, .emp th { padding: 3px 20px 3px 0; }
@media screen, projection, tv {
  body { margin: 2% 4% 2% 4%; background-color: gray; }
  div.accountspage { background-color: white; padding: 2em 2em 2em 2em; width: 21cm; height: 29.7cm; }
  div.titlepage { padding: 5em 2em 2em 2em; margin: 2em 0 2em 0; }
}
"""
