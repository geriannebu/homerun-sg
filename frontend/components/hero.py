import base64
from pathlib import Path

import streamlit.components.v1 as components

def _get_logo_src() -> str:
    here = Path(__file__).parent
    assets = here.parent / "assets"
    candidates = [
        assets / "homerunlogo_square.png",
        assets / "homerunlogo.png",
        assets / "homerunlogo_square.jpeg",
        assets / "homerunlogo.jpeg",
    ]
    for p in candidates:
        if p.exists():
            mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    return ""


def get_logo_img_tag(size: int = 96) -> str:
    """Return an <img> HTML tag with the logo as a base64 data URI, or a fallback emoji."""
    src = _get_logo_src()
    if src:
        return (
            f"<img src='{src}' alt='HomeRun' "
            f"style='width:{size}px;height:{size}px;object-fit:cover;"
            f"display:block;margin:0 auto;'/>"
        )
    return "<span style='font-size:3.5rem;'>🏠</span>"


def render_hero() -> None:
    logo_src = _get_logo_src()
    logo_tag = (
        f"<img class=\\'logo-img\\' src=\\'{logo_src}\\' alt=\\'HomeRun\\' />"
        if logo_src else "<span class=\\'logo-mono\\'>H</span>"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:100%;font-family:'DM Sans',-apple-system,sans-serif;background:transparent;color:#0f172a;overflow:hidden}}
.hero{{position:relative;width:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:52px 32px 64px;background:#fafafa;overflow:hidden;}}
.hero::before{{content:'';position:absolute;inset:0;background-image:linear-gradient(rgba(255,68,88,0.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,68,88,0.05) 1px,transparent 1px);background-size:44px 44px;mask-image:radial-gradient(ellipse 80% 70% at 50% 0%,black 0%,transparent 80%);pointer-events:none;}}
.hero::after{{content:'';position:absolute;top:-80px;left:50%;transform:translateX(-50%);width:600px;height:360px;background:radial-gradient(ellipse,rgba(255,68,88,0.12) 0%,transparent 65%);pointer-events:none;}}
.logo-wrap{{position:relative;width:148px;height:148px;margin:0 auto 20px;animation:logo-in 0.75s cubic-bezier(0.22,1,0.36,1) both;z-index:1;}}
.logo-halo{{position:absolute;inset:-10px;border-radius:38px;background:conic-gradient(from 0deg,rgba(255,68,88,0.60),rgba(255,107,107,0.18),rgba(255,68,88,0.60));animation:spin 8s linear infinite;}}
.logo-halo-inner{{position:absolute;inset:-3px;border-radius:32px;background:#fafafa;}}
.logo-circle{{position:relative;z-index:1;width:100%;height:100%;border-radius:30px;background:#fff;display:grid;place-items:center;box-shadow:0 0 0 1px rgba(255,68,88,0.12),0 14px 44px rgba(255,68,88,0.18),0 2px 8px rgba(0,0,0,0.06);overflow:hidden;}}
.logo-img{{width:100%;height:100%;object-fit:cover;}}
.logo-mono{{font-size:48px;font-weight:800;color:#FF4458;font-family:'DM Sans',sans-serif;}}
@keyframes logo-in{{from{{opacity:0;transform:scale(0.68) translateY(22px)}}to{{opacity:1;transform:scale(1) translateY(0)}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.wordmark{{font-family:'DM Sans',sans-serif;font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:#FF4458;margin-bottom:16px;opacity:0;animation:fadeup 0.5s 0.28s ease both;z-index:1;}}
.title{{font-family:'DM Sans',sans-serif;font-size:clamp(40px,5.8vw,76px);line-height:0.92;letter-spacing:-0.045em;font-weight:800;color:#0b132d;max-width:860px;margin:0 auto 16px;opacity:0;animation:fadeup 0.6s 0.14s ease both;z-index:1;}}
.accent{{background:linear-gradient(130deg,#FF4458 0%,#FF6B6B 55%,#FF8C69 100%);-webkit-background-clip:text;background-clip:text;color:transparent;}}
.sub{{font-size:clamp(14px,1.7vw,17px);line-height:1.75;font-weight:500;color:#64748b;max-width:540px;margin:0 auto 30px;opacity:0;animation:fadeup 0.6s 0.20s ease both;z-index:1;}}
.ticker-wrap{{position:relative;width:100%;max-width:660px;margin:0 auto 30px;height:60px;overflow:hidden;opacity:0;animation:fadeup 0.6s 0.30s ease both;z-index:1;}}
.ticker-track{{display:flex;flex-direction:column;animation:tick 9s ease-in-out infinite}}
.ticker-item{{height:60px;display:flex;align-items:center;justify-content:center;gap:16px;flex-shrink:0}}
.ticker-num{{font-family:'DM Sans',sans-serif;font-size:32px;font-weight:800;letter-spacing:-0.05em;background:linear-gradient(130deg,#FF4458,#FF6B6B);-webkit-background-clip:text;background-clip:text;color:transparent;line-height:1;}}
.ticker-label{{font-size:13px;font-weight:600;color:#64748b;text-align:left;line-height:1.4;max-width:180px}}
.ticker-div{{width:1px;height:30px;background:rgba(255,68,88,0.18);flex-shrink:0}}
@keyframes tick{{0%,26%{{transform:translateY(0)}}33%,59%{{transform:translateY(-60px)}}66%,92%{{transform:translateY(-120px)}}100%{{transform:translateY(0)}}}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:30px;opacity:0;animation:fadeup 0.6s 0.36s ease both;z-index:1;}}
.chip{{display:inline-flex;align-items:center;gap:6px;padding:8px 15px;border-radius:999px;background:rgba(255,255,255,0.92);border:1px solid rgba(255,68,88,0.14);box-shadow:0 2px 12px rgba(0,0,0,0.05);color:#334155;font-size:12.5px;font-weight:700;white-space:nowrap;}}
.cta-row{{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:center;opacity:0;animation:fadeup 0.6s 0.42s ease both;z-index:1;}}
.cta-primary{{display:inline-flex;align-items:center;gap:10px;padding:15px 32px;border-radius:999px;background:linear-gradient(130deg,#FF4458 0%,#FF6B6B 100%);color:#fff;text-decoration:none;font-family:'DM Sans',sans-serif;font-size:14.5px;font-weight:800;letter-spacing:-0.01em;box-shadow:0 12px 36px rgba(255,68,88,0.32);transition:transform 0.17s ease,box-shadow 0.17s ease;cursor:pointer;border:none;}}
.cta-primary:hover{{transform:translateY(-2px);box-shadow:0 18px 44px rgba(255,68,88,0.42)}}
.cta-ghost{{display:inline-flex;align-items:center;gap:8px;padding:13px 22px;border-radius:999px;background:rgba(255,255,255,0.90);border:1px solid rgba(15,23,42,0.10);color:#475569;font-size:13px;font-weight:700;box-shadow:0 2px 12px rgba(15,23,42,0.05);}}
.scroll-hint{{position:absolute;bottom:14px;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:4px;color:#94a3b8;font-size:10px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;pointer-events:none;opacity:0;animation:fadeup 0.5s 1.1s ease both,bob 2.6s 1.8s ease-in-out infinite;animation-fill-mode:forwards;}}
@keyframes fadeup{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes bob{{0%,100%{{transform:translateX(-50%) translateY(0)}}50%{{transform:translateX(-50%) translateY(6px)}}}}
</style>
</head>
<body>
<div class="hero">
  <div class="logo-wrap">
    <div class="logo-halo"></div>
    <div class="logo-halo-inner"></div>
    <div class="logo-circle">{logo_tag}</div>
  </div>
  <div class="wordmark">HomeRun &middot; Singapore</div>
  <div class="title">Find the <span class="accent">fair&nbsp;price</span><br>of your dream flat</div>
  <div class="sub">Swipe through personalised HDB recommendations, curated to match your lifestyle and budget.</div>
  <div class="feature-cards" style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin:20px auto 24px;max-width:680px;">
    <div style="flex:1;min-width:160px;max-width:200px;background:rgba(255,255,255,0.9);border:1px solid rgba(255,68,88,0.12);border-radius:18px;padding:20px 16px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.05);">
      <div style="font-size:1.8rem;margin-bottom:8px;">🎯</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:0.82rem;font-weight:800;color:#0b132d;margin-bottom:6px;">Smart Quiz</div>
      <div style="font-size:0.74rem;color:#64748b;font-weight:500;line-height:1.5;">Personality-style quiz that maps your lifestyle to ideal flats</div>
    </div>
    <div style="flex:1;min-width:160px;max-width:200px;background:rgba(255,255,255,0.9);border:1px solid rgba(255,68,88,0.12);border-radius:18px;padding:20px 16px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.05);">
      <div style="font-size:1.8rem;margin-bottom:8px;">💘</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:0.82rem;font-weight:800;color:#0b132d;margin-bottom:6px;">Swipe to Save</div>
      <div style="font-size:0.74rem;color:#64748b;font-weight:500;line-height:1.5;">Tinder-style swiping to shortlist your favourite flats</div>
    </div>
    <div style="flex:1;min-width:160px;max-width:200px;background:rgba(255,255,255,0.9);border:1px solid rgba(255,68,88,0.12);border-radius:18px;padding:20px 16px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.05);">
      <div style="font-size:1.8rem;margin-bottom:8px;">📊</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:0.82rem;font-weight:800;color:#0b132d;margin-bottom:6px;">Compare</div>
      <div style="font-size:0.74rem;color:#64748b;font-weight:500;line-height:1.5;">Side-by-side comparison of saved flats across all metrics</div>
    </div>
  </div>
  <div class="cta-row">
    <a class="cta-primary" id="cta" href="#">Start your search <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8l5 5 5-5" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></a>
    <div class="cta-ghost"><svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.5" stroke="#94a3b8" stroke-width="1.4"/><path d="M8 5v3.5l2 2" stroke="#94a3b8" stroke-width="1.4" stroke-linecap="round"/></svg>Takes about 2 minutes</div>
  </div>
  <div class="scroll-hint"><span>Scroll</span><svg width="13" height="13" viewBox="0 0 20 20" fill="none"><path d="M10 4v12M5 11l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
</div>
<script>
(function(){{
  var cta=document.getElementById('cta');
  if(cta){{
    cta.addEventListener('click',function(e){{
      e.preventDefault();
      try{{
        var t=window.parent.document.getElementById('nw-form-anchor');
        if(t){{t.scrollIntoView({{behavior:'smooth',block:'start'}})}}
        else{{window.parent.scrollBy({{top:window.parent.innerHeight*0.92,behavior:'smooth'}})}}
      }}catch(err){{window.parent.scrollBy({{top:700,behavior:'smooth'}})}}
    }});
  }}
  function resize(){{
    var h=document.documentElement.getBoundingClientRect().height;
    window.parent.postMessage({{type:'streamlit:setFrameHeight',height:Math.ceil(h)}},'*');
  }}
  resize();
  window.addEventListener('load',resize);
  if(document.fonts&&document.fonts.ready){{document.fonts.ready.then(resize);}}
  setTimeout(resize,200);
  setTimeout(resize,600);
}})();
</script>
</body>
</html>"""

    components.html(html, height=730, scrolling=False)
