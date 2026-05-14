"""
Machine-learning for individualized recipe recommendation
What it does:
  1. Embeds each saved recipe (title + ingredient names) into a vector
     using a  sentence-transformer model ("all-MiniLM-L6-v2").
     The vector is stored in the local SQLite database.
  2. Lets the user rate saved recipes 1-5 stars in the sidebar
  3. Builds a "preference vector" = rating-weighted average of the
     embeddings of recipes the user has rated.
  4. When the user runs a new search, blends the existing
     waste-score / serving-proximity ranking with cosine similarity to
     that preference vector, so future results lean toward the kind of
     recipes the user has rated highly and away from those rated low.

Several functions in app.py import from here. A few helpers below
(get_saved_with_ratings, _update_rating) are near-duplicates of
queries that already exist in db.py. I kept ML-specific versions
here so the rest of the app can keep using its original DB code
unchanged, and so anything ML-related lives in one place.
"""

import numpy as np
import streamlit as st

from src.db import get_conn, save_recipe, get_nutrient
from src.api import calculate_waste_score

MODEL_NAME = "all-MiniLM-L6-v2"


@st.cache_resource(show_spinner="Loading recommendation model...")
def _get_model():
    """Load the sentence transformer model once and reuse it.
    @st.cache_resource caches the loaded model across Streamlit reruns
    so we don't reload it every time the user clicks
    something. 
    Import i inside the function, the sentence_transformers package is only loaded 
    when the model is needed for the first time.
    """
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def _build_text(recipe):
    """Build the text that gets into the embedding model (out of recipe name and ingredients)
    The model later converts this string into a 384-D vector that captures the recipe's semantic meaning
    """
    title = recipe.get("title", "")
    ings = recipe.get("nutrition", {}).get("ingredients", [])
    return title + " " + " ".join(ing.get("name", "") for ing in ings)


def _embed(text):
    """Turn a string into a 384-dim float32 vector.
    normalize_embeddings=True scales every vector to length 1 so a
    later dot product (`a @ b`) is directly the cosine similarity
    between the two vectors.
    """
    return _get_model().encode(text, normalize_embeddings=True).astype(np.float32)


# Saving
def embed_and_save_recipe(user_id, recipe):
    """Compute the recipe's embedding and persist it via save_recipe.
    Called from app.py whenever the user picks a recipe (either by
    winning the battle or by clicking "Pick this one"). The embedding
    is stored with the rest of the recipe so it can later contribute to the 
    preference vector if the user rates it (which will happen later)
    """
    vec = _embed(_build_text(recipe))
    # Convert the NumPy embedding vector to raw bytes so SQLite can
    # store it as a BLOB column. We reverse this with np.frombuffer
    # when reading the vector back out of the DB.
    save_recipe(user_id, recipe, embedding=vec.tobytes())


# Sidebar data and rating UI
def get_saved_with_ratings(user_id):
    """Return the user's saved recipes plus row id and current rating.
    """
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
    """Write the user's new star rating for a saved recipe.

    Filtering by both id AND user_id is a small safety measure: even
    if rec_id were ever wrong, the UPDATE can only ever touch rows
    that belong to the logged-in user.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE saved_recipes SET rating=? WHERE id=? AND user_id=?",
        (new_rating, rec_id, user_id),
    )
    conn.commit()
    conn.close()


def render_rating_widget(rec_id, user_id, current_rating, key_prefix):
    """Render a 1-5 star widget that send the rating back to the DB.
    (minus 1 because st.feedback is 0-indexed internally).
    """
    widget_key = f"rate_{key_prefix}_{rec_id}"
    # setting an initial value: the stored rating only the first time we render it; 
    # afterwards Streamlit owns this session_state slot
    if widget_key not in st.session_state and current_rating:
        st.session_state[widget_key] = current_rating - 1
    new = st.feedback("stars", key=widget_key)
    # st.feedback returns 0-4 (or None if nothing is selected).
    # Convert back to 1-5 and only hit the database when the value actually changed.
    if new is not None and (new + 1) != (current_rating or 0):
        _update_rating(rec_id, user_id, new + 1)
        # Force a rerun so the sidebar immediately reflects the new rating and the 
        # next search picks up the updated preference vector.
        st.rerun()


def get_preference_vector(user_id):
    """Return the user's preference vector, or None if no ratings yet.
    weights = (rating - 3) — so 4-5★ recipes pull the vector toward
    them, 1-2★ recipes push it away, and 3★ recipes are neutral. The
    final vector is L2-normalized so it can be compared with another
    unit vector via a plain dot product (cosine sim.).
    """
    conn = get_conn()
    c = conn.cursor()
    # Only consider recipes that have a star rating and an embedding stored.
    c.execute(
        "SELECT rating, embedding FROM saved_recipes "
        "WHERE user_id=? AND rating > 0 AND embedding IS NOT NULL",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    if not rows:
        return None
    # Changes BLOB back into a 384D float32 array and stack put into a (n_rated, 384) matrix.
    vecs = np.stack([np.frombuffer(b, dtype=np.float32) for _, b in rows])
    weights = np.array([r - 3 for r, _ in rows], dtype=np.float32)
    # Multiply each row by its weight (recipe embedded * what you rated it),
    # then sum down to a single 384-dim vector (creating one single vector out of all the sclaed recipes)
    pref = (vecs * weights[:, None]).sum(axis=0)
    # dividing vector by its lenght gives unit vector, which is what cosine similarity expects.
    norm = np.linalg.norm(pref)
    return pref / norm if norm > 0 else None


def rank_recipes(recipes, selected, priority, persons, user_id):
    """Rank search results by waste + serving proximity + preference.
    If the user has no ratings yet, the result is the original
    waste(0.7) + serving-proximity(0.3) score. Once at least one
    recipe has been rated, the final score becomes 0.5 * (that base) + 0.5 * (cosine similarity to the preference
    vector, rescaled to [0, 1]).
    """
    pref = get_preference_vector(user_id)
    sims = None
    if pref is not None and recipes:
        # Embed every candidate recipe and dot it with the preference
        # vector. since all ar normed, just multiply them
        embeds = np.stack([_embed(_build_text(r)) for r in recipes])
        sims = embeds @ pref
        # Cosine similarities live in [-1, 1]; rescale them to [0, 1] so they are 
        # directly comparable to the waste/proximity score in the mix
        # If every candidate has the same similarity (hi == lo), fall back to a neutral 0.5 to avoid dividing by zero.
        lo, hi = sims.min(), sims.max()
        sims = (sims - lo) / (hi - lo) if hi > lo else np.full_like(sims, 0.5)

    scored = []
    for i, r in enumerate(recipes):
        # "base" score: how well the recipe uses the ingredients the user has on hand (waste) 
        # and how close its serving count is to the requested number of persons (proximity).
        waste = calculate_waste_score(r, selected, priority)[0]
        servings = r.get("servings", persons)
        proximity = max(0, 1 - abs(servings - persons) / max(persons, 1))
        base = 0.7 * waste + 0.3 * proximity
        # Blend the base with the  similarity. Equal weight (0.5 / 0.5) (no math necessity)
        s = 0.5 * base + 0.5 * float(sims[i]) if sims is not None else base
        scored.append((s, r))
    # Sort tuples by score (first element) in descending order so the best match ends up first.
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]
