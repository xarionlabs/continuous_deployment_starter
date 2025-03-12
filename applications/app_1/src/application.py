import streamlit as st
from shared_lib.src.shared_function import get_shared_str

def get_str():
    return get_shared_str()

st.text(get_str())
