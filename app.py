import streamlit as st

st.set_page_config(page_title="EVE Data", layout="wide")

pages = [
    st.Page("pages/home.py", title="Home", default=True),
    st.Page("pages/planetary_industry.py", title="Planetary Industry"),
]

pg = st.navigation(pages)
pg.run()
