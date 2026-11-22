"""
Answer Sheet Evaluator - interactive Streamlit UI (Problem Statement 24).
Run:  streamlit run app.py
"""

import html
import io
import json
import os
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from dotenv import load_dotenv

from evaluator import PROVIDERS, STRICTNESS, _words, evaluate_answer
from samples import SAMPLES

load_dotenv()
st.set_page_config(page_title="Answer Sheet Evaluator", page_icon="📝", layout="wide")

STATUS_ICON = {"covered": "✅", "partial": "🟡", "missing": "❌"}
STATUS_COLOR = {"covered": "#2E9E5B", "partial": "#E0A500", "missing": "#D64545"}
GRADE_COLOR = {"A+": "#1B8A4B", "A": "#2E9E5B", "B+": "#5AAE3A", "B": "#8DB02E",
               "C": "#E0A500", "D": "#E07B00", "F": "#D64545"}

# chart text colour follows Streamlit's light/dark theme
try:
    _dark = st.context.theme.type == "dark"
except Exception:
    _dark = False
_ink, _grid = ("#FAFAFA", "rgba(250,250,250,.12)") if _dark else ("#31333F", "rgba(49,51,63,.12)")
pio.templates["app"] = go.layout.Template(layout=dict(
    font=dict(color=_ink), xaxis=dict(gridcolor=_grid, color=_ink), yaxis=dict(gridcolor=_grid, color=_ink),
    legend=dict(font=dict(color=_ink))))
pio.templates.default = "plotly+app"

st.markdown("""
<style>
.grade-badge {display:inline-block; padding:.35rem 1.1rem; border-radius:999px; color:#fff;
              font-weight:700; font-size:1.6rem; letter-spacing:.5px}
.hl {padding:.05rem .2rem; border-radius:4px}
.answer-box {border:1px solid rgba(128,128,128,.35); border-radius:10px; padding:1rem 1.1rem;
             line-height:1.75; font-size:1rem}
.chip {display:inline-block; margin:.15rem .3rem .15rem 0; padding:.15rem .6rem; border-radius:999px;
       font-size:.85rem; color:#fff}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- state
ss = st.session_state
for k, v in {"q": "", "m": "", "s": "", "x": 5.0, "rubric": "", "history": [], "result": None,
             "result_id": 0, "compare": None, "batch_out": None}.items():
    ss.setdefault(k, v)


def load_sample():
    name = ss.get("sample_pick")
    s = next((x for x in SAMPLES if x["name"] == name), None)
    if s:
        ss.q, ss.m, ss.s, ss.x, ss.rubric = s["question"], s["model_answer"], s["student_answer"], \
            float(s["max_marks"]), ""


def clear_inputs():
    ss.q = ss.m = ss.s = ss.rubric = ""
    ss.x = 5.0
    ss.sample_pick = None
    ss.result = None
    ss.compare = None


def round_half(x):
    return round(float(x) * 2) / 2


def grade_of(pct):
    for cut, g in ((90, "A+"), (80, "A"), (70, "B+"), (60, "B"), (50, "C"), (40, "D")):
        if pct >= cut:
            return g
    return "F"


# ---------------------------------------------------------------- charts
def gauge(value, max_value, title="Score"):
    pct = 100 * value / max_value if max_value else 0
    color = GRADE_COLOR[grade_of(pct)]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix": f" / {max_value:g}", "font": {"size": 34}},
        title={"text": title, "font": {"size": 15}},
        gauge={"axis": {"range": [0, max_value]}, "bar": {"color": color, "thickness": .75},
               "steps": [{"range": [0, max_value * .4], "color": "rgba(214,69,69,.15)"},
                         {"range": [max_value * .4, max_value * .7], "color": "rgba(224,165,0,.15)"},
                         {"range": [max_value * .7, max_value], "color": "rgba(46,158,91,.15)"}]}))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def points_chart(df):
    d = df.copy()
    d["label"] = [p if len(p) <= 45 else p[:42] + "…" for p in d["point"]]
    fig = go.Figure()
    fig.add_bar(y=d["label"], x=d["weight"], orientation="h", name="Possible",
                marker_color="rgba(128,128,128,.25)", hovertext=d["point"])
    fig.add_bar(y=d["label"], x=d["marks"], orientation="h", name="Awarded",
                marker_color=[STATUS_COLOR.get(s, "#888") for s in d["status"]], hovertext=d["point"])
    fig.update_layout(barmode="overlay", height=max(220, 48 * len(d) + 60),
                      margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.15),
                      yaxis=dict(autorange="reversed"), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Marks")
    return fig


def highlight(text, key_points):
    """Wrap evidence phrases found in the student answer in coloured <mark> tags."""
    spans = []
    low = text.lower()
    for kp in key_points:
        ev = (kp.get("evidence") or "").strip().strip('"').strip("'")
        if len(ev) < 4 or kp["status"] == "missing":
            continue
        for piece in re.split(r"\s*(?:\.\.\.|…|;|\|)\s*", ev):
            i = low.find(piece.lower()) if len(piece) >= 4 else -1
            if i != -1:
                spans.append((i, i + len(piece), kp["status"], kp["point"]))
    spans.sort()
    out, pos = [], 0
    for a, b, status, point in spans:
        if a < pos:
            continue
        out.append(html.escape(text[pos:a]))
        out.append(f'<mark class="hl" title="{html.escape(point)}" '
                   f'style="background:{STATUS_COLOR[status]}33;border-bottom:2px solid {STATUS_COLOR[status]}">'
                   f'{html.escape(text[a:b])}</mark>')
        pos = b
    out.append(html.escape(text[pos:]))
    return "".join(out).replace("\n", "<br>"), len(spans)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    provider = st.selectbox("LLM provider", list(PROVIDERS))
    cfg = PROVIDERS[provider]
    model = st.text_input("Model", value=cfg["default_model"], disabled=cfg["base_url"] is None)
    api_key = None  # keys are read only from the .env file and are never shown in the UI
    if cfg["env_key"]:
        if os.getenv(cfg["env_key"]):
            st.caption("🔒 API key loaded securely from .env")
        else:
            st.warning(f"No API key found. Add {cfg['env_key']} to the .env file, or pick *Offline demo*.")
    strictness = st.select_slider("Grading style", list(STRICTNESS), value="Balanced")
    st.caption(STRICTNESS[strictness])
    st.divider()
    count_slot = st.empty()  # filled at the end of the script so it includes this run's evaluation
    with st.expander("ℹ️ How it works"):
        st.markdown(
            "1. Model answer is split into key points with weights = max marks\n"
            "2. Each point is checked in the student answer (covered / partial / missing)\n"
            "3. Marks = sum of points − deductions for wrong facts\n"
            "4. You can **edit the rubric** to override any decision")

st.title("📝 Answer Sheet Evaluator")
st.caption("Compare a student's descriptive answer with the model answer and get a suggested score with feedback.")

tab_eval, tab_batch, tab_hist = st.tabs(["✍️ Evaluate", "📊 Batch (CSV)", "🕘 History"])


# ---------------------------------------------------------------- results view
def show_result(r, rid):
    base = pd.DataFrame(r.key_points) if r.key_points else pd.DataFrame(
        columns=["point", "weight", "status", "marks", "evidence"])

    # The teacher's working copy of the rubric lives in session state; every edit is applied to it and the
    # editor is re-created (new key version) so derived marks show up in the table straight away.
    df_key, ver_key = f"rub_{rid}", f"ver_{rid}"
    if df_key not in ss:
        ss[df_key] = base[["point", "weight", "status", "marks", "evidence"]].copy()
        ss[ver_key] = 0
    editor_key = f"editor_{rid}_{ss[ver_key]}"

    def apply_edits():
        df = ss[df_key].copy()
        for row, changes in ss[editor_key]["edited_rows"].items():
            w = float(df.at[row, "weight"] or 0)
            if "status" in changes:
                df.at[row, "status"] = changes["status"]
                if "marks" not in changes:
                    df.at[row, "marks"] = {"covered": w, "partial": w / 2, "missing": 0.0}[changes["status"]]
            if "marks" in changes and changes["marks"] is not None:
                df.at[row, "marks"] = min(max(float(changes["marks"]), 0.0), w)
        ss[df_key] = df
        ss[ver_key] += 1

    def reset_edits():
        ss[df_key] = base[["point", "weight", "status", "marks", "evidence"]].copy()
        ss[ver_key] += 1

    headline = st.container()  # filled after the editor so it reflects teacher overrides, but shown first
    hl, hr = st.columns([4, 1])
    hl.markdown("#### 📋 Rubric — edit any row to override the AI")
    hr.button("↺ Reset to AI marks", on_click=reset_edits, key=f"reset_{rid}", width="stretch")
    st.caption("Double-click a **Status** to change it (marks update automatically), or type your own **Marks**. "
               "The total updates instantly.")
    st.data_editor(
        ss[df_key], key=editor_key, hide_index=True, on_change=apply_edits,
        width="stretch", num_rows="fixed",
        column_config={
            "point": st.column_config.TextColumn("Key point", disabled=True, width="large"),
            "weight": st.column_config.NumberColumn("Weight", disabled=True, format="%.2f"),
            "status": st.column_config.SelectboxColumn("Status", options=["covered", "partial", "missing"],
                                                       required=True),
            "marks": st.column_config.NumberColumn("Marks", min_value=0.0, step=0.25, format="%.2f"),
            "evidence": st.column_config.TextColumn("Evidence in student answer", disabled=True),
        })

    edited = ss[df_key]

    cdl, cdr = st.columns([1, 3])
    deduction = cdl.number_input("Deduction for wrong facts", 0.0, float(r.max_marks), float(r.deduction), 0.5,
                                 key=f"ded_{rid}")
    if len(edited):
        tw = edited["weight"].sum()
        raw = edited["marks"].sum() * (r.max_marks / tw if tw and abs(tw - r.max_marks) > .01 else 1)
        final = round_half(min(max(raw - deduction, 0), r.max_marks))
    else:
        final = r.awarded_marks
    changed = abs(final - r.awarded_marks) > 1e-9
    pct = round(100 * final / r.max_marks, 1)
    grade = grade_of(pct)
    if changed:
        cdr.info(f"✏️ Teacher-adjusted score **{final:g}** (AI suggested {r.awarded_marks:g}).")

    # ----- headline (rendered into the container above the rubric)
    g1, g2 = headline.columns([1.2, 1])
    with g1:
        st.plotly_chart(gauge(final, r.max_marks, "Teacher-adjusted score" if changed else "Suggested score"),
                        width="stretch", key=f"gauge_{rid}_{final}")
    with g2:
        st.markdown(f'<div style="margin-top:2.2rem">Grade<br><span class="grade-badge" '
                    f'style="background:{GRADE_COLOR[grade]}">{grade}</span></div>', unsafe_allow_html=True)
        st.metric("Percentage", f"{pct}%", delta=f"{final - r.awarded_marks:+g} vs AI" if changed else None)
        counts = edited["status"].value_counts() if len(edited) else {}
        st.markdown("".join(f'<span class="chip" style="background:{STATUS_COLOR[s]}">{STATUS_ICON[s]} '
                            f'{int(counts.get(s, 0))} {s}</span>' for s in STATUS_COLOR), unsafe_allow_html=True)

    if r.feedback:
        headline.info(f"**Feedback:** {r.feedback}")

    t1, t2, t3 = st.tabs(["🖍️ Answer highlights", "📈 Marks per point", "💬 Detailed feedback"])
    with t1:
        marked, n = highlight(ss.get("graded_answer", ""), edited.to_dict("records"))
        st.markdown(f'<div class="answer-box">{marked or "<i>(blank answer)</i>"}</div>', unsafe_allow_html=True)
        st.caption(f"{n} evidence phrase(s) highlighted · hover a highlight to see which key point it matches · "
                   + " ".join(f"<span style='color:{c}'>■</span> {s}" for s, c in STATUS_COLOR.items()
                              if s != "missing"), unsafe_allow_html=True)
    with t2:
        if len(edited):
            st.plotly_chart(points_chart(edited), width="stretch", theme=None, key=f"pts_{rid}")
        else:
            st.write("No key points returned.")
    with t3:
        a, b = st.columns(2)
        with a:
            st.markdown("**✅ Strengths**")
            for s in r.strengths or ["—"]:
                st.markdown(f"- {s}")
        with b:
            st.markdown("**❌ Missing points**")
            miss = [p for p, s in zip(edited.get("point", []), edited.get("status", [])) if s != "covered"] \
                if len(edited) else r.missing_points
            for m in miss or ["None — all key points covered! 🎉"]:
                st.markdown(f"- {m}")
        if r.incorrect_statements:
            st.markdown("**⚠️ Incorrect statements**")
            for s in r.incorrect_statements:
                st.markdown(f"- {s}")
        if r.improved_answer_tip:
            st.success(f"💡 **Tip to score full marks:** {r.improved_answer_tip}")

    out = r.to_dict() | {"final_marks": final, "final_percentage": pct, "final_grade": grade,
                         "teacher_adjusted": changed, "key_points": edited.to_dict("records"),
                         "deduction": deduction}
    st.download_button("⬇️ Download result (JSON)", json.dumps(out, indent=2),
                       file_name="evaluation.json", mime="application/json", key=f"dl_{rid}")
    st.caption(f"Evaluated with {r.provider} · {r.model}. This is a suggested score — the teacher has the final say.")

    # keep history in sync with teacher overrides
    for h in ss.history:
        if h["id"] == rid:
            h.update(marks=final, percentage=pct, grade=grade, adjusted=changed)


def run_eval(style):
    return evaluate_answer(ss.q, ss.m, ss.s, ss.x, ss.rubric, style, provider, model, api_key)


# ---------------------------------------------------------------- evaluate tab
with tab_eval:
    st.markdown("**Try a sample:**")
    st.pills("Sample", [s["name"] for s in SAMPLES], key="sample_pick", on_change=load_sample,
             label_visibility="collapsed")

    st.text_area("Question", key="q", height=70, placeholder="Type the exam question…")
    col_a, col_b = st.columns(2)
    with col_a:
        st.text_area("Model answer", key="m", height=220, placeholder="Paste the teacher's model answer…")
        st.caption(f"📝 {len(ss.m.split())} words")
    with col_b:
        st.text_area("Student answer", key="s", height=220, placeholder="Paste the student's answer…")
        mw, sw = _words(ss.m), _words(ss.s)
        overlap = int(100 * len(mw & sw) / len(mw)) if mw else 0
        st.caption(f"📝 {len(ss.s.split())} words · 🔎 rough keyword overlap with model answer: **{overlap}%**")
        if mw:
            st.progress(overlap / 100)

    col_c, col_d = st.columns([1, 3])
    col_c.number_input("Max marks", min_value=0.5, max_value=100.0, step=0.5, key="x")
    col_d.text_input("Custom rubric / marking scheme (optional)", key="rubric",
                     placeholder="e.g. Definition - 1 mark, Diagram - 2 marks, Example - 2 marks")

    b1, b2, b3, _ = st.columns([1.2, 1.6, 0.8, 2])
    go_eval = b1.button("🚀 Evaluate answer", type="primary", width="stretch")
    go_cmp = b2.button("⚖️ Compare grading styles", width="stretch",
                       help="Grade the same answer as Lenient, Balanced and Strict to see how much the marks change")
    b3.button("🧹 Clear", on_click=clear_inputs, width="stretch")

    if (go_eval or go_cmp) and (not ss.q.strip() or not ss.m.strip()):
        st.warning("Please enter at least the question and the model answer.")
    elif go_eval:
        with st.status("Evaluating…", expanded=True) as status:
            try:
                st.write("🧩 Building the scoring prompt…")
                st.write(f"🤖 Asking {provider}…")
                result = run_eval(strictness)
                st.write("✅ Checking and validating the marks…")
                ss.result_id += 1
                ss.result, ss.graded_answer, ss.compare = result, ss.s, None
                ss.history.append({"id": ss.result_id, "time": datetime.now().strftime("%H:%M:%S"),
                                   "question": ss.q[:60], "marks": result.awarded_marks,
                                   "max_marks": result.max_marks, "percentage": result.percentage,
                                   "grade": result.grade, "style": strictness, "model": result.model,
                                   "adjusted": False, "result": result, "answer": ss.s})
                status.update(label=f"Done — {result.awarded_marks:g} / {result.max_marks:g}", state="complete",
                              expanded=False)
                if model and result.model != model:
                    st.warning(f"Model '{model}' is not available on {provider}, so '{result.model}' was used.")
                st.toast(f"Scored {result.awarded_marks:g} / {result.max_marks:g} ({result.grade})", icon="📝")
            except Exception as e:
                status.update(label="Evaluation failed", state="error")
                st.error(f"Evaluation failed: {e}")
    elif go_cmp:
        rows, bar = [], st.progress(0.0, text="Comparing grading styles…")
        try:
            for i, style in enumerate(STRICTNESS):
                r = run_eval(style)
                rows.append({"Style": style, "Marks": r.awarded_marks, "Percentage": r.percentage, "Grade": r.grade})
                bar.progress((i + 1) / len(STRICTNESS), text=f"{style}: {r.awarded_marks:g}")
            ss.compare = (pd.DataFrame(rows), float(ss.x))
        except Exception as e:
            st.error(f"Comparison failed: {e}")
        bar.empty()

    if ss.compare is not None:
        cdf, mx = ss.compare
        st.markdown("#### ⚖️ Grading style comparison")
        fig = px.bar(cdf, x="Style", y="Marks", text="Marks", color="Style",
                     color_discrete_sequence=["#2E9E5B", "#3A7BD5", "#D64545"], range_y=[0, mx])
        fig.update_layout(height=280, showlegend=False, margin=dict(t=10, b=10),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch", theme=None)
        spread = cdf["Marks"].max() - cdf["Marks"].min()
        st.caption(f"Spread between styles: **{spread:g} marks**. A big spread means the answer is borderline.")

    if ss.result is not None:
        st.divider()
        show_result(ss.result, ss.result_id)

# ---------------------------------------------------------------- batch tab
with tab_batch:
    st.markdown("Upload a CSV with columns **question, model_answer, student_answer, max_marks** "
                "(optional: **student_name**, **rubric**). Each row is graded separately.")
    template = pd.DataFrame([{"student_name": f"Student {i + 1}", **{k: s[k] for k in
                              ("question", "model_answer", "student_answer", "max_marks")}}
                             for i, s in enumerate(SAMPLES)])
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Download sample CSV", template.to_csv(index=False), "sample_answers.csv", "text/csv")
    use_demo = c2.toggle("Use the 5 built-in samples instead of uploading")

    up = None if use_demo else st.file_uploader("CSV file", type="csv")
    df = template if use_demo else (pd.read_csv(up).fillna("") if up is not None else None)
    if df is not None:
        need = {"question", "model_answer", "student_answer", "max_marks"}
        if not need.issubset(df.columns):
            st.error(f"Missing columns: {', '.join(sorted(need - set(df.columns)))}")
        else:
            with st.expander(f"Preview ({len(df)} answers)"):
                st.dataframe(df, width="stretch", hide_index=True)
            if st.button("🚀 Evaluate all", type="primary"):
                rows, bar = [], st.progress(0.0)
                for i, row in df.iterrows():
                    name = row.get("student_name", f"Row {i + 1}") or f"Row {i + 1}"
                    try:
                        r = evaluate_answer(str(row["question"]), str(row["model_answer"]),
                                            str(row["student_answer"]), float(row["max_marks"]),
                                            str(row.get("rubric", "")), strictness, provider, model, api_key)
                        rows.append({"student_name": name, "question": row["question"], "marks": r.awarded_marks,
                                     "max_marks": r.max_marks, "percentage": r.percentage, "grade": r.grade,
                                     "missing_points": "; ".join(r.missing_points), "feedback": r.feedback})
                    except Exception as e:
                        rows.append({"student_name": name, "question": row["question"], "marks": None,
                                     "max_marks": row["max_marks"], "percentage": None, "grade": "ERR",
                                     "missing_points": "", "feedback": f"Error: {e}"})
                    bar.progress(len(rows) / len(df), text=f"Graded {len(rows)} / {len(df)}: {name}")
                ss.batch_out = pd.DataFrame(rows)
                st.toast(f"Graded {len(rows)} answers", icon="📊")

    out = ss.batch_out
    if out is not None and len(out):
        ok = out.dropna(subset=["percentage"])
        st.markdown("#### 📊 Class analytics")
        k1, k2, k3, k4 = st.columns(4)
        if len(ok):
            k1.metric("Average", f"{ok['percentage'].mean():.1f}%")
            k2.metric(f"Highest · {ok.loc[ok['percentage'].idxmax(), 'student_name']}",
                      f"{ok['percentage'].max():.1f}%")
            k3.metric(f"Lowest · {ok.loc[ok['percentage'].idxmin(), 'student_name']}",
                      f"{ok['percentage'].min():.1f}%")
            k4.metric("Pass rate (≥40%)", f"{100 * (ok['percentage'] >= 40).mean():.0f}%")
            ch1, ch2 = st.columns([1.6, 1])
            with ch1:
                fig = px.bar(ok, x="student_name", y="percentage", color="grade", text="marks",
                             color_discrete_map=GRADE_COLOR, hover_data=["question", "max_marks"],
                             labels={"student_name": "Student", "percentage": "%"}, range_y=[0, 100])
                fig.add_hline(y=40, line_dash="dot", annotation_text="pass")
                fig.update_layout(height=320, margin=dict(t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width="stretch", theme=None)
            with ch2:
                gc = ok["grade"].value_counts().reset_index()
                fig = px.pie(gc, names="grade", values="count", hole=.55, color="grade",
                             color_discrete_map=GRADE_COLOR)
                fig.update_layout(height=320, margin=dict(t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width="stretch", theme=None)

        grades = st.multiselect("Filter by grade", sorted(out["grade"].unique()), placeholder="All grades")
        view = out[out["grade"].isin(grades)] if grades else out
        st.dataframe(view, width="stretch", hide_index=True, column_config={
            "percentage": st.column_config.ProgressColumn("Percentage", min_value=0, max_value=100, format="%.0f%%")})
        buf = io.StringIO()
        out.to_csv(buf, index=False)
        st.download_button("⬇️ Download results CSV", buf.getvalue(), "results.csv", "text/csv")

# ---------------------------------------------------------------- history tab
with tab_hist:
    if not ss.history:
        st.info("No evaluations yet — grade an answer in the **Evaluate** tab and it will show up here.")
    else:
        h = pd.DataFrame([{k: v for k, v in x.items() if k not in ("result", "answer")} for x in ss.history])
        fig = px.line(h, x="id", y="percentage", markers=True, text="grade", hover_data=["question", "marks"],
                      labels={"id": "Evaluation #", "percentage": "%"}, range_y=[0, 105])
        fig.update_traces(textposition="top center")
        fig.update_xaxes(dtick=1)
        fig.update_layout(height=260, margin=dict(t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch", theme=None)
        st.dataframe(h, width="stretch", hide_index=True, column_config={
            "percentage": st.column_config.ProgressColumn("Percentage", min_value=0, max_value=100, format="%.0f%%"),
            "adjusted": st.column_config.CheckboxColumn("Teacher-adjusted")})
        hc1, hc2, hc3 = st.columns([2, 1, 1])
        pick = hc1.selectbox("Re-open an evaluation", [x["id"] for x in ss.history],
                             format_func=lambda i: next(f"#{x['id']} · {x['time']} · {x['question']}"
                                                        for x in ss.history if x["id"] == i))
        if hc2.button("↩️ Open in Evaluate tab", width="stretch"):
            item = next(x for x in ss.history if x["id"] == pick)
            ss.result, ss.result_id, ss.graded_answer = item["result"], item["id"], item["answer"]
            st.toast("Opened — switch to the ✍️ Evaluate tab", icon="↩️")
        if hc3.button("🗑️ Clear history", width="stretch"):
            ss.history = []
            st.rerun()
        st.download_button("⬇️ Download history CSV", h.to_csv(index=False), "history.csv", "text/csv")

count_slot.metric("Answers evaluated this session", len(ss.history))
