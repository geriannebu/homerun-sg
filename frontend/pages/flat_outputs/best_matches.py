"""
frontend/pages/flat_outputs/best_matches.py

Tinder-style swipe deck.
  Right / ♥  → Like (shortlist)
  Left  / ✕  → Pass (skip)
  Up    / ⭐  → Super-save (also goes to shortlist, highlighted)
  Click card → Detail overlay

State is written back to the active search session in session_state.
"""

import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from backend.utils.formatters import fmt_sgd, valuation_tag_html
from backend.utils.constants import TOWN_COORDS
from frontend.state.session import get_active_session, record_swipe
from frontend.components.listing_detail import show_listing_detail


DEFAULT_COORD = (1.3521, 103.8198)

AMENITY_ICONS = {
    "mrt": "🚇", "bus": "🚌", "healthcare": "🏥",
    "schools": "🏫", "hawker": "🍜", "retail": "🛍️",
}


def _map_url(town: str) -> str:
    lat, lon = TOWN_COORDS.get(town, DEFAULT_COORD)
    return (
        f"https://www.openstreetmap.org/export/embed.html"
        f"?bbox={lon-0.012},{lat-0.008},{lon+0.012},{lat+0.008}"
        f"&layer=mapnik&marker={lat},{lon}"
    )


def _val_color(label: str) -> str:
    if "Steal" in label:  return "#059E87"
    if "Fair"  in label:  return "#2563eb"
    if "Slight" in label: return "#d97706"
    return "#dc2626"


def _why_match(row, inputs) -> str:
    """Generate a short 'why this matches you' blurb."""
    rank = getattr(inputs, "amenity_rank", [])
    top  = rank[0] if rank else None
    diff = float(row.get("asking_vs_predicted_pct", 0))

    reasons = []
    if diff <= -5:
        reasons.append("priced below model estimate")
    elif diff <= 3:
        reasons.append("fairly priced")

    if top:
        icon  = AMENITY_ICONS.get(top, "")
        label = {"mrt": "MRT access", "bus": "bus connectivity",
                 "healthcare": "healthcare nearby", "schools": "schools nearby",
                 "hawker": "hawker food nearby", "retail": "shopping nearby"}.get(top, top)
        reasons.append(f"{icon} good {label}")

    return "Matches on " + " · ".join(reasons) if reasons else "Good overall fit"


def _build_card_data(df: pd.DataFrame, inputs, unseen_ids: list) -> list:
    cards = []
    df_unseen = df[df["listing_id"].isin(unseen_ids)]
    for _, row in df_unseen.iterrows():
        diff  = float(row.get("asking_vs_predicted_pct", 0))
        label = str(row.get("valuation_label", ""))
        town  = str(row.get("town", ""))
        cards.append({
            "id":         str(row.get("listing_id", "")),
            "town":       town,
            "flat_type":  str(row.get("flat_type", "")),
            "area":       float(row.get("floor_area_sqm", 0)),
            "storey":     str(row.get("storey_range", "")),
            "asking":     int(row.get("asking_price", 0)),
            "predicted":  int(row.get("predicted_price", 0)),
            "diff_pct":   round(diff, 1),
            "label":      label,
            "label_color": _val_color(label),
            "map_url":    _map_url(town),
            "why":        _why_match(row, inputs),
        })
    return cards


def render_listing_tab(listings_df: pd.DataFrame):
    if listings_df is None or listings_df.empty:
        st.info("No listings available. Run a search first.")
        return

    session = get_active_session()
    if session is None:
        st.info("No active search session found.")
        return

    inputs      = session["inputs"]
    unseen_ids  = session["unseen_ids"]
    liked_ids   = session["liked_ids"]
    passed_ids  = session["passed_ids"]

    # ── Compact top-nav strip ──────────────────────────────────────────────
    col_brand, col_saved, col_compare, col_account = st.columns([3, 1, 1, 1])
    with col_brand:
        st.markdown(
            """<div style="font-family:'DM Sans',sans-serif;font-size:1rem;font-weight:800;
                color:#0b132d;letter-spacing:-0.02em;padding:6px 0;">🏠 HomeRun</div>""",
            unsafe_allow_html=True,
        )
    with col_saved:
        if st.button("♥ Saved", key="nav_saved", use_container_width=True):
            st.session_state.active_page = "Saved"
            st.rerun()
    with col_compare:
        if st.button("⚖️ Compare", key="nav_compare", use_container_width=True):
            st.session_state.active_page = "Compare"
            st.rerun()
    with col_account:
        if st.button("👤 Account", key="nav_account", use_container_width=True):
            st.session_state.active_page = "Account"
            st.rerun()

    st.markdown("<hr style='margin:8px 0 12px;border:none;border-top:1px solid #f0f4f8;'>", unsafe_allow_html=True)

    # ── Deck exhausted ───────────────────────────────────────────────────────
    if not unseen_ids:
        _render_deck_done(session, listings_df)
        return

    # ── Build cards from unseen ──────────────────────────────────────────────
    cards      = _build_card_data(listings_df, inputs, unseen_ids)
    cards_json = json.dumps(cards)
    session_id = session["session_id"]

    # ── Swipe iframe ─────────────────────────────────────────────────────────
    html = _build_swipe_html(cards_json)
    components.html(html, height=720, scrolling=False)

    # ── Match score bar + amenity badges (btogether-style) ──────────────────
    top_card = None
    if unseen_ids:
        top_row = listings_df[listings_df["listing_id"] == unseen_ids[0]]
        if not top_row.empty:
            top_card = top_row.iloc[0]

    if top_card is not None:
        score = float(top_card.get("overall_value_score", 0))
        color = "#059E87" if score >= 75 else "#d97706" if score >= 50 else "#FF4458"
        st.markdown(
            f"""<div style="margin:8px 0 10px;">
                <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.08em;color:#94a3b8;margin-bottom:5px;">🎯 Match Score</div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="flex:1;height:8px;border-radius:4px;background:#f1f5f9;overflow:hidden;">
                        <div style="width:{score}%;height:100%;background:{color};border-radius:4px;
                             transition:width 0.4s;"></div>
                    </div>
                    <span style="font-weight:800;color:{color};font-size:0.88rem;min-width:2.8rem;">{score:.0f}%</span>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # Amenity badges row — pull from session amenity weights
        amenity_scores = {k: float(top_card.get(f"{k}_score", 0)) for k in AMENITY_ICONS}
        badges = ""
        for key, icon in AMENITY_ICONS.items():
            val = amenity_scores.get(key, 0)
            good = val >= 60
            border = "#059E87" if good else "#d97706"
            label = {"mrt": "MRT", "bus": "Bus", "healthcare": "Health",
                     "schools": "Schools", "hawker": "Hawker", "retail": "Shops"}.get(key, key)
            badges += (
                f'<span style="display:inline-flex;align-items:center;gap:4px;'
                f'padding:4px 9px;border-radius:999px;border:1.5px solid {border};'
                f'font-size:0.72rem;font-weight:700;color:#334155;white-space:nowrap;">'
                f'{icon} {label}</span>'
            )
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;">{badges}</div>',
            unsafe_allow_html=True,
        )

    # ── Handle swipe events via button callbacks ─────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    top_id_for_controls = unseen_ids[0] if unseen_ids else None
    _render_swipe_controls(session_id, top_id_for_controls)

    # "View details" for the top card
    if top_id_for_controls:
        _, detail_col, _ = st.columns([2, 1.5, 2])
        with detail_col:
            if st.button("View details", key=f"deck_detail_{top_id_for_controls}",
                         use_container_width=True):
                show_listing_detail(top_id_for_controls)

    # ── Saved count banner ───────────────────────────────────────────────────
    if liked_ids or passed_ids:
        total = len(listings_df)
        seen  = len(liked_ids) + len(passed_ids)
        st.markdown(
            f"<p style='text-align:center;font-size:0.78rem;color:#9ca3af;"
            f"margin-top:0.4rem;'>{seen} of {total} seen · "
            f"{len(liked_ids)} saved · {len(passed_ids)} passed</p>",
            unsafe_allow_html=True,
        )


def _render_swipe_controls(session_id: str, top_id: str | None):
    """Streamlit button fallbacks that actually record swipes in session state."""
    if not top_id:
        return

    col1, col2, col3, col4, col5 = st.columns([1, 1, 0.6, 1, 1])
    with col2:
        if st.button("✕  Pass", key=f"pass_{top_id}", use_container_width=True):
            record_swipe(session_id, top_id, "left")
            st.rerun()
    with col3:
        st.markdown("<div style='height:38px'></div>", unsafe_allow_html=True)
    with col4:
        if st.button("♥  Save", key=f"save_{top_id}", type="primary",
                     use_container_width=True):
            record_swipe(session_id, top_id, "right")
            st.rerun()

    # Super-save as a smaller secondary row
    _, mid, _ = st.columns([2, 1, 2])
    with mid:
        if st.button("⭐ Super", key=f"super_{top_id}", use_container_width=True):
            record_swipe(session_id, top_id, "up")
            st.rerun()


def _render_deck_done(session: dict, listings_df: pd.DataFrame):
    liked   = session["liked_ids"]
    supers  = session["super_ids"]
    passed  = session["passed_ids"]

    st.markdown(
        f"""
        <div style="text-align:center;padding:2rem 1rem;">
            <div style="font-size:3rem;margin-bottom:0.8rem;">🎉</div>
            <h2 style="font-size:1.6rem;font-weight:800;letter-spacing:-0.03em;
                       color:#0f172a;margin-bottom:0.4rem;">You've seen them all</h2>
            <p style="font-size:0.88rem;color:#9ca3af;margin-bottom:1.6rem;">
                Head to the <strong>Saved</strong> tab to review your picks.
            </p>
            <div style="display:flex;gap:24px;justify-content:center;margin-bottom:1.8rem;">
                <div style="text-align:center;">
                    <div style="font-size:2rem;font-weight:800;color:#059E87;">{len(liked)}</div>
                    <div style="font-size:0.72rem;color:#9ca3af;font-weight:600;
                         text-transform:uppercase;letter-spacing:0.06em;">Saved</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:2rem;font-weight:800;color:#d97706;">{len(supers)}</div>
                    <div style="font-size:0.72rem;color:#9ca3af;font-weight:600;
                         text-transform:uppercase;letter-spacing:0.06em;">Super-saved</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:2rem;font-weight:800;color:#9ca3af;">{len(passed)}</div>
                    <div style="font-size:0.72rem;color:#9ca3af;font-weight:600;
                         text-transform:uppercase;letter-spacing:0.06em;">Passed</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Review saved →", type="primary", use_container_width=True):
            st.session_state.active_page = "Saved"
            st.rerun()
    with c2:
        if st.button("Restart deck", use_container_width=True):
            # Reset unseen to full listing set
            for s in st.session_state.search_sessions:
                if s["session_id"] == session["session_id"]:
                    s["unseen_ids"] = list(listings_df["listing_id"].values)
                    s["liked_ids"]  = []
                    s["super_ids"]  = []
                    s["passed_ids"] = []
            st.rerun()

    # Show saved flats preview
    if liked:
        st.markdown("---")
        _render_saved_preview(session, listings_df)


def _render_saved_preview(session: dict, listings_df: pd.DataFrame):
    liked  = session["liked_ids"]
    supers = session["super_ids"]
    st.markdown(
        "<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.08em;color:#059E87;margin-bottom:0.8rem;'>"
        f"Saved from this session ({len(liked)})</p>",
        unsafe_allow_html=True,
    )
    saved_df = listings_df[listings_df["listing_id"].isin(liked)]
    for _, row in saved_df.iterrows():
        is_super  = row["listing_id"] in supers
        badge     = "⭐ Super-saved" if is_super else "♥ Saved"
        badge_col = "#d97706" if is_super else "#059E87"
        diff      = float(row.get("asking_vs_predicted_pct", 0))
        tag       = valuation_tag_html(row.get("valuation_label", ""))

        st.markdown(
            f"""
            <div class="nw-listing">
                <div class="nw-listing-header">
                    <div>
                        <div class="nw-listing-id">{row['listing_id']} · {row['town']}</div>
                        <div class="nw-listing-meta">
                            {row['flat_type']} · {row.get('floor_area_sqm','')} sqm
                            · Storey {row.get('storey_range','')}
                        </div>
                    </div>
                    <div>
                        <div class="nw-listing-asking">{fmt_sgd(row['asking_price'])}</div>
                        <div class="nw-listing-predicted">
                            Predicted: {fmt_sgd(row['predicted_price'])}
                        </div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-top:8px;flex-wrap:wrap;">
                    {tag}
                    <span style="font-size:0.78rem;color:#9ca3af;">{diff:+.1f}% vs model</span>
                    <span style="font-size:0.74rem;font-weight:700;
                          color:{badge_col};margin-left:auto;">{badge}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("View details →", key=f"preview_detail_{row['listing_id']}",
                     use_container_width=True):
            show_listing_detail(str(row["listing_id"]))


def _build_swipe_html(cards_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{font-family:'DM Sans',-apple-system,sans-serif;background:#f5f7fa;overflow:hidden}}
#app{{display:flex;flex-direction:column;align-items:center;padding:16px 16px 20px;}}
.hdr{{width:100%;max-width:400px;display:flex;justify-content:space-between;
      align-items:center;margin-bottom:12px;}}
.hdr-title{{font-size:1rem;font-weight:800;color:#0f172a;}}
.hdr-count{{font-size:0.75rem;font-weight:600;color:#9ca3af;background:#fff;
            border:1px solid #e4e7ed;padding:3px 9px;border-radius:999px;}}
#stack{{position:relative;width:100%;max-width:400px;height:520px;margin-bottom:16px;}}
.card{{position:absolute;inset:0;background:#fff;border-radius:22px;
       box-shadow:0 4px 24px rgba(0,0,0,0.10),0 1px 4px rgba(0,0,0,0.06);
       overflow:hidden;cursor:grab;user-select:none;touch-action:none;
       transform-origin:50% 110%;will-change:transform;}}
.card:active{{cursor:grabbing}}
.card.gone{{display:none!important}}
.card:nth-child(2){{transform:scale(0.95) translateY(12px);z-index:1;pointer-events:none;transition:transform 0.15s ease;}}
.card:nth-child(3){{transform:scale(0.90) translateY(22px);z-index:0;pointer-events:none;transition:transform 0.15s ease;}}
.card:nth-child(n+4){{display:none}}
.card-map{{width:100%;height:210px;overflow:hidden;background:#e8f0e8;position:relative;}}
.card-map iframe{{width:100%;height:calc(100% + 30px);border:none;pointer-events:none;margin-top:-30px;}}
.card-map-fade{{position:absolute;inset:0;
  background:linear-gradient(to bottom,transparent 50%,rgba(255,255,255,0.92) 100%);
  pointer-events:none;}}
.card-body{{padding:14px 18px 16px;}}
.card-town{{font-size:1.2rem;font-weight:800;color:#0f172a;letter-spacing:-0.03em;margin-bottom:1px;}}
.card-type{{font-size:0.78rem;color:#9ca3af;font-weight:500;margin-bottom:10px;}}
.card-tag{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:0.74rem;
           font-weight:700;margin-bottom:10px;border:1.5px solid;}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px;}}
.stat{{background:#f7f8fa;border-radius:9px;padding:6px 8px;text-align:center;}}
.stat-v{{font-size:0.86rem;font-weight:700;color:#0f172a;}}
.stat-k{{font-size:0.62rem;color:#9ca3af;font-weight:600;text-transform:uppercase;
          letter-spacing:0.05em;margin-top:1px;}}
.price-row{{display:flex;align-items:baseline;gap:8px;margin-bottom:6px;}}
.asking{{font-size:1.3rem;font-weight:800;color:#0f172a;letter-spacing:-0.03em;}}
.predicted{{font-size:0.78rem;color:#9ca3af;}}
.why{{font-size:0.76rem;color:#059E87;font-weight:600;}}
.ov{{position:absolute;inset:0;border-radius:22px;display:flex;align-items:center;
     justify-content:center;opacity:0;pointer-events:none;z-index:10;
     font-size:2rem;font-weight:800;letter-spacing:0.04em;}}
.ov-r{{background:rgba(68,214,173,0.18);color:#059E87;border:3px solid #059E87;}}
.ov-l{{background:rgba(255,68,88,0.14);color:#FF4458;border:3px solid #FF4458;}}
.ov-u{{background:rgba(78,203,241,0.18);color:#0ea5e9;border:3px solid #4ECBF1;}}
.dots{{display:flex;gap:5px;justify-content:center;margin-bottom:10px;}}
.dot{{width:6px;height:6px;border-radius:50%;background:#e4e7ed;transition:all 0.2s;}}
.dot.cur{{background:#059E87;width:16px;border-radius:3px;}}
.dot.done{{background:#a7f3d0;}}
#empty{{display:none;flex-direction:column;align-items:center;text-align:center;
        padding:2rem 1rem;max-width:400px;width:100%;}}
.em-icon{{font-size:2.5rem;margin-bottom:8px;}}
.em-title{{font-size:1.3rem;font-weight:800;color:#0f172a;letter-spacing:-0.03em;margin-bottom:4px;}}
.em-sub{{font-size:0.84rem;color:#9ca3af;margin-bottom:1rem;}}
</style>
</head>
<body>
<div id="app">
  <div class="hdr">
    <div class="hdr-title">Discover</div>
    <div class="hdr-count" id="ctr">— / —</div>
  </div>
  <div class="dots" id="dots"></div>
  <div id="stack"></div>
  <div id="empty">
    <div class="em-icon">✅</div>
    <div class="em-title">All caught up!</div>
    <div class="em-sub">Use the buttons below to review your saved flats.</div>
  </div>
</div>
<script>
const CARDS={cards_json};
let idx=0;
function buildDots(){{
  const el=document.getElementById('dots');
  el.innerHTML='';
  CARDS.forEach((_,i)=>{{
    const d=document.createElement('div');
    d.className='dot'+(i===0?' cur':'');
    d.id='d'+i; el.appendChild(d);
  }});
}}
function tickDot(i,dir){{
  const d=document.getElementById('d'+i);
  if(d) d.className='dot done';
  const n=document.getElementById('d'+(i+1));
  if(n) n.className='dot cur';
}}
function updateCtr(){{
  document.getElementById('ctr').textContent=(idx+1)+' / '+CARDS.length;
}}
function cardHTML(c,i){{
  const ds=c.diff_pct>=0?'+':'';
  const el=document.createElement('div');
  el.className='card'; el.dataset.i=i;
  el.innerHTML=`
    <div class="ov ov-r" id="or${{i}}">SAVE ✓</div>
    <div class="ov ov-l" id="ol${{i}}">PASS ✕</div>
    <div class="ov ov-u" id="ou${{i}}">⭐ SUPER</div>
    <div class="card-map">
      <iframe src="${{c.map_url}}" loading="lazy"></iframe>
      <div class="card-map-fade"></div>
    </div>
    <div class="card-body">
      <div class="card-town">${{c.town}}</div>
      <div class="card-type">${{c.flat_type}}</div>
      <div class="card-tag" style="color:${{c.label_color}};border-color:${{c.label_color}};background:${{c.label_color}}18">${{c.label}}</div>
      <div class="stats">
        <div class="stat"><div class="stat-v">${{c.area}}<small style="font-size:0.6rem"> sqm</small></div><div class="stat-k">Area</div></div>
        <div class="stat"><div class="stat-v">${{c.storey}}</div><div class="stat-k">Storey</div></div>
        <div class="stat"><div class="stat-v">${{ds}}${{c.diff_pct}}%</div><div class="stat-k">vs est.</div></div>
      </div>
      <div class="price-row">
        <div class="asking">S$${{c.asking.toLocaleString()}}</div>
        <div class="predicted">est. S$${{c.predicted.toLocaleString()}}</div>
      </div>
      <div class="why">${{c.why}}</div>
    </div>`;
  return el;
}}
function buildStack(){{
  const s=document.getElementById('stack');
  s.innerHTML='';
  for(let i=Math.min(idx+2,CARDS.length-1);i>=idx;i--){{
    s.appendChild(cardHTML(CARDS[i],i));
  }}
  updateCtr(); attachDrag();
}}
function doSwipe(dir){{
  if(idx>=CARDS.length)return;
  const s=document.getElementById('stack');
  const top=s.querySelector('.card:first-child');
  if(!top)return;
  // Promote second card immediately so it animates in sync
  const behind=s.querySelector('.card:nth-child(2)');
  if(behind){{
    behind.style.transition='transform 0.32s ease';
    behind.style.transform='scale(1) translateY(0)';
  }}
  const tx=dir==='right'?640:dir==='left'?-640:0;
  const ty=dir==='up'?-720:0;
  const r=dir==='right'?22:dir==='left'?-22:0;
  top.style.transition='transform 0.32s cubic-bezier(0.25,0.46,0.45,0.94),opacity 0.28s';
  top.style.transform=`translate(${{tx}}px,${{ty}}px) rotate(${{r}}deg)`;
  top.style.opacity='0';
  tickDot(idx,dir);
  window.parent.postMessage({{type:'nw_swipe',dir,id:CARDS[idx].id}},'*');
  idx++;
  setTimeout(()=>{{
    top.remove();
    if(idx<CARDS.length){{buildStack();}}
    else{{
      document.getElementById('stack').style.display='none';
      document.getElementById('empty').style.display='flex';
      document.getElementById('ctr').textContent='Done';
      window.parent.postMessage({{type:'nw_deck_done'}},'*');
    }}
  }},310);
}}
function attachDrag(){{
  const s=document.getElementById('stack');
  const card=s.querySelector('.card:first-child');
  if(!card)return;
  let sx=0,sy=0,drag=false;
  card.addEventListener('mousedown',e=>{{sx=e.clientX;sy=e.clientY;drag=true;card.style.transition='none';}});
  window.addEventListener('mousemove',e=>{{if(!drag)return;move(e.clientX,e.clientY);}});
  window.addEventListener('mouseup',  e=>{{if(!drag)return;drag=false;end(e.clientX,e.clientY);}});
  card.addEventListener('touchstart',e=>{{const t=e.touches[0];sx=t.clientX;sy=t.clientY;drag=true;card.style.transition='none';}},{{passive:true}});
  card.addEventListener('touchmove', e=>{{if(!drag)return;const t=e.touches[0];move(t.clientX,t.clientY);e.preventDefault();}},{{passive:false}});
  card.addEventListener('touchend',  e=>{{if(!drag)return;drag=false;const t=e.changedTouches[0];end(t.clientX,t.clientY);}});
  function move(x,y){{
    const dx=x-sx,dy=y-sy,rot=dx*0.07;
    card.style.transform=`translate(${{dx}}px,${{dy}}px) rotate(${{rot}}deg)`;
    // Scale up the card beneath as top card moves
    const behind=s.querySelector('.card:nth-child(2)');
    if(behind){{
      const progress=Math.min(1,Math.sqrt(dx*dx+dy*dy)/120);
      const sc=0.95+(0.05*progress),ty=12-(12*progress);
      behind.style.transform=`scale(${{sc}}) translateY(${{ty}}px)`;
    }}
    const i=card.dataset.i;
    const aX=Math.abs(dx),aY=Math.abs(dy),th=50;
    const r=document.getElementById('or'+i),l=document.getElementById('ol'+i),u=document.getElementById('ou'+i);
    if(dy<-th&&aX<aY){{r.style.opacity=0;l.style.opacity=0;u.style.opacity=Math.min(1,(-dy-th)/60);}}
    else if(dx>th){{l.style.opacity=0;u.style.opacity=0;r.style.opacity=Math.min(1,(dx-th)/60);}}
    else if(dx<-th){{r.style.opacity=0;u.style.opacity=0;l.style.opacity=Math.min(1,(-dx-th)/60);}}
    else{{r.style.opacity=0;l.style.opacity=0;u.style.opacity=0;}}
  }}
  function end(x,y){{
    const dx=x-sx,dy=y-sy,th=80;
    if(dy<-th&&Math.abs(dx)<Math.abs(dy))doSwipe('up');
    else if(dx>th)doSwipe('right');
    else if(dx<-th)doSwipe('left');
    else{{
      card.style.transition='transform 0.28s ease';
      card.style.transform='';
      // Reset second card
      const behind=s.querySelector('.card:nth-child(2)');
      if(behind){{behind.style.transform='scale(0.95) translateY(12px)';}}
      const i=card.dataset.i;
      ['or','ol','ou'].forEach(p=>{{const el=document.getElementById(p+i);if(el)el.style.opacity=0;}});
    }}
  }}
}}
// Auto-resize
function resize(){{window.parent.postMessage({{type:'streamlit:setFrameHeight',height:document.body.scrollHeight}},'*');}}
buildDots(); buildStack();
window.addEventListener('load',resize); setTimeout(resize,300); setTimeout(resize,700);
</script>
</body>
</html>"""
