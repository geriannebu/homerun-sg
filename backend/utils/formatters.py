def fmt_sgd(value):
    return f"${value:,.0f}"


def valuation_tag_html(label: str) -> str:
    mapping = {
        "🔥 Steal": '<span class="nw-tag nw-tag-steal">🔥 Steal</span>',
        "✅ Fair": '<span class="nw-tag nw-tag-fair">✅ Fair</span>',
        "⚠️ Slightly overpriced": '<span class="nw-tag nw-tag-slight">⚠️ Slightly overpriced</span>',
        "🚩 Overpriced": '<span class="nw-tag nw-tag-over">🚩 Overpriced</span>',
    }
    return mapping.get(label, f"<span>{label}</span>")