import sqlite3

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
    )""")
    conn.commit()
    try:
        c.execute("ALTER TABLE saved_recipes ADD COLUMN instructions TEXT")
        conn.commit()
    except Exception:
        pass
    # ML: ADD COLUMNS FOR THE ML LAYER — `embedding` STORES THE SENTENCE
    # VECTOR (BLOB) USED FOR PREFERENCE LEARNING, `rating` STORES THE
    # USER'S 1-5 STAR FEEDBACK FROM THE SIDEBAR.
    try:
        c.execute("ALTER TABLE saved_recipes ADD COLUMN embedding BLOB")
        conn.commit()
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE saved_recipes ADD COLUMN rating INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.close()


def save_recipe(user_id, recipe, embedding=None):  # ML: ADDED OPTIONAL `embedding` KWARG SO ml.embed_and_save_recipe CAN PERSIST THE SENTENCE VECTOR
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
        "INSERT INTO saved_recipes (user_id, recipe_id, recipe_title, recipe_image, calories, protein, instructions, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",  # ML: ADDED `embedding` COLUMN
        (user_id, recipe.get("id"), recipe.get("title"), recipe.get("image"),
         get_nutrient(recipe, "Calories"), get_nutrient(recipe, "Protein"), steps_text, embedding),  # ML: ADDED `embedding` VALUE
    )
    conn.commit()
    conn.close()


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
