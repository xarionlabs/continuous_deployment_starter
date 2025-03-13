import streamlit as st
from st_oauth import setup
setup()

if not st.experimental_user.is_logged_in:
    if st.button("Log in with Google"):
        st.login()
    st.stop()

if st.button("Log out"):
    st.logout()
st.markdown(f"Welcome! {st.experimental_user.name}")
