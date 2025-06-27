# --- Imports ---
import os
import json
from datetime import datetime
import openai
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import pytesseract
import PyPDF2
import docx
from murf_integration import get_murf_api
import moviepy as mpy  # type: ignore
import tempfile


# --- Environment & Configuration ---
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- Constants & Global Variables ---
USER_DB = "users.json"
INTERVIEW_DB = "interviews.json"
COMPANIES = [
    "Google", "Microsoft", "Amazon", "OpenAI", "Meta", "Apple", "StartupX", "Your Own Startup",
]
JOB_TITLES = [
    "Software Engineer", "Data Scientist", "Product Manager", "UX Designer", "AI Researcher", "Hotel Manager"
]
QUESTION_TYPES = {
    "MCQ": "Multiple-choice questions with 4 options and the correct answer.",
    "Practical": "Hands-on or coding/practical scenario questions.",
    "Theoretical": "Conceptual or theory-based questions."
}
SUBJECTS = {
    "DSA": ["Arrays", "Linked Lists", "Trees", "Graphs", "Sorting", "Searching", "Dynamic Programming", "Stacks & Queues"],
    "OS": ["Processes", "Threads", "Memory Management", "Scheduling", "Synchronization", "Deadlocks"],
    "OOPs": ["Classes & Objects", "Inheritance", "Polymorphism", "Encapsulation", "Abstraction", "Design Patterns"],
    "System Design": ["Scalability", "Databases", "APIs", "Microservices", "Caching", "Load Balancing"],
    "AI/ML": ["Machine Learning", "Deep Learning", "Natural Language Processing", "Computer Vision"]
}

# --- Ensure DB Files Exist ---
if not os.path.exists(USER_DB):
    with open(USER_DB, "w") as f:
        json.dump({}, f)
if not os.path.exists(INTERVIEW_DB):
    with open(INTERVIEW_DB, "w") as f:
        json.dump({}, f)

# --- Utility Functions ---
def add_vertical_space(lines=1):
    for _ in range(lines):
        st.write("")

def back_to_dashboard_button(key_suffix="", target_page="dashboard"):
    btn_style = """
        <style>
        .mini-back-btn {
            font-size: 0.95rem !important;
            padding: 2px 10px !important;
            border-radius: 7px !important;
            min-width: 0 !important;
            width: fit-content !important;
            height: 32px !important;
            margin: 0.5em 0 0.5em 0 !important;
            background: #f3f3f3 !important;
            color: #333 !important;
            border: 1px solid #e0e0e0 !important;
            box-shadow: none !important;
        }
        </style>
    """
    st.markdown(btn_style, unsafe_allow_html=True)
    # Center the back button using columns
    col1, col2, col3 = st.columns([2,2,2])
    with col2:
        if st.button("\U0001F519 Back", key=f"back_to_dashboard_{key_suffix}", use_container_width=True):
            st.session_state.page = target_page
            st.session_state.logged_in = False if target_page == "login" else st.session_state.get("logged_in", False)
            st.rerun()

# --- API/Data Functions ---
def get_gemini_api_key():
    gemini_api_key = st.session_state.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    return gemini_api_key

def fetch_gemini_questions(company, job, difficulty, count, qtype):
    GEMINI_API_KEY = get_gemini_api_key()
    if not GEMINI_API_KEY:
        st.error("Gemini API key not set. Please set the GEMINI_API_KEY environment variable or enter it in the sidebar.")
        return []
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    prompt = (
        f"Generate {count} {qtype} interview questions for a {job} role at {company}. "
        f"Difficulty: {difficulty}. "
        f"{QUESTION_TYPES[qtype]} "
        f"For each question, also provide a model answer. "
        f"Return ONLY a Python list of tuples, where each tuple is (question, correct_option, options_dict, explanation)."
    )
    try:
        response = model.generate_content(prompt)
        import ast
        content = response.text.strip()
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1:
            list_str = content[start:end+1]
            try:
                qa_pairs = ast.literal_eval(list_str)
            except Exception as e:
                import re
                list_str_fixed = re.sub(r',\s*([\]\)])', r'\1', list_str)
                list_str_fixed = list_str_fixed.replace("'", '"')
                try:
                    import json
                    qa_pairs = json.loads(list_str_fixed)
                except Exception as e2:
                    st.error(f"Could not parse Gemini response: {e}\nTried JSON parse: {e2}")
                    st.code(content)
                    return []
            questions = []
            for item in qa_pairs:
                if isinstance(item, (list, tuple)) and len(item) >= 4:
                    questions.append({
                        "question": item[0],
                        "correct_option": item[1],
                        "options": item[2],
                        "explanation": item[3]
                    })
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    questions.append({
                        "question": item[0],
                        "correct_option": None,
                        "options": None,
                        "explanation": item[1]
                    })
            if questions:
                return questions
        st.error("Gemini did not return a valid Python list. Please try again.")
        st.code(content)
        return []
    except Exception as e:
        st.error(f"Error fetching questions from Gemini: {e}")
        return []

def authenticate(username, password):
    with open(USER_DB, "r") as f:
        users = json.load(f)
    return users.get(username) == password

def register(username, password):
    with open(USER_DB, "r") as f:
        users = json.load(f)
    if username in users:
        return False
    users[username] = password
    with open(USER_DB, "w") as f:
        json.dump(users, f)
    return True

def save_interview(username, interview):
    with open(INTERVIEW_DB, "r") as f:
        data = json.load(f)
    if username not in data:
        data[username] = []
    data[username].append(interview)
    with open(INTERVIEW_DB, "w") as f:
        json.dump(data, f)

def get_history(username):
    with open(INTERVIEW_DB, "r") as f:
        data = json.load(f)
    return data.get(username, [])

# --- Feature-Specific Helpers ---
def murf_tts(text, voice_id=None):
    try:
        valid_voices = ["en-US-terrell", "en-US-samantha"]
        if voice_id not in valid_voices:
            voice_id = "en-US-terrell"
        murf = get_murf_api()
        if not murf:
            return None
        # --- Murf API text length fix ---
        max_len = 3000
        if len(text) > max_len:
            # Try to cut at a sentence boundary if possible
            truncated = text[:max_len]
            last_dot = truncated.rfind('.')
            if last_dot > 0 and last_dot > max_len - 200:
                truncated = truncated[:last_dot+1]
            text = truncated
        audio_data = murf.text_to_speech(text, voice_id)
        if audio_data:
            if isinstance(audio_data, str):
                if audio_data.startswith("http"):
                    import requests
                    audio_bytes = requests.get(audio_data).content
                elif os.path.exists(audio_data):
                    with open(audio_data, "rb") as f:
                        audio_bytes = f.read()
                else:
                    audio_bytes = audio_data.encode("utf-8")
            else:
                audio_bytes = audio_data
            return audio_bytes
        return None
    except Exception as e:
        return None

def get_voice_options(murf=None):
    voices = [
        {"id": "en-US-terrell", "name": "en-US-Terrell", "gender": "Male"},
        {"id": "en-US-samantha", "name": "en-US-Samantha", "gender": "Female"}
    ]
    if murf and hasattr(murf, "get_available_voices") and callable(getattr(murf, "get_available_voices")):
        try:
            murf_voices = murf.get_available_voices()
            if isinstance(murf_voices, list) and len(murf_voices) > 0 and all(isinstance(v, dict) and 'id' in v and 'name' in v for v in murf_voices):
                voices = murf_voices
        except Exception as e:
            pass
    for v in voices:
        if 'gender' in v and v['gender']:
            v['name'] = f"{v['name']} ({v['gender']})"
    seen_ids = set()
    unique_voices = []
    for v in voices:
        if v['id'] not in seen_ids:
            unique_voices.append(v)
            seen_ids.add(v['id'])
    return {v["name"]: v["id"] for v in unique_voices}

def render_feature_cards(feature_rows):
    cols = st.columns(len(feature_rows[0]))
    for i, feat in enumerate(feature_rows[0]):
        with cols[i]:
            st.markdown(f"""
            <div class='feature-card' style='border-top: 4px solid {feat['color']};'>
                <span class='stat-icon' style='color:{feat['color']}'>{feat['icon']}</span>
                <div class='feature-title'>{feat['title']}</div>
                <div class='feature-desc'>{feat['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"{feat['title']}", key=f"cardbtn_{i}", use_container_width=True):
                st.session_state.page = feat['page']
                st.rerun()

# --- UI Page Functions ---
# --- Custom CSS for Modern Card UI ---
st.markdown("""
    <style>
    body, .stApp {
        /* Modern, soft blue-violet gradient background */
        background: linear-gradient(135deg, #e0e7fa 0%, #f5e6ff 40%, #d1e7ff 100%) !important;
        min-height: 100vh;
    }
    .login-card, .signup-card {
        background: linear-gradient(135deg, #fffde4 0%, #e1f5fe 100%);
        border-radius: 22px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.12);
        padding: 2.5rem 2rem 2rem 2rem;
        max-width: 370px;
        margin: 2.5rem auto 1.5rem auto;
        position: relative;
    }
    .login-card:before, .signup-card:before {
        content: "";
        position: absolute;
        top: -40px; left: -40px;
        width: 80px; height: 80px;
        background: rgba(200, 230, 201, 0.18);
        border-radius: 50%;
        z-index: 0;
    }
    .login-card:after, .signup-card:after {
        content: "";
        position: absolute;
        top: -30px; right: -30px;
        width: 60px; height: 60px;
        background: rgba(224, 247, 250, 0.15);
        border-radius: 50%;
        z-index: 0;
    }
    .login-card h2, .signup-card h2 {
        text-align: center;
        margin-bottom: 1.5rem;
        font-weight: 700;
        color: #333;
        z-index: 1;
        position: relative;
    }
    .login-btn, .signup-btn {
        background: linear-gradient(90deg, #ffb347 0%, #ffcc33 100%);
        color: #222;
        border: none;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: 600;
        width: 100%;
        padding: 0.7rem 0;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 8px rgba(255, 180, 80, 0.15);
        transition: background 0.2s;
    }
    .login-btn:hover, .signup-btn:hover {
        background: linear-gradient(90deg, #ffcc33 0%, #ffb347 100%);
        color: #111;
    }
    .stTextInput>div>div>input, .stTextInput>div>div>textarea {
        background: #f8fafc !important;
        border-radius: 7px !important;
        border: 1.5px solid #b2dfdb !important;
        font-size: 1rem !important;
        padding: 0.6rem 0.8rem !important;
    }
    .stCheckbox>label {
        font-size: 1rem !important;
        color: #444 !important;
    }
    .stApp {
        min-height: 100vh;
    }
    /* Blue-violet app bar at the top */
    .appbar-title {
        width: 420px;
        max-width: 90vw;
        margin: 32px auto 0px auto; /* Remove extra space below the app bar */
        padding: 1.1rem 0.5rem;
        background: linear-gradient(90deg, #7f9cf5 0%, #a18ff5 100%);
        border-radius: 32px;
        box-shadow: 0 4px 24px 0 rgba(127, 156, 245, 0.18);
        text-align: center;
        font-size: 2.1rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: 1px;
        position: relative;
        z-index: 10;
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }
    @media (max-width: 600px) {
        .appbar-title { font-size: 1.2rem; padding: 0.7rem 0.2rem; }
        .login-card, .signup-card { padding: 1.2rem 0.5rem 1rem 0.5rem; }
    }
    </style>
""", unsafe_allow_html=True)

# --- AppBar with App Name ---
st.markdown('<div class="appbar-title">🧑‍💼 AI Interview Expert</div>', unsafe_allow_html=True)

# Remove/hide the empty container below the app bar on the login page (including its height/space)
if st.session_state.get("page", "login") == "login":
    st.markdown(
        """
        <style>
        /* Hide any empty div directly after the appbar-title and remove its space */
        .appbar-title + div:empty {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def login_page():
    # Centered card layout for login
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<h2>Login</h2>', unsafe_allow_html=True)
    login_method = st.radio("Login with:", ["Username", "Email"], horizontal=True)
    # --- Fix label and variable for username/email ---
    if login_method == "Username":
        login_input = st.text_input("Username", key="login_username")
        login_key = "username"
    else:
        login_input = st.text_input("Email", key="login_email")
        login_key = "email"
    password = st.text_input("Password", type="password", key="login_password")
    remember = st.checkbox("Remember me", key="login_remember")
    col1, col2 = st.columns([2, 2])
    with col1:
        login_clicked = st.button("Login", key="login_btn", use_container_width=True)
    with col2:
        signup_clicked = st.button("Sign Up", key="goto_signup_btn", use_container_width=True)
    if login_clicked:
        username = login_input.strip()
        # --- Only allow username login (since register uses username as key) ---
        if login_method == "Username":
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid credentials")
        else:
            st.error("Login with Email is not supported. Please use Username.")
    if signup_clicked:
        st.session_state.page = "signup"
        st.rerun()
    st.markdown('<div style="text-align:center; margin-top:1rem;">Don\'t have an account? <span style="color:#ff9800; font-weight:600;">Sign Up</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def signup_page():
    # Centered card layout for signup
    st.markdown('<div class="signup-card">', unsafe_allow_html=True)
    st.markdown('<h2>Create an account</h2>', unsafe_allow_html=True)
    username = st.text_input("Username", key="signup_username")
    # Remove email field since login/register is username-based
    password = st.text_input("Password", type="password", key="signup_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
    remember = st.checkbox("Remember me", key="signup_remember")
    col1, col2 = st.columns([2, 2])
    with col1:
        signup_clicked = st.button("Sign Up", key="signup_btn", use_container_width=True)
    with col2:
        login_clicked = st.button("Login", key="goto_login_btn", use_container_width=True)
    if signup_clicked:
        if password != confirm_password:
            st.error("Passwords do not match.")
        elif not username or not password:
            st.error("Please fill all fields.")
        elif register(username, password):
            st.success("Registered! Please log in.")
            st.session_state.page = "login"
        else:
            st.error("Username exists")
    if login_clicked:
        st.session_state.page = "login"
        st.rerun()
    st.markdown('<div style="text-align:center; margin-top:1rem;">Already have an account? <span style="color:#ff9800; font-weight:600;">Login</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard_page():
    # Ensure Streamlit renders the dashboard content
    st.write(f"Welcome, **{st.session_state.get('username', 'User')}**! 👋")

    # --- Dashboard Stats Cards (top row, minimized and equal size) ---
    stats = [
        {
            "label": "Interviews Attempted",
            "value": len(get_history(st.session_state.get('username', ''))),
            "icon": "📝",
            "desc": "Total interview sessions you've attempted."
        },
        {
            "label": "Topics Learned",
            "value": 0,  # You can update this with your logic
            "icon": "📚",
            "desc": "Topics you have learned or practiced."
        },
        {
            "label": "History",
            "value": "",  # No count, just a link/button
            "icon": "🕑",
            "desc": "View your interview history."
        }
    ]
    # Use equal and minimal width columns for all three cards
    stat_cols = st.columns([1, 1, 1])
    card_css = """
        <style>
        .mini-stat-card {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(127,156,245,0.07);
            padding: 0.7rem 0.5rem 0.7rem 0.5rem;
            margin-bottom: 8px;
            text-align: center;
            min-width: 120px;
            max-width: 180px;
            width: 100%;
            display: inline-block;
        }
        .mini-stat-card .stat-icon {
            font-size: 1.5rem;
        }
        .mini-stat-card .stat-label {
            font-size: 1rem;
            font-weight: 700;
            color: #7f9cf5;
        }
        .mini-stat-card .stat-value {
            font-size: 1.2rem;
            font-weight: 600;
            color: #333;
        }
        .mini-stat-card .stat-desc {
            font-size: 0.85rem;
            color: #888;
        }
        </style>
    """
    st.markdown(card_css, unsafe_allow_html=True)
    for i, stat in enumerate(stats):
        with stat_cols[i]:
            st.markdown(
                f"""
                <div class="mini-stat-card">
                    <div class="stat-icon">{stat['icon']}</div>
                    <div class="stat-label">{stat['label']}</div>
                    <div class="stat-value">{stat['value']}</div>
                    <div class="stat-desc">{stat['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    # Add a "View History" button in the third card
    with stat_cols[2]:
        if st.button("View History", key="view_history_btn", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()

    # --- Voice Settings Card (centered, similar to screenshot) ---
    st.markdown(
        """
        <div style="background: #f7f8fd; border-radius: 14px; box-shadow: 0 1px 4px rgba(127,156,245,0.06); padding: 1.1rem 1rem 1.1rem 1rem; margin: 0.5rem auto 1.2rem auto; max-width: 600px;">
            <b>Voice Settings</b><br>
            <span style="font-size:0.98rem; color:#555;">
                Personalize your experience by choosing your preferred voice for each feature.
            </span>
            <span style="float:right;">
                <a href="#" onclick="window.location.hash='voice_settings';window.location.reload();" style="color:#7f9cf5;font-weight:600;text-decoration:none;">
                    Customize Voices
                </a>
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Feature Cards (replace with your app features) ---
    features = [
        {
            "icon": "🎯",
            "title": "Tech Interview",
            "desc": "Practice technical interviews.",
            "color": "#7f9cf5",
            "page": "interview"
        },
        {
            "icon": "👨‍🏫",
            "title": "AI Teacher",
            "desc": "Get AI-powered explanations and tutoring.",
            "color": "#a18ff5",
            "page": "ai_teacher"
        },
        {
            "icon": "🗣️",
            "title": "HR Chat",
            "desc": "Practice HR interview questions.",
            "color": "#4F8BF9",
            "page": "communication"
        },
        {
            "icon": "📄",
            "title": "Resume Analyzer",
            "desc": "Analyze and improve your resume.",
            "color": "#8E24AA",
            "page": "resume_analyzer"
        },
        {
    "icon": "🎬",
    "title": "Video Summary",
    "desc": "Watch a video summary of your interview journey.",
    "color": "#ff9800",
    "page": "video_summary"
}
    ]
    # Arrange features in two rows, 3 + 2
    feature_rows = [features[:3], features[3:]]
    for row in feature_rows:
        cols = st.columns(len(row))
        for i, feat in enumerate(row):
            with cols[i]:
                st.markdown(
                    f"""
                    <div class='feature-card' style='border-top: 4px solid {feat['color']}; margin-bottom: 18px;'>
                        <span class='stat-icon' style='color:{feat['color']};font-size:2.1rem;'>{feat['icon']}</span>
                        <div class='feature-title' style="font-weight:600;font-size:1.1rem;">{feat['title']}</div>
                        <div class='feature-desc' style="font-size:0.97rem;color:#555;">{feat['desc']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"{feat['title']}", key=f"cardbtn_{feat['title']}", use_container_width=True):
                    st.session_state.page = feat['page']
                    st.rerun()

    if st.button("Logout", key="logout_btn", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.page = "login"
        st.rerun()

def video_summary_page():
    st.markdown("<h2 style='text-align:center;'>🎬 Video Summary</h2>", unsafe_allow_html=True)
    st.info("Watch a video summary of your interview journey: Tech Interview, HR Chat, and Resume Analyzer.")

    username = st.session_state.get('username', 'User')
    interview_count = len(get_history(username))
    hr_count = interview_count
    resume_count = 1 if st.session_state.get("ats_json") else 0

    texts = [
        f"AI Interview Summary for {username}",
        f"Tech Interviews Attempted: {interview_count}",
        f"HR Chats Completed: {hr_count}",
        f"Resumes Analyzed: {resume_count}",
        "Keep practicing and improving!"
    ]

    clips = []
    for txt in texts:
        clip = mpy.TextClip(txt, color='white', bg_color='#7f9cf5', size=(720, 480), method='caption', font='Arial', fontsize=48).set_duration(2)
        clips.append(clip)

    video = mpy.concatenate_videoclips(clips, method="compose")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmpfile:
        video.write_videofile(tmpfile.name, fps=24, codec="libx264", audio=False, verbose=False, logger=None)
        st.video(tmpfile.name)

    st.markdown("This is an auto-generated video summary of your interview journey.")
    back_to_dashboard_button("video_summary", target_page="dashboard")

def ai_teacher_page():
    st.markdown("<h2 style='text-align:center;'>👨‍🏫 AI Teacher</h2>", unsafe_allow_html=True)
    st.info("Ask any technical question and get an AI-powered explanation.")

    # Use a local variable for question input, do not set st.session_state["ai_teacher_q"] directly
    question = st.text_area("Enter your technical question:", key="ai_teacher_q")
    explanation = st.session_state.get("ai_teacher_explanation", "")

    # Minimize the size of Get Explanation, Next, and Back buttons
    btn_css = """
        <style>
        .min-btn button, .min-btn-back button {
            min-width: 120px !important;
            min-height: 38px !important;
            font-size: 1rem !important;
            padding: 2px 10px !important;
            border-radius: 7px !important;
        }
        </style>
    """
    st.markdown(btn_css, unsafe_allow_html=True)

    btn_col1, btn_col2, btn_col3 = st.columns([2,1,2])
    with btn_col2:
        get_exp_clicked = st.button("Explain", key="ai_teacher_btn", use_container_width=True, help="Get AI explanation", type="primary")
    next_clicked = False
    next_col1, next_col2, next_col3 = st.columns([3,1,3])
    with next_col2:
        next_clicked = st.button("Next", key="ai_teacher_next_btn", use_container_width=True, help="Next question", type="secondary")

    if get_exp_clicked:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            GEMINI_API_KEY = get_gemini_api_key()
            if not GEMINI_API_KEY:
                st.error("Gemini API key not set. Please set it in the sidebar.")
            else:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
                prompt = f"You are an expert technical teacher. Explain the following question in detail, with examples if possible. Question: {question}"
                try:
                    response = model.generate_content(prompt)
                    explanation = response.text.strip()
                    # Minimize feedback length (first 3 sentences or 350 chars)
                    import re
                    sentences = re.split(r'(?<=[.!?])\s+', explanation)
                    short_explanation = ""
                    char_limit = 900
                    for sent in sentences:
                        if len(short_explanation) + len(sent) > char_limit:
                            break
                        short_explanation += sent + " "
                        if short_explanation.count('.') >= 3:
                            break
                    short_explanation = short_explanation.strip()
                    st.session_state["ai_teacher_explanation"] = short_explanation if short_explanation else explanation
                except Exception as e:
                    st.error(f"Error from Gemini API: {e}")

    # Next button clears the explanation and question for a new input
    if next_clicked:
        st.session_state["ai_teacher_explanation"] = ""
        # Do NOT set st.session_state["ai_teacher_q"] here, just rerun to clear explanation
        st.experimental_rerun()

    if st.session_state.get("ai_teacher_explanation"):
        st.success("AI Explanation:")
        st.write(st.session_state["ai_teacher_explanation"])
        # --- Audio button for AI Teacher answer ---
        audio_col1, audio_col2, audio_col3 = st.columns([3,2,3])
        with audio_col2:
            st.markdown("""
                <style>
                div[data-testid="stHorizontalBlock"] button[title="View fullscreen"] {
                    display: none !important;
                }
                div[data-testid="stHorizontalBlock"] div[role="button"] + div[role="button"] {
                    display: none !important;
                }
                </style>
            """, unsafe_allow_html=True)
            if st.button("🔊 Voice", key="ai_teacher_audio_btn", use_container_width=True):
                voice_id = st.session_state.get("selected_voice", "en-US-terrell")
                murf = get_murf_api()
                if murf:
                    audio_bytes = murf_tts(st.session_state["ai_teacher_explanation"], voice_id)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                    else:
                        st.warning("Could not generate audio. Check Murf API key and voice settings.")
                else:
                    st.warning("Murf API is not available. Please check your Murf API key in the sidebar.")

# --- Resume Analyzer Page ---
def resume_analyzer_page():
    st.markdown("<h2 style='text-align:center;'>📄 Resume Analyzer</h2>", unsafe_allow_html=True)
    st.info("Upload your resume (PDF, DOCX, TXT, or PNG image) to get AI-powered feedback.")
    uploaded_file = st.file_uploader("Upload Resume", type=["pdf", "docx", "txt", "png"], key="resume_upload")
    submit_btn_style = """
        <style>
        .min-submit-btn button {
            min-width: 120px !important;
            min-height: 38px !important;
            font-size: 1rem !important;
        }
        </style>
    """
    st.markdown(submit_btn_style, unsafe_allow_html=True)
    # --- Center the Submit button ---
    submit_clicked = False
    submit_col1, submit_col2, submit_col3 = st.columns([3,2,3])
    with submit_col2:
        submit_clicked = st.button("Submit", key="resume_submit_btn", use_container_width=True, help="Process the uploaded file", type="primary")
    resume_text = ""
    # Always clear previous resume_text if a new file is uploaded
    if uploaded_file is not None and submit_clicked:
        try:
            filename = uploaded_file.name.lower()
            allowed_exts = [".pdf", ".docx", ".txt", ".png"]
            allowed_mimes = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
                "text/plain",
                "image/png"
            ]
            if not any(filename.endswith(ext) for ext in allowed_exts) or uploaded_file.type not in allowed_mimes:
                st.error("Unsupported file type. Only PDF, DOCX, TXT, or PNG files are allowed.")
                st.session_state.pop("resume_text", None)
            else:
                if uploaded_file.type == "application/pdf":
                    reader = PyPDF2.PdfReader(uploaded_file)
                    resume_text = " ".join(page.extract_text() or '' for page in reader.pages)
                elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
                    doc = docx.Document(uploaded_file)
                    resume_text = " ".join(p.text for p in doc.paragraphs)
                elif uploaded_file.type == "text/plain":
                    resume_text = uploaded_file.read().decode("utf-8")
                elif uploaded_file.type == "image/png":
                    from PIL import Image
                    import io
                    image_bytes = uploaded_file.read()
                    try:
                        image = Image.open(io.BytesIO(image_bytes))
                        st.image(image, caption="Uploaded Resume Image", use_container_width=True)
                        resume_text = pytesseract.image_to_string(image)
                    except Exception as e:
                        st.error(f"Could not display or process the uploaded image: {e}")
                        resume_text = ""
                else:
                    st.error("Unsupported file type.")
                    resume_text = ""
                if resume_text:
                    st.session_state["resume_text"] = resume_text
                else:
                    st.session_state.pop("resume_text", None)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            resume_text = ""
    # Show ATS analysis UI if resume_text is available
    if "resume_text" in st.session_state and st.session_state["resume_text"]:
        st.markdown("<h4 style='margin-top:1.5em;'>ATS Analysis</h4>", unsafe_allow_html=True)
        job_title = st.text_input("Target Job Title (for ATS analysis)", value=st.session_state.get("resume_job_title", "Software Engineer"), key="resume_job_title_input")
        st.session_state["resume_job_title"] = job_title
        # --- Center Analyze Resume button ---
        analyze_col1, analyze_col2, analyze_col3 = st.columns([3,2,3])
        with analyze_col2:
            analyze_clicked = st.button("Analyze Resume", key="analyze_resume_btn", use_container_width=True)
        if analyze_clicked:
            GEMINI_API_KEY = get_gemini_api_key()
            if not GEMINI_API_KEY:
                st.error("Gemini API key not set. Please set it in the sidebar.")
            else:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
                prompt = f"""
You are an expert ATS (Applicant Tracking System) and resume reviewer. Analyze the following resume text for the job title: {job_title}.

1. Give an ATS score (0-100) based on keyword matching, formatting, and relevance for the job title.
2. List important keywords or terms that are missing for this job title.
3. Give 3-5 actionable suggestions to improve the resume for ATS systems.
4. Provide a short summary of strengths and weaknesses.

Return your answer in this JSON format:
{{
  "ats_score": <score>,
  "missing_terms": [<list of missing terms>],
  "suggestions": [<list of suggestions>],
  "summary": "<short summary>"
}}

Resume Text:
{st.session_state['resume_text'][:4000]}
"""
                try:
                    response = model.generate_content(prompt)
                    import json, re
                    match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if match:
                        ats_json = json.loads(match.group(0))
                        st.markdown(f"<h5>ATS Score: <span style='color:#0077b6'>{ats_json.get('ats_score', 'N/A')}</span>/100</h5>", unsafe_allow_html=True)
                        st.markdown("<b>Missing Keywords/Terms:</b>", unsafe_allow_html=True)
                        if ats_json.get('missing_terms'):
                            st.write(", ".join(ats_json['missing_terms']))
                        else:
                            st.write("None")
                        st.markdown("<b>Suggestions to Improve:</b>", unsafe_allow_html=True)
                        for s in ats_json.get('suggestions', []):
                            st.write(f"- {s}")
                        st.markdown("<b>Summary:</b>", unsafe_allow_html=True)
                        st.write(ats_json.get('summary', ''))
                        st.session_state["ats_json"] = ats_json  # Store in session state
                except Exception as e:
                    st.error(f"Error analyzing resume: {e}")

        # --- AUDIO BUTTON FOR FEEDBACK/SUMMARY (always visible if ats_json exists) ---
        if st.session_state.get("ats_json"):
            audio_col1, audio_col2, audio_col3 = st.columns([3,2,3])
            with audio_col2:
                play_audio = st.button("🔊 Listen to ATS Feedback", key="resume_audio_btn", use_container_width=True)
            if play_audio:
                ats_json = st.session_state["ats_json"]
                summary_text = ats_json.get("summary", "")
                suggestions = ats_json.get("suggestions", [])
                ats_score = ats_json.get("ats_score", "N/A")
                feedback_text = f"ATS Score: {ats_score}/100. "
                if suggestions:
                    feedback_text += ' '.join(suggestions) + ' '
                feedback_text += summary_text
                voice_id = st.session_state.get("selected_voice", "en-US-terrell")
                murf = get_murf_api()
                if murf:
                    audio_bytes = murf_tts(feedback_text, voice_id)
                    if audio_bytes:
                        audio_player_col1, audio_player_col2, audio_player_col3 = st.columns([3,2,3])
                        with audio_player_col2:
                            st.audio(audio_bytes, format="audio/mp3")
                    else:
                        st.warning("Could not generate audio. Check Murf API key and voice settings.")
                else:
                    st.warning("Murf API is not available. Please check your Murf API key in the sidebar.")
        # --- Center the Back button below everything ---
        back_col1, back_col2, back_col3 = st.columns([3,2,3])
        with back_col2:
            back_to_dashboard_button("resume_analyzer", target_page="dashboard")

def voice_settings_page():
    st.markdown("<h2 style='text-align:center;'>🔊 Voice Settings</h2>", unsafe_allow_html=True)
    st.info("Select your preferred voice for audio features.")
    murf = get_murf_api()
    # --- Replace voice selection with Male/Female choice ---
    gender_options = {
        "Male": "en-US-terrell",
        "Female": "en-US-samantha"
    }
    # Get current voice as gender
    current_voice_id = st.session_state.get("selected_voice", "en-US-terrell")
    current_gender = "Male" if current_voice_id == "en-US-terrell" else "Female"
    selected_gender = st.selectbox("Select Voice (Gender):", list(gender_options.keys()), index=0 if current_gender == "Male" else 1)
    selected_voice_id = gender_options[selected_gender]
    if st.button("Play Sample", key="play_voice_sample", use_container_width=True):
        sample_text = "This is a sample of the selected voice."
        audio_bytes = murf_tts(sample_text, selected_voice_id)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
        else:
            st.warning("Could not play sample. Check Murf API key and voice selection.")
    if st.button("Save Voice Preference", key="save_voice_pref", use_container_width=True):
        st.session_state.selected_voice = selected_voice_id
        st.success(f"Voice preference saved: {selected_gender}")
    back_to_dashboard_button("voice_settings", target_page="dashboard")

def interview_page():
    st.markdown("<h2 style='text-align:center;'>🎯 Practice Interview</h2>", unsafe_allow_html=True)
    
    # Initialize Murf API
    murf = get_murf_api()
    if not murf:
        st.warning("Please enter your Murf API key in the sidebar for voice features.")
    
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = False
        
    if not st.session_state.interview_started:
        st.markdown("##### 🚀 Setup your interview")
        company = st.selectbox("🏢 Target Company/Startup", COMPANIES)
        job = st.selectbox("💼 Job Title", JOB_TITLES)
        subject = st.selectbox("📚 Subject", list(SUBJECTS.keys()))
        topic = st.selectbox("🔖 Topic", SUBJECTS[subject])
        diff = st.selectbox("📈 Difficulty", ["easy", "medium", "hard"])
        qtype = st.selectbox("❓ Question Type", list(QUESTION_TYPES.keys()), format_func=lambda x: f"{x} - {QUESTION_TYPES[x]}")
        count = st.slider("🔢 Number of Questions", 1, 75, 5)
        
        # Voice settings (just enable/disable, not select voice here)
        enable_voice = st.checkbox("Enable voice interaction", value=st.session_state.get("voice_enabled", True))
        st.session_state.voice_enabled = enable_voice
        
        if st.button("Start Interview", use_container_width=True):
            qa_pairs = fetch_gemini_questions(company, job, diff, count, qtype)
            if not qa_pairs:
                st.error("Could not fetch questions. Please try again.")
                return
            # --- Fix: Store full dicts for MCQ, just text for others ---
            if qtype == "MCQ":
                st.session_state.questions = qa_pairs  # list of dicts
                st.session_state.model_answers = qa_pairs  # same dicts
            else:
                st.session_state.questions = [q["question"] for q in qa_pairs]
                st.session_state.model_answers = [q["explanation"] for q in qa_pairs]
            st.session_state.answers = []
            st.session_state.current = 0
            st.session_state.interview_started = True
            st.session_state.start_time = datetime.now()
            st.session_state.company = company
            st.session_state.job = job
            st.session_state.diff = diff
            st.session_state.qtype = qtype
            st.session_state.voice_enabled = enable_voice
            st.rerun()
    else:
        qn = st.session_state.current
        if qn < len(st.session_state.questions):
            # --- Fix: Always use dict for MCQ, string for others ---
            if st.session_state.qtype == "MCQ":
                qdict = st.session_state.questions[qn]
                question_text = qdict["question"]
                options = qdict.get("options")
                correct_option = qdict.get("correct_option")
            else:
                question_text = st.session_state.questions[qn]
                options = None
                correct_option = None
            st.markdown(f"**Question {qn+1}:** {question_text}")
            # Add Listen to Question button for MCQ immediately after the question text
            if st.session_state.qtype == "MCQ":
                if st.session_state.get("voice_enabled") and get_murf_api():
                    if st.button("🔊 Listen to Question", key=f"listen_mcq_{qn}"):
                        audio_bytes = murf_tts(
                            question_text,
                            st.session_state.selected_voice
                        )
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3")
                # Show options if MCQ
                if options and isinstance(options, dict):
                    st.markdown("**Options:**")
                    option_keys = list(options.keys())
                    option_labels = [f"{k}: {options[k]}" for k in option_keys]
                    selected = st.radio("Select your answer", option_labels, key=f"mcq_radio_{qn}")
                    ans = selected.split(":", 1)[0].strip() if selected else ""
                else:
                    ans = ""
            else:
                # Do not show options for Theoretical or Practical
                # Play question audio if voice is enabled
                if st.session_state.get("voice_enabled") and get_murf_api():
                    if st.button("🔊 Listen to Question"):
                        audio_bytes = murf_tts(
                            question_text,
                            st.session_state.selected_voice
                        )
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3")
                st.markdown("**Type your answer below:**")
                ans = st.text_area("Your Answer", key=f"answer_{qn}")
            # --- Submit logic (typed or transcribed) ---
            if st.button("Submit Answer", use_container_width=True):
                if st.session_state.qtype == "MCQ":
                    # --- Improved: Accept correct key OR correct value as correct answer ---
                    user_ans = ans.strip().lower()
                    is_correct = False
                    if correct_option and options and isinstance(options, dict):
                        # Accept if user enters the correct key (case-insensitive)
                        if user_ans == str(correct_option).strip().lower():
                            is_correct = True
                        else:
                            # Accept if user enters the correct value (case-insensitive)
                            correct_value = options.get(str(correct_option))
                            if correct_value and user_ans == str(correct_value).strip().lower():
                                is_correct = True
                            else:
                                # Accept if user enters the value for any key that matches the correct value
                                for k, v in options.items():
                                    if k.lower() == str(correct_option).strip().lower() and user_ans == str(v).strip().lower():
                                        is_correct = True
                                        break
                                    if v and user_ans == str(v).strip().lower() and k.lower() == str(correct_option).strip().lower():
                                        is_correct = True
                                        break
                    score = 1 if is_correct else 0
                    model_answer = qdict.get("explanation", "")
                else:
                    model_answer = st.session_state.model_answers[qn] if "model_answers" in st.session_state else ""
                    score = min(10, max(1, len(ans.strip()) // 20))
                    is_correct = None

                improvements = []
                # More realistic feedback logic
                if st.session_state.qtype == "MCQ":
                    if is_correct:
                        improvements.append("Correct answer!")
                    else:
                        improvements.append("Incorrect. Review the correct answer below.")
                else:
                    if len(ans.strip()) < 30:
                        improvements.append("Your answer is too short. Try to elaborate more and provide specific details.")
                    if model_answer and ans.strip().lower() not in model_answer.lower():
                        improvements.append("Your answer misses some key points. Review the model answer for more depth and accuracy.")
                    if score >= 8 and not improvements:
                        improvements.append("Excellent answer! You covered all the important aspects.")
                    elif score >= 5 and not improvements:
                        improvements.append("Good effort! Consider adding more examples or details next time.")
                    elif score < 5 and not improvements:
                        improvements.append("Work on structuring your answer and addressing the main question points.")

                feedback = {
                    "overall_score": score,
                    "suggested_improvements": improvements,
                    "model_answer": model_answer
                }
                # Show options in feedback only for MCQ
                if st.session_state.qtype == "MCQ":
                    # Try to get options for feedback
                    options = None
                    if "model_answers" in st.session_state and len(st.session_state.model_answers) > qn:
                        if isinstance(st.session_state.model_answers[qn], dict):
                            options = st.session_state.model_answers[qn].get("options")
                    if not options and "questions" in st.session_state and len(st.session_state.questions) > qn and isinstance(st.session_state.questions[qn], dict):
                        options = st.session_state.questions[qn].get("options")
                    if options and isinstance(options, dict):
                        feedback["options"] = options
                    feedback["is_correct"] = is_correct
                    feedback["correct_option"] = correct_option

                st.session_state.answers.append({
                    "question": question_text,
                    "answer": ans,
                    "feedback": feedback
                })
                # --- Restore voice feedback generation for MCQ and others ---
                if st.session_state.get("voice_enabled") and murf:
                    feedback_text = f"Your score is {score} out of 10. "
                    if improvements:
                        feedback_text += " ".join(improvements)
                    else:
                        feedback_text += "Good job!"
                    audio_bytes = murf_tts(
                        feedback_text,
                        st.session_state.selected_voice
                    )
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                st.session_state.current += 1
                st.rerun()
        else:
            st.success("🎉 Interview Complete!")
            duration = datetime.now() - st.session_state.start_time
            # --- MCQ summary logic ---
            if st.session_state.qtype == "MCQ":
                total = len(st.session_state.answers)
                num_correct = sum(1 for a in st.session_state.answers if a["feedback"].get("is_correct"))
                percent = (num_correct / total) * 100 if total else 0
                overall_score = percent
            else:
                overall_score = sum(a["feedback"]["overall_score"] for a in st.session_state.answers) / len(st.session_state.answers)
            interview = {
                "company": st.session_state.company,
                "job_title": st.session_state.job,
                "difficulty": st.session_state.diff,
                "question_type": st.session_state.qtype,
                "date": st.session_state.start_time.strftime("%Y-%m-%d %H:%M"),
                "duration": str(duration).split(".")[0],
                "overall_score": overall_score,
                "answers": st.session_state.answers
            }
            save_interview(st.session_state.username, interview)
            st.markdown(f"#### 📝 Interview Summary for {interview['company']}")
            st.write(f"**Job Title:** {interview['job_title']}")
            st.write(f"**Difficulty:** {interview['difficulty']}")
            st.write(f"**Question Type:** {interview['question_type']}")
            st.write(f"**Date:** {interview['date']}")
            st.write(f"**Duration:** {interview['duration']}")
            if st.session_state.qtype == "MCQ":
                st.write(f"**Score:** {num_correct} / {total} correct ({percent:.1f}%)")
            else:
                st.write(f"**Overall Score:** {overall_score:.1f}/10")
            for idx, ans in enumerate(interview["answers"]):
                st.markdown(f"---\n**Q{idx+1}:** {ans['question']}")
                if st.session_state.qtype == "MCQ":
                    is_correct = ans['feedback'].get('is_correct')
                    correct_option = ans['feedback'].get('correct_option')
                    if is_correct:
                        st.write("✅ **Correct**")
                    else:
                        st.write("❌ **Incorrect**")
                        st.write(f"**Correct Answer:** {correct_option}")
                    st.write(f"**Score:** {ans['feedback']['overall_score']} (1=correct, 0=wrong)")
                else:
                    st.write(f"**Score:** {ans['feedback']['overall_score']}/10")
                st.write("**Feedback:**")
                for imp in ans['feedback']['suggested_improvements']:
                    st.write(f"- {imp}")
                if 'model_answer' in ans['feedback']:
                    st.write("**Model Answer:**")
                    st.write(ans['feedback']['model_answer'])
                # --- Add audio feedback button for all question types ---
                if st.session_state.get("voice_enabled") and get_murf_api():
                    if st.button(f"🔊 Listen to Feedback for Q{idx+1}", key=f"audio_feedback_{idx}"):
                        feedback_text = f"Your score is {ans['feedback']['overall_score']} out of 10. "
                        if ans['feedback']['suggested_improvements']:
                            feedback_text += ' '.join(ans['feedback']['suggested_improvements'])
                        else:
                            feedback_text += "Good job!"
                        audio_bytes = murf_tts(
                            feedback_text,
                            st.session_state.selected_voice
                        )
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3")
            if st.session_state.qtype in ["Theoretical", "Practical"]:
                st.info("Scores for Theoretical and Practical questions are based on answer quality (max 10 per question). Feedback and model answers are provided for improvement.")
            if st.button("Start New Interview", use_container_width=True):
                st.session_state.interview_started = False
                st.rerun()
            # Add back button after interview summary
            back_to_dashboard_button("interview_summary", target_page="dashboard")

def communication_page():
    st.markdown("<h2 style='text-align:center;'>🗣️ One-on-One Communication (HR Interview Chat)</h2>", unsafe_allow_html=True)
    try:
        murf = get_murf_api()
    except Exception as e:
        murf = None
        st.error(f"Error initializing Murf API: {e}")
        return
    if not murf:
        st.error("Please enter your Murf API key in the sidebar for voice features.")
        return

    # --- Session state for HR chat ---
    if "hr_chat_history" not in st.session_state:
        st.session_state.hr_chat_history = []
    if "hr_current_question" not in st.session_state:
        st.session_state.hr_current_question = None
    if "hr_waiting_for_answer" not in st.session_state:
        st.session_state.hr_waiting_for_answer = False
    if "hr_chat_active" not in st.session_state:
        st.session_state.hr_chat_active = False

    # Start HR round button (if not active)
    if not st.session_state.hr_chat_active:
        start_col1, start_col2 = st.columns([2, 2])
        with start_col2:
            if st.button("Start HR Round", key="hr_start_btn", use_container_width=True):
                st.session_state.hr_chat_active = True
                st.session_state.hr_chat_history = []
                st.session_state.hr_current_question = None
                st.session_state.hr_waiting_for_answer = False
                # Immediately fetch the first HR question
                GEMINI_API_KEY = get_gemini_api_key()
                if not GEMINI_API_KEY:
                    st.error("Gemini API key not set. Please set it in the sidebar.")
                    return
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
                prompt = (
                    "You are an HR interviewer for a top company. Ask the user a real-world behavioral or situational interview question. "
                    "Do not answer, only ask a question."
                )
                try:
                    response = model.generate_content(prompt)
                    hr_question = response.text.strip()
                except Exception as e:
                    hr_question = f"[Error from Gemini API: {e}]"
                st.session_state.hr_current_question = hr_question
                st.session_state.hr_waiting_for_answer = True
                st.rerun()
        back_to_dashboard_button("communication_convo", target_page="dashboard")
        return

    # --- Main HR chat flow ---
    if st.session_state.hr_chat_active and st.session_state.hr_waiting_for_answer:
        # Show chat history
        for entry in st.session_state.hr_chat_history:
            st.markdown(f"**HR:** {entry['question']}")
            st.markdown(f"**You:** {entry['answer']}")
            st.markdown(f"**Feedback:** {entry['feedback']}")
            st.markdown("---")
        # Show current question
        st.markdown(f"**HR:** {st.session_state.hr_current_question}")
        # Optionally, play question audio
        if st.button("🔊 Listen to Question", key="hr_listen_q"):
            audio_bytes = murf_tts(st.session_state.hr_current_question)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")
        # User answers: text or .wav upload
        answer = st.text_area("Your Answer (type here)", key="hr_answer_text")
        audio_file = st.file_uploader("Or upload a .wav audio answer", type=["wav"], key="hr_audio_upload")
        transcript = ""
        if audio_file is not None:
            # Transcribe audio using OpenAI Whisper
            try:
                import openai
                openai.api_key = os.getenv("OPENAI_API_KEY")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(audio_file.read())
                    tmp_path = tmp.name
                with open(tmp_path, "rb") as af:
                    transcript_resp = openai.Audio.transcribe("whisper-1", af)
                    transcript = transcript_resp["text"]
                os.remove(tmp_path)
                st.success(f"Transcribed: {transcript}")
            except Exception as e:
                st.error(f"Audio transcription failed: {e}")
        user_final_answer = transcript if transcript else answer
        # Submit answer
        if st.button("Submit Answer", key="hr_submit_btn", use_container_width=True):
            if not user_final_answer.strip():
                st.warning("Please provide an answer (text or audio).")
                st.stop()
            # Get feedback from Gemini
            GEMINI_API_KEY = get_gemini_api_key()
            if not GEMINI_API_KEY:
                st.error("Gemini API key not set. Please set it in the sidebar.")
                st.stop()
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
            feedback_prompt = (
                f"You are an expert HR interviewer. The user answered the following HR interview question.\n"
                f"Question: {st.session_state.hr_current_question}\n"
                f"User's Answer: {user_final_answer}\n"
                "Give detailed, constructive feedback and advice (at least 50 words) on how the user could improve their answer."
            )
            try:
                feedback_resp = model.generate_content(feedback_prompt)
                feedback = feedback_resp.text.strip()
            except Exception as e:
                feedback = f"[Error from Gemini API: {e}]"
            # Save to chat history
            st.session_state.hr_chat_history.append({
                "question": st.session_state.hr_current_question,
                "answer": user_final_answer,
                "feedback": feedback
            })
            st.session_state.hr_waiting_for_answer = False
            st.session_state.hr_last_feedback = feedback
            st.rerun()
        # Stop button
        stop_col1, stop_col2, stop_col3 = st.columns([2,2,2])
        with stop_col2:
            if st.button("Stop", key="hr_stop_btn", use_container_width=True):
                st.session_state.hr_chat_active = False
                st.session_state.hr_chat_history = []
                st.session_state.hr_current_question = None
                st.session_state.hr_waiting_for_answer = False
                st.rerun()
        return

    # --- After feedback, show feedback and Next Question button ---
    if st.session_state.hr_chat_active and not st.session_state.hr_waiting_for_answer:
        last_entry = st.session_state.hr_chat_history[-1] if st.session_state.hr_chat_history else None
        if last_entry:
            st.markdown(f"**HR:** {last_entry['question']}")
            st.markdown(f"**You:** {last_entry['answer']}")
            st.markdown(f"**Feedback:** {last_entry['feedback']}")
        # Next Question button
        next_col1, next_col2, next_col3 = st.columns([2,2,2])
        with next_col2:
            if st.button("Next Question", key="hr_next_btn", use_container_width=True):
                GEMINI_API_KEY = get_gemini_api_key()
                if not GEMINI_API_KEY:
                    st.error("Gemini API key not set. Please set it in the sidebar.")
                    return
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
                prompt = (
                    "You are an HR interviewer for a top company. Ask the user a real-world behavioral or situational interview question. "
                    "Do not answer, only ask a question."
                )
                try:
                    response = model.generate_content(prompt)
                    hr_question = response.text.strip()
                except Exception as e:
                    hr_question = f"[Error from Gemini API: {e}]"
                st.session_state.hr_current_question = hr_question
                st.session_state.hr_waiting_for_answer = True
                st.rerun()
        # Stop button
        stop_col1, stop_col2, stop_col3 = st.columns([2,2,2])
        with stop_col2:
            if st.button("Stop", key="hr_stop_btn2", use_container_width=True):
                st.session_state.hr_chat_active = False
                st.session_state.hr_chat_history = []
                st.session_state.hr_current_question = None
                st.session_state.hr_waiting_for_answer = False
                st.rerun()
        return

    # Back button always at the bottom
    back_to_dashboard_button("communication_convo", target_page="dashboard")

# --- Streamlit Main Page Router ---
if "page" not in st.session_state:
    st.session_state.page = "login"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
# --- Ensure selected_voice is always initialized ---
if "selected_voice" not in st.session_state:
    # Use get_voice_options with a fallback if Murf API is not available
    try:
        murf = get_murf_api()
    except Exception:
        murf = None
    voice_options = get_voice_options(murf)
    st.session_state.selected_voice = list(voice_options.values())[0] if voice_options else "en-US-terrell"
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.page == "dashboard":
    dashboard_page()
elif st.session_state.page == "interview":
    interview_page()
elif st.session_state.page == "communication":
    communication_page()
elif st.session_state.page == "ai_teacher":
    ai_teacher_page()
elif st.session_state.page == "resume_analyzer":
    resume_analyzer_page()
elif st.session_state.page == "voice_settings":
    voice_settings_page()
elif st.session_state.page == "video_summary":
    video_summary_page()
else:
    # Fallback: If page is not recognized, redirect to dashboard
    st.session_state.page = "dashboard"
    st.rerun()