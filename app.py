"""Companies House micro-entity accounts filing app.

Single-company filing pipeline for CORSICA STREET 567 LIMITED (10303807).
  input form -> validation -> iXBRL -> GovTalk envelope -> gateway submit -> status
"""

import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify

import requests as http_requests
from ixbrl import generate_ixbrl
from govtalk import build_submission_envelope, build_status_envelope, build_ack_envelope
from gateway import submit as gw_submit, poll_status as gw_poll, acknowledge as gw_ack, GATEWAY_URL

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-me")

# --- Configuration ---
GW_URL = os.environ.get("CH_GATEWAY_URL", GATEWAY_URL)
PRESENTER_ID = os.environ.get("CH_PRESENTER_ID", "")
PRESENTER_AUTH = os.environ.get("CH_PRESENTER_AUTH", "")
IS_TEST = os.environ.get("CH_ENVIRONMENT", "test") != "live"

# Default values — numbers don't change year to year
DEFAULTS = {
    "company_name": "CORSICA STREET 567 LIMITED",
    "company_number": "10303807",
    "company_auth_code": "",
    "period_start": "2025-08-01",
    "period_end": "2026-07-31",
    "prior_period_end": "2025-07-31",
    "fixed_assets": 20199,
    "current_assets": 0,
    "net_current_assets": 0,
    "total_assets_less_current_liabilities": 20199,
    "creditors_after_one_year": 20193,
    "provisions": 0,
    "accruals_deferred_income": 0,
    "net_assets": 6,
    "capital_and_reserves": 6,
    "prior_fixed_assets": 20199,
    "prior_current_assets": 0,
    "prior_net_current_assets": 0,
    "prior_total_assets_less_current_liabilities": 20199,
    "prior_creditors_after_one_year": 20193,
    "prior_provisions": 0,
    "prior_accruals_deferred_income": 0,
    "prior_net_assets": 6,
    "prior_capital_and_reserves": 6,
    "director_name": "Gerald Hughes",
    "approval_date": "",
    "avg_employees": 0,
    "prior_avg_employees": 0,
}

current_filing = dict(DEFAULTS)


@app.route("/")
def index():
    return render_template("form.html", a=current_filing)


@app.route("/setup")
def setup():
    return render_template("setup.html", presenter_id_set=bool(PRESENTER_ID), presenter_auth_set=bool(PRESENTER_AUTH), is_test=IS_TEST)


@app.route("/test-gateway", methods=["POST"])
def test_gateway():
    """Test connectivity to the Companies House XML Gateway."""
    checks = {
        "gateway_url": GW_URL,
        "environment": "TEST" if IS_TEST else "LIVE",
        "presenter_id_set": bool(PRESENTER_ID),
        "presenter_auth_set": bool(PRESENTER_AUTH),
        "gateway_reachable": False,
        "gateway_status_code": None,
        "gateway_error": None,
    }

    try:
        # Send a minimal POST to the gateway — it will reject it, but that proves connectivity
        resp = http_requests.post(
            GW_URL,
            data=b"<ping/>",
            headers={"Content-Type": "text/xml"},
            timeout=10,
        )
        checks["gateway_reachable"] = True
        checks["gateway_status_code"] = resp.status_code
        # Any response (even an error XML) means we reached the server
        if "GovTalkMessage" in resp.text or resp.status_code in (200, 400, 405, 500):
            checks["gateway_responding"] = True
            checks["gateway_response_snippet"] = resp.text[:300]
        else:
            checks["gateway_responding"] = False
            checks["gateway_response_snippet"] = resp.text[:300]
    except http_requests.ConnectionError:
        checks["gateway_error"] = "Cannot connect. Check your internet connection."
    except http_requests.Timeout:
        checks["gateway_error"] = "Connection timed out after 10 seconds."
    except http_requests.RequestException as e:
        checks["gateway_error"] = str(e)

    return jsonify(checks)


@app.route("/submit", methods=["POST"])
def submit_form():
    global current_filing
    f = request.form
    a = {
        "company_name": f.get("company_name", "").strip(),
        "company_number": f.get("company_number", "").strip(),
        "company_auth_code": f.get("company_auth_code", "").strip(),
        "period_start": f.get("period_start", ""),
        "period_end": f.get("period_end", ""),
        "prior_period_end": f.get("prior_period_end", ""),
        "fixed_assets": _int(f.get("fixed_assets")),
        "current_assets": _int(f.get("current_assets")),
        "creditors_after_one_year": _int(f.get("creditors_after_one_year")),
        "provisions": _int(f.get("provisions")),
        "accruals_deferred_income": _int(f.get("accruals_deferred_income")),
        "capital_and_reserves": _int(f.get("capital_and_reserves")),
        "director_name": f.get("director_name", "").strip(),
        "approval_date": f.get("approval_date", ""),
        "avg_employees": _int(f.get("avg_employees")),
        "prior_fixed_assets": _int(f.get("prior_fixed_assets")),
        "prior_current_assets": _int(f.get("prior_current_assets")),
        "prior_creditors_after_one_year": _int(f.get("prior_creditors_after_one_year")),
        "prior_provisions": _int(f.get("prior_provisions")),
        "prior_accruals_deferred_income": _int(f.get("prior_accruals_deferred_income")),
        "prior_capital_and_reserves": _int(f.get("prior_capital_and_reserves")),
        "prior_avg_employees": _int(f.get("prior_avg_employees")),
    }

    # Computed fields
    a["net_current_assets"] = a["current_assets"]
    a["total_assets_less_current_liabilities"] = a["fixed_assets"] + a["net_current_assets"]
    a["net_assets"] = (
        a["total_assets_less_current_liabilities"]
        - a["creditors_after_one_year"]
        - a["provisions"]
        - a["accruals_deferred_income"]
    )
    a["prior_net_current_assets"] = a["prior_current_assets"]
    a["prior_total_assets_less_current_liabilities"] = a["prior_fixed_assets"] + a["prior_net_current_assets"]
    a["prior_net_assets"] = (
        a["prior_total_assets_less_current_liabilities"]
        - a["prior_creditors_after_one_year"]
        - a["prior_provisions"]
        - a["prior_accruals_deferred_income"]
    )

    errors = _validate(a)
    if errors:
        for e in errors:
            flash(e, "error")
        current_filing = a
        return redirect(url_for("index"))

    current_filing = a
    return redirect(url_for("preview"))


@app.route("/preview")
def preview():
    if not current_filing.get("company_name"):
        flash("No accounts data.", "error")
        return redirect(url_for("index"))
    ixbrl_html = generate_ixbrl(current_filing)
    return render_template("preview.html", a=current_filing, ixbrl_html=ixbrl_html)


@app.route("/ixbrl")
def view_ixbrl():
    if not current_filing.get("company_name"):
        return "No accounts data", 400
    return Response(generate_ixbrl(current_filing), mimetype="application/xhtml+xml")


@app.route("/envelope")
def view_envelope():
    if not current_filing.get("company_name"):
        return "No accounts data", 400
    ixbrl_html = generate_ixbrl(current_filing)
    envelope, _ = build_submission_envelope(
        presenter_id=PRESENTER_ID or "TEST_PRESENTER",
        presenter_auth=PRESENTER_AUTH or "TEST_AUTH",
        company_number=current_filing["company_number"],
        company_name=current_filing["company_name"],
        company_auth_code=current_filing["company_auth_code"] or "000000",
        ixbrl_document=ixbrl_html,
        made_up_date=current_filing["period_end"],
        contact_name=current_filing["director_name"],
        is_test=IS_TEST,
    )
    return Response(envelope, mimetype="application/xml")


@app.route("/file", methods=["POST"])
def file_accounts():
    if not current_filing.get("company_name"):
        flash("No accounts data.", "error")
        return redirect(url_for("index"))
    if not PRESENTER_ID or not PRESENTER_AUTH:
        flash("Set CH_PRESENTER_ID and CH_PRESENTER_AUTH env vars.", "error")
        return redirect(url_for("preview"))
    if not current_filing.get("company_auth_code"):
        flash("Company authentication code is required.", "error")
        return redirect(url_for("preview"))

    ixbrl_html = generate_ixbrl(current_filing)
    envelope, txn_id = build_submission_envelope(
        presenter_id=PRESENTER_ID,
        presenter_auth=PRESENTER_AUTH,
        company_number=current_filing["company_number"],
        company_name=current_filing["company_name"],
        company_auth_code=current_filing["company_auth_code"],
        ixbrl_document=ixbrl_html,
        made_up_date=current_filing["period_end"],
        contact_name=current_filing["director_name"],
        is_test=IS_TEST,
    )

    result = gw_submit(envelope, GW_URL)

    current_filing["last_submission"] = {
        "timestamp": datetime.now().isoformat(),
        "transaction_id": txn_id,
        "qualifier": result["qualifier"],
        "correlation_id": result.get("correlation_id", ""),
        "errors": result["errors"],
        "raw_response": result["raw_response"],
    }

    if result["errors"]:
        for err in result["errors"]:
            flash(f"Gateway error: {err['text']}", "error")
    else:
        flash(f"Submitted. Qualifier: {result['qualifier']}", "success")

    return redirect(url_for("status"))


@app.route("/status")
def status():
    submission = current_filing.get("last_submission", {})
    return render_template("status.html", a=current_filing, submission=submission)


@app.route("/poll", methods=["POST"])
def poll_submission():
    submission = current_filing.get("last_submission", {})
    if not PRESENTER_ID:
        flash("Presenter credentials not set.", "error")
        return redirect(url_for("status"))

    status_env = build_status_envelope(
        presenter_id=PRESENTER_ID,
        presenter_auth=PRESENTER_AUTH,
        submission_number="000001",
        is_test=IS_TEST,
    )
    result = gw_poll(status_env, GW_URL)

    submission["poll_result"] = {
        "timestamp": datetime.now().isoformat(),
        "qualifier": result["qualifier"],
        "status_code": result.get("status_code", ""),
        "rejections": result.get("rejections", []),
        "errors": result["errors"],
        "raw_response": result["raw_response"],
    }

    # Send acknowledgment
    if result["qualifier"] != "error":
        ack_env = build_ack_envelope(PRESENTER_ID, PRESENTER_AUTH, is_test=IS_TEST)
        gw_ack(ack_env, GW_URL)

    return redirect(url_for("status"))


def _int(val):
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def _validate(a: dict) -> list[str]:
    errors = []
    if not a["company_name"]:
        errors.append("Company name is required.")
    if not a["company_number"] or len(a["company_number"]) != 8:
        errors.append("Company number must be 8 characters.")
    if not a["period_start"] or not a["period_end"]:
        errors.append("Accounting period dates are required.")
    if not a["director_name"]:
        errors.append("Director name is required.")
    if a["net_assets"] != a["capital_and_reserves"]:
        errors.append(
            f"Balance sheet does not balance: net assets ({a['net_assets']:,}) "
            f"!= capital and reserves ({a['capital_and_reserves']:,})."
        )
    return errors


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4825, debug=True)
