import streamlit as st
import os

# ── App-wide config ──────────────────────────────────────────────────────────
def apply_config():
    st.set_page_config(
        page_title="MyApp",
        page_icon="images/logo.png",
        layout="wide",
        initial_sidebar_state="expanded", 
    )

# ── Header ───────────────────────────────────────────────────────────────────
def render_header(title: str = "Geo_Map"):
    st.image("images/logo.png", width=80)
    st.markdown(f"### {title}")
    
# ── Footer ───────────────────────────────────────────────────────────────────

def render_footer(text: str = "© 2026 MyApp · All rights reserved"):
    st.markdown(f'<div class="app-footer">{text}</div>', unsafe_allow_html=True)
    