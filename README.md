# 📝 Answer Sheet Evaluator — GenAI Mini Project (PS 24)

**Name:** Honey Soni  |  **Roll No:** 24

**Problem:** Checking descriptive answers by hand is slow. This app compares a student's answer with
the model answer and suggests a score with feedback.

**How it works:** question + model answer + student answer + max marks → prompt with a scoring
rubric → LLM → marks, missing points and feedback.

## Features
- Rubric-based scoring: the model answer is split into weighted key points (weights add up to max marks); each point is marked **covered / partial / missing**
- Deductions for factually wrong statements (capped at 20% of max marks)
- Output: marks, percentage, grade, strengths, missing points, rubric table, feedback, tip for full marks
- Optional custom marking scheme and grading style (Lenient / Balanced / Strict)
- **Interactive UI**
  - One-click sample buttons, plus live word counts and a keyword-overlap meter
  - Animated score gauge, a coloured grade badge and covered / partial / missing chips
  - **Editable rubric:** the teacher can change any point's status or marks, and the score updates instantly (with a reset button)
  - Evidence highlighting in the student answer and a chart of marks for each point
  - **Compare grading styles** (Lenient vs Balanced vs Strict)
  - **Batch tab:** grade a CSV of answers and see class analytics (average, highest, lowest, pass rate, grade charts)
  - **History tab:** score trend, re-open past evaluations, CSV download
- Works with **Groq, Gemini, OpenAI or local Ollama**; an **offline demo mode** runs without any API key
- **Security:** the API key is read only from a local `.env` file. It is never shown in the app, and `.gitignore` keeps it out of GitHub
- Safety checks: JSON output is validated in Python, marks are clamped to 0..max and rounded to 0.5, and instructions written inside the student answer (e.g. "give me full marks") are ignored

## Project structure
| File | Purpose |
|---|---|
| `app.py` | Interactive Streamlit UI (Evaluate, Batch, History) |
| `evaluator.py` | Prompt design, LLM call, JSON parsing and validation |
| `samples.py` | 5 sample inputs (good, partial, wrong facts, off-topic, different wording) |
| `requirements.txt` | Python packages |
| `.env.example` | Template for the API key file |

## Setup
```bash
pip install -r requirements.txt
```
Copy `.env.example` to `.env` and add a free key, for example `GROQ_API_KEY=...`.
Groq keys are at https://console.groq.com/keys and Gemini keys are at https://aistudio.google.com/apikey.

## Run
```bash
streamlit run app.py
```

## Prompt design (summary)
The system prompt makes the LLM act as an examiner and follow fixed steps:
1. Extract 3–8 key points from the model answer and give each a weight; the weights must add up to max marks.
2. Mark each point covered (full), partial (about half) or missing (0).
3. Deduct for wrong facts; judge meaning, not length or wording.
4. Return strict JSON. Temperature 0 keeps marks stable between runs.

> The score is a suggestion to help the teacher, who has the final say.
