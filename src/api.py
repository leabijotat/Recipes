import streamlit as st
import requests
import plotly.graph_objects as go

from src.db import get_nutrient

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
        "number":                10,
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


def get_recipe_ingredient_names(recipe):
    names = []
    for ing in recipe.get("nutrition", {}).get("ingredients", []):
        names.append(ing.get("name", "").lower())
    return names


def ingredient_in_recipe(ingredient, ingredient_names, recipe_title):
    ing_lower = ingredient.lower()
    for name in ingredient_names:
        if ing_lower == name or ing_lower in name.split():
            return True
    if ing_lower in recipe_title.lower().split():
        return True
    return False


def calculate_waste_score(recipe, selected_ingredients, priority_ingredients):
    recipe_title     = recipe.get("title", "")
    ingredient_names = get_recipe_ingredient_names(recipe)

    has_selected = len(selected_ingredients) > 0
    has_priority = len(priority_ingredients) > 0

    if has_selected:
        matched = sum(
            1 for ing in selected_ingredients
            if ingredient_in_recipe(ing, ingredient_names, recipe_title)
        )
        ingredient_score = matched / len(selected_ingredients)
    else:
        ingredient_score = None

    if has_priority:
        matched_priority = sum(
            1 for ing in priority_ingredients
            if ingredient_in_recipe(ing, ingredient_names, recipe_title)
        )
        priority_score = matched_priority / len(priority_ingredients)
    else:
        priority_score = None

    if ingredient_score is not None and priority_score is not None:
        final = 0.6 * ingredient_score + 0.4 * priority_score
    elif ingredient_score is not None:
        final = ingredient_score
    elif priority_score is not None:
        final = priority_score
    else:
        final = 0.5

    return final, ingredient_score, priority_score


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
        annotations=[dict(text=f"<b>{calories}</b><br>kcal", x=0.5, y=0.5, font_size=16, showarrow=False)],
        showlegend=True,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.08),
        margin=dict(t=10, b=20, l=10, r=10),
        height=190,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def make_calorie_bar(recipe):
    protein = get_nutrient(recipe, "Protein")
    carbs   = get_nutrient(recipe, "Carbohydrates")
    fat     = get_nutrient(recipe, "Fat")
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
        st.markdown(f"**{recipe.get('readyInMinutes', '?')} min** &nbsp;·&nbsp; **{recipe.get('servings', '?')} servings**")
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

            n_stars  = max(1, min(5, round(score * 4) + 1))
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

        chosen = st.button("Pick this recipe", key=f"choose_{key_prefix}", use_container_width=True, type="primary")
    return chosen
