import hashlib
import streamlit as st
from src.vision import extract_ingredients


def render_fridge_scanner():
    with st.expander("Scan fridge photo with AI"):
        photo = st.file_uploader("Upload a fridge photo", type=["jpg", "jpeg", "png"], key="fridge_photo")
        if photo:
            photo_bytes = photo.read()
            photo_hash = hashlib.md5(photo_bytes).hexdigest()
            if st.session_state.get("scanned_photo_hash") != photo_hash:
                with st.spinner("Scanning your fridge..."):
                    found = extract_ingredients(photo_bytes)
                    st.session_state["scanned_ingredients"] = [item["name"] for item in found]
                    st.session_state["scanned_photo_hash"] = photo_hash

    if st.session_state.get("scanned_ingredients"):
        st.success("Found: " + ", ".join(st.session_state["scanned_ingredients"]))

    return st.session_state.get("scanned_ingredients", [])
