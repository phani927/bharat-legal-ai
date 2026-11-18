import streamlit as st
from openai import OpenAI
from supabase import create_client, Client
from pypdf import PdfReader
from docx import Document

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

# Helper: Extract text from PDF, DOCX, or TXT with page numbers
def extract_document_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pages = []
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- [PAGE {idx}] ---\n{text}")
        return "\n\n".join(pages)
    elif name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")

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
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    profile_res = supabase.table("profiles").select("is_approved").eq("id", res.user.id).execute()

                    if profile_res.data and profile_res.data[0]["is_approved"] == True:
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        st.rerun()
                    else:
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
        st.session_state.pop("active_docs", None)
        st.rerun()

    st.title("⚖️ Indian Legal AI Assistant")
    st.write("A prototype AI engine tuned for Indian Jurisprudence by Phani.")

    # Show active uploaded documents banner if files are loaded in memory
    if st.session_state.get("active_docs"):
        names = ", ".join(st.session_state.active_docs.keys())
        col1, col2 = st.columns([4, 1])
        col1.info(f"📄 Active Case Files ({len(st.session_state.active_docs)}): **{names}**")
        if col2.button("Clear Files"):
            st.session_state.pop("active_docs", None)
            st.rerun()

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

    # 6. Chat Input with Multi-File '+' Attachment
    submission = st.chat_input(
        "Ask about Indian law or click + to attach judgments/depositions...",
        accept_file="multiple",
        file_type=["pdf", "docx", "txt"]
    )

    if submission:
        user_text = submission.text or ""
        uploaded_files = submission.files or []

        # Process all attached files and store them in session_state
        if uploaded_files:
            if "active_docs" not in st.session_state:
                st.session_state.active_docs = {}

            badges = []
            for f in uploaded_files:
                extracted = extract_document_text(f)
                if extracted.strip():
                    st.session_state.active_docs[f.name] = extracted
                    badges.append(f"`{f.name}` (~{len(extracted)//4:,} tokens)")
                else:
                    st.error(f"No selectable text in `{f.name}`. If scanned, run OCR first.")
                    st.stop()

            badge_line = "📎 **Attached:** " + ", ".join(badges) + "\n\n"
            user_text = badge_line + (user_text or "Please review and analyze these case documents.")

        if user_text.strip():
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.markdown(user_text)

            # Inject all active documents into API context without bloating Supabase chat history
            api_messages = list(st.session_state.messages)
            if st.session_state.get("active_docs"):
                combined_sections = []
                for fname, ftext in st.session_state.active_docs.items():
                    combined_sections.append(f"=== DOCUMENT: {fname} ===\n{ftext}")
                all_docs_text = "\n\n".join(combined_sections)
                doc_prompt = f"Attached case documents. Cite document names and [PAGE X] numbers:\n\n{all_docs_text}"
                api_messages.insert(1, {"role": "system", "content": doc_prompt})

            with st.chat_message("assistant"):
                stream = client.chat.completions.create(
                    model="gpt-6.2-astra",
                    reasoning_effort="high",
                    messages=api_messages,
                    stream=True,
                )

                response = st.write_stream(stream)

                confirmed_model = stream.response.headers.get("openai-model", "gpt-6.2-astra")
                st.caption(f"Model: `{confirmed_model}`")

            st.session_state.messages.append({"role": "assistant", "content": response})

            # Persist updated conversation to Supabase
            supabase.table("user_chat_history").upsert({
                "user_id": st.session_state.user.id,
                "chat_data": st.session_state.messages
            }).execute()
