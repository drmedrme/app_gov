"""GovTalk envelope builder for Companies House XML Gateway.

Builds the correct GovTalk v1.0 envelope with FormSubmission body
for iXBRL accounts filing. The iXBRL document is base64-encoded
inside a <Document><Data> element per the CH specification.

References:
  - CH XML Gateway Interface Specification
  - FormSubmission-v2-11.xsd
  - cybermaggedon/companies-house-filing (reference implementation)
"""

import base64
import hashlib
import uuid
from lxml import etree

GT_NS = "http://www.govtalk.gov.uk/CM/envelope"
FS_NS = "http://xmlgw.companieshouse.gov.uk/Header"
GT_SCHEMA = "http://xmlgw.companieshouse.gov.uk/v2-1/schema/Egov_ch-v2-0.xsd"
FS_SCHEMA = "http://xmlgw.companieshouse.gov.uk/v1-1/schema/forms/FormSubmission-v2-11.xsd"
STATUS_NS = "http://xmlgw.companieshouse.gov.uk"


def _md5(value: str) -> str:
    """MD5 hex digest of a string (CHMD5 authentication)."""
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def build_submission_envelope(
    presenter_id: str,
    presenter_auth: str,
    company_number: str,
    company_name: str,
    company_auth_code: str,
    ixbrl_document: str,
    made_up_date: str,
    contact_name: str = "",
    contact_email: str = "",
    submission_number: str = "000001",
    is_test: bool = True,
) -> tuple[str, str]:
    """Build a GovTalk submission envelope for accounts filing.

    Returns:
        (envelope_xml, transaction_id) tuple.
    """
    transaction_id = uuid.uuid4().hex[:35]

    GT = "{%s}" % GT_NS
    XSI = "{http://www.w3.org/2001/XMLSchema-instance}"

    root = etree.Element(
        f"{GT}GovTalkMessage",
        nsmap={
            None: GT_NS,
            "dsig": "http://www.w3.org/2000/09/xmldsig#",
            "gt": "http://www.govtalk.gov.uk/schemas/govtalk/core",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )
    root.set(f"{XSI}schemaLocation", f"{GT_NS} {GT_SCHEMA}")

    # EnvelopeVersion
    ev = etree.SubElement(root, f"{GT}EnvelopeVersion")
    ev.text = "1.0"

    # Header
    header = etree.SubElement(root, f"{GT}Header")

    # MessageDetails
    msg = etree.SubElement(header, f"{GT}MessageDetails")
    cls = etree.SubElement(msg, f"{GT}Class")
    cls.text = "Accounts"
    qual = etree.SubElement(msg, f"{GT}Qualifier")
    qual.text = "request"
    txn = etree.SubElement(msg, f"{GT}TransactionID")
    txn.text = transaction_id
    gw_test = etree.SubElement(msg, f"{GT}GatewayTest")
    gw_test.text = "1" if is_test else "0"

    # SenderDetails with CHMD5 authentication
    sender = etree.SubElement(header, f"{GT}SenderDetails")
    id_auth = etree.SubElement(sender, f"{GT}IDAuthentication")
    sid = etree.SubElement(id_auth, f"{GT}SenderID")
    sid.text = _md5(presenter_id)
    auth = etree.SubElement(id_auth, f"{GT}Authentication")
    method = etree.SubElement(auth, f"{GT}Method")
    method.text = "CHMD5"
    value = etree.SubElement(auth, f"{GT}Value")
    value.text = _md5(presenter_auth)
    if contact_email:
        email = etree.SubElement(sender, f"{GT}EmailAddress")
        email.text = contact_email

    # GovTalkDetails
    gt_details = etree.SubElement(root, f"{GT}GovTalkDetails")
    etree.SubElement(gt_details, f"{GT}Keys")

    # Body — contains FormSubmission
    body = etree.SubElement(root, f"{GT}Body")
    _build_form_submission(
        body, company_number, company_name, company_auth_code,
        ixbrl_document, made_up_date, contact_name, submission_number,
    )

    xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return xml.decode("utf-8"), transaction_id


def _build_form_submission(
    parent, company_number, company_name, company_auth_code,
    ixbrl_document, made_up_date, contact_name, submission_number,
):
    """Build the FormSubmission element inside the Body."""
    FS = "{%s}" % FS_NS
    XSI = "{http://www.w3.org/2001/XMLSchema-instance}"

    fs = etree.SubElement(
        parent,
        f"{FS}FormSubmission",
        nsmap={None: FS_NS, "xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    )
    fs.set(f"{XSI}schemaLocation", f"{FS_NS} {FS_SCHEMA}")

    # FormHeader
    fh = etree.SubElement(fs, f"{FS}FormHeader")
    cn = etree.SubElement(fh, f"{FS}CompanyNumber")
    cn.text = company_number
    ct = etree.SubElement(fh, f"{FS}CompanyType")
    ct.text = "EW"  # England/Wales
    cname = etree.SubElement(fh, f"{FS}CompanyName")
    cname.text = company_name
    cac = etree.SubElement(fh, f"{FS}CompanyAuthenticationCode")
    cac.text = company_auth_code
    pkg = etree.SubElement(fh, f"{FS}PackageReference")
    pkg.text = f"ACCOUNTS-{company_number}"
    lang = etree.SubElement(fh, f"{FS}Language")
    lang.text = "EN"
    fi = etree.SubElement(fh, f"{FS}FormIdentifier")
    fi.text = "Accounts"
    sn = etree.SubElement(fh, f"{FS}SubmissionNumber")
    sn.text = submission_number
    if contact_name:
        ctn = etree.SubElement(fh, f"{FS}ContactName")
        ctn.text = contact_name

    # DateSigned
    ds = etree.SubElement(fs, f"{FS}DateSigned")
    ds.text = made_up_date

    # Form — empty for iXBRL accounts
    etree.SubElement(fs, f"{FS}Form")

    # Document — iXBRL base64-encoded
    doc = etree.SubElement(fs, f"{FS}Document")
    data = etree.SubElement(doc, f"{FS}Data")
    data.text = base64.b64encode(ixbrl_document.encode("utf-8")).decode("ascii")
    doc_date = etree.SubElement(doc, f"{FS}Date")
    doc_date.text = made_up_date
    fn = etree.SubElement(doc, f"{FS}Filename")
    fn.text = "accounts.html"
    content_type = etree.SubElement(doc, f"{FS}ContentType")
    content_type.text = "application/xml"
    cat = etree.SubElement(doc, f"{FS}Category")
    cat.text = "ACCOUNTS"


def build_status_envelope(
    presenter_id: str,
    presenter_auth: str,
    submission_number: str = "",
    company_number: str = "",
    is_test: bool = True,
) -> str:
    """Build a GetSubmissionStatus request envelope."""
    GT = "{%s}" % GT_NS

    root = _make_envelope_root("GetSubmissionStatus", presenter_id, presenter_auth, is_test)

    # Body
    body = etree.SubElement(root, f"{GT}Body")
    gs = etree.SubElement(body, "GetSubmissionStatus", xmlns=STATUS_NS)
    pid = etree.SubElement(gs, "PresenterID")
    pid.text = presenter_id
    if submission_number:
        sn = etree.SubElement(gs, "SubmissionNumber")
        sn.text = submission_number
    if company_number:
        cn = etree.SubElement(gs, "CompanyNumber")
        cn.text = company_number

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def build_ack_envelope(
    presenter_id: str,
    presenter_auth: str,
    is_test: bool = True,
) -> str:
    """Build a GetStatusAck acknowledgment envelope."""
    GT = "{%s}" % GT_NS

    root = _make_envelope_root("GetStatusAck", presenter_id, presenter_auth, is_test)

    body = etree.SubElement(root, f"{GT}Body")
    etree.SubElement(body, "StatusAck", xmlns=STATUS_NS)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def _make_envelope_root(class_name, presenter_id, presenter_auth, is_test):
    """Build a basic GovTalk envelope (header only, no body)."""
    GT = "{%s}" % GT_NS

    root = etree.Element(f"{GT}GovTalkMessage", nsmap={None: GT_NS})

    ev = etree.SubElement(root, f"{GT}EnvelopeVersion")
    ev.text = "1.0"

    header = etree.SubElement(root, f"{GT}Header")
    msg = etree.SubElement(header, f"{GT}MessageDetails")
    cls = etree.SubElement(msg, f"{GT}Class")
    cls.text = class_name
    qual = etree.SubElement(msg, f"{GT}Qualifier")
    qual.text = "request"
    gw_test = etree.SubElement(msg, f"{GT}GatewayTest")
    gw_test.text = "1" if is_test else "0"

    sender = etree.SubElement(header, f"{GT}SenderDetails")
    id_auth = etree.SubElement(sender, f"{GT}IDAuthentication")
    sid = etree.SubElement(id_auth, f"{GT}SenderID")
    sid.text = _md5(presenter_id)
    auth_el = etree.SubElement(id_auth, f"{GT}Authentication")
    method = etree.SubElement(auth_el, f"{GT}Method")
    method.text = "CHMD5"
    value = etree.SubElement(auth_el, f"{GT}Value")
    value.text = _md5(presenter_auth)

    gt_details = etree.SubElement(root, f"{GT}GovTalkDetails")
    etree.SubElement(gt_details, f"{GT}Keys")

    return root
