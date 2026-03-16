"""Landing page for the NOH Maternity Platform."""

import os
import streamlit as st

st.set_page_config(
    page_title="Network One Health — Maternity Care",
    page_icon="\U0001f37c",
    layout="wide",
)

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "noh_logo.png")

# ---------------------------------------------------------------------------
# Global styling — premium card-based design
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarCollapsedControl"] { display: none; }

    .block-container { max-width: 940px; padding-top: 2rem; }

    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, span, div {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    /* Hero section */
    .hero-section {
        background: linear-gradient(160deg, #2d6159 0%, #40887d 50%, #5ca89e 100%);
        border-radius: 20px;
        padding: 48px 40px;
        text-align: center;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: '';
        position: absolute;
        top: -80px; right: -60px;
        width: 300px; height: 300px;
        background: rgba(255,255,255,0.05);
        border-radius: 50%;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        color: #fff;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding: 5px 14px;
        border-radius: 20px;
        margin-bottom: 16px;
    }
    .hero-section h1 {
        font-size: 32px;
        font-weight: 800;
        color: #fff !important;
        margin: 0 0 8px 0;
        line-height: 1.2;
    }
    .hero-section p {
        font-size: 16px;
        color: rgba(255,255,255,0.85);
        max-width: 520px;
        margin: 0 auto;
        line-height: 1.5;
    }

    /* Tool cards */
    .tool-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 32px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.04);
        transition: all 0.25s ease;
        height: 100%;
        position: relative;
    }
    .tool-card:hover {
        box-shadow: 0 4px 16px rgba(64,136,125,0.15), 0 8px 32px rgba(0,0,0,0.06);
        transform: translateY(-3px);
        border-color: #40887d;
    }
    .card-icon {
        width: 56px; height: 56px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        margin-bottom: 18px;
    }
    .card-icon-teal { background: #e6f2f0; }
    .card-icon-amber { background: #fef3e8; }
    .card-title {
        font-size: 20px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 8px;
    }
    .card-desc {
        font-size: 14px;
        color: #6b7280;
        line-height: 1.6;
        margin-bottom: 16px;
    }
    .card-badges {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }
    .card-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 99px;
    }
    .badge-blue { background: #e0f2fe; color: #0369a1; }
    .badge-green { background: #e6f2f0; color: #2d6159; }
    .badge-amber { background: #fef3e8; color: #92400e; }

    /* Stacked cards background */
    .cards-section {
        background: #f7f8fa;
        border-radius: 20px;
        padding: 40px 32px;
        margin-bottom: 32px;
    }
    .cards-section-title {
        font-size: 12px;
        font-weight: 700;
        color: #40887d;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-align: center;
        margin-bottom: 8px;
    }
    .cards-section-heading {
        font-size: 24px;
        font-weight: 800;
        color: #111827;
        text-align: center;
        margin-bottom: 28px;
    }

    /* Included section */
    .included-card {
        background: #fff;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #f0f0f0;
        text-align: center;
        height: 100%;
    }
    .included-icon {
        font-size: 32px;
        margin-bottom: 10px;
        display: block;
    }
    .included-title {
        font-size: 15px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 8px;
    }
    .included-list {
        font-size: 13px;
        color: #6b7280;
        line-height: 1.7;
        text-align: left;
        list-style: none;
        padding: 0;
    }
    .included-list li::before {
        content: '\u2713';
        color: #40887d;
        font-weight: 700;
        margin-right: 6px;
    }

    /* Trust bar */
    .trust-bar {
        display: flex;
        justify-content: center;
        gap: 32px;
        flex-wrap: wrap;
        padding: 20px 0;
        margin-bottom: 16px;
    }
    .trust-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: #6b7280;
        font-weight: 500;
    }
    .trust-icon { color: #40887d; font-size: 16px; }

    /* Style Streamlit buttons */
    .stButton > button, .stLinkButton > a {
        width: 100% !important;
        height: 48px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:hover, .stLinkButton > a:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }

    /* Equal height columns */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }

    /* Footer */
    .footer-text {
        text-align: center;
        font-size: 12px;
        color: #9ca3af;
        padding: 16px 0;
        line-height: 1.6;
    }
    .footer-text a { color: #40887d; text-decoration: none; }

    @media (max-width: 768px) {
        .hero-section { padding: 32px 20px; }
        .cards-section { padding: 24px 16px; }
        .trust-bar { gap: 16px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero section
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-section">
        <div class="hero-badge">South Africa's Risk-Rated Maternity Bundle</div>
        <h1>Network One Maternity</h1>
        <p>One fee covers your full maternity journey — antenatal visits, delivery,
        anaesthetist, scans, blood tests, and doula support. No separate bills.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Trust bar
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="trust-bar">
        <div class="trust-item"><span class="trust-icon">\u2713</span> No login required</div>
        <div class="trust-item"><span class="trust-icon">\u2713</span> Results in under 2 minutes</div>
        <div class="trust-item"><span class="trust-icon">\u2713</span> Evidence-based pricing</div>
        <div class="trust-item"><span class="trust-icon">\u2713</span> POPIA compliant</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Tool selection cards
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="cards-section">
        <div class="cards-section-title">Choose Your Tool</div>
        <div class="cards-section-heading">See what you could save</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Remove the background div and render cards inside Streamlit columns
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(
        """
        <div class="tool-card">
            <div class="card-icon card-icon-teal">\U0001f4ca</div>
            <div class="card-title">Cost Estimator</div>
            <div class="card-desc">
                Compare separate bills from 6-7 providers against the NOH
                all-in-one bundle. See a detailed breakdown of what you'd pay
                with traditional care vs our maternity package.
            </div>
            <div class="card-badges">
                <span class="card-badge badge-blue">\u23f1 3-5 minutes</span>
                <span class="card-badge badge-green">Detailed breakdown</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/1_Cost_Estimator.py",
        label="Estimate My Costs",
        icon="\U0001f4ca",
        use_container_width=True,
    )

with col2:
    st.markdown(
        """
        <div class="tool-card">
            <div class="card-icon card-icon-amber">\u26a1</div>
            <div class="card-title">QuickQuote</div>
            <div class="card-desc">
                Answer a few questions about your pregnancy and health to get a
                personalised, risk-rated estimate in under a minute. Fast,
                simple, and tailored to your profile.
            </div>
            <div class="card-badges">
                <span class="card-badge badge-amber">\u26a1 Under 1 minute</span>
                <span class="card-badge badge-green">Risk-rated</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/2_QuickQuote.py",
        label="Get My QuickQuote",
        icon="\u26a1",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# What's included
# ---------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="cards-section-title">What's included</div>
    <div class="cards-section-heading">Your complete maternity package</div>
    """,
    unsafe_allow_html=True,
)

inc1, inc2, inc3 = st.columns(3, gap="medium")

with inc1:
    st.markdown(
        """
        <div class="included-card">
            <span class="included-icon">\U0001fa7a</span>
            <div class="included-title">Antenatal Care</div>
            <ul class="included-list">
                <li>10-14 consultations</li>
                <li>All ultrasound scans</li>
                <li>Booking blood tests</li>
                <li>Antenatal classes</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

with inc2:
    st.markdown(
        """
        <div class="included-card">
            <span class="included-icon">\U0001f3e5</span>
            <div class="included-title">Delivery</div>
            <ul class="included-list">
                <li>Private hospital facility</li>
                <li>Obstetrician (24hr cover)</li>
                <li>Anaesthetist</li>
                <li>NVD or C-section</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

with inc3:
    st.markdown(
        """
        <div class="included-card">
            <span class="included-icon">\U0001e49a</span>
            <div class="included-title">Support</div>
            <ul class="included-list">
                <li>Doula birth support</li>
                <li>3 postnatal visits</li>
                <li>Midwife-led care</li>
                <li>Pap smear included</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="footer-text">
        Estimates are based on publicly available 2024-2026 pricing data.
        Actual costs depend on your clinical profile, hospital, and specialist.<br><br>
        Network One Health &nbsp;|&nbsp;
        <a href="mailto:info@networkonehealth.co.za">info@networkonehealth.co.za</a> &nbsp;|&nbsp;
        011 458 2497 &nbsp;|&nbsp;
        <a href="https://wa.me/27664992713">WhatsApp</a> &nbsp;|&nbsp;
        <a href="https://hpmanyonga.github.io/noh-hub/faq.html">FAQ</a>
    </div>
    """,
    unsafe_allow_html=True,
)
