# handles the fridge photo scan: uploads a photo, sends it to Claude and returns the detected ingredients

import hashlib # used to figure out if the same image has been uploaded and scanned already to avoid redundant API calls
import streamlit as st
from src.vision import extract_ingredients # sends the photo to Claude and returns detected ingredients

# renders the fridge scanner UI and returns a list of detected ingredient names
def render_fridge_scanner():
    # collapsible UI block, the scan only runs when the user opens and uploads a photo
    with st.expander("Scan fridge photo with AI"):
        photo = st.file_uploader("Upload a fridge photo", type=["jpg", "jpeg", "png"], key="fridge_photo")
        if photo:
            photo_bytes = photo.read()
            # computes a fingerprint of the image to avoid calling the API again for the same photo
            photo_hash = hashlib.md5(photo_bytes).hexdigest()
            if st.session_state.get("scanned_photo_hash") != photo_hash:
                with st.spinner("Scanning your fridge..."):
                    found = extract_ingredients(photo_bytes)
                    # extracts only the ingredient names from the result and saves them in session state
                    st.session_state["scanned_ingredients"] = [item["name"] for item in found]
                    st.session_state["scanned_photo_hash"] = photo_hash
        # if the ingredients were already scanned and saved in session state, show them as a success message
        if st.session_state.get("scanned_ingredients"):
            st.success("Found: " + ", ".join(st.session_state["scanned_ingredients"]))
     # returns the found ingredients so app.py can use them, or an empty list if nothing was scanned yet
    return st.session_state.get("scanned_ingredients", [])
