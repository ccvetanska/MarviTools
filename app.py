import streamlit as st
from ui.image_resizer_tab import render as render_image_resizer

st.set_page_config(page_title="Marvi Tools", page_icon="", layout="centered")

st.title("Marvi инструменти")
tabs = st.tabs(["Обработи картинка за продукт", "Очаквай скоро"])

with tabs[0]:
    render_image_resizer()

with tabs[1]:
    st.info("Очаквай скооро!")
