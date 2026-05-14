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
- **ML Ranking** — recipes are re-ranked using sentence embeddings and star ratings to surface results that match your personal taste over time
- **Saved Recipes** — selected recipes are saved to your profile with full instructions and a 1–5 star rating widget

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

## Use of AI Declaration

In accordance with HSG guidelines on generative AI, we disclose the following use of AI tools in this project. All AI-generated output was reviewed and validated by the responsible team member before integration.

### AI within the application

- **Fridge Scanner** — Claude Haiku 4.5 (`claude-haiku-4-5`) via Anthropic API  
  Analyses uploaded fridge photos and extracts a list of detected ingredients

### AI as a development tool

We used **Claude Code** (powered by **Claude Sonnet 4.6**, `claude-sonnet-4-6`) as a coding assistant during development. Specifically:

- **Integration** — assistance in merging independently developed modules from different group members into a single coherent codebase
- **Debugging** — identifying and fixing compatibility issues that arose during integration (e.g. session state conflicts, API key loading)

Reference: [HSG Guidelines for Generative AI](https://universitaetstgallen.sharepoint.com/sites/PruefungenDE/SitePages/Arbeiten-mit-KI.aspx)

