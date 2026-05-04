
import streamlit as st
import sqlite3
import requests
import os
import plotly.graph_objects as go

# ─────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────
DB_NAME = "app.db"

def get_conn():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        allergies TEXT,
        diet TEXT,
        religion TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────

GOAL_PARAMS = {
    "Balanced":     {"maxCalories": 800},
    "Light":        {"maxCalories": 500, "maxFat": 15},
    "Energizing":   {"minCarbs": 40},
    "High Protein": {"minProtein": 30},
}

GOAL_DESCRIPTIONS = {
    "Balanced":     "≤ 800 kcal",
    "Light":        "≤ 500 kcal · ≤ 15g fat",
    "Energizing":   "40g+ carbs",
    "High Protein": "30g+ protein",
}

ALLERGY_MAP = {
    "peanuts": "peanut",
    "milk":    "dairy",
    "eggs":    "egg",
    "gluten":  "gluten",
    "soy":     "soy",
    "seafood": "seafood",
}

DIET_MAP = {
    "Vegetarian": "vegetarian",
    "Vegan":      "vegan",
    "None":       "",
}

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
    background: #F0F9F4;
    border: 1px solid #C8E6D8;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 12px;
    color: #208b3a;
    font-weight: 600;
    margin-right: 4px;
}

.waste-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: 600;
    color: #92400E;
    margin-top: 6px;
}

.waste-detail {
    font-size: 11px;
    color: #999;
    margin-top: 2px;
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  HELPERS — DB
# ─────────────────────────────────────────
def get_user_preferences(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT allergies, diet, religion FROM preferences WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        allergies_str, diet, religion = row
        allergies = [a.strip() for a in allergies_str.split(",") if a.strip()] if allergies_str else []
        return {"allergies": allergies, "diet": diet, "religion": religion}
    return {"allergies": [], "diet": "None", "religion": "None"}


# ─────────────────────────────────────────
#  API
# ─────────────────────────────────────────
def build_nutrition_params(goal, manual_override, manual_cal, manual_prot, manual_fat, manual_carbs):
    if manual_override:
        params = {}
        if manual_cal   > 0: params["maxCalories"] = manual_cal
        if manual_prot  > 0: params["minProtein"]  = manual_prot
        if manual_fat   > 0: params["maxFat"]      = manual_fat
        if manual_carbs > 0: params["minCarbs"]    = manual_carbs
        return params
    return GOAL_PARAMS[goal]


def search_recipes(ingredients, nutrition_params, preferences, max_time, persons, api_key):
    url = "https://api.spoonacular.com/recipes/complexSearch"

    intolerances = [ALLERGY_MAP.get(a.lower(), a) for a in preferences["allergies"]]
    diet = DIET_MAP.get(preferences.get("diet", "None"), "")

    params = {
        "apiKey":                api_key,
        "maxReadyTime":          max_time,
        "number":                6,
        "addRecipeNutrition":    True,
        "addRecipeInstructions": True,
        "fillIngredients":       True,
        **nutrition_params,
    }
    if ingredients:
        params["includeIngredients"] = ",".join(ingredients)
        params["sort"] = "min-missing-ingredients"
        params["sortDirection"] = "asc"
    if diet:
        params["diet"] = diet
    if intolerances:
        params["intolerances"] = ",".join(intolerances)

    try:
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 401:
            st.error("❌ Invalid API key.")
        elif resp.status_code == 402:
            st.error("❌ API quota exceeded for today.")
        else:
            st.error(f"API error {resp.status_code}: {e}")
        return []
    except Exception as e:
        st.error(f"Connection error: {e}")
        return []


# ─────────────────────────────────────────
#  WASTE SCORE
# ─────────────────────────────────────────
def get_recipe_ingredient_names(recipe):
    names = []
    for ing in recipe.get("nutrition", {}).get("ingredients", []):
        names.append(ing.get("name", "").lower())
    return names


def ingredient_in_recipe(ingredient, ingredient_names, recipe_title):
    ing_lower = ingredient.lower()
    for name in ingredient_names:
        # Exact match or word in the name
        if ing_lower == name or ing_lower in name.split():
            return True
    # Check in title word by word
    if ing_lower in recipe_title.lower().split():
        return True
    return False


def calculate_waste_score(recipe, selected_ingredients, priority_ingredients):
    """
    Returns a score between 0 and 1.
    Composed of:
      - ingredient_match (60%): % of selected ingredients used by the recipe
      - priority_match   (40%): % of expiring-soon ingredients used by the recipe
    If only one source of info is available, it counts for 100%.
    """
    recipe_title    = recipe.get("title", "")
    ingredient_names = get_recipe_ingredient_names(recipe)

    has_selected = len(selected_ingredients) > 0
    has_priority = len(priority_ingredients) > 0

    # ── Ingredient match ──
    if has_selected:
        matched = sum(
            1 for ing in selected_ingredients
            if ingredient_in_recipe(ing, ingredient_names, recipe_title)
        )
        ingredient_score = matched / len(selected_ingredients)
    else:
        ingredient_score = None

    # ── Priority match ──
    if has_priority:
        matched_priority = sum(
            1 for ing in priority_ingredients
            if ingredient_in_recipe(ing, ingredient_names, recipe_title)
        )
        priority_score = matched_priority / len(priority_ingredients)
    else:
        priority_score = None

    # ── Combine ──
    if ingredient_score is not None and priority_score is not None:
        final = 0.6 * ingredient_score + 0.4 * priority_score
    elif ingredient_score is not None:
        final = ingredient_score
    elif priority_score is not None:
        final = priority_score
    else:
        final = 0.5  # No info → neutral

    return final, ingredient_score, priority_score


def render_waste_stars(score, ingredient_score, priority_score, selected_ingredients, priority_ingredients):
    """Render a star badge + detail line for the waste indicator."""
    # 1–5 stars
    n_stars = max(1, min(5, round(score * 4) + 1))
    stars_filled = "★" * n_stars
    stars_empty  = "☆" * (5 - n_stars)

    # Detail line
    parts = []
    if selected_ingredients and ingredient_score is not None:
        pct = round(ingredient_score * 100)
        parts.append(f"{pct}% ingredients used")
    if priority_ingredients and priority_score is not None:
        pct = round(priority_score * 100)
        parts.append(f"{pct}% expiring items used")
    detail = " · ".join(parts) if parts else "No ingredients selected"

    badge = (
        f'<div class="waste-badge">'
        f'<span style="color:#F59E0B;">{stars_filled}</span>'
        f'<span style="color:#D1D5DB;">{stars_empty}</span>'
        f'&nbsp;Waste score'
        f'</div>'
        f'<div class="waste-detail">{detail}</div>'
    )
    return badge


# ─────────────────────────────────────────
# NUTRITION / CHART
# ─────────────────────────────────────────
def get_nutrient(recipe, name):
    for n in recipe.get("nutrition", {}).get("nutrients", []):
        if n["name"].lower() == name.lower():
            return round(n["amount"])
    return 0


def make_donut(recipe):
    protein  = get_nutrient(recipe, "Protein")
    carbs    = get_nutrient(recipe, "Carbohydrates")
    fat      = get_nutrient(recipe, "Fat")
    calories = get_nutrient(recipe, "Calories")

    fig = go.Figure(go.Pie(
        labels=["Protein", "Carbs", "Fat"],
        values=[protein * 4, carbs * 4, fat * 9],
        hole=0.58,
        marker_colors=["#38A3A5", "#22577A", "#57CC99"],
        textinfo="label+percent",
        hovertemplate="%{label}: %{customdata}g<extra></extra>",
        customdata=[protein, carbs, fat],
    ))
    fig.update_layout(
        annotations=[dict(
            text=f"<b>{calories}</b><br>kcal",
            x=0.5, y=0.5, font_size=16, showarrow=False
        )],
        showlegend=True,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.08),
        margin=dict(t=10, b=30, l=10, r=10),
        height=240,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────
#  RECIPE CARD
# ─────────────────────────────────────────
def render_recipe_card(recipe, idx, selected_ingredients, priority_ingredients):
    protein  = get_nutrient(recipe, "Protein")
    carbs    = get_nutrient(recipe, "Carbohydrates")
    fat      = get_nutrient(recipe, "Fat")
    calories = get_nutrient(recipe, "Calories")

    score, ing_score, prio_score = calculate_waste_score(
        recipe, selected_ingredients, priority_ingredients
    )

    with st.container(border=True):
        col_img, col_info = st.columns([1, 2])

        with col_img:
            if recipe.get("image"):
                st.image(recipe["image"], use_container_width=True)

        with col_info:
            st.markdown(f'<div class="recipe-title">{recipe["title"]}</div>', unsafe_allow_html=True)
            st.markdown(
                f"⏱️ **{recipe.get('readyInMinutes', '?')} min** &nbsp;·&nbsp; "
                f"🍽️ **{recipe.get('servings', '?')} servings**"
            )
            st.markdown(
                f'<span class="macro-pill"> {calories} kcal</span>'
                f'<span class="macro-pill"> {protein}g prot</span>'
                f'<span class="macro-pill"> {carbs}g carbs</span>'
                f'<span class="macro-pill"> {fat}g fat</span>',
                unsafe_allow_html=True
            )
            # Waste badge
            badge_html = render_waste_stars(score, ing_score, prio_score, selected_ingredients, priority_ingredients)
            st.markdown(badge_html, unsafe_allow_html=True)

        with st.expander("✨ View full recipe"):
            left, right = st.columns([1, 1])

            with left:
                st.markdown("#### Nutritional breakdown")
                st.plotly_chart(make_donut(recipe), use_container_width=True, key=f"donut_{idx}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Protein",  f"{protein}g")
                m2.metric("Carbs",    f"{carbs}g")
                m3.metric("Fat",      f"{fat}g")

            with right:
                st.markdown("#### Instructions")
                instructions = recipe.get("analyzedInstructions", [])
                if instructions and instructions[0].get("steps"):
                    for step in instructions[0]["steps"]:
                        st.markdown(f"**{step['number']}.** {step['step']}")
                else:
                    st.info("No instructions available for this recipe.")

                used_ings = recipe.get("usedIngredients", [])
                missed_ings = recipe.get("missedIngredients", [])
                if used_ings or missed_ings:
                    st.markdown("#### Ingredients")
                    for ing in used_ings:
                        st.markdown(f"✅ {ing.get('original', ing.get('name', ''))}")
                    for ing in missed_ings:
                        st.markdown(f"🛒 {ing.get('original', ing.get('name', ''))}")


# ─────────────────────────────────────────
#  SESSION INIT
# ─────────────────────────────────────────
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

# ─────────────────────────────────────────
#  LOGIN / SIGNUP
# ─────────────────────────────────────────
if st.session_state["logged_in_user"] is None:

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown('<div style="text-align:center; font-size:36px; font-weight:800; color:#22577A;"> Bonn app! 🥗</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center; color:#57CC99; font-size:15px; margin-bottom:20px;">Recipes crafted just for you</div>', unsafe_allow_html=True)

            login_tab, signup_tab = st.tabs(["Login", "Create account"])

            with login_tab:
                st.markdown("### Welcome back!")
                login_email    = st.text_input("Email",    key="login_email")
                login_password = st.text_input("Password", type="password", key="login_password")

                if st.button("Login", use_container_width=True):
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
                all_allergies  = list(set(selected_allergies + manual_allergies_list))
                allergies_for_db = ",".join(all_allergies)

                diet_preference       = st.selectbox("Diet preference",       ["None", "Vegetarian", "Vegan"])
                religious_restriction = st.selectbox("Religious restriction",  ["None", "Halal", "Kosher"])

                if st.button("Create account", use_container_width=True):
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
                        except sqlite3.IntegrityError:
                            st.error("This email already exists.")

# ─────────────────────────────────────────
#  MAIN APP (logged in)
# ─────────────────────────────────────────
else:
    user_id = st.session_state["logged_in_user"]

    # Load preferences once per session
    if "preferences" not in st.session_state:
        st.session_state["preferences"] = get_user_preferences(user_id)
    prefs = st.session_state["preferences"]

    # API key from secrets
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("SPOONACULAR_API_KEY", "")

    # Sidebar — user profile
    with st.sidebar:
        st.markdown("### 👤 Your profile")
        if prefs["allergies"]:
            st.markdown(f"**Allergies:** {', '.join(prefs['allergies'])}")
        if prefs["diet"] != "None":
            st.markdown(f"**Diet:** {prefs['diet']}")
        if prefs["religion"] != "None":
            st.markdown(f"**Restriction:** {prefs['religion']}")
        st.markdown("---")
        if st.button("Logout"):
            for key in ["logged_in_user", "preferences", "recipes", "search"]:
                st.session_state.pop(key, None)
            st.rerun()

    # Header
    st.markdown('<div class="app-title">Bon app! 🥗</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Recipes crafted just for you</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2])

    with col_left:

        # 1 — Ingredients
        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">1</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Ingredients</span></div>',
                        unsafe_allow_html=True)
            selected_ingredients = st.multiselect(
                "", ["tomato", "spinach", "chickpeas", "zucchini", "onion",
                     "carrot", "potato", "chicken", "rice", "pasta",
                     "egg", "cheese", "milk", "salmon", "avocado"],
                placeholder="Add ingredients..."
            )

        # 2 — Expiring soon
        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">2</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Expiring soon 🕐</span></div>',
                        unsafe_allow_html=True)
            st.caption("Select ingredients that need to be eaten first — recipes using them will be ranked higher.")
            priority_pool = selected_ingredients if selected_ingredients else [
                "tomato", "spinach", "chickpeas", "zucchini", "onion",
                "carrot", "potato", "chicken", "rice", "pasta",
                "egg", "cheese", "milk", "salmon", "avocado"
            ]
            priority_ingredients = st.multiselect(
                "", priority_pool,
                placeholder="e.g. spinach, milk...",
                key="priority"
            )

        # 3 — Goal
        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">3</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Your goal</span></div>',
                        unsafe_allow_html=True)
            goal = st.radio("", ["Balanced", "Light", "Energizing", "High Protein"])
            st.markdown(f'<div class="goal-hint">{GOAL_DESCRIPTIONS[goal]}</div>', unsafe_allow_html=True)

            manual_override = st.toggle("⚙️ Set macros manually")
            manual_cal = manual_prot = manual_fat = manual_carbs = 0
            if manual_override:
                manual_cal   = st.number_input("Max calories (kcal)", min_value=0, max_value=2000, value=600, step=50)
                manual_prot  = st.number_input("Min protein (g)",     min_value=0, max_value=200,  value=20,  step=5)
                manual_fat   = st.number_input("Max fat (g)",         min_value=0, max_value=200,  value=20,  step=5)
                manual_carbs = st.number_input("Min carbs (g)",       min_value=0, max_value=500,  value=0,   step=5)

        # 4 — Prep time
        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">4</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Preparation time</span></div>',
                        unsafe_allow_html=True)
            max_time = st.slider("", min_value=10, max_value=90, value=30, step=5, format="%d min")

        # 5 — Persons
        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">5</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Number of persons</span></div>',
                        unsafe_allow_html=True)
            persons = st.number_input("", min_value=1, max_value=10, value=2)

        if st.button("Find my recipes ✨", use_container_width=True):
            nutrition_params = build_nutrition_params(
                goal, manual_override,
                manual_cal, manual_prot, manual_fat, manual_carbs
            )
            with st.spinner("Finding the perfect recipes for you..."):
                recipes = search_recipes(
                    selected_ingredients, nutrition_params,
                    prefs, max_time, persons, api_key
                )
            # Sort by waste score descending
            if recipes:
                recipes.sort(
                    key=lambda r: calculate_waste_score(r, selected_ingredients, priority_ingredients)[0],
                    reverse=True
                )
            st.session_state["recipes"]              = recipes
            st.session_state["selected_ingredients"] = selected_ingredients
            st.session_state["priority_ingredients"] = priority_ingredients
            st.session_state["search"]               = True

    # ── Right column — results ──
    with col_right:
        if st.session_state.get("search"):
            recipes             = st.session_state.get("recipes", [])
            saved_selected      = st.session_state.get("selected_ingredients", [])
            saved_priority      = st.session_state.get("priority_ingredients", [])

            if recipes:
                st.markdown(
                    '<div style="border-left:3px solid #22577A; padding-left:12px; '
                    'margin-bottom:20px; font-size:18px; font-weight:600; color:#22577A;">'
                    f'{len(recipes)} recipes found · sorted by waste score</div>',
                    unsafe_allow_html=True
                )
                for i, recipe in enumerate(recipes):
                    render_recipe_card(recipe, i, saved_selected, saved_priority)
            else:
                st.warning("No recipes found. Try relaxing some constraints (time, macros, or ingredients).")
        else:
            st.markdown(
                "<p style='color:#aaa; text-align:center; margin-top:120px; font-size:15px;'>"
                "Your recipes will appear here after clicking<br><b>Find my recipes ✨</b></p>",
                unsafe_allow_html=True
            )
