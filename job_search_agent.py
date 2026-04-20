#!/usr/bin/env python3
# test: release manager pipeline validation Only
"""
Job Search Agent - Daily 2:30 PM PST
Searches for Sr. Director of Engineering roles in retail tech.
Sends digest email via Gmail SMTP (App Password).
Now that app password has been fixed gmail should be recieved everyday.
Optimized for Tier 1 API: 2 queries, 120s gap, conservative tokens.
"""

import os
import sys
import time
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from google import genai
from google.genai import types

# ── CONFIG ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_SENDER       = "vermasangeeta@gmail.com"
TARGET_EMAIL       = "vermasangeeta@gmail.com"
ROLE               = "Senior Director of Engineering"
LOG_FILE           = os.path.expanduser("~/capstone/logs/job_agent.log")

# 2 queries only — enough coverage, stays under Tier 1 token limits
SEARCH_QUERIES = [
    f'"{ROLE}" Retail Engineering hiring 2026',
    f'"VP of Engineering" OR "Sr Director Engineering" retail omnichannel POS jobs 2026',
]

FILTER_SYSTEM = f"""Extract job postings from search results for "{ROLE}" in retail technology.

INCLUDE only: Senior/Sr Director at retail, ecommerce, omnichannel, POS companies.

For each match output:
COMPANY: [name]
TITLE: [title]
LOCATION: [city/remote/hybrid]
FIT_SCORE: [1-10]
HIGHLIGHTS: [2-3 responsibilities]
URL: [link or company careers page]
---
If none: NO_MATCHES"""


def create_client():
    if not GEMINI_API_KEY:
        log("ERROR: GEMINI_API_KEY is not set")
        sys.exit(1)
    return genai.Client(api_key=GEMINI_API_KEY)


def response_text(response):
    return response.text if response.text else ""

# ── LOGGING ──────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── SEARCH ────────────────────────────────────────────────────────────────────
def search_and_filter(client, query: str) -> str:
    """Run one query with Gemini. Retry on transient errors."""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f'Search and extract job matches for:\n"{query}"\nToday: {datetime.now().strftime("%B %d, %Y")}',
                config=types.GenerateContentConfig(
                    system_instruction=FILTER_SYSTEM,
                    temperature=0.0,
                    max_output_tokens=600,
                ),
            )
            return response_text(response)
        except Exception as e:
            if attempt < 2:
                wait = 120
                log(f"  → Error, retrying in {wait}s ({attempt + 1}/2): {e}")
                time.sleep(wait)
            else:
                log(f"  → Failed after retries: {e}")
                return ""
    return ""


def consolidate(client, raw_blocks: list) -> str:
    """Deduplicate and rank results using Gemini."""
    combined = "\n\n===\n\n".join(raw_blocks)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=(
                f"Job results for '{ROLE}' in retail tech:\n\n{combined}\n\n"
                "1. Remove duplicates\n"
                "2. Rank by FIT_SCORE descending\n"
                "3. Keep same format (COMPANY/TITLE/LOCATION/FIT_SCORE/HIGHLIGHTS/URL/---)\n"
                "4. Add one sentence: MARKET_SUMMARY\n"
                "List all if fewer than 10."
            ),
            config=types.GenerateContentConfig(
                system_instruction="You are a recruiter assistant.",
                temperature=0.0,
                max_output_tokens=800,
            ),
        )
        return response_text(response)
    except Exception as e:
        log(f"Consolidation error: {e}")
        return combined

# ── EMAIL ─────────────────────────────────────────────────────────────────────
def send_via_smtp(subject: str, body: str) -> bool:
    if not GMAIL_APP_PASSWORD:
        log("⚠️  GMAIL_APP_PASSWORD not set — saving locally only<--This should not show anymore")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = TARGET_EMAIL
    msg.attach(MIMEText(body, "plain"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_SENDER, TARGET_EMAIL, msg.as_string())
    return True

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("Job Search Agent starting")
    log(f"Role: {ROLE}")
    log(f"Recipient: {TARGET_EMAIL}")
    log(f"Queries: {len(SEARCH_QUERIES)}")

    client = create_client()

    # ── 1. Search queries ─────────────────────────────────────────────────────
    raw_results = []
    for i, query in enumerate(SEARCH_QUERIES, 1):
        log(f"[{i}/{len(SEARCH_QUERIES)}] Searching: {query[:70]}...")
        result = search_and_filter(client, query)
        if result and "NO_MATCHES" not in result:
            raw_results.append(result)
            log(f"  → {result.count('COMPANY:')} match(es) found")
        else:
            log("  → No matches in this batch")

        # Wait 2 minutes between queries — fully resets the per-minute token window
        if i < len(SEARCH_QUERIES):
            log("  → Waiting 120s before next query...")
            time.sleep(120)

    if not raw_results:
        log("No results found — sending empty digest")
        raw_results = ["No matching jobs found today. Will retry tomorrow."]

    # ── 2. Consolidate ────────────────────────────────────────────────────────
    log("Consolidating results...")
    digest_body = consolidate(client, raw_results)

    # ── 3. Build + send email ─────────────────────────────────────────────────
    today   = datetime.now().strftime("%A, %B %d, %Y")
    subject = f"🎯 Daily Job Digest: {ROLE} in Retail Engineering — {today}"
    email_body = f"""Hi Sangeeta,

Here is your daily job search digest for {ROLE} in retail technology.
Generated: {today}

{'=' * 55}

{digest_body}

{'=' * 55}

Generated by your Job Search Agent.
Queries run: {len(SEARCH_QUERIES)} | Batches with results: {len(raw_results)}
"""
    log("Sending email via Gmail SMTP...")
    try:
        if send_via_smtp(subject, email_body):
            log(f"✅ Email sent to {TARGET_EMAIL}")
    except Exception as e:
        log(f"❌ Gmail SMTP error: {e}")

    fallback = os.path.expanduser(
        f"~/capstone/logs/digest_{datetime.now().strftime('%Y%m%d')}.txt"
    )
    with open(fallback, "w") as f:
        f.write(f"Subject: {subject}\n\n{email_body}")
    log(f"Digest saved locally: {fallback}")
    log("Job Search Agent complete")
    log("=" * 60)


if __name__ == "__main__":
    main()
