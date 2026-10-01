from __future__ import annotations
import html
import json
import os
from datetime import datetime, timezone
import time
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from academy.models import ROOT, curriculum
from academy.progress import ProgressStore
from academy.engine import start_local_engine, ready, prom_query, query_rows, sql_query
from academy.data import CALM_TIME, BURST_TIME, samples
from academy.animations import concept_animation
from academy.tutor import ask, configured
from academy.security import plain_model_text

load_dotenv(ROOT / ".env", override=False)
st.set_page_config(
    page_title="PromQL Zero to Hero", page_icon="🔥", layout="wide", initial_sidebar_state="expanded"
)
st.html((ROOT / "academy/style.css").read_text())
LEVELS = curriculum()


@st.cache_resource
def services():
    store = ProgressStore(os.getenv("ACADEMY_DB") or None)
    start_local_engine()
    return store


store = services()


def navigate(page, level=None):
    st.session_state.page = page
    if level is not None:
        st.session_state.level = level


def profile():
    if os.getenv("REQUIRE_LOGIN", "false").lower() == "true":
        if not st.user.is_logged_in:
            st.title("Your learning journey starts here")
            st.write("Sign in to keep your lessons, quizzes, and badges private.")
            if st.button("Sign in", type="primary"):
                st.login()
            st.stop()
        return store.oidc_profile(
            st.user.get("iss", "configured-provider"), st.user["sub"], st.user.get("name", "Explorer")
        )
    if "profile" not in st.session_state:
        st.session_state.profile, st.session_state.recovery = store.create()
    return st.session_state.profile


learner = profile()
summary = store.summary(learner)
done = {row["level"] for row in summary["completed"]}
st.session_state.setdefault("page", "Overview")
st.session_state.setdefault("level", min(summary["unlocked"], 10))

with st.sidebar:
    st.markdown(
        '<div class="brand"><span>◉</span> PROMQL<span class="brand-small">ZERO TO HERO</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("A LITTLE SQL. A LOT OF SIGNAL.")
    st.radio(
        "Explore the academy",
        ["Overview", "Learn", "Query lab", "Ask the tutor", "My badges", "Behind the scenes"],
        key="page",
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(f"**YOUR JOURNEY** &nbsp; `{len(done)} / 11`", unsafe_allow_html=True)
    st.progress(len(done) / 11)
    st.caption(f"{summary['xp']:,} XP · {summary['attempts']} completed attempts")
    options = list(range(summary["unlocked"] + 1))
    if st.session_state.level not in options:
        st.session_state.level = options[-1]
    st.selectbox(
        "Current level",
        options,
        format_func=lambda i: f"{'✓' if i in done else '○'} {i:02} · {LEVELS[i].title}",
        key="level",
    )
    if os.getenv("REQUIRE_LOGIN", "false").lower() != "true":
        with st.expander("Save or resume your journey"):
            st.caption(
                "This local profile uses a private recovery code. Save it to resume after a browser reset."
            )
            if "recovery" in st.session_state:
                st.code(st.session_state.recovery, language=None)
            with st.form("resume"):
                token = st.text_input("Recovery code", type="password")
                submitted = st.form_submit_button("Resume saved progress")
            if submitted:
                found = store.resume(token)
                if found:
                    st.session_state.profile = found
                    st.session_state.recovery = token.strip()
                    for state_key in list(st.session_state):
                        if state_key.startswith("quiz-result-"):
                            del st.session_state[state_key]
                    st.rerun()
                else:
                    st.error("That recovery code was not found on this server.")
    if os.getenv("REQUIRE_LOGIN", "false").lower() == "true":
        st.button("Sign out", on_click=st.logout)
    st.caption("Built with Python + Streamlit")

level = LEVELS[st.session_state.level]


def eyebrow(text):
    st.markdown(f'<div class="eyebrow">{html.escape(text)}</div>', unsafe_allow_html=True)


def heading(title, subtitle):
    st.title(title)
    st.markdown(f'<p class="subtitle">{html.escape(subtitle)}</p>', unsafe_allow_html=True)


def draw_result(data, key):
    rows = query_rows(data)
    if not rows:
        st.info("Empty result: no series matched at this evaluation time. Empty is different from zero.")
        return
    frame = pd.DataFrame(rows)
    if data["resultType"] == "matrix":
        frame["time"] = pd.to_datetime(frame.timestamp, unit="s", utc=True)
        labels = [c for c in frame if c not in ("timestamp", "value", "time")]
        frame["series"] = frame[labels].fillna("").astype(str).agg(" · ".join, axis=1) if labels else "result"
        fig = px.line(
            frame,
            x="time",
            y="value",
            color="series",
            color_discrete_sequence=["#ff8759", "#72dfb8", "#78b6ff", "#ba9aff"],
        )
        fig.update_layout(
            height=320, margin=dict(l=0, r=0, t=15, b=0), legend_title=None, paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, width="stretch", key=key)
    else:
        st.dataframe(frame.drop(columns=["timestamp"], errors="ignore"), hide_index=True, width="stretch")


def lab_panel(prefix, show_hint=True):
    st.markdown(f"**Your challenge:** {level.lab}")
    scenario = st.radio("Scenario", ["Normal traffic", "Incident"], horizontal=True, key=prefix + "scenario")
    at = CALM_TIME if scenario == "Normal traffic" else BURST_TIME
    st.caption(
        "Fixed evaluation time: " + datetime.fromtimestamp(at, timezone.utc).isoformat() + " · synthetic data"
    )
    if not ready():
        st.warning(
            "The PromQL engine is offline. Run `python scripts/bootstrap.py` to enable execution and quiz grading."
        )
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### PromQL")
        prom = st.text_area("PromQL expression", level.promql, height=180, key=prefix + "prom")
        view = st.radio(
            "PromQL view", ["Instant table", "15-minute chart"], horizontal=True, key=prefix + "view"
        )
        if st.button("Run PromQL →", type="primary", key=prefix + "run-prom"):
            try:
                with st.spinner("Evaluating with Prometheus…"):
                    result = prom_query(prom, at, range_seconds=900 if view == "15-minute chart" else 0)
                st.session_state[prefix + "presult"] = {
                    "result": result,
                    "query": prom,
                    "at": at,
                    "view": view,
                }
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
        result = st.session_state.get(prefix + "presult")
        if result and result["at"] == at and result["query"] == prom and result["view"] == view:
            draw_result(result["result"], prefix + "chart")
    with right:
        st.markdown("#### SQL · DuckDB")
        sql = st.text_area("SQL query", level.sql, height=180, key=prefix + "sql")
        st.caption("Tables: `snapshot` at this instant · `samples` across time")
        if st.button("Run SQL →", key=prefix + "run-sql"):
            try:
                with st.spinner("Running in the SQL worker…"):
                    result = sql_query(sql, at)
                st.session_state[prefix + "sresult"] = {"result": result, "query": sql, "at": at}
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
        result = st.session_state.get(prefix + "sresult")
        if result and result["at"] == at and result["query"] == sql:
            payload = result["result"]
            st.dataframe(
                pd.DataFrame(payload["rows"], columns=payload["columns"]), hide_index=True, width="stretch"
            )
            if payload["truncated"]:
                st.caption("Showing the first 200 rows.")
    st.info("**How close is the SQL analogy?** " + level.equivalence)
    if show_hint:
        with st.expander("A nudge in the right direction"):
            st.write(level.lab_hint)
    with st.expander("Inspect the fixture data and schema"):
        df = pd.DataFrame(samples())
        st.dataframe(df[df.timestamp == at], hide_index=True, width="stretch")
        st.caption(
            "Empty dimension strings mean that label is absent. Only these synthetic tables are queryable."
        )


def quiz_panel():
    st.markdown("### Prove what you learned")
    st.write(
        "Answer five questions and solve the query challenge. Score at least 80% and pass both lab scenarios to unlock the next level."
    )
    previous = st.session_state.get(f"quiz-result-{level.id}")
    if previous:
        if previous["passed"]:
            st.success(
                f"{level.icon} {level.badge} earned · {previous['score']}% · +100 XP on your first pass"
            )
            if level.id < 10:
                st.button(
                    "Continue to the next level →",
                    on_click=navigate,
                    args=("Learn", level.id + 1),
                    type="primary",
                )
            else:
                st.success("You completed all 11 levels. You're a PromQL Hero!")
        else:
            st.warning(
                f"Quiz: {previous['score']}%. Lab: {'passed' if previous['lab_pass'] else 'needs another look'}."
            )
        st.write(previous["lab_message"])
        for i, item in enumerate(previous["feedback"], 1):
            with st.expander(f"{'✓' if item['correct'] else '↻'} Question {i} feedback"):
                st.write("**Answer:** " + item["answer"])
                st.write(item["explanation"])
        if st.button("Practice with another quiz", key=f"retry-{level.id}"):
            del st.session_state[f"quiz-result-{level.id}"]
            st.rerun()
        return
    attempt = store.start_attempt(learner, level.id)
    questions = {q.id: q for q in level.questions}
    answers = {}
    with st.form("quiz-" + attempt["id"]):
        for number, ident in enumerate(json.loads(attempt["question_ids"]), 1):
            question = questions[ident]
            answer = st.radio(
                f"{number}. {question.prompt}",
                range(len(question.options)),
                format_func=lambda i, q=question: q.options[i],
                index=None,
                key=attempt["id"] + ident,
            )
            answers[ident] = answer
        st.markdown("#### Your query challenge")
        st.write(level.lab)
        query = st.text_area("Submit your PromQL solution", height=120, key="solution-" + attempt["id"])
        submitted = st.form_submit_button("Check answers & earn badge", type="primary")
    if submitted:
        if any(answer is None for answer in answers.values()) or not query.strip():
            st.warning("Complete all five answers and enter your query first.")
        elif not ready():
            st.warning("Start the PromQL engine before submitting. Your current answers are still here.")
        else:
            with st.spinner("Checking your answers and both fixture scenarios…"):
                result = store.grade(learner, attempt["id"], answers, query)
            st.session_state[f"quiz-result-{level.id}"] = result
            st.rerun()


if st.session_state.page == "Overview":
    eyebrow("YOUR OBSERVABILITY ADVENTURE")
    st.markdown(
        '<div class="hero"><div class="hero-tag">11 LEVELS · REAL QUERIES · ANIMATED LESSONS</div><h1>Start at zero.<br>Think in <em>signals.</em></h1><p>Learn PromQL with the SQL you know.<br>Watch it move. Try it yourself. Earn your next level.</p></div>',
        unsafe_allow_html=True,
    )
    a, b, c = st.columns(3)
    a.metric("Levels completed", f"{len(done)} / 11")
    b.metric("Experience earned", f"{summary['xp']:,} XP")
    c.metric("Next badge", LEVELS[summary["unlocked"]].badge if len(done) < 11 else "PromQL Hero 🏆")
    st.button(
        "Continue your journey →" if done else "Start level 0 →",
        type="primary",
        on_click=navigate,
        args=("Learn", summary["unlocked"]),
    )
    st.markdown("### Your path from curious to confident")
    st.caption("Every stop includes an animated explanation, a SQL bridge, a live lab, and a quiz.")
    for first in range(0, 11, 3):
        columns = st.columns(3, gap="medium")
        for column, item in zip(columns, LEVELS[first : first + 3]):
            with column:
                locked = item.id > summary["unlocked"]
                with st.container(border=True):
                    st.markdown(
                        f'<div class="level-meta">LEVEL {item.id:02} <span>{"✓ COMPLETE" if item.id in done else "LOCKED" if locked else "READY"}</span></div><div class="level-icon">{item.icon}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"#### {item.title}")
                    st.caption(item.subtitle)
                    st.caption(f"{item.minutes} MIN · {item.badge.upper()}")
                    st.button(
                        "Review lesson"
                        if item.id in done
                        else "Unlock with previous quiz"
                        if locked
                        else "Explore lesson →",
                        disabled=locked,
                        key=f"open-{item.id}",
                        on_click=navigate,
                        args=("Learn", item.id),
                        width="stretch",
                    )

elif st.session_state.page == "Learn":
    eyebrow(f"LEVEL {level.id:02} / 10 · {level.minutes} MIN · {level.badge}")
    heading(level.title, level.subtitle)
    learn, compare, practice, quiz = st.tabs(
        ["▶ Watch & learn", "⇄ The SQL bridge", "⌘ Practice", "✓ Level quiz"], key=f"lesson-tabs-{level.id}"
    )
    with learn:
        concept_animation(level)
        st.caption(
            "Press Play, pause at any point, or use the arrows and slider. The narration explains every step."
        )
        for lesson in level.lessons:
            st.markdown("### " + lesson.title)
            st.write(lesson.body)
        with st.container(border=True):
            st.markdown("**Take these with you**")
            for takeaway in level.takeaways:
                st.markdown("✓ " + takeaway)
        with st.expander("Common traps to avoid"):
            for pitfall in level.pitfalls:
                st.write("• " + pitfall)
    with compare:
        st.markdown("### Two languages. A clearer mental model.")
        for lesson in level.lessons:
            st.markdown("**" + lesson.title + "**")
            st.write(lesson.sql_connection)
        left, right = st.columns(2)
        with left:
            st.code(level.promql, language="promql")
        with right:
            st.code(level.sql, language="sql")
        st.info(level.equivalence)
    with practice:
        lab_panel(f"lesson-{level.id}-")
    with quiz:
        quiz_panel()
    st.divider()
    for i, url in enumerate(level.sources):
        st.link_button("Reference " + str(i + 1) + " ↗", url)

elif st.session_state.page == "Query lab":
    eyebrow("THE PLAYGROUND")
    heading(
        "One question. Two query languages.",
        "Experiment with real Prometheus and DuckDB on the same synthetic service data.",
    )
    lab_panel(f"lab-{level.id}-")

elif st.session_state.page == "Ask the tutor":
    eyebrow("A GUIDE AT EVERY LEVEL")
    heading(
        "Let's make it click.",
        "Ask for an explanation, compare a SQL idea, or bring a query that has you stuck.",
    )
    st.caption(
        (
            "AI tutor is configured"
            if configured()
            else "Reference tutor · answers from the learning library. Configure a model endpoint for generated explanations."
        )
        + f" · Context: Level {level.id}"
    )
    with st.expander("Include a query or manage conversation memory"):
        current = st.text_area("Optional PromQL query to investigate", key="tutor-query", height=90)
        remember = st.checkbox("Remember this learning conversation on this server", value=True)
        if st.button("Clear my conversation"):
            store.clear_history(learner)
            st.rerun()
    for message in store.history(learner)[-10:]:
        with st.chat_message(message["role"]):
            st.markdown(plain_model_text(message["body"]))
    question = st.chat_input("Why should I calculate rate before sum?")
    if question:
        last = st.session_state.get("last-question-time", 0)
        if time.monotonic() - last < 3:
            st.warning("Give the tutor a moment before the next question.")
        else:
            st.session_state["last-question-time"] = time.monotonic()
            with st.chat_message("user"):
                st.text(question)
            with st.chat_message("assistant"):
                with st.spinner("Finding references and checking the explanation…"):
                    try:
                        response = ask(
                            question, level.id, current, store.history(learner) if remember else []
                        )
                    except Exception:
                        st.error(
                            "The tutor could not finish this request. The lessons and query lab are still available."
                        )
                        st.stop()
                answer = response["answer"]
                if response.get("notice"):
                    st.info(response["notice"])
                st.markdown(plain_model_text(answer["explanation"]))
                left, right = st.columns(2)
                if answer["promql"]:
                    with left:
                        st.code(answer["promql"], language="promql")
                if answer["sql"]:
                    with right:
                        st.code(answer["sql"], language="sql")
                if answer["differences"]:
                    st.info(answer["differences"])
                if answer["follow_up"]:
                    st.markdown("**Try next:** " + plain_model_text(answer["follow_up"]))
                selected = {p["id"]: p for p in response["evidence"]}
                for ident in answer["citations"]:
                    if ident in selected:
                        st.link_button("Source: " + selected[ident]["title"], selected[ident]["url"])
                with st.expander("How this answer was produced"):
                    st.write(
                        f"{response['mode']} · {response['latency_seconds']}s · {response.get('tokens', 0)} model tokens"
                    )
                    st.write("Route: " + response["plan"]["intent"])
                    if response.get("tool_result"):
                        st.json(response["tool_result"])
                    st.caption(
                        "Retrieved sources are evidence. Scores and badges are controlled by the quiz engine."
                    )
                if remember:
                    store.remember(learner, "user", question)
                    store.remember(learner, "assistant", answer["explanation"])

elif st.session_state.page == "My badges":
    eyebrow("PROOF OF PROGRESS")
    heading(
        "Small wins. Stronger instincts.",
        "Every badge is earned by passing a quiz and a real query challenge.",
    )
    st.progress(len(done) / 11, text=f"{len(done)} of 11 badges collected · {summary['xp']} XP")
    for start in range(0, 11, 4):
        for col, item in zip(st.columns(4), LEVELS[start : start + 4]):
            with col:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="badge {"earned" if item.id in done else "locked"}"><div>{item.icon}</div><h3>{item.badge}</h3><p>LEVEL {item.id:02} · {"EARNED" if item.id in done else "KEEP LEARNING"}</p></div>',
                        unsafe_allow_html=True,
                    )
    if done:
        st.download_button(
            "Download my progress",
            json.dumps({"completed": summary["completed"], "xp": summary["xp"]}, indent=2),
            "promql-progress.json",
            "application/json",
        )
        st.caption("This report is for your records. It cannot be imported to bypass quiz checks.")

elif st.session_state.page == "Behind the scenes":
    eyebrow("BUILT TO TEACH. DESIGNED TO BE CHECKED.")
    heading("The academy, explained.", "Six weeks of AI techniques brought together in one learning product.")
    st.image(str(ROOT / "docs/assets/architecture.png"), width="stretch")
    st.markdown(
        "**Week 1** Streamlit and visual data exploration · **Week 2** RAG · **Week 3** stateful tool workflows · **Week 4** evaluations · **Week 5** a LoRA question router · **Week 6** security and guardrails."
    )
    st.write(
        "The Python app grades queries with the real Prometheus engine. DuckDB runs in a restricted worker. Both use synthetic fixtures. The tutor can read documentation and query fixtures; it cannot edit scores or badges."
    )
    st.info(
        "The LoRA training workflow is included in the repository. A trained adapter is activated only after a GPU training run and evaluation. The baseline router remains available."
    )
    st.markdown("**Runtime status**")
    st.write(
        {
            "Prometheus": "ready" if ready() else "not running",
            "Tutor": "model configured" if configured() else "reference mode",
            "Router": "endpoint configured" if configured("ROUTER") else "baseline",
            "Progress": "SQLite on this server",
        }
    )

st.markdown(
    '<div class="footer">PROMQL ZERO TO HERO <span>Understand the signal. Earn the skill.</span></div>',
    unsafe_allow_html=True,
)
