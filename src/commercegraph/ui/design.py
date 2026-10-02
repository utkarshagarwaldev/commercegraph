"""Local visual system. Dynamic text is escaped before entering decorative HTML."""

from html import escape

import streamlit as st

STYLES = """
<style>
:root { --cg-ink:#172b35; --cg-muted:#526772; --cg-teal:#087f72; }
.stApp { background:#f6f8f9; }
[data-testid="stHeader"] { background:rgba(246,248,249,.94); }
[data-testid="stMainBlockContainer"] { max-width:1280px; padding:2.4rem 3rem 4rem; }
.st-key-workspace_content { gap:1.15rem; }
h1,h2,h3 { color:var(--cg-ink); letter-spacing:-.035em; }
h1 { font-weight:700; }
h2 { font-size:1.45rem !important; }
h3 { font-size:1.1rem !important; }
p,li { line-height:1.6; }
[data-testid="stCaptionContainer"] { color:var(--cg-muted); opacity:1; }
[data-testid="stSidebar"] { background:#142d36; border-right:1px solid #263e47; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top:2rem; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#b8cbd1; opacity:1; }
[data-testid="stSidebar"] hr { border-color:#35505a; margin:1.4rem 0; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:.6rem; }
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding:.85rem .9rem; border-radius:10px; border:1px solid transparent;
    transition:background .15s ease; width:100%;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:#203e48; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background:#254b53; border-color:#3b686e;
}
[data-testid="stSidebar"] [role="radiogroup"] label p { color:#eef7f8; font-weight:500; }
[data-testid="stSidebar"] [data-testid="stButton"] button {
    color:#dcecef; border:1px solid #45616a; background:#203d47;
}
.cg-brand { display:flex; align-items:center; gap:11px; margin-bottom:5px; }
.cg-logo { display:grid; place-items:center; width:38px; height:38px;
    background:#a4e5d7; color:#163b40; border-radius:12px; font-size:24px; }
.cg-brand-name { color:#f1f7f7; font-size:20px; font-weight:650; letter-spacing:-.6px; }
.cg-brand-sub { color:#9bb5be; font-size:12px; margin:0 0 2.2rem 49px; }
.cg-sidebar-label { color:#8daab5; font-size:10px; font-weight:650;
    letter-spacing:1.6px; margin-bottom:10px; }
.cg-status { display:flex; align-items:center; gap:8px; color:#eef7f7; font-size:14px; }
.cg-dot { width:7px; height:7px; background:#80dac6; border-radius:50%; display:inline-block; }
.cg-sidebar-foot { color:#9bb5be; font-size:12px; line-height:1.8; }
.cg-topline { display:flex; align-items:center; justify-content:space-between;
    gap:14px; border-bottom:1px solid #dde5e7; padding-bottom:16px; margin-bottom:20px; }
.cg-breadcrumb { font-size:12px; color:#627982; }
.cg-breadcrumb b { color:#213b46; font-weight:550; }
.cg-tag { display:inline-flex; align-items:center; gap:7px; padding:5px 10px;
    border-radius:7px; background:#e6f3ee; border:1px solid #c7e5da;
    color:#286756; font-size:11px; font-weight:600; white-space:nowrap; }
.cg-hero { display:grid; grid-template-columns:1.4fr 1fr; align-items:center;
    gap:24px; padding:6px 0 10px; }
.cg-eyebrow { color:#087f72; font-size:10px; font-weight:700; letter-spacing:1.7px;
    text-transform:uppercase; margin-bottom:14px; }
.cg-hero h1 { font-size:clamp(30px,3.2vw,46px); line-height:1.15; margin:0 0 14px;
    padding:0; max-width:620px; letter-spacing:-1.8px; }
.cg-hero h1 .cg-accent { color:#087f72; }
.cg-hero p { color:#526772; font-size:14px; margin:0; max-width:460px; }
.cg-network { width:100%; max-width:345px; justify-self:end; }
.cg-section-heading { display:flex; align-items:center; justify-content:space-between;
    gap:12px; margin-bottom:2px; }
.cg-section-heading h2 { font-size:17px !important; margin:0; padding:0; }
.cg-section-detail { color:#6a7f88; font-size:11px; }
.st-key-workspace_content [data-testid="stForm"] { background:#fff; padding:1.5rem !important;
    border:1px solid #dbe5e6 !important; border-radius:16px !important;
    box-shadow:0 7px 24px #15394606; }
[data-testid="stTextArea"] textarea { background:#f8fafb; border-radius:10px;
    font-size:15px; line-height:1.65; padding:14px 16px; }
[data-testid="stTextArea"] [data-baseweb="textarea"] { border-color:#dbe4e7; }
.st-key-workspace_content button { border-radius:9px; min-height:42px; font-weight:550; }
.st-key-workspace_content button[kind="primaryFormSubmit"] { background:#087f72;
    border-color:#087f72; box-shadow:0 3px 8px #087f721a; }
.st-key-workspace_content button[kind="primaryFormSubmit"]:hover { background:#06695f; }
.st-key-workspace_content [class*="st-key-example_"] button {
    justify-content:flex-start; background:#fff; border-color:#dce6e8;
    padding:12px 15px; min-height:52px; color:#304c57;
}
.st-key-workspace_content [class*="st-key-example_"] button:hover {
    border-color:#80b9ae; background:#f0f8f5; color:#086c62;
}
.cg-steps { display:grid; grid-template-columns:repeat(3,1fr); gap:24px;
    border-top:1px solid #dde5e7; padding-top:22px; margin-top:8px; }
.cg-step-number { font-size:10px; letter-spacing:1px; color:#087f72; font-weight:700; }
.cg-steps h3 { margin:6px 0; padding:0; font-size:13px !important; letter-spacing:0; }
.cg-steps p { color:#627782; font-size:12px; margin:0; line-height:1.7; }
.cg-page-heading { margin:7px 0 12px; }
.cg-page-heading h1 { font-size:34px; margin:0 0 8px; padding:0; }
.cg-page-heading p { color:#526772; font-size:14px; margin:0; }
.cg-answer-question { font-size:13px; color:#516a75; border-bottom:1px solid #e0e8ea;
    padding-bottom:14px; margin-bottom:14px; }
.cg-answer { white-space:pre-wrap; overflow-wrap:anywhere; font-family:inherit;
    font-size:16px; line-height:1.85; color:#213b46; }
.cg-answer-meta { color:#637c86; font-size:11px; margin-top:18px; }
.st-key-workspace_content [data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius:14px; border-color:#dce6e8;
}
.st-key-explorer_controls, .st-key-workspace_content [class*="_answer"] {
    background:#fff; border-radius:14px;
}
.st-key-workspace_content [data-testid="stMetric"] {
    background:#fff; border:1px solid #dce6e8; border-radius:12px; padding:18px 20px;
}
.st-key-workspace_content [data-testid="stMetricValue"] { color:#153e46; }
.st-key-workspace_content [data-testid="stExpander"] { background:#fff; border-radius:10px; }
.st-key-workspace_content [data-testid="stDataFrame"] { border-radius:10px; }
button:focus-visible,textarea:focus-visible { outline:3px solid #56b9a3 !important;
    outline-offset:3px; }
@media (max-width:1100px) {
    [data-testid="stMainBlockContainer"] { padding-left:2rem; padding-right:2rem; }
    .cg-hero { grid-template-columns:1.5fr 1fr; gap:12px; }
    .cg-hero h1 { font-size:34px; }
}
@media (max-width:700px) {
    [data-testid="stMainBlockContainer"] { padding:4rem 1.1rem 3rem; }
    .cg-topline { margin-bottom:22px; }
    .cg-hero { display:block; padding-bottom:12px; }
    .cg-hero h1 { font-size:34px; letter-spacing:-1.2px; }
    .cg-network { display:none; }
    .cg-hero p { font-size:13px; }
    .cg-steps { grid-template-columns:1fr; gap:17px; }
    .cg-section-heading { align-items:flex-start; }
    .cg-section-detail { max-width:120px; text-align:right; }
    .st-key-workspace_content [data-testid="stForm"] { padding:1.1rem !important; }
    .cg-page-heading h1 { font-size:29px; }
}
@media (prefers-reduced-motion:reduce) { * { transition:none !important; } }
</style>
"""

NETWORK = """
<svg class="cg-network" viewBox="0 0 345 220" aria-hidden="true">
<defs><pattern id="dots" width="17" height="17" patternUnits="userSpaceOnUse">
<circle cx="1" cy="1" r="1" fill="#d6e2e3"/></pattern></defs>
<rect x="10" y="7" width="325" height="205" rx="20" fill="url(#dots)"/>
<g stroke="#9cbdb7" stroke-width="1.4" fill="none">
<path d="M171 112L74 62M171 112L273 51M171 112L276 161M171 112L74 169"/>
<path d="M74 62L74 169M273 51L276 161" stroke-dasharray="4 5" opacity=".55"/></g>
<g fill="#fff" stroke="#d5e4e0"><rect x="29" y="41" width="93" height="43" rx="10"/>
<rect x="227" y="30" width="95" height="43" rx="10"/>
<rect x="222" y="140" width="103" height="43" rx="10"/>
<rect x="29" y="148" width="93" height="43" rx="10"/></g>
<g font-family="Arial,sans-serif" font-size="11" fill="#49616c" text-anchor="middle">
<text x="76" y="67">Products</text><text x="274" y="56">Vendors</text>
<text x="274" y="166">Customers</text><text x="75" y="174">Orders</text></g>
<circle cx="171" cy="112" r="35" fill="#d9eee7"/>
<circle cx="171" cy="112" r="25" fill="#087f72"/>
<g stroke="#d8f6eb" stroke-width="1.7"><path d="M162 105L180 111L166 121Z" fill="none"/></g>
<g fill="#e0f8ee"><circle cx="162" cy="105" r="3"/><circle cx="180" cy="111" r="3"/>
<circle cx="166" cy="121" r="3"/></g>
</svg>
"""


def apply_styles():
    st.markdown(STYLES, unsafe_allow_html=True)


def top_line(view, mode):
    label = "Gemini · Live" if mode == "live" else "Offline demo"
    st.markdown(
        f'<div class="cg-topline"><div class="cg-breadcrumb">Workspace &nbsp; / &nbsp; '
        f'<b>{escape(view)}</b></div><span class="cg-tag">'
        f'<span class="cg-dot"></span>{label}</span></div>',
        unsafe_allow_html=True,
    )


def ask_heading():
    st.markdown(
        '<div class="cg-hero"><div><div class="cg-eyebrow">Commerce intelligence</div>'
        '<h1>Your data, connected.<br><span class="cg-accent">Your answers, grounded.</span></h1>'
        "<p>Turn a question into a clear answer. Follow the products, people, "
        "and purchases behind it.</p></div>" + NETWORK + "</div>",
        unsafe_allow_html=True,
    )


def page_heading(eyebrow, title, description):
    st.markdown(
        f'<div class="cg-page-heading"><div class="cg-eyebrow">{escape(eyebrow)}</div>'
        f"<h1>{escape(title)}</h1><p>{escape(description)}</p></div>",
        unsafe_allow_html=True,
    )


def section_heading(title, detail=""):
    st.markdown(
        f'<div class="cg-section-heading"><h2>{escape(title)}</h2>'
        f'<span class="cg-section-detail">{escape(detail)}</span></div>',
        unsafe_allow_html=True,
    )


def answer_text(result):
    st.markdown(
        f'<div class="cg-answer-question">{escape(result["question"])}</div>'
        f'<div class="cg-answer">{escape(result["answer"])}</div>'
        f'<div class="cg-answer-meta">{result["duration_seconds"]:.2f} seconds &nbsp;·&nbsp; '
        f"{escape(result['model'])} &nbsp;·&nbsp; {escape(result['mode'].title())}</div>",
        unsafe_allow_html=True,
    )


def empty_state():
    st.markdown(
        '<div class="cg-steps"><div><div class="cg-step-number">01 / ASK</div>'
        "<h3>Start with a question</h3><p>Find products, compare suppliers, or inspect "
        'a customer’s orders.</p></div><div><div class="cg-step-number">02 / CONNECT</div>'
        "<h3>Follow the relationships</h3><p>Each query retrieves the relevant records "
        'from the commerce graph.</p></div><div><div class="cg-step-number">03 / VERIFY</div>'
        "<h3>See the evidence</h3><p>Inspect the source records and connections. "
        "Export the answer for a closer look.</p></div></div>",
        unsafe_allow_html=True,
    )
