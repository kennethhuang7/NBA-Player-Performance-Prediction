import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'streamlit_app'))

import streamlit as st
from Home import main

st.set_page_config(
    page_title="NBA Predictions",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

if __name__ == "__main__":
    main()

