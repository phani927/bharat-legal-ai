import streamlit as st
from openai import OpenAI
from supabase import create_client, Client

st.set_page_config(page_title="Indian Legal AI", page_icon="⚖️")

# 1. Initialize Clients
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "user" not in st.session_state:
    st.session_state.user = None
if "session" not in st.session_state:
    st.session_state.session = None

# Restore Supabase auth session across reruns
if st.session_state.session:
    try:
        supabase.auth.set_session(
            st.session_state.session.access_token, 
            st.session_state.session.refresh_token
        )
    except Exception:
        st.session_state.user = None
        st.session_state.session = None

# 2. Authentication Gate (Login / Sign Up)
if st.session_state.user is None:
    st.title("⚖️ Indian Legal AI Assistant by Phani")
    st.write("Please sign in or create an account to access the legal engine.")
    
    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])
    
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                try:
                    # Authenticate user credentials
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    
                    # Check if the user has been approved by an admin in the profiles table
                    profile_res = supabase.table("profiles").select("is_approved").eq("id", res.user.id).execute()
                    
                    if profile_res.data and profile_res.data[0]["is_approved"] == True:
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        st.rerun()
                    else:
                        # Revoke session immediately if not approved
                        supabase.auth.sign_out()
                        st.warning("Your account is pending admin approval. Please check back later.")
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_pwd")
            if st.form_submit_button("Create Account"):
                try:
                    supabase.auth.sign_up({"email": new_email, "password": new_password})
                    st.success("Account created successfully! It is currently pending administrator approval.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")

# 3. Authenticated Interface
else:
    # Sidebar Session Management
    st.sidebar.write(f"Logged in as: **{st.session_state.user.email}**")
    if st.sidebar.button("Log Out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.session = None
        st.session_state.messages = []
        st.rerun()

    st.title("⚖️ Indian Legal AI Assistant")
    st.write("A prototype AI engine tuned for Indian Jurisprudence by Phani.")

    # 4. Load Persistent Chat History
    if "messages" not in st.session_state:
        response = supabase.table("user_chat_history").select("chat_data").eq("user_id", st.session_state.user.id).execute()
        if response.data:
            st.session_state.messages = response.data[0]["chat_data"]
        else:
            st.session_state.messages = [
                {"role": "system", "content": "You are a highly capable Indian Legal Assistant. Answer questions based on the Constitution of India, the Bharatiya Nyaya Sanhita, civil procedure codes, and Supreme Court precedent. Be precise, formal, and cite specific sections where possible."}
            ]

    # 5. Render History
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 6. Chat Input & Streaming
    if prompt := st.chat_input("Ask a question about Indian law..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-6.2-astra",
                reasoning_effort="high",
                messages=st.session_state.messages,
                stream=True,
            )

            resolved_model = None
            def stream_text(chunks):
                nonlocal resolved_model
                for chunk in chunks:
                    if chunk.model:
                        resolved_model = chunk.model
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            response = st.write_stream(stream)
            if resolved_model:
                st.caption(f"Model: `{resolved_model}`")
        
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Persist updated conversation to Supabase
        supabase.table("user_chat_history").upsert({
            "user_id": st.session_state.user.id,
            "chat_data": st.session_state.messages
        }).execute()
