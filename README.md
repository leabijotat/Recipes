# Bon app! — Recipes crafted just for you

## Problem

People often don't know what to cook with the ingredients they already have at home. This leads to unnecessary food waste, unplanned grocery shopping, and difficulty sticking to nutritional goals. Existing recipe platforms require manual searching and don't account for what's already in your fridge, your dietary restrictions, or your personal health goals.

**Bon app!** solves this by letting users input their available ingredients — manually or via an AI-powered fridge scan — set nutritional goals and dietary preferences, and receive personalized recipe recommendations ranked by how well they use up what's already on hand.

---

## Features

- **AI Fridge Scanner** — upload a fridge photo, Claude Vision automatically identifies ingredients
- **Recipe Search** — Spoonacular API returns recipes filtered by ingredients, nutrition, prep time, and dietary restrictions
- **Waste Score** — recipes are ranked by how many of your ingredients they use, with extra weight for expiring items
- **Battle Mode** — compare recipes head-to-head with nutritional breakdowns and taste profiles
- **User Accounts** — login/signup with allergy, diet, and religious preferences stored in a database
- **Saved Recipes** — winning recipes are saved to your profile with full instructions

---

## Project Structure

```
├── app.py              # Main Streamlit app — all pages and UI logic
├── src/
│   ├── api.py          # Spoonacular API calls, waste scoring, Plotly charts
│   ├── db.py           # SQLite database setup and queries
│   ├── fridge_scan.py  # Streamlit UI for the fridge scanner
│   └── vision.py       # Claude Vision API — image encoding and ingredient extraction
├── env/.env            # API keys (not included in submission)
└── requirements.txt    # Python dependencies
```

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Create a file `env/.env` with:
```
SPOONACULAR_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

---

## AI Tools Used

This project was developed with the assistance of **Claude (Anthropic)** as a coding tool. In line with HSG guidelines, all AI-generated contributions have been reviewed and understood by the responsible team member.

| Area | Tool | Usage |
|------|------|-------|
| Fridge Scanner (`vision.py`, `fridge_scan.py`) | Claude | Implementation of Claude Vision API for ingredient recognition from photos |
| UI & Styling (`app.py`) | Claude | CSS styling, Streamlit layout and session state patterns |
| Recipe API & Scoring (`api.py`) | Claude | Spoonacular integration, waste score algorithm, Plotly charts |
| Database (`db.py`) | Claude | SQLite schema design and query functions |
| Debugging | Claude | Fixing bugs across all files (e.g. API key loading, rerun conflicts) |

Reference: [HSG Guidelines for Generative AI](https://universitaetstgallen.sharepoint.com/sites/PruefungenDE/SitePages/Arbeiten-mit-KI.aspx)

---

## Contribution Matrix

| Task | Sydney | David | Julia | Lea | Raphael |
|------|--------|-------|-------|-----|---------|
| Project Management | | | | | |
| Concept & Problem Definition | | | | | |
| Fridge Scanner (AI Vision) | | | | | |
| Recipe API & Scoring | | | | | |
| Database & User Auth | | | | | |
| UI / Frontend | | | | | |
| Battle Mode | | | | | |
| Testing & Debugging | | | | | |
| Video & Presentation | | | | | |

**Legend:** 🟩 Main contributor &nbsp;·&nbsp; 🟦 Significant contribution &nbsp;·&nbsp; 🟨 Support &nbsp;·&nbsp; ⬜ No contribution
