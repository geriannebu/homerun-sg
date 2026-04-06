"""
app.py — HomeRun SG

Flow:
  1. Landing page  → "Get Started" opens an auth dialog (create account / log in)
  2. Onboarding    → step-by-step preferences
  3. Auto-search   → deck generated from prefs
  4. Discover      → swipe deck (primary screen)
  5. Saved         → cross-session saved flats
  6. Compare       → side-by-side comparison
  7. Account       → preferences + session history
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import pandas as pd
from pathlib import Path
from PIL import Image as _PILImage

def _resolve_logo() -> str:
    """Returns the path to the horizontal logo with text for the UI header."""
    base = Path(__file__).parent / "frontend" / "assets"
    p = base / "homerun_logo.png"
    return str(p) if p.exists() else ""

def _load_page_icon():
    """Returns a square-cropped 64×64 image for the browser tab (favicon)."""
    base = Path(__file__).parent / "frontend" / "assets"
    p = base / "homerun_icon.png"

    if not p.exists():
        return None

    img = _PILImage.open(p).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top  = (h - side) // 2
    img  = img.crop((left, top, left + side, top + side))
    return img.resize((64, 64), _PILImage.LANCZOS)

_LOGO_PATH   = _resolve_logo()
_PAGE_ICON   = _load_page_icon()


def get_logo_img_tag(height: int = 40, use_icon: bool = False) -> str:
    """
    Helper to return a base64 encoded img tag.
    Fixes the TypeError by accepting 'use_icon'.
    """
    base = Path(__file__).parent / "frontend" / "assets"
    filename = "homerun_icon.png" if use_icon else "homerun_logo.png"
    p = base / filename

    if not p.exists():
        return ""

    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f'<img src="data:image/png;base64,{data}" height="{height}px" style="vertical-align: middle;">'


from frontend.styles.css import inject_css
from frontend.state.session import init_session_state, create_search_session, get_active_session
from frontend.state.user_store import load_user_store_into_session, save_user_store_from_session

from frontend.components.onboarding import (
    clear_preferences_from_session,
    render_onboarding,
    build_inputs_from_prefs,
    restore_preferences_for_user,
    persist_current_preferences_for_user,
)

from backend.services.predictor_service import get_prediction_bundle
from backend.services.map_service import get_map_bundle

from frontend.pages.flat_outputs.best_matches import render_listing_tab
from frontend.pages.saved import render_saved_page
from frontend.pages.comparison_tool import render_comparison_page
from frontend.pages.account import render_account_page
from frontend.pages.explore import render_explore_page
from data.load_data import load_all_data


st.set_page_config(
    page_title="HomeRun SG",
    page_icon=_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = ["Discover", "Saved", "Compare", "Explore", "Account"]


# ── Auth dialog ───────────────────────────────────────────────────────────────

@st.dialog("Welcome to HomeRun", width="small")
def _show_auth_dialog(initial_tab: str = "create"):
    st.markdown(
        f"""
        <div style="text-align:center;margin-bottom:1.4rem;">
            <div style="margin-bottom:0.9rem;">
                {get_logo_img_tag(50)} 
            </div>
            <p style="font-size:0.88rem;color:#6b7280;margin:0;">
                Your personalised HDB flat finder
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    create_tab, login_tab = st.tabs(["Create account", "Log in"])

    with create_tab:
        email    = st.text_input("Email", placeholder="you@email.com",
                                 key="dialog_create_email")
        password = st.text_input("Password", type="password",
                                 placeholder="Choose a password",
                                 key="dialog_create_password")
        st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)
        if st.button("Create account & get started →", type="primary",
                     use_container_width=True, key="dialog_create_btn"):
            if not email or not password:
                st.warning("Please fill in both fields.")
            elif email in st.session_state.users:
                st.warning("An account with this email already exists. Try logging in.")
            else:
                st.session_state.users[email] = {"password": password, "preferences": {}}
                st.session_state.user_histories[email] = []
                save_user_store_from_session()
                st.session_state.current_user = email
                clear_preferences_from_session()
                st.session_state.onboarding_complete = False
                st.rerun()

    with login_tab:
        l_email    = st.text_input("Email", key="dialog_login_email")
        l_password = st.text_input("Password", type="password",
                                   key="dialog_login_password")
        st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)
        if st.button("Log in →", type="primary",
                     use_container_width=True, key="dialog_login_btn"):
            users = st.session_state.users
            if l_email in users and users[l_email]["password"] == l_password:
                st.session_state.current_user = l_email
                restore_preferences_for_user(l_email)
                st.rerun()
            else:
                st.error("Invalid email or password.")

    st.markdown(
        "<div style='display:flex;align-items:center;gap:8px;margin:1rem 0 0.6rem;'>"
        "<div style='flex:1;height:1px;background:rgba(0,0,0,0.08);'></div>"
        "<span style='font-size:0.72rem;color:#b0b0c0;white-space:nowrap;'>or</span>"
        "<div style='flex:1;height:1px;background:rgba(0,0,0,0.08);'></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Continue as Guest →", use_container_width=True, key="dialog_guest_btn"):
        st.session_state.current_user = "__guest__"
        clear_preferences_from_session()
        st.session_state.onboarding_complete = False
        st.rerun()
    st.markdown(
        "<p style='text-align:center;font-size:0.72rem;color:#b0b0c0;"
        "margin-top:0.5rem;'>Guest data is not saved between sessions.</p>",
        unsafe_allow_html=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_session_state()
    load_user_store_into_session()
    inject_css()

    # ── 1. Auth gate ──────────────────────────────────────────────────────────
    if not st.session_state.get("current_user"):
        _render_landing_page()
        return

    # ── 2. Sidebar ────────────────────────────────────────────────────────────
    _render_sidebar()
    page = st.session_state.active_page

    # ── 3. Onboarding gate ────────────────────────────────────────────────────
    if page == "Discover" and not st.session_state.get("onboarding_complete"):
        _run_onboarding()
        return

    # ── 4. Route ──────────────────────────────────────────────────────────────
    if page == "Discover":
        _render_discover()
    elif page == "Saved":
        render_saved_page()
    elif page == "Compare":
        _render_compare()
    elif page == "Explore":
        _render_explore()
    elif page == "Account":
        render_account_page()
   


# ── Landing page ──────────────────────────────────────────────────────────────

def _render_landing_page():
    """Landing page — hero, feature sections, reviews, CTA."""
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(
            f"""
            <div style="padding:5rem 0 1.5rem;text-align:center;">
                <div style="display:inline-block;border-radius:32px;overflow:hidden;
                            box-shadow:0 0 0 1px rgba(255,68,88,0.1),
                                       0 16px 48px rgba(255,68,88,0.18);
                            margin-bottom:1.6rem;">
                    {get_logo_img_tag(192)}
                </div>
                <p style="font-size:0.95rem;color:#94a3b8;font-weight:500;
                          margin:0.4rem 0 2rem;line-height:1.6;">
                    Match. Price. Decide.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Get Started →", type="primary",
                     use_container_width=True, key="landing_get_started"):
            _show_auth_dialog()

        st.markdown(
            "<p style='text-align:center;font-size:0.78rem;color:#b0b0c0;"
            "margin-top:0.8rem;'>Already have an account? "
            "Click Get Started and switch to Log in.</p>",
            unsafe_allow_html=True,
        )

    # ── Floating CTA (appears on scroll) ──────────────────────────────────────

    st.markdown("""
    <style>
    #hr-float-btn {
      position:fixed; bottom:40px; right:40px; z-index:999999;
      background:linear-gradient(130deg,#FF4458 0%,#FF6B6B 100%);
      color:#fff; border:none; border-radius:999px;
      padding:16px 32px; font-family:'DM Sans',-apple-system,sans-serif;
      font-size:15px; font-weight:800; cursor:pointer;
      box-shadow:0 10px 30px rgba(255,68,88,0.45);
      visibility: hidden; opacity:0;
      transform:translateY(20px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    #hr-float-btn.hr-show {
      visibility: visible; opacity:1; transform:translateY(0);
    }
    #hr-float-btn:hover {
      box-shadow:0 15px 45px rgba(255,68,88,0.6);
      transform:translateY(-3px);
    }
    </style>
    <button id="hr-float-btn" onclick="window.scrollTo({top:0, behavior:'smooth'})">Get Started →</button>
    <script>
    (function(){
      // Targets the main Streamlit window to detect scrolling correctly
      const btn = window.parent.document.getElementById('hr-float-btn') || document.getElementById('hr-float-btn');
      window.parent.addEventListener('scroll', function() {
        if (window.parent.scrollY > 200) btn.classList.add('hr-show');
        else btn.classList.remove('hr-show');
      }, {passive:true});
    })();
    </script>
    """, unsafe_allow_html=True)

    # ── How it works ──────────────────────────────────────────────────────────
    components.html("""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{overflow:hidden}body{font-family:'DM Sans',-apple-system,sans-serif;background:#fff;}
</style></head><body>
    <div style="padding:48px 40px 48px;background:#fff;">
      <div style="max-width:960px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:48px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.16em;
                      text-transform:uppercase;color:#FF4458;margin-bottom:14px;">
            HOW IT WORKS
          </div>
          <h2 style="font-family:'DM Sans',-apple-system,sans-serif;font-size:2.4rem;
                     font-weight:800;color:#0b132d;letter-spacing:-0.035em;margin:0;">
            Your dream flat, in 4 easy steps
          </h2>
          <p style="font-size:1rem;color:#64748b;font-weight:500;margin:14px auto 0;
                    max-width:480px;line-height:1.7;">
            No spreadsheets. No cold calls. Just smart, personalised recommendations.
          </p>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:24px;">

          <div style="background:#fafafa;border:1px solid #f0f0f0;border-radius:22px;
                      padding:32px 28px;display:flex;gap:20px;align-items:flex-start;">
            <div style="flex-shrink:0;width:48px;height:48px;border-radius:14px;
                        background:#FFF0F1;border:1.5px solid rgba(255,68,88,0.20);
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.4rem;">🎯</div>
            <div>
              <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
                          text-transform:uppercase;color:#FF4458;margin-bottom:6px;">Step 1</div>
              <div style="font-size:1.05rem;font-weight:800;color:#0b132d;margin-bottom:8px;">
                Take the Smart Quiz
              </div>
              <div style="font-size:0.875rem;color:#64748b;line-height:1.65;font-weight:500;">
                Answer a short personality-style quiz about your lifestyle, commute habits,
                and priorities. Takes under 2 minutes.
              </div>
            </div>
          </div>

          <div style="background:#fafafa;border:1px solid #f0f0f0;border-radius:22px;
                      padding:32px 28px;display:flex;gap:20px;align-items:flex-start;">
            <div style="flex-shrink:0;width:48px;height:48px;border-radius:14px;
                        background:#FFF0F1;border:1.5px solid rgba(255,68,88,0.20);
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.4rem;">💘</div>
            <div>
              <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
                          text-transform:uppercase;color:#FF4458;margin-bottom:6px;">Step 2</div>
              <div style="font-size:1.05rem;font-weight:800;color:#0b132d;margin-bottom:8px;">
                Swipe Through Matches
              </div>
              <div style="font-size:0.875rem;color:#64748b;line-height:1.65;font-weight:500;">
                Browse curated HDB listings Tinder-style. Swipe right to save, left to skip —
                your shortlist builds itself.
              </div>
            </div>
          </div>

          <div style="background:#fafafa;border:1px solid #f0f0f0;border-radius:22px;
                      padding:32px 28px;display:flex;gap:20px;align-items:flex-start;">
            <div style="flex-shrink:0;width:48px;height:48px;border-radius:14px;
                        background:#FFF0F1;border:1.5px solid rgba(255,68,88,0.20);
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.4rem;">💰</div>
            <div>
              <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
                          text-transform:uppercase;color:#FF4458;margin-bottom:6px;">Step 3</div>
              <div style="font-size:1.05rem;font-weight:800;color:#0b132d;margin-bottom:8px;">
                Get the Fair Price
              </div>
              <div style="font-size:0.875rem;color:#64748b;line-height:1.65;font-weight:500;">
                Our ML model predicts the true resale value of each flat so you always
                know if you're getting a fair deal.
              </div>
            </div>
          </div>

          <div style="background:#fafafa;border:1px solid #f0f0f0;border-radius:22px;
                      padding:32px 28px;display:flex;gap:20px;align-items:flex-start;">
            <div style="flex-shrink:0;width:48px;height:48px;border-radius:14px;
                        background:#FFF0F1;border:1.5px solid rgba(255,68,88,0.20);
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.4rem;">⚖️</div>
            <div>
              <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
                          text-transform:uppercase;color:#FF4458;margin-bottom:6px;">Step 4</div>
              <div style="font-size:1.05rem;font-weight:800;color:#0b132d;margin-bottom:8px;">
                Compare &amp; Decide
              </div>
              <div style="font-size:0.875rem;color:#64748b;line-height:1.65;font-weight:500;">
                Put your saved flats side-by-side across price, location, and key metrics.
                Make the call with confidence.
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
<script>(function(){function r(){var h=document.body.offsetHeight;window.parent.postMessage({type:'streamlit:setFrameHeight',height:Math.ceil(h)},'*');}r();window.addEventListener('load',r);if(document.fonts&&document.fonts.ready){document.fonts.ready.then(r);}setTimeout(r,150);setTimeout(r,600);})();</script>
</body></html>""", height=700, scrolling=False)

    # ── Reviews ───────────────────────────────────────────────────────────────
    # ── Reviews (Updated Padding) ───────────────────────────────────────────────
    components.html("""<!DOCTYPE html>
    <html><head><meta charset="utf-8"/>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    html{overflow:hidden}
    body{font-family:'DM Sans',-apple-system,sans-serif;background:#f9f9f9;}
    .carousel{display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;
    -webkit-overflow-scrolling:touch;padding:4px 40px 20px;
    scrollbar-width:thin;scrollbar-color:#FF4458 #f0f0f0;}
    .carousel::-webkit-scrollbar{height:4px;}
    .carousel::-webkit-scrollbar-track{background:#f0f0f0;border-radius:2px;}
    .carousel::-webkit-scrollbar-thumb{background:#FF4458;border-radius:2px;}
    .card{flex:0 0 calc(25% - 12px);scroll-snap-align:start;background:#fff;
    border-radius:18px;padding:20px 18px;
    box-shadow:0 2px 16px rgba(0,0,0,0.06);border:1px solid #f0f0f0;}
    .avatar{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;
    justify-content:center;color:#fff;font-weight:800;font-size:0.88rem;flex-shrink:0;}
    .gsvg{margin-left:auto;flex-shrink:0;}
    </style></head><body>
    <div style="padding:40px 0 80px;background:#f9f9f9;"> <div style="text-align:center;margin-bottom:28px;padding:0 40px;">
        <div style="font-size:11px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#FF4458;margin-bottom:10px;">REVIEWS</div>
        <h2 style="font-size:2rem;font-weight:800;color:#0b132d;letter-spacing:-0.035em;margin:0 0 6px;">Loved by flat hunters across Singapore</h2>
        <div style="color:#FBBC04;font-size:1.25rem;letter-spacing:2px;">★★★★★</div>
        <p style="font-size:0.85rem;color:#64748b;font-weight:500;margin:6px 0 0;">4.9 out of 5 &nbsp;·&nbsp; 8 reviews</p>
    </div>
    <div class="carousel">
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#4285F4;">L</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Lucille</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★★</div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"Finally found a resale flat that fits my budget without the stress. HomeRun made the whole process so much more manageable!"</p>
      <div style="font-size:0.7rem;color:#9ca3af;">March 2025</div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#34A853;">N</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Nadia</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★★</div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"The price predictions are scarily accurate. Helped me negotiate a much better deal on my Tampines resale — saved thousands."</p>
      <div style="font-size:0.7rem;color:#9ca3af;">February 2025</div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#EA4335;">X</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Xinyan</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★★</div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"Love the swipe feature — it made browsing flats actually fun. The UX is really clean and nothing feels overwhelming."</p>
      <div style="font-size:0.7rem;color:#9ca3af;">January 2025</div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#FBBC04;">S</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Sooah</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★★</div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"As a first-time buyer I had no clue what a fair price even meant. HomeRun gave me so much confidence going into viewings."</p>
      <div style="font-size:0.7rem;color:#9ca3af;">March 2025</div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#9c27b0;">C</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Camille</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★★</div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"The comparison tool is a total game changer. Side-by-side metrics saved me hours of research across PropertyGuru listings."</p>
      <div style="font-size:0.7rem;color:#9ca3af;">February 2025</div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#00897B;">E</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Emma</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★<span style="color:#d1d5db;">★</span></div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"Really clean interface and the quiz is super intuitive. Would love more town options but overall it's brilliant."</p>
      <div style="font-size:0.7rem;color:#9ca3af;">January 2025</div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#FF4458;">G</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Gerianne</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★★</div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"Showed this to my parents and they were genuinely impressed. Beats scrolling PropertyGuru for hours — highly recommend!"</p>
      <div style="font-size:0.7rem;color:#9ca3af;">March 2025</div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:12px;">
        <div class="avatar" style="background:#F06292;">A</div>
        <div><div style="font-weight:700;font-size:0.85rem;color:#0b132d;">Abigail</div><div style="color:#FBBC04;font-size:0.75rem;">★★★★★</div></div>
        <svg class="gsvg" width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC04"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </div>
      <p style="font-size:0.81rem;color:#374151;line-height:1.6;margin:0 0 10px;font-weight:500;">"The quiz took 2 minutes and gave me spot-on recommendations. I was genuinely surprised by how accurate the suggestions were."</p>
      <div style="font-size:0.7rem;color:#9ca3af;">February 2025</div>
    </div>
    </div>
    </div>
    <script>(function(){function r(){var h=document.body.offsetHeight;window.parent.postMessage({type:'streamlit:setFrameHeight',height:Math.ceil(h)},'*');}r();window.addEventListener('load',r);if(document.fonts&&document.fonts.ready){document.fonts.ready.then(r);}setTimeout(r,150);setTimeout(r,600);})();</script>
    </body></html>""", height=520, scrolling=False)

    # ── Bottom CTA ────────────────────────────────────────────────────────────
    components.html("""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{font-family:'DM Sans',-apple-system,sans-serif;background:#fff;}
</style></head><body>
    <div style="padding:64px 40px 72px;background:#fff;text-align:center;">
      <h2 style="font-family:'DM Sans',-apple-system,sans-serif;font-size:2rem;
                 font-weight:800;color:#0b132d;letter-spacing:-0.03em;margin:0 0 12px;">
        Ready to find your flat?
      </h2>
      <p style="font-size:0.95rem;color:#64748b;font-weight:500;margin:0;">
        Join thousands of Singaporeans making smarter HDB decisions.
      </p>
    </div>
<script>(function(){function r(){var h=document.body.scrollHeight;window.parent.postMessage({type:'streamlit:setFrameHeight',height:h},'*');}r();window.addEventListener('load',r);if(document.fonts&&document.fonts.ready){document.fonts.ready.then(r);}setTimeout(r,200);setTimeout(r,600);})();</script>
</body></html>""", height=180, scrolling=False)


# ── Sidebar ───────────────────────────────────────────────────────────────────

_PAGE_ICONS = {"Discover": "🔥", "Saved": "♥", "Compare": "⚖️", "Explore": "🔎", "Account": "👤"}


def _render_sidebar():
    from frontend.state.session import get_active_session

    # Logo
    try:
        st.logo(_LOGO_PATH, size="large")
    except Exception:
        pass

    logo_html = get_logo_img_tag(36, use_icon=True)
    st.sidebar.markdown(
        f"""
        <div style="padding:1.3rem 1.1rem 1.1rem;
                    border-bottom:1px solid rgba(255,255,255,0.06);
                    display:flex;align-items:center;gap:11px;">
            <div style="flex-shrink:0;width:36px;height:36px;border-radius:10px;
                        overflow:hidden;
                        box-shadow:0 0 0 1px rgba(255,68,88,0.25),
                                   0 0 14px rgba(255,68,88,0.30),
                                   0 0 28px rgba(255,68,88,0.12);">
                {logo_html}
            </div>
            <div style="font-family:'DM Sans',sans-serif;font-size:0.96rem;font-weight:800;
                        color:rgba(255,255,255,0.94);letter-spacing:-0.03em;">HomeRun</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Nav ───────────────────────────────────────────────────────────────────
    st.sidebar.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

    nav_display = [f"{_PAGE_ICONS[p]}  {p}" for p in PAGES]
    displayed = st.sidebar.radio(
        "Nav",
        nav_display,
        index=PAGES.index(st.session_state.active_page),
        label_visibility="collapsed",
    )
    page = PAGES[nav_display.index(displayed)]
    if page != st.session_state.active_page:
        st.session_state.active_page = page
        st.rerun()

    # ── Current deck card ─────────────────────────────────────────────────────
    session = get_active_session()
    if session:
        n_liked = len(session["liked_ids"])
        n_passed = len(session["passed_ids"])
        n_unseen = len(session["unseen_ids"])
        total = n_liked + n_passed + n_unseen
        seen = n_liked + n_passed
        pct = int(seen / total * 100) if total else 0
        circ = 213.6
        arc = round(pct / 100 * circ, 1)

        st.sidebar.markdown(
            f"""
            <div class="hr-deck-card">
                <div class="hr-deck-label">Current deck</div>
                <div class="hr-deck-session-name">{session['label']}</div>
                <div class="hr-deck-ring-row">
                    <svg width="72" height="72" viewBox="0 0 80 80">
                        <circle cx="40" cy="40" r="34" fill="none"
                                stroke="rgba(255,255,255,0.10)" stroke-width="6"/>
                        <circle cx="40" cy="40" r="34" fill="none"
                                stroke="#FF6B6B" stroke-width="6"
                                stroke-dasharray="{arc} {circ}"
                                stroke-linecap="round"
                                transform="rotate(-90 40 40)"/>
                        <text x="40" y="46" text-anchor="middle"
                              fill="white" font-size="15" font-weight="800"
                              font-family="DM Sans, sans-serif">{pct}%</text>
                    </svg>
                    <div class="hr-deck-ring-meta">
                        <div class="hr-deck-ring-meta-item">
                            <span class="hr-deck-big" style="color:#FF6B6B;">{n_liked}</span>
                            <span class="hr-deck-key">♥ saved</span>
                        </div>
                        <div class="hr-deck-ring-meta-item">
                            <span class="hr-deck-big"
                                  style="color:rgba(255,255,255,0.9);">{n_unseen}</span>
                            <span class="hr-deck-key">left</span>
                        </div>
                        <div class="hr-deck-ring-meta-item">
                            <span class="hr-deck-big"
                                  style="color:rgba(255,255,255,0.35);">{n_passed}</span>
                            <span class="hr-deck-key">✕ passed</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.sidebar.markdown('<div class="hr-new-search">', unsafe_allow_html=True)
        if st.sidebar.button("🔍  New search", key="sidebar_new_search_btn", use_container_width=True):
            from backend.services.quiz import reset_quiz

            reset_quiz(prefill_from_existing=True)

            st.session_state.onboarding_step = 1
            st.session_state.onboarding_complete = False
            st.session_state.done_confirmed = False
            st.session_state.active_page = "Discover"

            st.session_state.compare_selected_ids = []
            st.session_state.custom_compare_rows = []

            st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # ── Logged-in-as / guest footer ───────────────────────────────────────────
    user = st.session_state.get("current_user", "")
    is_guest = user == "__guest__"
    if is_guest:
        st.sidebar.markdown(
            """
            <div style="padding:0.85rem 1.1rem 0.7rem;border-top:1px solid rgba(255,255,255,0.07);
                        margin-top:auto;">
                <div style="display:inline-block;font-size:0.62rem;font-weight:700;
                            letter-spacing:0.08em;text-transform:uppercase;
                            background:rgba(255,180,0,0.18);color:#FFC107;
                            border-radius:6px;padding:2px 7px;margin-bottom:4px;">
                    Guest mode
                </div>
                <div style="font-size:0.72rem;color:rgba(255,255,255,0.38);font-weight:500;
                            margin-top:2px;">Sign up to save your data</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        uname = user.split("@")[0] if "@" in user else user
        initial = uname[0].upper() if uname else "?"
        st.sidebar.markdown(
            f"""
            <div style="padding:0.8rem 1rem 0.75rem;
                        border-top:1px solid rgba(255,255,255,0.06);
                        display:flex;align-items:center;gap:9px;">
                <div style="width:30px;height:30px;border-radius:50%;flex-shrink:0;
                            background:linear-gradient(135deg,#FF4458,#FF6B6B);
                            display:flex;align-items:center;justify-content:center;
                            font-family:'DM Sans',sans-serif;font-size:0.72rem;
                            font-weight:800;color:#fff;
                            box-shadow:0 2px 8px rgba(255,68,88,0.35);">
                    {initial}
                </div>
                <div style="overflow:hidden;">
                    <div style="font-family:'DM Sans',sans-serif;font-size:0.78rem;
                                font-weight:600;color:rgba(255,255,255,0.82);
                                letter-spacing:-0.01em;white-space:nowrap;
                                overflow:hidden;text-overflow:ellipsis;">
                        {uname}
                    </div>
                    <div style="font-size:0.62rem;color:rgba(255,255,255,0.30);
                                font-weight:500;margin-top:1px;">
                        HomeRun account
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Onboarding ────────────────────────────────────────────────────────────────

def _run_onboarding():
    done = render_onboarding()
    if done:
        with st.spinner("Building your personalised deck…"):
            inputs     = build_inputs_from_prefs()
            bundle = get_prediction_bundle(
                inputs,
                ranking_profile=getattr(inputs, "ranking_profile", "balanced"),
            )
            map_bundle = get_map_bundle(inputs, bundle["recommendations_df"])
        create_search_session(inputs, bundle, map_bundle)
        st.session_state.onboarding_complete = True
        st.session_state.done_confirmed      = False  # reset for future new searches
        persist_current_preferences_for_user()
        st.rerun()


# ── Discover ──────────────────────────────────────────────────────────────────

def _render_discover():
    from frontend.state.session import get_active_session

    session = get_active_session()
    if session is None:
        st.info("No active session. Complete onboarding to get started.")
        return

    bundle     = session["bundle"]
    inputs     = session["inputs"]
    map_bundle = session["map_bundle"]

    _render_value_strip(bundle, inputs)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    render_listing_tab(bundle["listings_df"])


def _render_value_strip(bundle: dict, inputs):
    pred   = bundle.get("predicted_price", 0)
    ci_low = bundle.get("confidence_low", 0)
    ci_hi  = bundle.get("confidence_high", 0)
    budget = inputs.budget

    if budget is None:
        budget_display   = "Flexible"
        color            = "#64748b"
        bg               = "rgba(100,116,139,0.07)"
        border           = "rgba(100,116,139,0.20)"
        headroom_display = "No cap"
    else:
        diff   = ((budget - pred) / pred * 100) if pred else 0
        sign   = "+" if diff >= 0 else ""
        color  = "#059669" if diff >= 0 else "#e11d48"
        bg     = "rgba(5,150,105,0.07)"  if diff >= 0 else "rgba(225,29,72,0.07)"
        border = "rgba(5,150,105,0.20)"  if diff >= 0 else "rgba(225,29,72,0.20)"
        budget_display   = f"S${budget:,.0f}"
        headroom_display = f"{sign}{diff:.1f}%"

    # CI range string — shown as "S$380k – S$460k", not ±
    if ci_low and ci_hi:
        ci_display = f"S${ci_low:,.0f} – S${ci_hi:,.0f}"
        ci_sub     = "95% price range"
    else:
        ci_display = "—"
        ci_sub     = "95% price range"

    st.markdown(
    """
    <div style="margin-bottom:10px;">
        <div style="font-size:1.0rem;font-weight:800;color:#0f172a;letter-spacing:-0.02em;">
            Overview of your filtered matches
        </div>
        <div style="font-size:0.82rem;color:#64748b;margin-top:3px;line-height:1.45;">
            These figures summarise the median pricing across flats that match your quiz filters.
            Individual recommendations below may differ.
        </div>
    </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <style>
        .hr-tip {{ position:relative; display:inline-flex; align-items:center; cursor:help; }}
        .hr-tip .hr-tt {{
            visibility:hidden; opacity:0;
            position:absolute; bottom:150%; left:50%; transform:translateX(-50%);
            background:#1e293b; color:#f8fafc;
            padding:9px 12px; border-radius:10px;
            font-size:0.68rem; font-weight:500; line-height:1.55;
            width:220px; white-space:normal;
            text-transform:none; letter-spacing:0;
            pointer-events:none;
            box-shadow:0 4px 16px rgba(0,0,0,0.25);
            transition:opacity 0.15s ease, visibility 0.15s ease;
            z-index:9999;
        }}
        .hr-tip:hover .hr-tt {{ visibility:visible; opacity:1; }}
        </style>
        <div style="display:flex;align-items:stretch;
                    background:#f8fafc;border:1px solid #eef2f7;border-radius:16px;
                    margin-bottom:6px;overflow:visible;">
            <div style="flex:1;padding:10px 14px;">
                <div style="font-size:0.58rem;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.09em;color:#94a3b8;display:flex;align-items:center;gap:4px;">
                    Median predicted value
                    <span class="hr-tip">
                        <span style="font-size:0.7rem;opacity:0.45;line-height:1;">ℹ️</span>
                        <span class="hr-tt">
                            The middle estimated resale price across flats matching your filters.
                            Half are predicted to sell below this, half above —
                            a realistic benchmark for what similar flats are worth right now.
                        </span>
                    </span>
                </div>
                <div style="font-size:1.0rem;font-weight:800;color:#0f172a;
                             letter-spacing:-0.025em;margin-top:1px;">
                    S${pred:,.0f}
                </div>
            </div>
            <div style="width:1px;background:#e8edf4;flex-shrink:0;"></div>
            <div style="flex:1.4;padding:10px 14px;">
                <div style="font-size:0.58rem;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.09em;color:#94a3b8;display:flex;align-items:center;gap:4px;">
                    Median 95% price range
                    <span class="hr-tip">
                        <span style="font-size:0.7rem;opacity:0.45;line-height:1;">ℹ️</span>
                        <span class="hr-tt">
                            The range our model thinks the flat is likely worth.
                            There's a 95% chance the true fair price falls between these two numbers —
                            think of it as a confidence window, not an exact figure.
                        </span>
                    </span>
                </div>
                <div style="font-size:1.0rem;font-weight:800;color:#0f172a;
                             letter-spacing:-0.025em;margin-top:1px;white-space:nowrap;">
                    {ci_display}
                </div>
            </div>
            <div style="width:1px;background:#e8edf4;flex-shrink:0;"></div>
            <div style="flex:1;padding:10px 14px;">
                <div style="font-size:0.58rem;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.09em;color:#94a3b8;">Your budget</div>
                <div style="font-size:1.0rem;font-weight:800;color:#0f172a;
                             letter-spacing:-0.025em;margin-top:1px;">
                    {budget_display}
                </div>
            </div>
            <div style="width:1px;background:#e8edf4;flex-shrink:0;"></div>
            <div style="flex:1;padding:10px 14px;background:{bg};border-left:2px solid {border};">
                <div style="font-size:0.58rem;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.09em;color:#94a3b8;">Budget vs median</div>
                <div style="font-size:1.0rem;font-weight:800;color:{color};
                             letter-spacing:-0.025em;margin-top:1px;">
                    {headroom_display}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Compare ───────────────────────────────────────────────────────────────────

def _render_compare():
    from frontend.state.session import get_active_session_liked_df, get_active_session

    selected_ids = st.session_state.get("compare_selected_ids", [])

    session = get_active_session()
    if session is None:
        render_comparison_page(inputs=None, listings_df=pd.DataFrame())
        return

    liked_df = get_active_session_liked_df()

    extra_rows = session.get("extra_saved_rows", [])
    if extra_rows:
        extra_df = pd.DataFrame(extra_rows)
        liked_df = pd.concat([liked_df, extra_df], ignore_index=True, sort=False)

    compare_df = pd.DataFrame()
    if not liked_df.empty and selected_ids:
        compare_df = liked_df[
            liked_df["listing_id"].astype(str).isin([str(x) for x in selected_ids])
        ].copy()

    render_comparison_page(inputs=session["inputs"], listings_df=compare_df)
    
def _render_explore():

    session = get_active_session()
    inputs = session["inputs"] if session else None

    try:
        full_df, _ = load_all_data()
    except Exception:
        full_df = pd.DataFrame()

    render_explore_page(inputs=inputs, listings_df=full_df)

if __name__ == "__main__":
    main()
