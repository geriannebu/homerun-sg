from __future__ import annotations
import streamlit as st

# ── Constants ──────────────────────────────────────────────────────────────────

QUESTION_BANK = [
    {
        "id": "q1",
        "text": "What makes your daily commute feel easiest?",
        "options": [
            {"id": "q1_a", "label": "A fast MRT connection", "amenity": "train"},
            {"id": "q1_b", "label": "A bus stop very close to home", "amenity": "bus"},
            {"id": "q1_c", "label": "No strong preference", "amenity": None},
        ],
    },
    {
        "id": "q2",
        "text": "On most days, how do you usually handle meals?",
        "options": [
            {"id": "q2_a", "label": "I like affordable cooked food nearby", "amenity": "hawker"},
            {"id": "q2_b", "label": "I usually buy food while running errands at a mall", "amenity": "mall"},
            {"id": "q2_c", "label": "I prefer buying groceries and preparing food at home", "amenity": "supermarket"},
        ],
    },
    {
        "id": "q3",
        "text": "Which of these matters more for your household right now?",
        "options": [
            {"id": "q3_a", "label": "A nearby clinic or polyclinic", "amenity": "polyclinic"},
            {"id": "q3_b", "label": "Good school access", "amenity": "primary_school"},
            {"id": "q3_c", "label": "A one-stop place for errands and essentials", "amenity": "mall"},
        ],
    },
    {
        "id": "q4",
        "text": "What sounds most like your usual weekend?",
        "options": [
            {"id": "q4_a", "label": "Eating around the neighbourhood and staying close to home", "amenity": "hawker"},
            {"id": "q4_b", "label": "Shopping, errands, cafés, or mall time", "amenity": "mall"},
            {"id": "q4_c", "label": "Stocking up on groceries for the week", "amenity": "supermarket"},
        ],
    },
    {
        "id": "q5",
        "text": "If you had to prioritise one, which would you choose?",
        "options": [
            {"id": "q5_a", "label": "Being near MRT over having more food options", "amenity": "train"},
            {"id": "q5_b", "label": "Having food options nearby over faster transport", "amenity": "hawker"},
            {"id": "q5_c", "label": "Having everyday essentials in one place", "amenity": "mall"},
        ],
    },
]

QUIZ_AMENITY_LABELS = {
    "train": "MRT stations",
    "bus": "Bus stops",
    "hawker": "Hawker centres",
    "mall": "Shopping malls",
    "supermarket": "Supermarkets",
    "polyclinic": "Hospitals / Polyclinics",
    "primary_school": "Schools",
}

NO_PREF_LABEL = "No preference"
TIE_THRESHOLD = 0.001
QUIZ_SCORE_BASE = 0.25


def _build_active_questions(selected: list[str]) -> list[dict]:
    sel, active = set(selected), []
    for q in QUESTION_BANK:
        valid = [o for o in q["options"] if (o["amenity"] in sel) or (o["amenity"] is None)]
        scored_valid = [o for o in valid if o["amenity"] is not None]

        if len(scored_valid) >= 2:
            has_none_option = any(o["amenity"] is None for o in valid)

            options = valid if has_none_option else valid + [{"label": NO_PREF_LABEL, "amenity": None}]

            active.append({
                **q,
                "options": options,
            })

    return active[:5]


def _compute_normalised_weights(
    selected: list[str],
    answers: dict[str, str | None],
) -> dict[str, float]:
    scores = {a: QUIZ_SCORE_BASE for a in selected}
    for amenity in answers.values():
        if amenity and amenity in scores:
            scores[amenity] += 1.0

    total = sum(scores.values())
    if total == 0:
        n = len(selected)
        return {a: round(1 / n, 4) for a in selected}

    return {a: round(v / total, 4) for a, v in scores.items()}


def rank_sum_weights(ranking: list[str]) -> dict[str, float]:
    n = len(ranking)
    denom = n * (n + 1) / 2
    return {a: round((n - i) / denom, 6) for i, a in enumerate(ranking)}


def _find_ties(
    ranking: list[str],
    weights: dict[str, float],
) -> list[tuple[str, str]]:
    ties = []
    for i in range(len(ranking) - 1):
        a1, a2 = ranking[i], ranking[i + 1]
        if abs(weights[a1] - weights[a2]) <= TIE_THRESHOLD:
            ties.append((a1, a2))
    return ties


def _init_state(ss) -> None:
    defaults = {
        "quiz_step": "select",
        "quiz_selected": [],
        "quiz_answers": {},
        "quiz_normalised_weights": {},
        "quiz_ranking": [],
        "quiz_ties": [],
        "quiz_tiebreak": {},
        "quiz_final_ranking": [],
    }
    for k, v in defaults.items():
        if k not in ss:
            ss[k] = v


def seed_quiz_from_existing_preferences() -> None:
    ss = st.session_state
    _init_state(ss)

    previous_selected = list(ss.get("quiz_selected", []) or [])
    previous_answers = dict(ss.get("quiz_answers", {}) or {})

    if previous_selected:
        ss["quiz_selected"] = previous_selected
        ss["quiz_answers"] = previous_answers
        ss["quiz_step"] = "select"
        return

    amenity_rank = ss.get("pref_amenity_rank") or []
    if not amenity_rank:
        return

    reverse_key_map = {
        "mrt": "train",
        "bus": "bus",
        "hawker": "hawker",
        "retail": "mall",
        "supermarket": "supermarket",
        "healthcare": "polyclinic",
        "schools": "primary_school",
    }

    selected = []
    for key in amenity_rank:
        old_key = reverse_key_map.get(key)
        if old_key and old_key not in selected:
            selected.append(old_key)

    if not selected:
        return

    ss["quiz_selected"] = selected
    ss["quiz_answers"] = previous_answers
    ss["quiz_step"] = "select"


def render_quiz() -> tuple[dict[str, float], list[str], dict[str, float]]:
    """
    Returns:
        scoring_weights    final rank-sum weights
        final_ranking      ordered amenity keys
        normalised_weights quiz-derived weights for transparency display
    """
    ss = st.session_state
    _init_state(ss)

    if ss.quiz_step == "select":
        st.markdown("**Step 1 — What amenities matter to you?**")
        st.caption("Select everything you care about. We'll personalise the quiz to match.")

        existing_selected = set(ss.get("quiz_selected", []))

        chosen = []
        cols = st.columns(2)
        for i, (key, label) in enumerate(QUIZ_AMENITY_LABELS.items()):
            cb_key = f"_qcb_{key}"
            if cb_key not in ss:
                ss[cb_key] = key in existing_selected

            with cols[i % 2]:
                if st.checkbox(label, key=cb_key):
                    chosen.append(key)

        c1, c2 = st.columns([1, 5])

        with c1:
            if st.button("← Back", key="_qback1"):
                st.session_state.onboarding_step = 6
                st.rerun()

        with c2:
            st.button(
                "Next →",
                key="_qnext1",
                disabled=len(chosen) < 1,
                on_click=lambda: ss.update({"quiz_selected": chosen, "quiz_step": "quiz"}),
            )

        return {}, [], {}

    if ss.quiz_step == "quiz":
        questions = _build_active_questions(ss.quiz_selected)

        if not questions:
            weights = _compute_normalised_weights(ss.quiz_selected, {})
            ranking = sorted(weights, key=lambda a: weights[a], reverse=True)
            ss.quiz_normalised_weights = weights
            ss.quiz_ranking = ranking
            ss.quiz_ties = _find_ties(ranking, weights)
            ss.quiz_tiebreak = {f"{a1}__{a2}": 0 for a1, a2 in ss.quiz_ties}
            ss.quiz_step = "tiebreak" if ss.quiz_ties else "done"
            st.rerun()
            return {}, [], {}

        st.markdown("**Step 2 — A few quick questions**")
        st.caption("Your answers help us understand what matters most to you.")

        answers: dict[str, str | None] = {}
        for q in questions:
            st.markdown(f"**{q['text']}**")
            option_labels = [o["label"] for o in q["options"]]
            option_keys = [o["amenity"] for o in q["options"]]
            prev_key = ss.quiz_answers.get(q["id"])
            prev_idx = option_keys.index(prev_key) if prev_key in option_keys else 0

            choice = st.radio(
                label=q["id"],
                options=option_labels,
                index=prev_idx,
                horizontal=True,
                label_visibility="collapsed",
                key=f"_qr_{q['id']}",
            )
            answers[q["id"]] = option_keys[option_labels.index(choice)]
            st.divider()

        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("← Back", key="_qback2"):
                ss.quiz_step = "select"
                st.rerun()
        with c2:
            if st.button("Next →", key="_qnext2"):
                ss.quiz_answers = answers
                weights = _compute_normalised_weights(ss.quiz_selected, answers)
                ranking = sorted(weights, key=lambda a: weights[a], reverse=True)
                ss.quiz_normalised_weights = weights
                ss.quiz_ranking = ranking
                ties = _find_ties(ranking, weights)
                ss.quiz_ties = ties
                ss.quiz_tiebreak = {f"{a1}__{a2}": 0 for a1, a2 in ties}
                ss.quiz_step = "tiebreak" if ties else "done"
                st.rerun()
        return {}, [], {}

    if ss.quiz_step == "tiebreak":
        ties = ss.quiz_ties
        ranking = list(ss.quiz_ranking)

        st.markdown("**Step 3 — Help us understand your preference**")
        st.caption("A few options came out very close, so this helps us refine the order.")

        for a1, a2 in ties:
            label1, label2 = QUIZ_AMENITY_LABELS[a1], QUIZ_AMENITY_LABELS[a2]
            key = f"{a1}__{a2}"

            st.markdown(f"**{label1} vs {label2}**")
            val = st.slider(
                label=key,
                min_value=-5,
                max_value=5,
                value=ss.quiz_tiebreak.get(key, 0),
                label_visibility="collapsed",
                key=f"_qtb_{key}",
            )

            cl, _, cr = st.columns([2, 1, 2])
            with cl:
                st.caption(f"◄ {label1}")
            with cr:
                st.caption(f"{label2} ►")

            ss.quiz_tiebreak[key] = val
            st.divider()

        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("← Back", key="_qback3"):
                ss.quiz_step = "quiz"
                st.rerun()
        with c2:
            if st.button("Apply →", key="_qnext3"):
                for a1, a2 in ties:
                    val = ss.quiz_tiebreak.get(f"{a1}__{a2}", 0)
                    if val > 0:
                        i1, i2 = ranking.index(a1), ranking.index(a2)
                        ranking[i1], ranking[i2] = ranking[i2], ranking[i1]
                ss.quiz_final_ranking = ranking
                ss.quiz_step = "done"
                st.rerun()
        return {}, [], {}

    if ss.quiz_step == "done":
        final_ranking = ss.quiz_final_ranking or ss.quiz_ranking
        scoring_weights = rank_sum_weights(final_ranking)
        return scoring_weights, final_ranking, ss.quiz_normalised_weights

    return {}, [], {}


def reset_quiz(prefill_from_existing: bool = False) -> None:
    previous_selected = list(st.session_state.get("quiz_selected", []) or [])
    previous_answers = dict(st.session_state.get("quiz_answers", {}) or {})

    for key in [
        "quiz_step",
        "quiz_selected",
        "quiz_answers",
        "quiz_normalised_weights",
        "quiz_ranking",
        "quiz_ties",
        "quiz_tiebreak",
        "quiz_final_ranking",
    ]:
        st.session_state.pop(key, None)

    for key in list(st.session_state.keys()):
        if key.startswith("_qcb_") or key.startswith("_qr_") or key.startswith("_qtb_"):
            st.session_state.pop(key, None)

    if prefill_from_existing:
        if previous_selected:
            st.session_state["quiz_selected"] = previous_selected
        if previous_answers:
            st.session_state["quiz_answers"] = previous_answers
        seed_quiz_from_existing_preferences()