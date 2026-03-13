"""Gmail API email sender via service account with domain-wide delegation."""

from __future__ import annotations

import base64
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import streamlit as st

NOH = "#40887d"
SENDER_EMAIL = "hp@hpmanyonga.com"
REPLY_TO = "Info@networkonehealth.co.za"
TEAM_EMAIL = "Info@networkonehealth.co.za"

_service = None


def _resolve_env(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then env vars as fallback."""
    try:
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, default)


def _get_gmail_service():
    """Build Gmail API service using service account with domain-wide delegation."""
    global _service
    if _service is not None:
        return _service

    creds_json = _resolve_env("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/gmail.send"]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        # Delegate to the sender email (requires domain-wide delegation)
        delegated = credentials.with_subject(SENDER_EMAIL)
        _service = build("gmail", "v1", credentials=delegated, cache_discovery=False)
        return _service
    except Exception:
        return None


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via Gmail API. Returns True on success."""
    service = _get_gmail_service()
    if not service:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"Network One Health <{SENDER_EMAIL}>"
        msg["Reply-To"] = REPLY_TO
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return True
    except Exception:
        return False


def send_client_confirmation(
    name: str,
    email: str,
    noh_low: int,
    noh_high: int,
    ffs_low: int,
    ffs_high: int,
    source: str = "Cost Estimator",
) -> bool:
    """Send a branded confirmation email to the client."""
    subject = "Your NOH Maternity Estimate — We'll Be In Touch"

    ffs_line = ""
    if ffs_low and ffs_high:
        ffs_line = f"""
        <tr>
            <td style="padding:8px 16px;color:#64748b;font-size:14px">Separate bills estimate</td>
            <td style="padding:8px 16px;font-weight:600;font-size:14px;text-align:right">R{ffs_low:,} — R{ffs_high:,}</td>
        </tr>"""

    html = f"""
    <div style="max-width:560px;margin:0 auto;font-family:Arial,sans-serif;color:#1e293b">
        <div style="background:{NOH};padding:24px 28px;border-radius:12px 12px 0 0">
            <h1 style="color:#fff;font-size:22px;margin:0">Network One Health</h1>
            <p style="color:#d1fae5;font-size:14px;margin:6px 0 0">Maternity Care</p>
        </div>
        <div style="border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;padding:28px">
            <p style="font-size:16px;margin:0 0 16px">Hi {name},</p>
            <p style="font-size:14px;line-height:1.6;color:#475569;margin:0 0 20px">
                Thank you for using our {source}. We've received your details and a member
                of our team will contact you to discuss your clinical needs and provide
                a personalised quote.
            </p>
            <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px;margin:0 0 20px">
                <tr>
                    <td style="padding:8px 16px;color:#64748b;font-size:14px">NOH bundle estimate</td>
                    <td style="padding:8px 16px;font-weight:700;font-size:14px;color:{NOH};text-align:right">
                        R{noh_low:,} — R{noh_high:,}
                    </td>
                </tr>
                {ffs_line}
            </table>
            <p style="font-size:13px;color:#94a3b8;line-height:1.5;margin:0 0 20px">
                This is an indicative estimate only. Your final quote will be based on a
                clinical review. Special tests and NICU costs are not included.
            </p>
            <p style="font-size:14px;color:#475569;margin:0 0 6px">
                <b>Questions?</b> Reply to this email or call us:
            </p>
            <p style="font-size:14px;color:{NOH};font-weight:600;margin:0">
                011 458 2497 · Info@networkonehealth.co.za
            </p>
        </div>
        <p style="text-align:center;font-size:11px;color:#94a3b8;margin:16px 0 0">
            Network One Health · Maternity Care
        </p>
    </div>
    """
    return _send_email(email, subject, html)


def send_team_notification(
    name: str,
    email: str,
    phone: str,
    province: str,
    timing: str,
    birth_type: str,
    complexity: str,
    noh_low: int,
    noh_high: int,
    ffs_low: int = 0,
    ffs_high: int = 0,
    source: str = "Cost Estimator",
) -> bool:
    """Send a notification email to the NOH team about the new lead."""
    subject = f"New Lead: {name} — {source}"

    html = f"""
    <div style="max-width:560px;margin:0 auto;font-family:Arial,sans-serif;color:#1e293b">
        <div style="background:{NOH};padding:16px 20px;border-radius:8px 8px 0 0">
            <h2 style="color:#fff;font-size:18px;margin:0">New Maternity Lead</h2>
            <p style="color:#d1fae5;font-size:13px;margin:4px 0 0">via {source}</p>
        </div>
        <div style="border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;padding:20px">
            <table style="width:100%;border-collapse:collapse;font-size:14px">
                <tr><td style="padding:6px 0;color:#64748b;width:140px">Name</td>
                    <td style="padding:6px 0;font-weight:600">{name}</td></tr>
                <tr><td style="padding:6px 0;color:#64748b">Email</td>
                    <td style="padding:6px 0"><a href="mailto:{email}" style="color:{NOH}">{email}</a></td></tr>
                <tr><td style="padding:6px 0;color:#64748b">Phone</td>
                    <td style="padding:6px 0"><a href="tel:{phone}" style="color:{NOH}">{phone}</a></td></tr>
                <tr><td style="padding:6px 0;color:#64748b">Province</td>
                    <td style="padding:6px 0">{province}</td></tr>
                <tr><td style="padding:6px 0;color:#64748b">Timing</td>
                    <td style="padding:6px 0">{timing}</td></tr>
                <tr><td style="padding:6px 0;color:#64748b">Birth type</td>
                    <td style="padding:6px 0">{birth_type}</td></tr>
                <tr><td style="padding:6px 0;color:#64748b">Care complexity</td>
                    <td style="padding:6px 0">{complexity}</td></tr>
                <tr style="border-top:1px solid #e2e8f0">
                    <td style="padding:10px 0 6px;color:#64748b">NOH estimate</td>
                    <td style="padding:10px 0 6px;font-weight:700;color:{NOH}">R{noh_low:,} — R{noh_high:,}</td></tr>
                {"<tr><td style='padding:6px 0;color:#64748b'>FFS estimate</td>"
                 f"<td style='padding:6px 0'>R{ffs_low:,} — R{ffs_high:,}</td></tr>"
                 if ffs_low and ffs_high else ""}
            </table>
            <p style="font-size:13px;color:#94a3b8;margin:16px 0 0">
                A confirmation email has been sent to the client. Please follow up within 24 hours.
            </p>
        </div>
    </div>
    """
    return _send_email(TEAM_EMAIL, subject, html)
