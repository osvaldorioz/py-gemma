import streamlit as st
import requests
import uuid

API_URL = "http://localhost:8000"

st.title("🍻 Chatbot de Cervezas 🍺")

chat_id = st.session_state.get("chat_id", None)
if not chat_id:
    response = requests.post(f"{API_URL}/chat/startChat")
    chat_id = response.json()["message"]
    st.session_state["chat_id"] = chat_id

prompt = st.text_input("Haz preguntas relacionadas con cervezas:")
if st.button("Enviar"):
    response = requests.post(f"{API_URL}/chat/{chat_id}", json={"prompt": prompt})
    st.write("Response:", response.json()["message"])