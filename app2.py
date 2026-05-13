
import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import requests
import os
import plotly.graph_objects as go
from dotenv import load_dotenv

# ─────────────────────────────────────────
#  DATABASE - sql tables linked by ID
# ─────────────────────────────────────────
DB_NAME = "app.db"

def get_conn():
    return sqlite3.connect(DB_NAME)


def get_nutrient(recipe, name):
    for n in recipe.get("nutrition", {}).get("nutrients", []):
        if n["name"].lower() == name.lower():
            return round(n["amount"])
    return 0


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
    c.execute("""
    CREATE TABLE IF NOT EXISTS saved_recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        recipe_id INTEGER,
        recipe_title TEXT,
        recipe_image TEXT,
        calories INTEGER,
        protein INTEGER,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""") # stock winning recipe --> linked to ID (for ML)
    conn.commit()
    # Migration: add instructions column if it doesn't exist yet
    try:
        c.execute("ALTER TABLE saved_recipes ADD COLUMN instructions TEXT")
        conn.commit()
    except Exception:
        pass
    conn.close()

init_db()

# put the winning recipe in table
def save_recipe(user_id, recipe):
    conn = get_conn()
    c = conn.cursor()
    instructions = recipe.get("analyzedInstructions", [])
    if instructions and instructions[0].get("steps"):
        steps_text = "\n".join(
            f"{s['number']}. {s['step']}" for s in instructions[0]["steps"]
        )
    else:
        steps_text = ""
    c.execute(
        "INSERT INTO saved_recipes (user_id, recipe_id, recipe_title, recipe_image, calories, protein, instructions) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, recipe.get("id"), recipe.get("title"), recipe.get("image"),
         get_nutrient(recipe, "Calories"), get_nutrient(recipe, "Protein"), steps_text),
    )
    conn.commit()
    conn.close()

# saved recipes put in sidebar 
def get_saved_recipes(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT recipe_title, recipe_image, calories, protein, saved_at, instructions FROM saved_recipes WHERE user_id=? ORDER BY saved_at DESC",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows

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

.view-btn button {
    background-color: transparent !important;
    color: #22577A !important;
    border: 1px solid #22577A !important;
    height: 30px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 0 10px !important;
    margin-top: 2px !important;
}
.view-btn button:hover {
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
#  USER PREFERENCES 
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


def search_recipes(ingredients, nutrition_params, preferences, max_time, api_key):
    url = "https://api.spoonacular.com/recipes/complexSearch"

    intolerances = [ALLERGY_MAP.get(a.lower(), a) for a in preferences["allergies"]]
    diet = DIET_MAP.get(preferences.get("diet", "None"), "")

    base_params = {
        "apiKey":                api_key,
        "maxReadyTime":          max_time,
        "number":                6,
        "addRecipeNutrition":    True,
        "addRecipeInstructions": True,
        "fillIngredients":       True,
        **nutrition_params,
    }
    if ingredients:
        base_params["includeIngredients"] = ",".join(ingredients)
        base_params["sort"] = "min-missing-ingredients"
        base_params["sortDirection"] = "asc"
    if diet:
        base_params["diet"] = diet
    if intolerances:
        base_params["intolerances"] = ",".join(intolerances)

    try:
        resp = requests.get(url, params=base_params, timeout=12)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 401:
            st.error("Invalid API key.")
        elif resp.status_code == 402:
            st.error("API quota exceeded for today.")
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




# ─────────────────────────────────────────
# NUTRITION / CHART
# ─────────────────────────────────────────
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
        textinfo="percent",
        textfont=dict(size=11),
        hovertemplate="%{label}: %{customdata}g (%{percent})<extra></extra>",
        customdata=[protein, carbs, fat],
    ))
    fig.update_layout(
        annotations=[dict(
            text=f"<b>{calories}</b><br>kcal",
            x=0.5, y=0.5, font_size=16, showarrow=False
        )],
        showlegend=True,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.08),
        margin=dict(t=10, b=20, l=10, r=10),
        height=190,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig



# ─────────────────────────────────────────
#  BATTLE CARD
# ─────────────────────────────────────────
def get_taste_profile(recipe_id, api_key):
    cache_key = f"taste_{recipe_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        resp = requests.get(
            f"https://api.spoonacular.com/recipes/{recipe_id}/tasteWidget.json",
            params={"apiKey": api_key},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        st.session_state[cache_key] = data
        return data
    except Exception:
        return None


def make_calorie_bar(recipe):
    protein  = get_nutrient(recipe, "Protein")
    carbs    = get_nutrient(recipe, "Carbohydrates")
    fat      = get_nutrient(recipe, "Fat")
    fig = go.Figure(go.Bar(
        x=["Protein", "Carbs", "Fat"],
        y=[protein * 4, carbs * 4, fat * 9],
        marker_color=["#38A3A5", "#22577A", "#57CC99"],
        text=[f"{protein*4}", f"{carbs*4}", f"{fat*9}"],
        textposition="outside",
        textfont=dict(size=11, color="#555"),
    ))
    fig.update_layout(
        title=dict(text="kcal per macro", font=dict(size=12, color="#888"), x=0.5),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        xaxis=dict(tickfont=dict(size=12)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        height=190,
        margin=dict(t=30, b=10, l=10, r=10),
    )
    return fig


def render_taste_bars(taste):
    attrs = [
        ("Savoriness", taste.get("savoriness", 0), "#22577A"),
        ("Saltiness",  taste.get("saltiness",  0), "#2D7EA8"),
        ("Fattiness",  taste.get("fattiness",  0), "#38A3A5"),
        ("Sourness",   taste.get("sourness",   0), "#4DB6AC"),
        ("Sweetness",  taste.get("sweetness",  0), "#57CC99"),
        ("Bitterness", taste.get("bitterness", 0), "#3A9BBF"),
        ("Spiciness",  taste.get("spiciness",  0), "#80ED99"),
    ]
    rows = ""
    for label, val, color in attrs:
        pct = round(min(val, 100))
        rows += (
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:7px;">'
            f'<div style="width:90px;font-size:12px;color:#555;">{label}</div>'
            f'<div style="flex:1;background:#EEF5FB;border-radius:6px;height:7px;">'
            f'<div style="width:{pct}%;background:{color};border-radius:6px;height:7px;"></div></div>'
            f'<div style="width:38px;text-align:right;font-size:11px;color:#38A3A5;font-weight:600;">{pct}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:#FAFAFA;border:1px solid #E7E7E2;border-radius:12px;padding:14px 16px;margin-top:12px;">'
        f'<div style="font-size:11px;font-weight:700;color:#22577A;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:10px;">Taste profile</div>'
        f'{rows}</div>',
        unsafe_allow_html=True,
    )


def render_battle_card(recipe, key_prefix, selected_ingredients, priority_ingredients, api_key=""):
    protein  = get_nutrient(recipe, "Protein")
    carbs    = get_nutrient(recipe, "Carbohydrates")
    fat      = get_nutrient(recipe, "Fat")
    calories = get_nutrient(recipe, "Calories")
    score, ing_score, prio_score = calculate_waste_score(recipe, selected_ingredients, priority_ingredients)

    with st.container(border=True):
        if recipe.get("image"):
            st.image(recipe["image"], use_container_width=True)
        st.markdown(f'<div class="recipe-title">{recipe["title"]}</div>', unsafe_allow_html=True)
        st.markdown(f"⏱️ **{recipe.get('readyInMinutes', '?')} min** &nbsp;·&nbsp; 🍽️ **{recipe.get('servings', '?')} servings**")
        st.markdown(
            f'<span class="macro-pill"> {calories} kcal</span>'
            f'<span class="macro-pill"> {protein}g prot</span>'
            f'<span class="macro-pill"> {carbs}g carbs</span>'
            f'<span class="macro-pill"> {fat}g fat</span>',
            unsafe_allow_html=True,
        )
        with st.expander("View details"):
            st.markdown('<div style="font-size:11px;font-weight:700;color:#22577A;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:4px;">Nutritional breakdown</div>', unsafe_allow_html=True)
            col_donut, col_bar = st.columns(2)
            with col_donut:
                st.plotly_chart(make_donut(recipe), use_container_width=True, key=f"donut_{key_prefix}", config={"displayModeBar": False})
            with col_bar:
                st.plotly_chart(make_calorie_bar(recipe), use_container_width=True, key=f"bar_{key_prefix}", config={"displayModeBar": False})
            taste = get_taste_profile(recipe.get("id"), api_key)
            if taste:
                render_taste_bars(taste)

            # Waste score breakdown
            n_stars = max(1, min(5, round(score * 4) + 1))
            ing_pct  = round(ing_score  * 100) if ing_score  is not None else None
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

            used_ings   = recipe.get("usedIngredients", [])
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

        chosen = st.button("Pick this recipe", key=f"choose_{key_prefix}", use_container_width=True)
    return chosen


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
            st.markdown('<div style="text-align:center; font-size:36px; font-weight:800; color:#22577A;"> Bon app! 🥗</div>', unsafe_allow_html=True)
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

    load_dotenv()
    api_key = os.environ.get("SPOONACULAR_API_KEY", "")

    # Sidebar — user profile
    with st.sidebar:
        st.markdown("### Your profile")
        if prefs["allergies"]:
            st.markdown(f"**Allergies:** {', '.join(prefs['allergies'])}")
        if prefs["diet"] != "None":
            st.markdown(f"**Diet:** {prefs['diet']}")
        if prefs["religion"] != "None":
            st.markdown(f"**Restriction:** {prefs['religion']}")
        st.markdown("---")
        st.markdown("### 🏆 My winning recipes")
        saved = get_saved_recipes(user_id)
        if saved:
            for i, (title, image, cal, prot, saved_at, instructions) in enumerate(saved):
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
                st.markdown('<div class="view-btn">', unsafe_allow_html=True)
                if st.button("View recipe", key=f"saved_{i}"):
                    st.session_state["detail_recipe"] = {
                        "title": title, "image": image, "cal": cal,
                        "prot": prot, "instructions": instructions
                    }
                    st.session_state["_prev_page"] = st.session_state.get("page", "quiz")
                    st.session_state["page"] = "detail"
                    st.session_state["do_scroll"] = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.caption("No saved recipes yet.")
        st.markdown("---")
        if st.button("Logout"):
            for key in ["logged_in_user", "preferences", "recipes", "search", "page",
                        "battle_champion", "battle_challenger_idx", "battle_recipes",
                        "battle_done", "battle_selected", "battle_priority", "battle_saved",
                        "detail_recipe"]:
                st.session_state.pop(key, None)
            st.rerun()

    # Scroll to top on navigation
    if st.session_state.pop("do_scroll", False):
        components.html("""
<script>
    function scrollUp() {
        const selectors = [
            'section.main',
            '[data-testid="stAppViewContainer"]',
            '[data-testid="stAppViewBlockContainer"]',
            '.main',
            'html',
            'body'
        ];
        selectors.forEach(sel => {
            const el = window.parent.document.querySelector(sel);
            if (el) { el.scrollTop = 0; el.scrollTo(0, 0); }
        });
        window.parent.scrollTo(0, 0);
    }
    scrollUp();
    setTimeout(scrollUp, 100);
    setTimeout(scrollUp, 300);
</script>
""", height=1)

    page = st.session_state.get("page", "quiz")

    # ── PAGE DETAIL ──
    if page == "detail":
        recipe = st.session_state.get("detail_recipe", {})
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← Back"):
            st.session_state["page"] = st.session_state.get("_prev_page", "quiz")
            st.session_state["do_scroll"] = True
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

        st.markdown('<div class="app-title">Bon app! 🥗</div>', unsafe_allow_html=True)
        st.markdown('<div class="app-subtitle">Recipes crafted just for you</div>', unsafe_allow_html=True)

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
            manual_ingredients = st.text_input("Other ingredients", placeholder="e.g. tofu, lentils, broccoli")
            manual_ingredients_list = [i.strip().lower() for i in manual_ingredients.split(",") if i.strip()]
            selected_ingredients = list(set(selected_ingredients + manual_ingredients_list))

        with st.container(border=True):
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                        '<span class="section-num">2</span>'
                        '<span style="font-size:17px;font-weight:600;color:#22577A;">Expiring soon</span></div>',
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

        if st.button("Find my recipes ✨", use_container_width=True):
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
                def combined_score(r):
                    waste = calculate_waste_score(r, selected_ingredients, priority_ingredients)[0]
                    servings = r.get("servings", persons)
                    # Proximity score : 1.0 if exact, decrease with the gap
                    proximity = max(0, 1 - abs(servings - persons) / max(persons, 1))
                    return 0.7 * waste + 0.3 * proximity #calculation of priorities 

                recipes.sort(key=combined_score, reverse=True)
                st.session_state["battle_recipes"]        = recipes[:3]
                st.session_state["battle_champion"]       = recipes[0]
                st.session_state["battle_challenger_idx"] = 1
                st.session_state["battle_done"]           = False
                st.session_state["battle_selected"]       = selected_ingredients
                st.session_state["battle_priority"]       = priority_ingredients
                st.session_state["page"]      = "battle"
                st.session_state["do_scroll"] = True
                st.rerun()
            else:
                st.warning("No recipes found. Try relaxing some constraints.")

    # ── PAGE BATAILLE ──
    else:  # page == "battle"
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← Back to quiz"):
            st.session_state["page"]      = "quiz"
            st.session_state["do_scroll"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("battle_done"): 
            champion    = st.session_state["battle_champion"]
            sel         = st.session_state["battle_selected"]
            prio        = st.session_state["battle_priority"]
            score, _, _ = calculate_waste_score(champion, sel, prio)
            n_stars     = max(1, min(5, round(score * 4) + 1))

            # Auto-save once when the winner screen first appears
            if not st.session_state.get("battle_saved"):
                save_recipe(user_id, champion)
                st.session_state["battle_saved"] = True

            st.markdown(
                f'<div style="text-align:center; margin-bottom:20px;">'
                f'<div style="font-size:40px; margin-bottom:6px;">🏆</div>'
                f'<div style="font-size:22px; font-weight:700; letter-spacing:2px; color:#38A3A5; text-transform:uppercase; margin-bottom:10px;">Your winning recipe</div>'
                f'<div style="font-size:32px; font-weight:900; color:#22577A; margin-bottom:8px;">{champion["title"]}</div>'
                f'<div style="font-size:22px; color:#F4A261;">{"★" * n_stars}{"☆" * (5 - n_stars)}</div>'
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
            st.markdown('<div style="text-align:center; color:#888; font-size:13px; margin-bottom:10px;">Saved to your winning recipes!</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### Instructions")
            instructions = champion.get("analyzedInstructions", [])
            if instructions and instructions[0].get("steps"):
                for step in instructions[0]["steps"]:
                    st.markdown(f"**{step['number']}.** {step['step']}")
            else:
                st.info("No instructions available.")

            st.markdown("")
            if st.button("Find new recipes", use_container_width=True):
                for key in ["battle_champion", "battle_challenger_idx",
                            "battle_recipes", "battle_done", "battle_selected",
                            "battle_priority", "battle_saved"]:
                    st.session_state.pop(key, None)
                st.session_state["page"]      = "quiz"
                st.session_state["do_scroll"] = True
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
                st.session_state["do_scroll"] = True
                if next_idx >= len(battle_recipes):
                    st.session_state["battle_done"] = True
                else:
                    st.session_state["battle_challenger_idx"] = next_idx
                st.rerun()
