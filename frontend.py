import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000/ask"

st.set_page_config(page_title="AI Mental Health Therapist", layout="wide")
st.title("SafeSpace - AI Mental Health Therapist")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

try:
    requests.get("http://127.0.0.1:8000", timeout=2)
    backend_available = True
except (requests.ConnectionError, requests.Timeout):
    backend_available = False

if not backend_available:
    st.info("Backend is still starting or temporarily unavailable. Refresh this page in a moment.")
    st.stop()

user_input = st.chat_input("What's on your mind today?")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
        try:
            res = requests.post(
                BACKEND_URL,
                json={
                    "message": user_input,
                    "history": st.session_state.chat_history[-12:],
                },
                timeout=60,
            )
            res.raise_for_status()
            response_data = res.json()["response"]
        except (requests.ConnectionError, requests.Timeout):
            st.error("Lost connection to backend. Please restart it and refresh.")
            st.stop()
        except Exception as e:
            response_data = f"I'm having trouble processing your request. Please try again. (Error: {e})"

    st.session_state.chat_history.append({"role": "assistant", "content": response_data})

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
