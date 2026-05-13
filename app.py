import hashlib
import streamlit as st
import sqlite3  #for the SQLite database

#for .env file
import os 
from dotenv import load_dotenv  
load_dotenv("env/.env")

# to get functions from other files
# ML: REMOVED `save_recipe` AND `get_saved_recipes` FROM THIS IMPORT — REPLACED BY
# `embed_and_save_recipe` AND `get_saved_with_ratings` FROM src/ml.py.
from src.db import init_db, get_user_preferences
from src.api import (
    GOAL_DESCRIPTIONS, build_nutrition_params, search_recipes,
    calculate_waste_score, render_battle_card, get_nutrient,
    make_donut, make_calorie_bar, get_taste_profile, render_taste_bars
)
# ML: ALL MACHINE-LEARNING HELPERS (EMBEDDING, RATING UI, PREFERENCE-AWARE RANKING) LIVE IN src/ml.py
from src.ml import (
    embed_and_save_recipe, get_saved_with_ratings,
    render_rating_widget, rank_recipes,
)
# FRIDGE: PHOTO-SCAN UI THAT RETURNS A LIST OF DETECTED INGREDIENT NAMES
from src.fridge_scan import render_fridge_scanner

# ─────────────────────────────────────────
#  PAGE CONFIG & CSS
# ─────────────────────────────────────────
st.set_page_config(page_title="Bon app! — recipes just for you", layout="centered")

st.markdown("""
<style>
.stApp { background-color: #F7FAF8; }

.block-container {
    max-width: 1100px !important;
    padding: 40px !important;
    margin-top: 60px !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: white;
    border-radius: 24px;
    box-shadow: 0 6px 24px rgba(34, 87, 122, 0.09);
    border: 1px solid #E7E7E2;
    padding: 18px;
    margin-bottom: 14px;
}

.app-title {
    text-align: center;
    color: #22577A;
    font-size: 44px;
    font-weight: 850;
    margin-bottom: 4px;
    letter-spacing: -1px;
}

.app-subtitle {
    text-align: center;
    color: #57CC99;
    font-size: 16px;
    margin-bottom: 30px;
    font-weight: 500;
}

.stButton>button {
    background-color: #22577A;
    color: white;
    border: none;
    border-radius: 14px;
    height: 52px;
    font-size: 17px;
    font-weight: 700;
    margin-top: 10px;
}
.stButton>button:hover {
    background-color: #38A3A5;
    color: white;
}

.recipe-title {
    font-size: 16px;
    font-weight: 700;
    color: #22577A;
    margin-bottom: 4px;
}

.macro-pill {
    display: inline-block;
    background: #EEF5FB;
    border: 1px solid #B8D6ED;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 12px;
    color: #22577A;
    font-weight: 600;
    margin-right: 4px;
}

.goal-hint {
    font-size: 12px;
    color: #888;
    margin-top: -8px;
    margin-bottom: 8px;
}

.section-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #22577A;
    color: white;
    font-size: 13px;
    font-weight: 600;
    flex-shrink: 0;
    margin-right: 8px;
}

.vs-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
    font-weight: 900;
    color: #22577A;
    height: 100%;
    padding-top: 80px;
}

.battle-title {
    text-align: center;
    font-size: 36px;
    font-weight: 900;
    color: #22577A;
    margin-bottom: 4px;
    letter-spacing: -1px;
}

.battle-subtitle {
    text-align: center;
    color: #888;
    font-size: 14px;
    margin-bottom: 20px;
}

.progress-bar-bg {
    background: #E7E7E2;
    border-radius: 10px;
    height: 8px;
    margin: 8px 0 18px 0;
}

.progress-bar-fill {
    background: linear-gradient(90deg, #22577A, #57CC99);
    border-radius: 10px;
    height: 8px;
}

.back-btn button {
    background-color: transparent !important;
    color: #22577A !important;
    border: 2px solid #22577A !important;
}
.back-btn button:hover {
    background-color: #22577A !important;
    color: white !important;
}

button[kind="secondary"] {
    background-color: transparent !important;
    color: #22577A !important;
    border: 1px solid #22577A !important;
    height: 28px !important;
    font-size: 11px !important;
    font-weight: 400 !important;
    padding: 0 8px !important;
    margin-top: 2px !important;
    min-height: unset !important;
    line-height: 1 !important;
}
button[kind="secondary"]:hover {
    background-color: #22577A !important;
    color: white !important;
}

.saved-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #E7E7E2;
}
.saved-card img {
    width: 52px;
    height: 52px;
    object-fit: cover;
    border-radius: 10px;
    flex-shrink: 0;
}
.saved-card-info {
    flex: 1;
    min-width: 0;
}
.saved-card-title {
    font-size: 13px;
    font-weight: 700;
    color: #22577A;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.saved-card-meta {
    font-size: 11px;
    color: #999;
    margin-top: 2px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  INIT
# ─────────────────────────────────────────
init_db() #creates tables in database
api_key = os.environ.get("SPOONACULAR_API_KEY", "")

# keep user logged in across reruns
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

# ─────────────────────────────────────────
#  LOGIN / SIGNUP
# ─────────────────────────────────────────
if st.session_state["logged_in_user"] is None:
    import sqlite3 as _sqlite3
    from src.db import get_conn

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown('<div style="text-align:center; font-size:36px; font-weight:800; color:#22577A;">Bon app!</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center; color:#57CC99; font-size:15px; margin-bottom:20px;">Recipes crafted just for you</div>', unsafe_allow_html=True)

            login_tab, signup_tab = st.tabs(["Login", "Create account"])

            with login_tab:
                st.markdown("### Welcome back!")
                login_email    = st.text_input("Email",    key="login_email")
                login_password = st.text_input("Password", type="password", key="login_password")

                if st.button("Login", use_container_width=True, type="primary"):
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("SELECT id, password FROM users WHERE email=?", (login_email,))
                    result = c.fetchone()
                    conn.close()
                    if result:
                        user_id, db_pw = result
                        if db_pw == login_password:
                            st.session_state["logged_in_user"] = user_id
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Wrong password.")
                    else:
                        st.error("User not found.")

            with signup_tab:
                st.markdown("### Create your account")
                email    = st.text_input("Email",    key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")

                st.markdown("### Tell us about you")
                selected_allergies = st.multiselect(
                    "Common allergies",
                    ["peanuts", "milk", "eggs", "gluten", "soy", "seafood"]
                )
                manual_allergies = st.text_input("Other allergies", placeholder="e.g. kiwi, strawberries")
                manual_allergies_list = [a.strip().lower() for a in manual_allergies.split(",") if a.strip()]
                all_allergies    = list(set(selected_allergies + manual_allergies_list))
                allergies_for_db = ",".join(all_allergies)

                diet_preference       = st.selectbox("Diet preference",      ["None", "Vegetarian", "Vegan"])
                religious_restriction = st.selectbox("Religious restriction", ["None", "Halal", "Kosher"])

                if st.button("Create account", use_container_width=True, type="primary"):
                    if not email or not password:
                        st.error("Please enter an email and password.")
                    else:
                        conn = get_conn()
                        c = conn.cursor()
                        try:
                            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
                            user_id = c.lastrowid
                            c.execute(
                                "INSERT INTO preferences (user_id, allergies, diet, religion) VALUES (?, ?, ?, ?)",
                                (user_id, allergies_for_db, diet_preference, religious_restriction)
                            )
                            conn.commit()
                            conn.close()
                            st.success("Account created! Please log in.")
                        except _sqlite3.IntegrityError:
                            st.error("This email already exists.")

# ─────────────────────────────────────────
#  MAIN APP (logged in)
# ─────────────────────────────────────────
else:
    from src.db import get_conn
    user_id = st.session_state["logged_in_user"]

    if "preferences" not in st.session_state:
        st.session_state["preferences"] = get_user_preferences(user_id)
    prefs = st.session_state["preferences"]

    # Sidebar
    with st.sidebar:
        st.markdown("### Your profile")
        if prefs["allergies"]:
            st.markdown(f"**Allergies:** {', '.join(prefs['allergies'])}")
        if prefs["diet"] != "None":
            st.markdown(f"**Diet:** {prefs['diet']}")
        if prefs["religion"] != "None":
            st.markdown(f"**Restriction:** {prefs['religion']}")
        st.markdown("---")
        st.markdown("### Selected recipes")  # ML: RENAMED FROM "My winning recipes" — STARS BELOW BUILD THE PREFERENCE VECTOR
        saved = get_saved_with_ratings(user_id)  # ML: REPLACED get_saved_recipes — THIS VERSION ALSO RETURNS rec_id + rating
        if saved:
            for i, (rec_id, title, image, cal, prot, saved_at, instructions, rating) in enumerate(saved):  # ML: UNPACK ADDITIONAL rec_id + rating
                img_tag = f'<img src="{image}" />' if image else '<div style="width:52px;height:52px;background:#EEF5FB;border-radius:10px;"></div>'
                st.markdown(
                    f'<div class="saved-card">'
                    f'{img_tag}'
                    f'<div class="saved-card-info">'
                    f'<div class="saved-card-title">{title}</div>'
                    f'<div class="saved-card-meta">{cal} kcal · {prot}g prot · {saved_at[:10]}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                render_rating_widget(rec_id, user_id, rating, f"side_{i}")  # ML: 1-5 STAR RATING — FEEDS THE PREFERENCE VECTOR
                if st.button("View recipe", key=f"saved_{i}"):
                    st.session_state["detail_recipe"] = {
                        "title": title, "image": image, "cal": cal,
                        "prot": prot, "instructions": instructions
                    }
                    st.session_state["_prev_page"] = st.session_state.get("page", "quiz")
                    st.session_state["page"] = "detail"
                    st.rerun()
        else:
            st.caption("No saved recipes yet.")
        st.markdown("---")
        if st.button("Logout", type="primary"):
            for key in ["logged_in_user", "preferences", "recipes", "search", "page",
                        "battle_champion", "battle_challenger_idx", "battle_recipes",
                        "battle_done", "battle_selected", "battle_priority", "battle_saved",
                        "detail_recipe", "scanned_ingredients", "scanned_photo_hash"]:
                st.session_state.pop(key, None)
            st.rerun()


    page = st.session_state.get("page", "quiz")

    # ── PAGE DETAIL ──
    if page == "detail":
        recipe = st.session_state.get("detail_recipe", {})
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← Back", type="primary"):
            st.session_state["page"] = st.session_state.get("_prev_page", "quiz")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f'<div style="text-align:center; margin: 20px 0 10px;">'
            f'<div style="font-size:32px; font-weight:900; color:#22577A;">{recipe.get("title","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<span class="macro-pill">{recipe.get("cal",0)} kcal</span>'
            f'<span class="macro-pill">{recipe.get("prot",0)}g prot</span>',
            unsafe_allow_html=True,
        )
        if recipe.get("image"):
            st.image(recipe["image"], use_container_width=True)

        st.markdown("---")
        st.markdown("#### Instructions")
        instructions = recipe.get("instructions", "")
        if instructions:
            for line in instructions.strip().split("\n"):
                st.markdown(line)
        else:
            st.info("No instructions available.")

    # ── PAGE QUIZ ──
    elif page == "quiz":
        st.markdown('<div class="app-title">Bon app!</div>', unsafe_allow_html=True)
        st.markdown('<div class="app-subtitle">Recipes crafted just for you</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">1</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Ingredients</span></div>',
                        unsafe_allow_html=True)
            manual_ingredients = st.text_input("Add ingredients", placeholder="e.g. chicken, tofu, lentils, broccoli")
            manual_list = [i.strip().lower() for i in manual_ingredients.split(",") if i.strip()]
            scanned = render_fridge_scanner()
            all_custom = list(dict.fromkeys(manual_list + scanned))
            if all_custom:
                # Key changes when the pool changes so new items appear pre-selected
                pool_key = "ing_" + hashlib.md5(",".join(sorted(all_custom)).encode()).hexdigest()[:8]
                selected_ingredients = st.multiselect(
                    "Your ingredients — deselect any you don't need:",
                    options=all_custom,
                    default=all_custom,
                    key=pool_key,
                )
            else:
                selected_ingredients = []
                st.caption("Type ingredients above or scan your fridge to get started.")

        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">2</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Expiring soon</span></div>',
                        unsafe_allow_html=True)
            st.caption("Select ingredients that need to be eaten first — recipes using them will be ranked higher.")
            priority_ingredients = st.multiselect(
                "", selected_ingredients,
                placeholder="e.g. spinach, milk...",
                key="priority",
            ) if selected_ingredients else []

            if selected_ingredients:
                chips = ""
                for ing in selected_ingredients:
                    if ing in priority_ingredients:
                        style = "background:#FEF3C7;color:#92400E;"
                        label = f"&#9889; {ing}"
                    else:
                        style = "background:#EEF5FB;color:#22577A;"
                        label = ing
                    chips += (
                        f'<span style="display:inline-block;{style}border-radius:16px;'
                        f'padding:3px 10px;font-size:12px;font-weight:600;margin:3px 4px 3px 0;">'
                        f'{label}</span>'
                    )
                st.markdown(
                    f'<div style="padding:12px 0 2px 0;">'
                    f'<span style="font-size:11px;font-weight:700;color:#aaa;text-transform:uppercase;'
                    f'letter-spacing:.05em;">Your pool &middot; {len(selected_ingredients)} ingredients</span>'
                    f'<div style="margin-top:8px;">{chips}</div></div>',
                    unsafe_allow_html=True,
                )

        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">3</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Your goal</span></div>',
                        unsafe_allow_html=True)
            goal = st.radio("", ["Balanced", "Light", "Energizing", "High Protein"])
            st.markdown(f'<div class="goal-hint">{GOAL_DESCRIPTIONS[goal]}</div>', unsafe_allow_html=True)

            manual_override = st.toggle("Set macros manually")
            manual_cal = manual_prot = manual_fat = manual_carbs = 0
            if manual_override:
                manual_cal   = st.number_input("Max calories (kcal)", min_value=0, max_value=2000, value=600, step=50)
                manual_prot  = st.number_input("Min protein (g)",     min_value=0, max_value=200,  value=20,  step=5)
                manual_fat   = st.number_input("Max fat (g)",         min_value=0, max_value=200,  value=20,  step=5)
                manual_carbs = st.number_input("Min carbs (g)",       min_value=0, max_value=500,  value=0,   step=5)

        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">4</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Preparation time</span></div>',
                        unsafe_allow_html=True)
            max_time = st.slider("", min_value=10, max_value=90, value=30, step=5, format="%d min")

        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">5</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Number of persons</span></div>',
                        unsafe_allow_html=True)
            persons = st.number_input("", min_value=1, max_value=10, value=2)

        if st.button("Find my recipes", use_container_width=True, type="primary"):
            nutrition_params = build_nutrition_params(
                goal, manual_override,
                manual_cal, manual_prot, manual_fat, manual_carbs
            )
            with st.spinner("Finding the perfect recipes for you..."):
                recipes = search_recipes(
                    selected_ingredients, nutrition_params,
                    prefs, max_time, api_key
                )
            if recipes:
                # ML: RANKING NOW LIVES IN src/ml.py — rank_recipes COMBINES THE
                # ORIGINAL waste(0.7) + serving-proximity(0.3) BASE WITH COSINE
                # SIMILARITY TO THE USER'S RATING-WEIGHTED PREFERENCE VECTOR
                # (0.5 / 0.5 BLEND ONCE AT LEAST ONE RECIPE HAS BEEN RATED).
                # REMOVED THE LOCAL `combined_score` HELPER + recipes.sort CALL.
                recipes = rank_recipes(recipes, selected_ingredients, priority_ingredients, persons, user_id)
                st.session_state["all_recipes"]           = recipes[:10]
                st.session_state["battle_recipes"]        = recipes[:3]
                st.session_state["battle_champion"]       = recipes[0]
                st.session_state["battle_challenger_idx"] = 1
                st.session_state["battle_done"]           = False
                st.session_state["battle_selected"]       = selected_ingredients
                st.session_state["battle_priority"]       = priority_ingredients
                st.session_state["page"]      = "results"
                st.rerun()
            else:
                st.warning("No recipes found. Try relaxing some constraints.")

    # ── PAGE RESULTS ──
    elif page == "results":
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← Back to quiz", type="primary"):
            st.session_state["page"] = "quiz"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="app-title">Your recipes</div>', unsafe_allow_html=True)
        st.markdown('<div class="app-subtitle">Pick one directly, or battle them to find the best!</div>', unsafe_allow_html=True)

        if st.button("Can't choose? Battle them!", use_container_width=True, type="primary"):
            st.session_state["battle_done"] = False
            st.session_state["battle_challenger_idx"] = 1
            st.session_state["page"] = "battle"
            st.rerun()

        sel  = st.session_state.get("battle_selected", [])
        prio = st.session_state.get("battle_priority", [])

        recipes = st.session_state["all_recipes"]
        cols = st.columns(2)
        for i, recipe in enumerate(recipes):
            protein  = get_nutrient(recipe, "Protein")
            carbs    = get_nutrient(recipe, "Carbohydrates")
            fat      = get_nutrient(recipe, "Fat")
            calories = get_nutrient(recipe, "Calories")
            with cols[i % 2]:
                with st.container(border=True):
                    if recipe.get("image"):
                        st.image(recipe["image"], use_container_width=True)
                    st.markdown(f'<div class="recipe-title">{recipe["title"]}</div>', unsafe_allow_html=True)
                    st.markdown(f"**{recipe.get('readyInMinutes', '?')} min** &nbsp;·&nbsp; **{recipe.get('servings', '?')} servings**")
                    st.markdown(
                        f'<span class="macro-pill">{calories} kcal</span>'
                        f'<span class="macro-pill">{protein}g prot</span>'
                        f'<span class="macro-pill">{carbs}g carbs</span>'
                        f'<span class="macro-pill">{fat}g fat</span>',
                        unsafe_allow_html=True,
                    )
                    score, ing_score, prio_score = calculate_waste_score(recipe, sel, prio)

                    with st.expander("View details"):
                        st.markdown(
                            '<div style="font-size:11px;font-weight:700;color:#22577A;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:4px;">Nutritional breakdown</div>',
                            unsafe_allow_html=True,
                        )

                        col_donut, col_bar =st.columns(2)

                        with col_donut:
                            st.plotly_chart(make_donut(recipe), use_container_width=True, key=f"result_donut_{i}", config={"displayModeBar": False})

                        with col_bar:
                            st.plotly_chart(make_calorie_bar(recipe), use_container_width=True, key=f"result_bar_{i}", config={"displayModeBar": False})

                        taste = get_taste_profile(recipe.get("id"),api_key)
                        if taste:
                            render_taste_bars(taste)

                        n_stars = max(1, min(5, round(score * 4) + 1))
                        ing_pct = round(ing_score * 100) if ing_score is not None else None
                        prio_pct = round(prio_score * 100) if prio_score is not None else None

                        card_ing = (
                             f'<div style="flex:1;background:white;border:1px solid #E7E7E2;border-radius:10px;padding:12px 14px;text-align:center;">'
                             f'<div style="font-size:26px;font-weight:800;color:#38A3A5;">{ing_pct}%</div>'
                             f'<div style="font-size:11px;color:#888;margin-top:2px;">Ingredients used</div>'
                             f'</div>'
                        ) if ing_pct is not None else ""

                        card_prio = (
                             f'<div style="flex:1;background:white;border:1px solid #E7E7E2;border-radius:10px;padding:12px 14px;text-align:center;">'
                             f'<div style="font-size:26px;font-weight:800;color:#57CC99;">{prio_pct}%</div>'
                             f'<div style="font-size:11px;color:#888;margin-top:2px;">Expiring items used</div>'
                             f'</div>'
                        ) if prio_pct is not None else ""

                        st.markdown(
                            f'<div style="background:#FAFAFA;border:1px solid #E7E7E2;border-radius:12px;padding:14px 16px;margin-top:12px;">'
                            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">'
                            f'<div style="font-size:11px;font-weight:700;color:#22577A;letter-spacing:0.05em;text-transform:uppercase;">Waste score</div>'
                            f'<div style="font-size:15px;color:#F59E0B;">{"★" * n_stars}<span style="color:#D1D5DB;">{"☆" * (5 - n_stars)}</span></div>'
                            f'</div>'
                            f'<div style="display:flex;gap:10px;">{card_ing}{card_prio}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                        used_ings = recipe.get("usedIngredients", [])
                        missed_ings = recipe.get("missedIngredients", [])

                        if used_ings or missed_ings:
                            rows = ""

                            for ing in used_ings:
                                name = ing.get("original", ing.get("name", ""))
                                rows += (
                                    f'<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #F3F3F3;">'
                                    f'<div style="width:8px;height:8px;border-radius:50%;background:#38A3A5;flex-shrink:0;"></div>'
                                    f'<div style="font-size:13px;color:#333;">{name}</div>'
                                    f'</div>'
                                )

                            for ing in missed_ings:
                                name = ing.get("original", ing.get("name", ""))
                                rows += (
                                    f'<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #F3F3F3;">'
                                    f'<div style="width:8px;height:8px;border-radius:50%;background:#E7E7E2;flex-shrink:0;"></div>'
                                    f'<div style="font-size:13px;color:#999;">{name}</div>'
                                    f'</div>'
                                )

                            st.markdown(
                                f'<div style="background:#FAFAFA;border:1px solid #E7E7E2;border-radius:12px;padding:14px 16px;margin-top:12px;">'
                                f'<div style="font-size:11px;font-weight:700;color:#22577A;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:8px;">Ingredients'
                                f'<span style="font-weight:400;color:#38A3A5;margin-left:8px;">· {len(used_ings)} on hand</span>'
                                f'<span style="font-weight:400;color:#aaa;margin-left:8px;">· {len(missed_ings)} to buy</span>'
                                f'</div>{rows}</div>',
                                unsafe_allow_html=True,
                        )

                    if st.button("Pick this one", key=f"pick_{i}", use_container_width=True, type="primary"):
                        st.session_state["battle_champion"] = recipe
                        st.session_state["battle_done"]     = True
                        st.session_state["battle_saved"]    = False
                        st.session_state["page"]            = "battle"
                        st.rerun()

    # ── PAGE BATTLE ──
    else:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← Back to quiz", type="primary"):
            st.session_state["page"]      = "quiz"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("battle_done"):
            champion    = st.session_state["battle_champion"]
            sel         = st.session_state["battle_selected"]
            prio        = st.session_state["battle_priority"]
            score, _, _ = calculate_waste_score(champion, sel, prio)
            n_stars     = max(1, min(5, round(score * 4) + 1))

            if not st.session_state.get("battle_saved"):
                embed_and_save_recipe(user_id, champion)  # ML: REPLACED save_recipe — ALSO COMPUTES + STORES THE SENTENCE EMBEDDING
                st.session_state["battle_saved"] = True

            st.markdown(
                f'<div style="text-align:center; margin-bottom:20px;">'
                f'<div style="font-size:22px; font-weight:700; letter-spacing:2px; color:#38A3A5; text-transform:uppercase; margin-bottom:10px;">Your winning recipe</div>'
                f'<div style="font-size:32px; font-weight:900; color:#22577A; margin-bottom:8px;">{champion["title"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            protein  = get_nutrient(champion, "Protein")
            carbs    = get_nutrient(champion, "Carbohydrates")
            fat      = get_nutrient(champion, "Fat")
            calories = get_nutrient(champion, "Calories")
            if champion.get("image"):
                col_l, col_img, col_r = st.columns([1, 2, 1])
                with col_img:
                    st.image(champion["image"], use_container_width=True)
            st.markdown(
                f'<div style="text-align:center; margin: 10px 0;">'
                f'<span class="macro-pill"> {calories} kcal</span>'
                f'<span class="macro-pill"> {protein}g prot</span>'
                f'<span class="macro-pill"> {carbs}g carbs</span>'
                f'<span class="macro-pill"> {fat}g fat</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div style="text-align:center; color:#888; font-size:13px; margin-bottom:10px;">Saved to your selected recipes!</div>', unsafe_allow_html=True)  # ML: RENAMED "winning" → "selected" TO MATCH SIDEBAR HEADER

            st.markdown("---")
            st.markdown("#### Instructions")
            instructions = champion.get("analyzedInstructions", [])
            if instructions and instructions[0].get("steps"):
                for step in instructions[0]["steps"]:
                    st.markdown(f"**{step['number']}.** {step['step']}")
            else:
                st.info("No instructions available.")

            st.markdown("")
            if st.button("Find new recipes", use_container_width=True, type="primary"):
                for key in ["battle_champion", "battle_challenger_idx",
                            "battle_recipes", "battle_done", "battle_selected",
                            "battle_priority", "battle_saved"]:
                    st.session_state.pop(key, None)
                st.session_state["page"]      = "quiz"
                st.rerun()

        else:
            battle_recipes = st.session_state["battle_recipes"]
            champion       = st.session_state["battle_champion"]
            challenger_idx = st.session_state["battle_challenger_idx"]
            sel            = st.session_state["battle_selected"]
            prio           = st.session_state["battle_priority"]
            challenger     = battle_recipes[challenger_idx]
            total_battles  = len(battle_recipes) - 1
            progress_pct   = int((challenger_idx - 1) / total_battles * 100) if total_battles > 1 else 0

            st.markdown('<div class="battle-title">May the best recipe win</div>', unsafe_allow_html=True)
            st.markdown('<div class="battle-subtitle">Open the details, then pick your favourite!</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="progress-bar-bg"><div class="progress-bar-fill" style="width:{progress_pct}%"></div></div>',
                unsafe_allow_html=True,
            )

            left_col, vs_col, right_col = st.columns([5, 1, 5])
            with left_col:
                chose_champion = render_battle_card(champion, f"champ_{challenger_idx}", sel, prio, api_key)
            with vs_col:
                st.markdown('<div class="vs-badge">VS</div>', unsafe_allow_html=True)
            with right_col:
                chose_challenger = render_battle_card(challenger, f"chal_{challenger_idx}", sel, prio, api_key)

            if chose_champion or chose_challenger:
                winner   = champion if chose_champion else challenger
                next_idx = challenger_idx + 1
                st.session_state["battle_champion"] = winner
                if next_idx >= len(battle_recipes):
                    st.session_state["battle_done"] = True
                else:
                    st.session_state["battle_challenger_idx"] = next_idx
                st.rerun()
