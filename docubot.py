import pathlib
import streamlit as st

st.set_page_config(layout="wide")

folder_path = pathlib.Path(__file__).parent

with open(folder_path / "README.md", "r") as f:
    text = f.read()

st.write(text)