import streamlit as st


def inject_css():
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           TOKENS  — Tinder-accurate palette
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        :root {
            --font:           'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-display:   'DM Sans', -apple-system, sans-serif;

            /* Tinder brand accent */
            --accent:         #FF4458;
            --accent-dark:    #087a68;
            --accent-light:   #f0fdf9;
            --accent-border:  #6ee7d3;

            /* coral for price-over warnings */
            --warn:           #FF4458;
            --warn-grad:      linear-gradient(135deg, #FF4458 0%, #FF6B6B 50%, #FF8C69 100%);

            /* tinder-style deck ring accent — kept for ring SVG */
            --tinder-1:       #FF4458;
            --tinder-2:       #FF6B6B;
            --tinder-3:       #FF8C69;
            --grad:           linear-gradient(135deg, #FF4458 0%, #FF6B6B 100%);
            --grad-subtle:    linear-gradient(135deg, rgba(255,68,88,0.10) 0%, rgba(255,107,107,0.10) 100%);

            /* dark sidebar */
            --sidebar-bg:     #1a1a2e;
            --sidebar-hover:  rgba(255,255,255,0.06);
            --sidebar-active: rgba(255,68,88,0.18);
            --sidebar-text:   rgba(255,255,255,0.85);
            --sidebar-text-1: rgba(255,255,255,0.97);
            --sidebar-text-3: rgba(255,255,255,0.55);
            --sidebar-border: rgba(255,255,255,0.12);

            /* white content area */
            --bg-page:        #ffffff;
            --bg-surface:     #ffffff;
            --bg-soft:        #f9f9f9;
            --bg-input:       #f4f4f4;

            /* borders — very light */
            --border:         #f0f0f0;
            --border-mid:     #e0e0e0;

            /* text */
            --text-1:         #1a1a2e;
            --text-2:         #555577;
            --text-3:         #b0b0c0;

            /* semantic */
            --green-soft:     #f0fdf4;
            --green-border:   #86efac;
            --green-text:     #15803d;
            --amber-soft:     #fffbeb;
            --amber-border:   #fcd34d;
            --amber-text:     #92400e;
            --red-soft:       #fff1f2;
            --red-border:     #fda4af;
            --red-text:       #be123c;

            /* elevation */
            --shadow-xs:      0 1px 4px rgba(0,0,0,0.06);
            --shadow-sm:      0 2px 16px rgba(0,0,0,0.07);
            --shadow:         0 4px 28px rgba(0,0,0,0.09);
            --shadow-card:    0 8px 40px rgba(0,0,0,0.12);
            --shadow-accent:  0 6px 24px rgba(255,68,88,0.28);

            /* geometry */
            --radius:         16px;
            --radius-lg:      22px;
            --radius-xl:      28px;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           GLOBAL RESET
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        [data-testid="stHeader"]     { background: transparent !important; }
        [data-testid="stDecoration"] { display: none !important; }
        [data-testid="stAppViewContainer"] { background: var(--bg-page) !important; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           DARK SIDEBAR
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"] {
            background: var(--sidebar-bg) !important;
            border-right: none !important;
        }
        section[data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebar"] > div:first-child {
            padding: 0 !important;
        }

        /* collapse arrow — make it visible on dark bg */
        [data-testid="stSidebarCollapsedControl"] button {
            color: rgba(255,255,255,0.6) !important;
        }

        /* sidebar scrollbar */
        section[data-testid="stSidebar"] ::-webkit-scrollbar { width: 4px; }
        section[data-testid="stSidebar"] ::-webkit-scrollbar-track { background: transparent; }
        section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 2px; }

        /* radio nav */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            gap: 2px !important;
            padding: 0.5rem 0.75rem !important;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
            font-family: var(--font) !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            color: var(--sidebar-text) !important;
            background: transparent !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.65rem 1rem !important;
            margin: 0 !important;
            transition: background 0.15s, color 0.15s !important;
            cursor: pointer !important;
            width: 100% !important;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
            background: var(--sidebar-hover) !important;
            color: var(--sidebar-text-1) !important;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-checked="true"] {
            background: var(--sidebar-active) !important;
            color: #FF6B6B !important;
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child {
            display: none !important;
        }

        /* sidebar buttons — gradient pill (New search is the only sidebar button) */
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(135deg,#FF4458,#FF6B6B) !important;
            border: none !important;
            border-radius: 10px !important;
            color: #ffffff !important;
            font-family: var(--font) !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em !important;
            padding: 0.35rem 0.9rem !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1.4 !important;
            box-shadow: 0 3px 10px rgba(255,68,88,0.28) !important;
            transition: opacity 0.15s, transform 0.15s !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            opacity: 0.90 !important;
            transform: translateY(-1px) !important;
        }

        /* sidebar markdown text */
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: var(--sidebar-text);
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           SIDEBAR BRAND CLASSES
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-side-header {
            padding: 1.6rem 1.1rem 1rem;
            border-bottom: 1px solid var(--sidebar-border);
        }
        .nw-side-brand {
            font-family: var(--font);
            font-size: 1.1rem;
            font-weight: 800;
            color: #ffffff !important;
            letter-spacing: -0.03em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .nw-side-brand-dot {
            width: 10px; height: 10px;
            border-radius: 50%;
            background: var(--grad);
            flex-shrink: 0;
            box-shadow: 0 0 8px rgba(255,68,88,0.5);
        }
        .nw-side-sub {
            font-family: var(--font);
            font-size: 0.73rem;
            color: var(--sidebar-text-3) !important;
            margin-top: 0.2rem;
            padding-left: 18px;
        }
        .nw-side-nav-label {
            font-family: var(--font);
            font-size: 0.62rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--sidebar-text-3) !important;
            padding: 1rem 1rem 0.25rem;
        }
        .nw-side-section {
            padding: 0.75rem 1rem 0.65rem;
            border-top: 1px solid var(--sidebar-border);
            margin-top: 0.3rem;
        }
        .nw-side-section-label {
            font-family: var(--font);
            font-size: 0.62rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--sidebar-text-3) !important;
            margin-bottom: 0.5rem;
        }
        .nw-side-stat {
            display: flex; align-items: baseline; gap: 6px; padding: 0.18rem 0;
        }
        .nw-side-stat-key {
            font-size: 0.73rem; color: var(--sidebar-text-3) !important;
            min-width: 56px; font-family: var(--font);
        }
        .nw-side-stat-val {
            font-size: 0.84rem; font-weight: 700;
            color: var(--sidebar-text-1) !important; font-family: var(--font);
        }
        .nw-side-chip {
            display: inline-flex; align-items: center; gap: 5px;
            padding: 0.3rem 0.65rem; border-radius: 999px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.15);
            font-family: var(--font); font-size: 0.73rem; font-weight: 600;
            color: rgba(255,255,255,0.8) !important;
        }
        .nw-side-chip.muted {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            color: var(--sidebar-text-3) !important;
        }
        /* account-required chip */
        .nw-side-chip.locked {
            background: rgba(255,68,88,0.18);
            border: 1px solid rgba(255,68,88,0.35);
            color: #FF8C8C !important;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           SIDEBAR — PROFILE CARD
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-profile-card {
            padding: 1rem 1.1rem 1.1rem;
            border-bottom: 1px solid var(--sidebar-border);
        }
        .nw-avatar {
            width: 40px; height: 40px; border-radius: 12px;
            background: linear-gradient(135deg,#FF4458,#FF6B6B);
            display: flex; align-items: center; justify-content: center;
            font-family: var(--font); font-size: 1rem; font-weight: 800;
            color: #fff !important;
            flex-shrink: 0;
            box-shadow: 0 4px 14px rgba(255,68,88,0.40);
        }
        .nw-profile-name {
            font-family: var(--font); font-size: 0.94rem; font-weight: 800;
            color: #ffffff !important; letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .nw-profile-sub {
            font-family: var(--font); font-size: 0.70rem;
            color: var(--sidebar-text-3) !important;
            margin-top: 2px;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           SIDEBAR — DECK CARD
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-deck-card {
            margin: 0.7rem 0.85rem 0.5rem;
            padding: 1rem 1rem 1.1rem;
            background: rgba(255,68,88,0.07);
            border: 1px solid rgba(255,68,88,0.18);
            border-radius: 18px;
        }
        .nw-deck-label {
            font-family: var(--font); font-size: 0.57rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.13em;
            color: rgba(255,107,107,0.55) !important;
            margin-bottom: 2px;
        }
        .nw-deck-session-name {
            font-family: var(--font); font-size: 0.82rem; font-weight: 700;
            color: rgba(255,255,255,0.85) !important;
            margin-bottom: 0.9rem;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .nw-deck-ring-row {
            display: flex; align-items: center; gap: 14px;
        }
        .nw-deck-ring-meta {
            display: flex; flex-direction: column; gap: 8px; flex: 1;
        }
        .nw-deck-ring-meta-item {
            display: flex; align-items: baseline; gap: 7px;
        }
        .nw-deck-big {
            font-family: var(--font); font-size: 1.25rem; font-weight: 800;
            letter-spacing: -0.04em; line-height: 1;
        }
        .nw-deck-key {
            font-family: var(--font); font-size: 0.70rem; font-weight: 600;
            color: var(--sidebar-text-3) !important;
        }

        /* new search button — Tinder gradient style */
        [data-testid="stSidebar"] .nw-new-search .stButton > button {
            background: linear-gradient(135deg,#FF4458,#FF6B6B) !important;
            border: none !important;
            color: #fff !important;
            font-weight: 700 !important;
            font-size: 0.85rem !important;
            border-radius: 12px !important;
            box-shadow: 0 6px 20px rgba(255,68,88,0.35) !important;
        }
        [data-testid="stSidebar"] .nw-new-search .stButton > button:hover {
            opacity: 0.92 !important;
            transform: translateY(-1px) !important;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           SIDEBAR — HR-PREFIX CLASSES (app.py)
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .hr-side-nav-label {
            font-family: var(--font);
            font-size: 0.62rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.12em;
            color: rgba(255,255,255,0.55) !important;
            padding: 1rem 1rem 0.25rem;
        }

        .hr-deck-card {
            margin: 0.7rem 0.85rem 0.5rem;
            padding: 1rem 1rem 1.1rem;
            background: rgba(255,68,88,0.08);
            border: 1.5px solid rgba(255,107,107,0.45);
            border-radius: 18px;
            box-shadow: 0 2px 14px rgba(255,68,88,0.18);
        }
        .hr-deck-label {
            font-family: var(--font); font-size: 0.57rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.13em;
            color: rgba(255,107,107,0.80) !important;
            margin-bottom: 2px;
        }
        .hr-deck-session-name {
            font-family: var(--font); font-size: 0.82rem; font-weight: 700;
            color: rgba(255,255,255,0.92) !important;
            margin-bottom: 0.9rem;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .hr-deck-ring-row { display: flex; align-items: center; gap: 14px; }
        .hr-deck-ring-meta { display: flex; flex-direction: column; gap: 8px; flex: 1; }
        .hr-deck-ring-meta-item { display: flex; align-items: baseline; gap: 7px; }
        .hr-deck-big {
            font-family: var(--font); font-size: 1.25rem; font-weight: 800;
            letter-spacing: -0.04em; line-height: 1;
        }
        .hr-deck-key {
            font-family: var(--font); font-size: 0.70rem; font-weight: 600;
            color: rgba(255,255,255,0.60) !important;
        }

        /* hr- new search button */
        .hr-new-search { padding: 0 0.85rem 0.6rem; }
        [data-testid="stSidebar"] .hr-new-search .stButton > button {
            background: linear-gradient(135deg,#FF4458,#FF6B6B) !important;
            border: none !important;
            color: rgba(255,255,255,0.95) !important;
            font-weight: 600 !important;
            font-size: 0.76rem !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 14px rgba(255,68,88,0.28) !important;
            letter-spacing: 0.01em !important;
        }
        [data-testid="stSidebar"] .hr-new-search .stButton > button:hover {
            opacity: 0.92 !important;
            transform: translateY(-1px) !important;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           MAIN CONTENT
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .block-container {
            max-width: 860px !important;
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-bottom: 3rem !important;
            font-family: var(--font) !important;
            background: var(--bg-page) !important;
        }
        .block-container,
        .block-container p,
        .block-container li,
        .block-container span:not([data-testid]),
        .block-container label { font-family: var(--font) !important; }

        .block-container h1 { font-size:2.1rem !important; font-weight:800 !important; letter-spacing:-0.04em !important; color:var(--text-1) !important; line-height:1.1 !important; }
        .block-container h2 { font-size:1.45rem !important; font-weight:800 !important; letter-spacing:-0.03em !important; color:var(--text-1) !important; }
        .block-container h3 { font-size:1rem !important; font-weight:700 !important; color:var(--text-1) !important; }
        .block-container p  { font-size:0.94rem !important; line-height:1.68 !important; color:var(--text-2) !important; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           DECK FOCUS WRAPPER
           Applied when swipe deck is primary
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-deck-focus .block-container {
            max-width: 520px !important;
            padding-top: 0.5rem !important;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           SECTION HEADERS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-section { padding: 0.5rem 0 0.25rem; }
        .nw-section-step {
            font-family: var(--font); font-size: 0.7rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.1em; color: var(--accent);
        }
        .nw-section-title {
            font-family: var(--font); font-size: 1.55rem; font-weight: 800;
            letter-spacing: -0.035em; color: var(--text-1); margin-top: 0.12rem; line-height: 1.15;
        }
        .nw-section-subtitle {
            font-family: var(--font); font-size: 0.88rem;
            color: var(--text-3); margin-top: 0.25rem;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           CARDS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-profile, .nw-listing, .nw-reco, .nw-pick, .nw-method {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            margin-bottom: 0.9rem;
            box-shadow: var(--shadow-sm);
        }
        .nw-profile, .nw-listing, .nw-reco, .nw-pick { padding: 1.1rem 1.25rem; }
        .nw-method {
            padding: 1.1rem 1.3rem; font-family: var(--font);
            font-size: 0.9rem; line-height: 1.75; color: var(--text-2);
        }
        .nw-method strong { color: var(--text-1); font-weight: 700; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           RESULTS BAND
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-results-band {
            background: var(--bg-surface); border: 1px solid var(--border);
            border-radius: var(--radius-xl); padding: 1.3rem 1.5rem 1.2rem;
            box-shadow: var(--shadow-sm); margin-bottom: 1rem;
        }
        .nw-band-header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem; margin-bottom:1rem; }
        .nw-band-title  { font-family:var(--font); font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-3); }
        .nw-badge-row   { display:flex; gap:6px; flex-wrap:wrap; }
        .nw-badge { display:inline-block; font-family:var(--font); font-size:0.72rem; font-weight:700; padding:3px 10px; border-radius:999px; }
        .nw-badge-mode { background:var(--accent-light); color:var(--accent-dark); border:1px solid var(--accent-border); }
        .nw-badge-rank { background:var(--amber-soft); color:var(--amber-text); border:1px solid var(--amber-border); }

        .nw-metrics-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin-bottom:0.9rem; }
        .nw-metric { background:var(--bg-soft); border:1px solid var(--border); border-radius:var(--radius); padding:0.85rem 1rem; }
        .nw-metric-label { font-family:var(--font); font-size:0.67rem; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-3); margin-bottom:5px; }
        .nw-metric-value { font-family:var(--font); font-size:1.1rem; font-weight:800; letter-spacing:-0.03em; color:var(--text-1); line-height:1.15; }
        .nw-metric-sub   { font-family:var(--font); font-size:0.68rem; color:var(--text-3); margin-top:3px; }
        .nw-metric.highlight .nw-metric-value { background: var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .nw-metric.warn      .nw-metric-value { color: var(--red-text); }

        .nw-why-box {
            background:var(--accent-light); border-left:3px solid var(--accent-border);
            border-radius:0 var(--radius) var(--radius) 0; padding:0.6rem 1rem;
            font-family:var(--font); font-size:0.82rem; color:var(--accent-dark); line-height:1.55;
        }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           LISTING CARDS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-listing-card {
            background:var(--bg-surface); border:1px solid var(--border);
            border-radius:var(--radius-lg); padding:1.1rem 1.25rem;
            margin-bottom:0.75rem; box-shadow:var(--shadow-xs);
            transition:box-shadow 0.18s ease, transform 0.18s ease;
        }
        .nw-listing-card:hover { box-shadow:var(--shadow-card); transform:translateY(-1px); }
        .nw-listing-card.top-pick {
            border-color:var(--accent-border);
            box-shadow:0 0 0 3px rgba(255,68,88,0.08), var(--shadow-xs);
        }
        .nw-listing-rank-badge { display:inline-block; font-family:var(--font); font-size:0.67rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; padding:2px 9px; border-radius:999px; margin-bottom:6px; }
        .nw-listing-rank-badge.pick { background:var(--accent-light); color:var(--accent-dark); border:1px solid var(--accent-border); }
        .nw-listing-rank-badge.rank { background:var(--bg-soft); color:var(--text-3); border:1px solid var(--border); }
        .nw-listing-header  { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
        .nw-listing-id      { font-family:var(--font); font-size:0.98rem; font-weight:700; color:var(--text-1); }
        .nw-listing-meta    { font-family:var(--font); font-size:0.8rem; color:var(--text-3); margin-top:0.2rem; line-height:1.4; }
        .nw-listing-asking  { font-family:var(--font); font-size:1.1rem; font-weight:800; text-align:right; color:var(--text-1); }
        .nw-listing-predicted { font-family:var(--font); font-size:0.76rem; color:var(--text-3); text-align:right; margin-top:0.1rem; }
        .nw-scores-row      { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin:0.7rem 0 0.55rem; }
        .nw-score-pill      { background:var(--bg-soft); border:1px solid var(--border); border-radius:var(--radius); padding:8px 11px 9px; }
        .nw-score-label     { font-family:var(--font); font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-3); margin-bottom:3px; }
        .nw-score-val       { font-family:var(--font); font-size:0.97rem; font-weight:800; color:var(--text-1); line-height:1; }
        .nw-score-val.highlight { background:var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .nw-score-bar-bg    { height:3px; background:var(--border); border-radius:2px; margin-top:5px; overflow:hidden; }
        .nw-score-bar-fill  { height:3px; background:var(--grad); border-radius:2px; }
        .nw-listing-footer  { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.4rem; margin-top:0.25rem; }
        .nw-listing-diff    { font-family:var(--font); font-size:0.78rem; color:var(--text-3); }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           METRICS (st.metric)
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        div[data-testid="metric-container"] {
            background:var(--bg-surface) !important; border:1px solid var(--border) !important;
            border-radius:var(--radius-lg) !important; padding:1rem 1.1rem !important;
            box-shadow:var(--shadow-sm) !important;
        }
        div[data-testid="metric-container"] label { font-family:var(--font) !important; font-size:0.7rem !important; font-weight:700 !important; text-transform:uppercase !important; letter-spacing:0.07em !important; color:var(--text-3) !important; }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-family:var(--font) !important; font-size:1.65rem !important; font-weight:800 !important; letter-spacing:-0.035em !important; color:var(--text-1) !important; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           BUDGET BANNERS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-budget-ok, .nw-budget-warn, .nw-budget-over {
            font-family:var(--font); font-size:0.9rem; font-weight:600;
            padding:0.9rem 1.1rem; border-radius:var(--radius);
            margin:0.8rem 0 1rem; box-shadow:var(--shadow-xs);
        }
        .nw-budget-ok   { background:var(--green-soft); border:1px solid var(--green-border); color:var(--green-text); }
        .nw-budget-warn { background:var(--amber-soft); border:1px solid var(--amber-border); color:var(--amber-text); }
        .nw-budget-over { background:var(--red-soft);   border:1px solid var(--red-border);   color:var(--red-text); }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           PICK CARD
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-pick { display:flex; gap:0.9rem; align-items:flex-start; }
        .nw-pick-icon  { font-size:1.5rem; line-height:1; flex-shrink:0; }
        .nw-pick-label { font-family:var(--font); font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-3); }
        .nw-pick-value { font-family:var(--font); font-size:1.05rem; font-weight:800; color:var(--text-1); margin-top:0.15rem; letter-spacing:-0.025em; }
        .nw-pick-sub   { font-family:var(--font); font-size:0.84rem; color:var(--text-2); margin-top:0.25rem; line-height:1.5; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           RECO / TOWN CARDS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-reco-header { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
        .nw-reco-name   { font-family:var(--font); font-size:0.97rem; font-weight:700; color:var(--text-1); }
        .nw-reco-why    { font-family:var(--font); font-size:0.81rem; color:var(--text-3); margin-top:0.2rem; line-height:1.5; }
        .nw-reco-score  { font-weight:800; color:var(--text-1); }
        .nw-reco-footer { margin-top:0.7rem; display:flex; justify-content:space-between; align-items:center; gap:0.6rem; flex-wrap:wrap; }
        .nw-reco-price  { font-weight:800; color:var(--text-1); font-size:0.94rem; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           TAGS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-reco-within, .nw-reco-over, .nw-tag,
        .nw-tag-steal, .nw-tag-fair, .nw-tag-slight, .nw-tag-over {
            display:inline-block; font-family:var(--font);
            padding:0.24rem 0.6rem; border-radius:999px; font-size:0.75rem; font-weight:700;
        }
        .nw-reco-within, .nw-tag-fair  { background:var(--green-soft); border:1px solid var(--green-border); color:var(--green-text); }
        .nw-reco-over,   .nw-tag-over  { background:var(--red-soft);   border:1px solid var(--red-border);   color:var(--red-text); }
        .nw-tag-steal                   { background:var(--green-soft); border:1px solid #86efac;             color:var(--green-text); }
        .nw-tag-slight                  { background:var(--amber-soft); border:1px solid var(--amber-border); color:var(--amber-text); }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           NO-MATCH / RECOVERY
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-no-match { background:var(--bg-surface); border:1.5px solid var(--red-border); border-radius:var(--radius-lg); padding:1.3rem 1.4rem; box-shadow:var(--shadow-xs); margin-bottom:1rem; }
        .nw-no-match-title { font-family:var(--font); font-size:1rem; font-weight:800; color:var(--red-text); margin-bottom:4px; }
        .nw-no-match-sub   { font-family:var(--font); font-size:0.86rem; color:var(--text-2); margin-bottom:0.9rem; }
        .nw-constraint-row { display:flex; flex-wrap:wrap; gap:7px; margin-bottom:1rem; }
        .nw-chip-fail { display:inline-block; font-family:var(--font); font-size:0.74rem; font-weight:700; padding:3px 10px; border-radius:999px; background:var(--red-soft); border:1px solid var(--red-border); color:var(--red-text); }
        .nw-chip-ok   { display:inline-block; font-family:var(--font); font-size:0.74rem; font-weight:700; padding:3px 10px; border-radius:999px; background:var(--green-soft); border:1px solid var(--green-border); color:var(--green-text); }
        .nw-recovery-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }
        .nw-recovery-card { background:var(--bg-soft); border:1px solid var(--border); border-radius:var(--radius); padding:0.85rem 1rem; }
        .nw-recovery-label { font-family:var(--font); font-size:0.67rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-3); margin-bottom:4px; }
        .nw-recovery-val   { font-family:var(--font); font-size:0.97rem; font-weight:800; color:var(--text-1); line-height:1.2; }
        .nw-recovery-hint  { font-family:var(--font); font-size:0.74rem; color:var(--text-3); margin-top:3px; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           SCENARIO CARDS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-scenario-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:0.75rem 0 0.6rem; }
        .nw-scenario-col  { background:var(--bg-soft); border:1px solid var(--border); border-radius:var(--radius); padding:0.9rem 1.05rem; }
        .nw-scenario-col.changed { border-color:var(--accent-border); background:var(--accent-light); }
        .nw-scenario-col-label { font-family:var(--font); font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-3); margin-bottom:5px; }
        .nw-scenario-col.changed .nw-scenario-col-label { color:var(--accent-dark); }
        .nw-scenario-price   { font-family:var(--font); font-size:1.3rem; font-weight:800; color:var(--text-1); letter-spacing:-0.025em; }
        .nw-scenario-delta   { font-family:var(--font); font-size:0.81rem; font-weight:600; margin-top:3px; }
        .nw-delta-up         { color:var(--red-text); }
        .nw-delta-down       { color:var(--green-text); }
        .nw-delta-none       { color:var(--text-3); }
        .nw-scenario-insight { background:var(--bg-soft); border:1px solid var(--border); border-radius:var(--radius); padding:0.65rem 0.9rem; font-family:var(--font); font-size:0.82rem; color:var(--text-2); line-height:1.55; margin-top:0.6rem; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           PIPELINE
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-pipeline { display:flex; align-items:center; gap:0; font-family:var(--font); font-size:0.72rem; font-weight:600; margin-bottom:1rem; flex-wrap:wrap; }
        .nw-pip-step { padding:5px 13px; background:var(--bg-soft); border:1px solid var(--border); color:var(--text-3); white-space:nowrap; }
        .nw-pip-step:first-child { border-radius:var(--radius) 0 0 var(--radius); }
        .nw-pip-step:last-child  { border-radius:0 var(--radius) var(--radius) 0; }
        .nw-pip-step.active { background:var(--accent-light); color:var(--accent-dark); border-color:var(--accent-border); }
        .nw-pip-arrow { font-size:0.65rem; color:var(--border-mid); padding:0 1px; background:var(--bg-soft); border-top:1px solid var(--border); border-bottom:1px solid var(--border); line-height:1; padding-top:6px; padding-bottom:6px; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           MISC
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        .nw-recent-search  { background:var(--bg-surface); border:1px solid var(--border); border-radius:var(--radius); padding:0.85rem; margin:1rem 0; box-shadow:var(--shadow-xs); }
        .nw-recent-label   { display:block; font-size:0.64rem; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; color:var(--accent); margin-bottom:0.25rem; }
        .nw-sub-section-label { font-family:var(--font); font-size:0.67rem; font-weight:700; text-transform:uppercase; letter-spacing:0.09em; color:var(--text-3); margin:1.2rem 0 0.5rem; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           STREAMLIT WIDGETS
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        div[data-testid="stDataFrame"] { border-radius:var(--radius-lg); overflow:hidden; border:1px solid var(--border); box-shadow:var(--shadow-sm); }

        /* Primary — Tinder gradient */
        button[data-testid="stBaseButton-primary"] {
            background: linear-gradient(135deg,#FF4458 0%,#FF6B6B 100%) !important;
            border: none !important; border-radius: 14px !important;
            padding: 0.68rem 2rem !important;
            box-shadow: 0 8px 24px rgba(255,68,88,0.28) !important;
            transition: all 0.2s ease !important;
        }
        button[data-testid="stBaseButton-primary"] p { color:#fff !important; font-weight:700 !important; font-family:var(--font) !important; }
        button[data-testid="stBaseButton-primary"]:hover { transform:translateY(-2px) !important; box-shadow:0 12px 32px rgba(255,68,88,0.38) !important; filter:brightness(1.05) !important; }

        /* Secondary */
        button[data-testid="stBaseButton-secondary"] {
            background: var(--bg-input) !important; border:1.5px solid var(--border) !important;
            border-radius:14px !important; padding:0.6rem 1.4rem !important; transition:all 0.15s ease !important;
        }
        button[data-testid="stBaseButton-secondary"] p { color:var(--text-1) !important; font-weight:600 !important; font-family:var(--font) !important; }
        button[data-testid="stBaseButton-secondary"]:hover { background:var(--bg-soft) !important; border-color:#d1d9e0 !important; }

        /* Inputs */
        .stTextInput input, .stNumberInput input {
            background:#f8fafc !important; border:1.5px solid #e8edf4 !important;
            border-radius:12px !important; font-family:var(--font) !important;
            transition: border-color 0.15s, box-shadow 0.15s !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color:rgba(255,68,88,0.45) !important;
            box-shadow: 0 0 0 3px rgba(255,68,88,0.10) !important;
        }
        .stSelectbox > div > div {
            background:#f8fafc !important; border:1.5px solid #e8edf4 !important;
            border-radius:12px !important;
        }

        /* Labels */
        .stSlider label p, .stSelectbox label p, .stNumberInput label p, .stTextInput label p { font-family:var(--font) !important; font-size:0.86rem !important; font-weight:600 !important; color:var(--text-2) !important; }
        .stCaption p { font-family:var(--font) !important; font-size:0.78rem !important; color:var(--text-3) !important; }
        .stAlert     { font-family:var(--font) !important; font-size:0.88rem !important; border-radius:var(--radius) !important; }

        /* Tabs — sleek pill style */
        .stTabs [data-baseweb="tab"] { font-family:var(--font) !important; font-size:0.88rem !important; font-weight:600 !important; color:#64748b !important; }
        .stTabs [data-baseweb="tab-list"] { background:#f1f5f9 !important; border-radius:var(--radius) !important; padding:4px !important; border:1px solid #e8edf4 !important; gap:2px !important; }
        .stTabs [aria-selected="true"] { background:#fff !important; border-radius:12px !important; box-shadow:0 2px 8px rgba(0,0,0,0.07),0 1px 2px rgba(0,0,0,0.04) !important; color:#0b132d !important; }
        /* Auth tabs — slightly larger, coral active state */
        .stTabs [data-baseweb="tab-list"] { width:100% !important; }
        .stTabs [data-baseweb="tab"] { flex:1 !important; justify-content:center !important; }

        /* Slider accent */
        .stSlider [data-testid="stSliderThumb"] { background:linear-gradient(135deg,#FF4458,#FF6B6B) !important; border:none !important; box-shadow:0 2px 10px rgba(255,68,88,0.40) !important; }
        .stSlider [data-baseweb="slider"] [role="progressbar"] { background:linear-gradient(90deg,#FF4458,#FF6B6B) !important; }

        hr { border:none !important; border-top:1px solid #eef2f7 !important; margin:1.5rem 0 !important; }

        /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           RESPONSIVE
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
        @media (max-width:900px) {
            .block-container { padding-left:1rem !important; padding-right:1rem !important; }
            .nw-metrics-grid  { grid-template-columns:repeat(3,minmax(0,1fr)); }
            .nw-recovery-grid { grid-template-columns:1fr 1fr; }
            .nw-scenario-grid { grid-template-columns:1fr; }
        }
        @media (max-width:600px) {
            .nw-metrics-grid  { grid-template-columns:1fr 1fr; }
            .nw-recovery-grid { grid-template-columns:1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
