"""
research_leads.py
-----------------
Deep pre-call research for each prospect:
  1. Finds their website (if not provided)
  2. Crawls key pages: home, about, services, pricing, contact, blog
  3. Extracts business intelligence: what they do, who they serve, what they sell
  4. Detects ad pixels (Meta, Google Ads, TikTok, LinkedIn)
  5. Finds social media profiles
  6. Searches DuckDuckGo for news, reviews, recent activity
  7. Feeds everything to Claude for a deep, specific pitch briefing

Output: leads_enriched.csv (used by run_calls.py)

Usage:
    python3 research_leads.py              # Research all leads
    python3 research_leads.py --limit 5    # Research first 5 only
    python3 research_leads.py --dry-run    # Preview without researching
"""

import csv
import os
import sys
import time
import argparse
import re
import requests
from urllib.parse import urlparse, urljoin, quote_plus
from bs4 import BeautifulSoup
import anthropic
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LEADS_FILE = "leads.csv"
ENRICHED_FILE = "leads_enriched.csv"
DELAY_BETWEEN_LEADS = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Pages to crawl beyond homepage
KEY_SUBPAGES = [
    "/about", "/about-us", "/our-story", "/who-we-are",
    "/services", "/what-we-do", "/solutions", "/offerings",
    "/pricing", "/plans", "/packages",
    "/contact", "/contact-us",
    "/work", "/portfolio", "/case-studies", "/clients",
    "/blog", "/news", "/insights",
    "/team", "/our-team",
]

AD_SIGNATURES = {
    "meta_pixel": ["fbq('init'", 'fbq("init"', "connect.facebook.net", "fbevents.js"],
    "google_ads": ["AW-", "googleads.g.doubleclick.net", "google_conversion_id", "'AW-", '"AW-'],
    "google_analytics": ["google-analytics.com/analytics.js", "googletagmanager.com/gtag", "gtag('config', 'G-", 'gtag("config", "G-'],
    "tiktok_pixel": ["analytics.tiktok.com", "ttq.load("],
    "linkedin_insight": ["_linkedin_partner_id", "snap.licdn.com"],
    "hotjar": ["hotjar.com/c/hotjar-"],
    "hubspot": ["js.hs-scripts.com", "hs-analytics.net"],
}

SOCIAL_PATTERNS = {
    "facebook": r"facebook\.com/(?!sharer|share|dialog|plugins|tr\?)[a-zA-Z0-9._/-]+",
    "instagram": r"instagram\.com/[a-zA-Z0-9._-]+",
    "linkedin": r"linkedin\.com/(?:company|in)/[a-zA-Z0-9._-]+",
    "twitter_x": r"(?:twitter|x)\.com/[a-zA-Z0-9_]+",
    "youtube": r"youtube\.com/(?:channel|c|@)[a-zA-Z0-9._-]+",
    "tiktok": r"tiktok\.com/@[a-zA-Z0-9._-]+",
}


# ── Website fetching ──────────────────────────────────────────────────────────

def fetch_url(url: str, timeout: int = 10) -> tuple[str | None, str | None]:
    """Fetch a URL, return (final_url, html) or (None, None)."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r.url, r.text
        # try http fallback
        r2 = requests.get(url.replace("https://", "http://"), headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r2.status_code == 200:
            return r2.url, r2.text
    except Exception:
        try:
            r = requests.get(url.replace("https://", "http://"), headers=HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return r.url, r.text
        except Exception:
            pass
    return None, None


def find_website(company: str, name: str) -> str | None:
    """Search DuckDuckGo for the company's website."""
    query = f"{company} official website" if company else f"{name} business website"
    try:
        r = requests.get(
            f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
            headers=HEADERS, timeout=10
        )
        soup = BeautifulSoup(r.text, "html.parser")
        skip = {"facebook.com", "linkedin.com", "yelp.com", "yellowpages.com",
                "instagram.com", "twitter.com", "wikipedia.org", "google.com"}
        for result in soup.select(".result__url")[:5]:
            url = result.get_text(strip=True)
            if not url.startswith("http"):
                url = "https://" + url
            domain = urlparse(url).netloc.replace("www.", "")
            if domain not in skip:
                return url
    except Exception:
        pass
    return None


# ── Deep content extraction ───────────────────────────────────────────────────

def extract_page_text(html: str, max_chars: int = 3000) -> str:
    """Extract clean readable text from HTML, removing nav/footer/scripts."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "iframe", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


def crawl_website(base_url: str) -> dict:
    """
    Crawl the homepage + key subpages.
    Returns dict of {page_name: text_content}.
    """
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    pages = {}

    # Homepage
    final_url, html = fetch_url(base_url)
    if html:
        pages["homepage"] = extract_page_text(html, 4000)

    # Try key subpages — stop after finding 4 with content
    found = 0
    for path in KEY_SUBPAGES:
        if found >= 4:
            break
        url = base + path
        _, html = fetch_url(url, timeout=7)
        if html:
            text = extract_page_text(html, 2000)
            if len(text) > 200:  # Skip near-empty pages
                page_name = path.strip("/").replace("-", "_") or "page"
                pages[page_name] = text
                found += 1
        time.sleep(0.3)

    return pages


def get_meta_info(html: str) -> dict:
    """Extract meta title, description, and H1s from homepage."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")][:3]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")][:5]
    return {
        "title": title.get_text(strip=True) if title else "",
        "meta_description": meta_desc.get("content", "").strip() if meta_desc else "",
        "h1s": h1s,
        "h2s": h2s,
    }


def detect_pixels(html: str) -> dict:
    return {platform: any(sig in html for sig in sigs)
            for platform, sigs in AD_SIGNATURES.items()}


def find_social_profiles(html: str) -> dict:
    found = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            unique = list(dict.fromkeys(matches))
            found[platform] = "https://" + unique[0]
    return found


def search_company_news(company: str, website_domain: str = "") -> str:
    """Search DuckDuckGo for recent news, reviews, or mentions."""
    queries = [f'"{company}" reviews', f'"{company}" services']
    results = []
    for query in queries[:1]:
        try:
            r = requests.get(
                f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
                headers=HEADERS, timeout=8
            )
            soup = BeautifulSoup(r.text, "html.parser")
            for s in soup.select(".result__snippet")[:3]:
                text = s.get_text(strip=True)
                if text and website_domain not in text:
                    results.append(text)
        except Exception:
            pass
        time.sleep(0.5)
    return " | ".join(results[:3]) if results else ""


# ── SEO Audit ─────────────────────────────────────────────────────────────────

def audit_seo(url: str, html: str, soup: BeautifulSoup) -> dict:
    """
    Score a website's on-page SEO (0-100) and return a list of specific issues.
    No API key needed — all checks run against the raw HTML.
    """
    score = 0
    issues = []
    wins = []

    # 1. HTTPS (10 pts)
    if url.startswith("https://"):
        score += 10
        wins.append("HTTPS enabled")
    else:
        issues.append("Not on HTTPS — Google penalises non-secure sites")

    # 2. Meta title (15 pts)
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        title_text = title_tag.get_text(strip=True)
        title_len = len(title_text)
        if 30 <= title_len <= 65:
            score += 15
            wins.append(f"Good meta title ({title_len} chars)")
        elif title_len > 65:
            score += 7
            issues.append(f"Meta title too long ({title_len} chars) — Google truncates after 65")
        else:
            score += 7
            issues.append(f"Meta title too short ({title_len} chars) — not enough keywords")
    else:
        issues.append("Missing meta title — one of the biggest SEO mistakes")

    # 3. Meta description (10 pts)
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content", "").strip():
        desc_len = len(meta_desc["content"].strip())
        if 120 <= desc_len <= 160:
            score += 10
            wins.append(f"Good meta description ({desc_len} chars)")
        else:
            score += 5
            issues.append(f"Meta description length off ({desc_len} chars, ideal: 120-160)")
    else:
        issues.append("No meta description — losing click-through rate in search results")

    # 4. H1 tag (10 pts)
    h1s = soup.find_all("h1")
    if len(h1s) == 1:
        score += 10
        wins.append("Correct single H1 tag")
    elif len(h1s) == 0:
        issues.append("No H1 tag found — search engines can't identify the main topic")
    else:
        score += 5
        issues.append(f"Multiple H1 tags ({len(h1s)}) — confuses search engines about page topic")

    # 5. Mobile responsive (10 pts)
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport:
        score += 10
        wins.append("Mobile responsive (viewport meta found)")
    else:
        issues.append("No mobile viewport tag — site may not be mobile-friendly (huge ranking factor)")

    # 6. Image alt text (10 pts)
    images = soup.find_all("img")
    if images:
        with_alt = [img for img in images if img.get("alt", "").strip()]
        pct = int(len(with_alt) / len(images) * 100)
        if pct >= 80:
            score += 10
            wins.append(f"Good image alt text coverage ({pct}%)")
        elif pct >= 50:
            score += 5
            issues.append(f"Only {pct}% of images have alt text — missing SEO & accessibility value")
        else:
            issues.append(f"Only {pct}% of images have alt text — major gap")
    else:
        score += 5  # No images, neutral

    # 7. Canonical tag (5 pts)
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical:
        score += 5
        wins.append("Canonical tag present")
    else:
        issues.append("No canonical tag — risk of duplicate content penalties")

    # 8. Structured data / Schema (5 pts)
    schema = soup.find("script", attrs={"type": "application/ld+json"})
    if schema:
        score += 5
        wins.append("Structured data (Schema.org) found")
    else:
        issues.append("No structured data — missing rich snippet opportunities in Google")

    # 9. Sitemap check (5 pts)
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    try:
        sitemap_r = requests.get(f"{base}/sitemap.xml", headers=HEADERS, timeout=5)
        if sitemap_r.status_code == 200 and "xml" in sitemap_r.text[:100].lower():
            score += 5
            wins.append("Sitemap.xml found")
        else:
            issues.append("No sitemap.xml — Google may miss pages on the site")
    except Exception:
        issues.append("Sitemap check failed")

    # 10. Content length (10 pts)
    text = soup.get_text(separator=" ", strip=True)
    word_count = len(text.split())
    if word_count >= 600:
        score += 10
        wins.append(f"Good content length ({word_count} words)")
    elif word_count >= 300:
        score += 5
        issues.append(f"Thin content ({word_count} words) — Google prefers pages with 600+ words")
    else:
        issues.append(f"Very thin content ({word_count} words) — likely to rank poorly")

    # 11. Google indexing check (bonus: check if site appears for its own name)
    google_indexed = check_google_indexed(parsed.netloc)
    if google_indexed:
        score += 5
        wins.append("Site appears in search results for own name")
    else:
        issues.append("Site may not be indexed by Google — not appearing in search for its own name")

    return {
        "seo_score": min(score, 100),
        "seo_grade": _seo_grade(score),
        "issues": issues,
        "wins": wins,
        "word_count": word_count,
    }


def check_google_indexed(domain: str) -> bool:
    """Check if the site appears in DuckDuckGo for a site: search."""
    try:
        r = requests.get(
            f"https://html.duckduckgo.com/html/?q=site:{quote_plus(domain)}",
            headers=HEADERS, timeout=8
        )
        soup = BeautifulSoup(r.text, "html.parser")
        results = soup.select(".result__url")
        return len(results) > 0
    except Exception:
        return False


def _seo_grade(score: int) -> str:
    if score >= 80: return "A — Good"
    if score >= 65: return "B — Decent"
    if score >= 50: return "C — Needs Work"
    if score >= 35: return "D — Poor"
    return "F — Critical Issues"


# ── Claude deep analysis ──────────────────────────────────────────────────────

def generate_deep_pitch(lead: dict, research: dict) -> str:
    """
    Feed all research to Claude and get a detailed, specific pitch briefing.
    For no-website leads, generates the special free-website pitch flow.
    For leads with a website, generates a standard deep pitch.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_pitch(research)

    # ── No website: use the special free-website pitch flow ──────────────────
    if not research.get("website_live"):
        company = lead.get("company", "this business")
        name = lead.get("name", "the prospect")
        notes = lead.get("notes", "none")
        news = research.get("news", "")

        no_website_prompt = f"""You are a senior sales strategist for a full-service AI and digital marketing agency.

This prospect has NO website. We use a specific foot-in-the-door strategy for these leads.

PROSPECT:
- Name: {name}
- Company: {company}
- Notes: {notes}
- Online mentions/search results: {news or 'none found'}

THE STRATEGY:
Our agent will say they tried to book a service through the prospect's website but couldn't find one.
We then offer a FREE demo website we already built for their type of business.
The ask is just honest feedback — no commitment.
If they're interested, we book a 15-min deployment call and can have it live same day.

Write a SHORT briefing (4-6 sentences) for the agent covering:
1. What we know about their business from search results (use to make the call feel personal)
2. The exact tone to use — this is a helpful call, not a sales call
3. What to say if they push back on "why free?" (answer: we want a testimonial / case study from their industry)
4. How to handle "I'm building one" vs "I don't need one" vs "I have one somewhere"

FLAG THIS CLEARLY at the top: ⚠️ NO WEBSITE LEAD — USE FREE WEBSITE PITCH FLOW"""

        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": no_website_prompt}],
            )
            return message.content[0].text.strip()
        except Exception:
            return f"⚠️ NO WEBSITE LEAD — USE FREE WEBSITE PITCH FLOW\nNo website found for {company}. Use the no-website script: mention you tried booking online, offer free demo site, book deployment call."

    # ── Has website: deep analysis pitch ─────────────────────────────────────
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    page_content = ""
    for page_name, text in research.get("pages", {}).items():
        page_content += f"\n\n--- {page_name.upper()} ---\n{text}"

    meta = research.get("meta", {})
    pixels = research.get("pixels", {})
    social = research.get("social", {})
    news_snippets = research.get("news", "")
    seo = research.get("seo", {})

    seo_issues_str = "\n".join(f"  - {i}" for i in seo.get("issues", [])) or "  None detected"
    seo_wins_str = "\n".join(f"  - w" for w in seo.get("wins", [])) or "  None"

    prompt = f"""You are a senior sales strategist for a full-service AI automation and digital marketing agency.

Your job: analyze everything we know about this prospect and write a DETAILED call briefing for our sales agent Alex.

IMPORTANT: This prospect HAS a website. Do NOT use or mention the free website pitch — that is only for prospects with no website.

The briefing must be specific — reference actual details from their website. Generic advice is useless.

═══════════════════════════════════════
PROSPECT INFO
═══════════════════════════════════════
Name: {lead.get('name', 'Unknown')}
Company: {lead.get('company', 'Unknown')}
Website: {research.get('website_url', 'not found')}
Notes from our team: {lead.get('notes', 'none')}

═══════════════════════════════════════
WEBSITE INTELLIGENCE
═══════════════════════════════════════
Page title: {meta.get('title', 'N/A')}
Meta description: {meta.get('meta_description', 'N/A')}
Main headings (H1): {', '.join(meta.get('h1s', [])) or 'none found'}
Sub-headings (H2): {', '.join(meta.get('h2s', [])) or 'none found'}

FULL PAGE CONTENT READ:
{page_content[:6000] if page_content else 'Website could not be read'}

═══════════════════════════════════════
SEO AUDIT RESULTS
═══════════════════════════════════════
SEO Score: {seo.get('seo_score', 'N/A')}/100 — Grade: {seo.get('seo_grade', 'N/A')}
Content word count: {seo.get('word_count', 'N/A')} words

SEO ISSUES FOUND (use these as conversation hooks):
{seo_issues_str}

SEO WINS:
{seo_wins_str}

═══════════════════════════════════════
DIGITAL MARKETING AUDIT
═══════════════════════════════════════
Running Meta/Facebook Ads: {pixels.get('meta_pixel', False)}
Running Google Ads: {pixels.get('google_ads', False)}
Has Google Analytics: {pixels.get('google_analytics', False)}
Running TikTok Ads: {pixels.get('tiktok_pixel', False)}
Has LinkedIn Insight Tag: {pixels.get('linkedin_insight', False)}
Has HubSpot CRM: {pixels.get('hubspot', False)}
Social profiles found: {list(social.keys()) if social else 'none'}

═══════════════════════════════════════
ONLINE MENTIONS / REVIEWS
═══════════════════════════════════════
{news_snippets or 'No external mentions found'}

═══════════════════════════════════════

Write a call briefing with these exact sections:

**BUSINESS SUMMARY** (2 sentences max)
What does this company actually do? Who are their customers? Be specific — use details from their website.

**SEO SITUATION** (very important — always include this)
Summarise their SEO score ({seo.get('seo_score', '?')}/100) in plain English. List the 2-3 most damaging issues from the audit in terms a business owner would understand — not technical jargon. Example: "Their site has no meta description, meaning Google shows random text in search results instead of a proper pitch to potential customers."

**TOP OPPORTUNITY**
The single most glaring gap — could be SEO, ads, social, or AI automation. Be specific. Reference their actual score or a specific issue found.

**OPENING LINE**
The exact first thing Alex should say that shows we've done homework. If their SEO score is below 60, lead with that: "I had a look at your website and ran a quick SEO check — you're scoring around X out of 100, which means you're probably not showing up when people search for [their service]. Is that something you've noticed?"

**PITCH ANGLE**
Which service fits best and why. If SEO score is below 65, always pitch SEO first and be specific about what's broken and what fixing it would do for their business.

**3 SMART QUESTIONS**
Specific to this business. At least one should be SEO-related if their score is below 70.

**OBJECTION PREP**
Most likely objection from this specific prospect and how to handle it.

Keep it punchy. Alex reads this right before calling."""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        return _fallback_pitch(research)


def _fallback_pitch(research: dict) -> str:
    insights = []
    if not research.get("website_live"):
        insights.append("No working website — pitch web presence + SEO package.")
    else:
        pixels = research.get("pixels", {})
        if not pixels.get("meta_pixel"):
            insights.append("Not running Facebook/Instagram ads.")
        if not pixels.get("google_ads"):
            insights.append("No Google Ads — missing search traffic.")
        if not research.get("social"):
            insights.append("No social profiles found.")
    return " | ".join(insights) if insights else "Standard pitch — website could not be read."


# ── Main research loop ────────────────────────────────────────────────────────

def research_lead(lead: dict) -> dict:
    result = {
        "website_url": None,
        "website_live": False,
        "pages": {},
        "meta": {},
        "pixels": {},
        "social": {},
        "news": "",
        "pitch_angle": "",
        "research_error": "",
    }

    # Step 1: Find website
    website = lead.get("website", "").strip()
    if not website:
        print(f"       → Searching for website...", flush=True)
        website = find_website(lead.get("company", ""), lead.get("name", ""))

    if not website:
        result["pitch_angle"] = _fallback_pitch(result)
        return result

    # Step 2: Fetch homepage
    final_url, homepage_html = fetch_url(website)
    if not homepage_html:
        result["website_url"] = website
        result["pitch_angle"] = _fallback_pitch(result)
        return result

    result["website_url"] = final_url
    result["website_live"] = True
    result["pixels"] = detect_pixels(homepage_html)
    result["social"] = find_social_profiles(homepage_html)
    result["meta"] = get_meta_info(homepage_html)

    # Step 3: SEO audit
    print(f"       → Running SEO audit...", flush=True)
    homepage_soup = BeautifulSoup(homepage_html, "html.parser")
    result["seo"] = audit_seo(final_url, homepage_html, homepage_soup)
    seo = result["seo"]
    print(f"       → SEO score: {seo['seo_score']}/100 ({seo['seo_grade']})", flush=True)
    if seo["issues"]:
        print(f"       → Issues: {'; '.join(seo['issues'][:3])}", flush=True)

    # Step 4: Deep crawl
    print(f"       → Crawling pages...", flush=True)
    result["pages"] = crawl_website(final_url)

    # Step 5: Search for news/reviews
    print(f"       → Searching for online mentions...", flush=True)
    domain = urlparse(final_url).netloc
    result["news"] = search_company_news(lead.get("company", ""), domain)

    # Step 6: Claude deep analysis
    print(f"       → Generating pitch with Claude...", flush=True)
    result["pitch_angle"] = generate_deep_pitch(lead, result)

    return result


def load_leads(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_enriched(leads: list[dict], filepath: str):
    fieldnames = [
        "name", "phone", "company", "website", "notes",
        "website_url", "website_live",
        "running_meta_ads", "running_google_ads", "running_tiktok_ads",
        "has_google_analytics", "has_linkedin_insight", "has_hubspot",
        "social_facebook", "social_instagram", "social_linkedin",
        "social_twitter", "social_youtube", "social_tiktok",
        "page_title", "meta_description",
        "seo_score", "seo_grade", "seo_issues",
        "pitch_angle", "research_error",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(LEADS_FILE):
        print(f"ERROR: {LEADS_FILE} not found.")
        sys.exit(1)

    leads = load_leads(LEADS_FILE)
    if args.limit:
        leads = leads[: args.limit]

    print(f"\nDeep Pre-Call Research")
    print(f"{'='*55}")
    print(f"  Leads to research : {len(leads)}")
    print(f"  Claude model      : claude-3-5-sonnet (deep analysis)")
    print(f"  Output            : {ENRICHED_FILE}")
    print(f"{'='*55}\n")

    if args.dry_run:
        for i, lead in enumerate(leads, 1):
            print(f"  {i:3}. {lead.get('name'):<20} {lead.get('company', '')}")
        print("\nDry run complete.")
        return

    enriched = []
    for i, lead in enumerate(leads, 1):
        name = lead.get("name", "Unknown")
        company = lead.get("company", "")
        print(f"[{i}/{len(leads)}] Researching {name} ({company})", flush=True)

        try:
            research = research_lead(lead)
            flat = {**lead}
            flat["website_url"] = research["website_url"] or ""
            flat["website_live"] = research["website_live"]
            pixels = research.get("pixels", {})
            flat["running_meta_ads"] = pixels.get("meta_pixel", False)
            flat["running_google_ads"] = pixels.get("google_ads", False)
            flat["running_tiktok_ads"] = pixels.get("tiktok_pixel", False)
            flat["has_google_analytics"] = pixels.get("google_analytics", False)
            flat["has_linkedin_insight"] = pixels.get("linkedin_insight", False)
            flat["has_hubspot"] = pixels.get("hubspot", False)
            social = research.get("social", {})
            flat["social_facebook"] = social.get("facebook", "")
            flat["social_instagram"] = social.get("instagram", "")
            flat["social_linkedin"] = social.get("linkedin", "")
            flat["social_twitter"] = social.get("twitter_x", "")
            flat["social_youtube"] = social.get("youtube", "")
            flat["social_tiktok"] = social.get("tiktok", "")
            meta = research.get("meta", {})
            flat["page_title"] = meta.get("title", "")
            flat["meta_description"] = meta.get("meta_description", "")
            seo = research.get("seo", {})
            flat["seo_score"] = seo.get("seo_score", "")
            flat["seo_grade"] = seo.get("seo_grade", "")
            flat["seo_issues"] = " | ".join(seo.get("issues", []))
            flat["pitch_angle"] = research["pitch_angle"]
            flat["research_error"] = research.get("research_error", "")

            pages_found = list(research.get("pages", {}).keys())
            print(f"       → Pages read: {', '.join(pages_found) or 'homepage only'}")
            print(f"       → SEO: {seo.get('seo_score', 'N/A')}/100 ({seo.get('seo_grade', 'N/A')})")
            print(f"       → Ads: Meta={'✓' if pixels.get('meta_pixel') else '✗'} | Google={'✓' if pixels.get('google_ads') else '✗'} | TikTok={'✓' if pixels.get('tiktok_pixel') else '✗'}")
            print(f"       → Social: {list(social.keys()) or 'none found'}")
            print()
            print(f"  PITCH BRIEFING:")
            print(f"  {'─'*50}")
            for line in research["pitch_angle"].split("\n"):
                print(f"  {line}")
            print(f"  {'─'*50}\n")

            enriched.append(flat)
        except Exception as e:
            lead["research_error"] = str(e)
            print(f"       → ERROR: {e}\n")
            enriched.append(lead)

        if i < len(leads):
            time.sleep(DELAY_BETWEEN_LEADS)

    save_enriched(enriched, ENRICHED_FILE)
    print(f"{'='*55}")
    print(f"  Research complete → {ENRICHED_FILE}")
    print(f"  Next: python3 run_calls.py")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
