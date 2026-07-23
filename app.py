import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Indian Legal AI", page_icon="⚖️")
st.title("⚖️ Indian Legal AI Assistant")
st.write("A prototype AI engine tuned for Indian Jurisprudence.")

# 1. Pull the API key securely from Streamlit's backend secrets
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# 2. Set up the chat memory and persona
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a highly capable Indian Legal Assistant. Answer questions based on the Constitution of India, the Bharatiya Nyaya Sanhita, civil procedure codes, and Supreme Court precedent. Be precise, formal, and cite specific sections where possible."}
    ]

# 3. Display the chat history
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 4. Accept user input
if prompt := st.chat_input("Ask a question about Indian law..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and stream the response
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            # model="gpt-4o",
            model="gpt-5.6-sol",
            messages=st.session_state.messages,
            stream=True,
        )
        response = st.write_stream(stream)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
