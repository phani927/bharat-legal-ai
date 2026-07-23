import streamlit as st
from openai import OpenAI

# 1. Set up the web page layout
st.set_page_config(page_title="Indian Legal AI", page_icon="⚖️")
st.title("⚖️ Indian Legal AI Assistant")
st.write("A prototype AI engine tuned for Indian jurisprudence (BNS, BSA, BNSS, Constitution).")

# 2. Sidebar for API Key (Protects your wallet)
with st.sidebar:
    st.header("Settings")
    user_api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    st.markdown("Get an API key from [platform.openai.com](https://platform.openai.com/).")

# 3. Stop the app if no key is provided
if not user_api_key:
    st.info("Please enter your OpenAI API key in the sidebar to begin.")
    st.stop()

# 4. Initialize the OpenAI client
client = OpenAI(api_key=user_api_key)

# 5. Set up the chat memory and the legal persona
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a highly capable Indian Legal Assistant. Answer questions based on the Constitution of India, the Bharatiya Nyaya Sanhita, civil procedure codes, and Supreme Court precedent. Be precise, formal, and cite specific sections where possible."}
    ]

# 6. Display the chat history on the screen
for message in st.session_state.messages:
    if message["role"] != "system": # We hide the system prompt from the user interface
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 7. Accept the user's legal question
if prompt := st.chat_input("Ask a question about Indian law..."):
    
    # Show the user's question on screen
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Ask OpenAI for the answer and stream it to the screen
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state.messages,
            stream=True,
        )
        response = st.write_stream(stream)
    
    # Save the AI's answer into the chat memory
    st.session_state.messages.append({"role": "assistant", "content": response})
