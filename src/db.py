import sqlite3

# Name of the SQLite database file
DB_NAME = "app.db"

# Create and return a database connection
def get_conn():
    return sqlite3.connect(DB_NAME)

# Retrieve a specific nutrient value from a recipe
def get_nutrient(recipe, name):
    # Loop through all nutrients in the recipe data
    for n in recipe.get("nutrition", {}).get("nutrients", []):
        # Compare nutrient names without case sensitivity
        if n["name"].lower() == name.lower():
            # Return the rounded nutrient amount
            return round(n["amount"])
    # Return 0 if the nutrient is not found
    return 0


# Initialize the database and create required tables
def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # Table for user login data
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )""")
    
    # Table for user dietary preferences and restrictions
    c.execute("""
    CREATE TABLE IF NOT EXISTS preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        allergies TEXT,
        diet TEXT,
        religion TEXT
    )""")
    
    # Table for recipes saved by users
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
    
    # Add instructions column 
    try:
        c.execute("ALTER TABLE saved_recipes ADD COLUMN instructions TEXT")
        conn.commit()
        
    # Ignore error if the column already exists
    except Exception:
        pass
    
    # Close database connection
    conn.close()

# Save a recipe to the database for a specific user
def save_recipe(user_id, recipe):
    conn = get_conn()
    c = conn.cursor()
    
    # Retrieve recipe instructions from API response
    instructions = recipe.get("analyzedInstructions", [])
    
    # Convert recipe steps into a readable text format
    if instructions and instructions[0].get("steps"):
        steps_text = "\n".join(
            f"{s['number']}. {s['step']}" for s in instructions[0]["steps"]
        )
    else:
        steps_text = ""
        
    # Insert recipe data into the saved_recipes table
    c.execute(
        "INSERT INTO saved_recipes (user_id, recipe_id, recipe_title, recipe_image, calories, protein, instructions) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, recipe.get("id"), recipe.get("title"), recipe.get("image"),
         get_nutrient(recipe, "Calories"), get_nutrient(recipe, "Protein"), steps_text),
    )
    conn.commit()
    
    # Close database connection
    conn.close()

# Retrieve all saved recipes for a user
def get_saved_recipes(user_id):
    conn = get_conn()
    c = conn.cursor()
    
    # Select saved recipes ordered by newest first
    c.execute(
        "SELECT recipe_title, recipe_image, calories, protein, saved_at, instructions FROM saved_recipes WHERE user_id=? ORDER BY saved_at DESC",
        (user_id,),
    )
    
    # Fetch all matching rows
    rows = c.fetchall()
    
    # Close database connection
    conn.close()
    
    return rows

# Retrieve user dietary preferences from the database
def get_user_preferences(user_id):
    conn = get_conn()
    c = conn.cursor()
    
    # Get allergies, diet and religion for a specific user
    c.execute("SELECT allergies, diet, religion FROM preferences WHERE user_id=?", (user_id,))
    
    # Fetch one matching row
    row = c.fetchone()
    
    # Close database connection
    conn.close()
    
    # Check if user preferences exist
    if row:
        
        # Unpack database values
        allergies_str, diet, religion = row
        
        # Convert comma-separated allergies into a clean list
        allergies = [a.strip() for a in allergies_str.split(",") if a.strip()] if allergies_str else []
        
        # Return preferences as a dictionary
        return {"allergies": allergies, "diet": diet, "religion": religion}
    
    # Return default values if no preferences are found
    return {"allergies": [], "diet": "None", "religion": "None"}

  