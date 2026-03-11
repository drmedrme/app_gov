"""Companies House XML Gateway client.

Handles submission, status polling, and acknowledgment against the CH XML Gateway.
All requests are POSTed to the same endpoint with different GovTalk envelopes.
Rate limit: max 2 requests/second per presenter.
"""

import requests
from lxml import etree

GATEWAY_URL = "https://xmlgw.companieshouse.gov.uk/v1-0/xmlgw/Gateway"
GT_NS = "http://www.govtalk.gov.uk/CM/envelope"
STATUS_NS = "http://xmlgw.companieshouse.gov.uk"


def submit(envelope_xml: str, gateway_url: str = GATEWAY_URL) -> dict:
    """Submit a GovTalk envelope to the gateway.

    Returns dict with: status, qualifier, correlation_id, errors, raw_response
    """
    return _post(envelope_xml, gateway_url)


def poll_status(status_envelope_xml: str, gateway_url: str = GATEWAY_URL) -> dict:
    """Poll for submission status. Returns status info including status_code."""
    result = _post(status_envelope_xml, gateway_url)

    # Parse SubmissionStatus from body if present
    try:
        root = etree.fromstring(result["raw_response"].encode("utf-8"))
        ns = {"gt": GT_NS, "ss": STATUS_NS}

        for status_el in root.findall(".//ss:Status", ns):
            sn = status_el.find("ss:SubmissionNumber", ns)
            sc = status_el.find("ss:StatusCode", ns)
            result["submission_number"] = sn.text if sn is not None else ""
            result["status_code"] = sc.text if sc is not None else ""

            # Rejections
            for rej in status_el.findall("ss:Rejections/ss:Reject", ns):
                code = rej.find("ss:RejectCode", ns)
                desc = rej.find("ss:Description", ns)
                result["rejections"] = result.get("rejections", [])
                result["rejections"].append({
                    "code": code.text if code is not None else "",
                    "description": desc.text if desc is not None else "",
                })

    except etree.XMLSyntaxError:
        pass

    return result


def acknowledge(ack_envelope_xml: str, gateway_url: str = GATEWAY_URL) -> dict:
    """Send acknowledgment after polling status."""
    return _post(ack_envelope_xml, gateway_url)


def _post(xml: str, url: str) -> dict:
    """POST XML to gateway and parse the response envelope."""
    headers = {"Content-Type": "text/xml"}

    try:
        resp = requests.post(url, data=xml.encode("utf-8"), headers=headers, timeout=60)
        return _parse_response(resp.text)
    except requests.RequestException as e:
        return {
            "qualifier": "error",
            "correlation_id": "",
            "errors": [{"type": "network", "text": str(e)}],
            "raw_response": "",
        }


def _parse_response(xml_text: str) -> dict:
    """Parse a GovTalk response envelope."""
    result = {
        "qualifier": "unknown",
        "correlation_id": "",
        "errors": [],
        "raw_response": xml_text,
    }

    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
        ns = {"gt": GT_NS}

        # Qualifier: "response", "acknowledgement", "error"
        qual = root.find(".//gt:Header/gt:MessageDetails/gt:Qualifier", ns)
        if qual is not None:
            result["qualifier"] = qual.text

        # Correlation ID (echoed transaction reference)
        corr = root.find(".//gt:Header/gt:MessageDetails/gt:CorrelationID", ns)
        if corr is not None:
            result["correlation_id"] = corr.text

        # Gateway timestamp
        ts = root.find(".//gt:Header/gt:MessageDetails/gt:GatewayTimestamp", ns)
        if ts is not None:
            result["gateway_timestamp"] = ts.text

        # Errors from GovTalkErrors
        for error in root.findall(".//gt:GovTalkErrors/gt:Error", ns):
            err_text = error.find("gt:Text", ns)
            err_type = error.find("gt:Type", ns)
            err_num = error.find("gt:Number", ns)
            result["errors"].append({
                "type": err_type.text if err_type is not None else "",
                "text": err_text.text if err_text is not None else "",
                "number": err_num.text if err_num is not None else "",
            })

    except etree.XMLSyntaxError:
        result["qualifier"] = "parse_error"
        result["errors"].append({"type": "fatal", "text": "Could not parse gateway response"})

    return result
