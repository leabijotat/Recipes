"""
Machine-learning layer for the Bon app! recipe app.

What it does:
  1. Embeds each saved recipe (title + ingredient names) into a vector
     using a small sentence-transformer model.
  2. Lets the user rate saved recipes 1-5 stars in the sidebar.
  3. Builds a "preference vector" = rating-weighted average of the
     embeddings of recipes the user has rated.
  4. When the user runs a new search, blends the existing
     waste-score / serving-proximity ranking with cosine similarity to
     that preference vector — so future results lean toward the kind of
     recipes the user has rated highly.

Everything ML-related lives here; the rest of the app only needs to
import a few small helpers from this file.
"""

import numpy as np
import streamlit as st

from src.db import get_conn, save_recipe, get_nutrient
from src.api import calculate_waste_score

MODEL_NAME = "all-MiniLM-L6-v2"


@st.cache_resource(show_spinner="Loading recommendation model...")
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def _build_text(recipe):
    title = recipe.get("title", "")
    ings = recipe.get("nutrition", {}).get("ingredients", [])
    return title + " " + " ".join(ing.get("name", "") for ing in ings)


def _embed(text):
    return _get_model().encode(text, normalize_embeddings=True).astype(np.float32)


# ── Saving ───────────────────────────────────────────────────────────
def embed_and_save_recipe(user_id, recipe):
    """Compute embedding for the recipe and persist it via save_recipe."""
    vec = _embed(_build_text(recipe))
    save_recipe(user_id, recipe, embedding=vec.tobytes())


# ── Sidebar data + rating UI ─────────────────────────────────────────
def get_saved_with_ratings(user_id):
    """Like db.get_saved_recipes but also returns row id + rating."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, recipe_title, recipe_image, calories, protein, saved_at, "
        "instructions, rating FROM saved_recipes WHERE user_id=? "
        "ORDER BY saved_at DESC",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def _update_rating(rec_id, user_id, new_rating):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE saved_recipes SET rating=? WHERE id=? AND user_id=?",
        (new_rating, rec_id, user_id),
    )
    conn.commit()
    conn.close()


def render_rating_widget(rec_id, user_id, current_rating, key_prefix):
    """Render a 1-5 star widget; persist changes and rerun on click."""
    widget_key = f"rate_{key_prefix}_{rec_id}"
    # Seed the widget with the stored value the first time we render it.
    if widget_key not in st.session_state and current_rating:
        st.session_state[widget_key] = current_rating - 1
    new = st.feedback("stars", key=widget_key)
    if new is not None and (new + 1) != (current_rating or 0):
        _update_rating(rec_id, user_id, new + 1)
        st.rerun()


# ── Preference vector + ranking ──────────────────────────────────────
def get_preference_vector(user_id):
    """Weighted sum of embeddings of recipes the user has rated.

    Weight = (rating - 3) so 4-5★ recipes pull the vector toward them
    and 1-2★ recipes push it away. Returns None if there are no rated
    recipes with embeddings yet.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT rating, embedding FROM saved_recipes "
        "WHERE user_id=? AND rating > 0 AND embedding IS NOT NULL",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    if not rows:
        return None
    vecs = np.stack([np.frombuffer(b, dtype=np.float32) for _, b in rows])
    weights = np.array([r - 3 for r, _ in rows], dtype=np.float32)
    pref = (vecs * weights[:, None]).sum(axis=0)
    norm = np.linalg.norm(pref)
    return pref / norm if norm > 0 else None


def rank_recipes(recipes, selected, priority, persons, user_id):
    """Rank search results by waste + serving proximity + preference.

    If the user has no ratings yet, falls back to the original
    waste(0.7) + serving-proximity(0.3) score. Once ratings exist, the
    final score is 0.5 * (that base) + 0.5 * (normalized cosine
    similarity to the preference vector).
    """
    pref = get_preference_vector(user_id)
    sims = None
    if pref is not None and recipes:
        embeds = np.stack([_embed(_build_text(r)) for r in recipes])
        sims = embeds @ pref
        lo, hi = sims.min(), sims.max()
        sims = (sims - lo) / (hi - lo) if hi > lo else np.full_like(sims, 0.5)

    scored = []
    for i, r in enumerate(recipes):
        waste = calculate_waste_score(r, selected, priority)[0]
        servings = r.get("servings", persons)
        proximity = max(0, 1 - abs(servings - persons) / max(persons, 1))
        base = 0.7 * waste + 0.3 * proximity
        s = 0.5 * base + 0.5 * float(sims[i]) if sims is not None else base
        scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored]
