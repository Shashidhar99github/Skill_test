import os
import streamlit as st
import google.generativeai as genai
import sqlite3
import bcrypt
import pandas as pd
from deep_translator import GoogleTranslator
from helpers.new1 import get_quiz_data
from helpers.quiz_utils import string_to_list, get_randomized_options
from apikey import gemini_api_key

# ===============================
# Database Setup
# ===============================
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()

# Optimize SQLite for speed
c.execute("PRAGMA journal_mode=WAL")
c.execute("PRAGMA synchronous=NORMAL")

# Users table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    phone TEXT NOT NULL,
    roll_no TEXT NOT NULL,
    password BLOB NOT NULL,
    name TEXT NOT NULL,
    college TEXT NOT NULL
)
''')

# Marks table
c.execute('''
CREATE TABLE IF NOT EXISTS marks (
    student_email TEXT,
    roll_no TEXT,
    subject TEXT,
    number_of_questions INTEGER,
    marks INTEGER,
    PRIMARY KEY (student_email, subject)
)
''')
conn.commit()

# ===============================
# Authentication
# ===============================
def register_user(email, phone, roll_no, password, name, college):
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        c.execute('''
        INSERT INTO users (email, phone, roll_no, password, name, college)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, phone, roll_no, hashed_pw, name, college))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(email, password):
    c.execute("SELECT password FROM users WHERE email=?", (email,))
    record = c.fetchone()
    if record:
        return bcrypt.checkpw(password.encode('utf-8'), record[0])
    return False

# ===============================
# Configure Gemini API
# ===============================
os.environ["GOOGLE_API_KEY"] = gemini_api_key
genai.configure(api_key=gemini_api_key)

# ===============================
# Streamlit UI Setup
# ===============================
st.set_page_config("QuizBuddy", page_icon="🌿", layout="wide")
st.markdown("""
<style>
body {background: linear-gradient(to bottom right, #e0f7fa, #e8f5e9);}
.block-container {background-color:#ffffffcc;border-radius:20px;padding:2rem 3rem;box-shadow:0px 8px 30px rgba(0,0,0,0.1);}
h1,h2,h3{text-align:center;color:#0B6623;font-family:'Segoe UI', sans-serif;}
div[data-testid="stButton"]>button {background:linear-gradient(90deg,#22c55e,#16a34a);color:white;border-radius:12px;padding:0.6rem 1.5rem;font-weight:600;transition: transform 0.2s;}
div[data-testid="stButton"]>button:hover {transform: scale(1.05);background:linear-gradient(90deg,#16a34a,#15803d);}
.radio-card {background-color:#d1fae5;border-radius:15px;padding:0.5rem 1rem;margin-bottom:0.5rem;cursor:pointer;transition:all 0.2s;}
.radio-card:hover {background-color:#22c55e;color:white;}
</style>
""", unsafe_allow_html=True)

st.title("🌿 :green[QuizBuddy] — Learn. Quiz. Practice 🧠")

# ===============================
# Session State Defaults
# ===============================
for key, value in {
    "logged_in": False,
    "is_admin": False,
    "email": None,
    "language": "English",
    "quiz_data_list": [],
    "user_answers": [],
    "correct_answers": [],
    "translated_questions": [],
    "explanations": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ===============================
# Cached Functions
# ===============================
@st.cache_data
def get_all_students():
    c.execute("SELECT email, phone, roll_no, name, college FROM users")
    return c.fetchall()

@st.cache_data
def get_all_marks():
    c.execute("SELECT student_email, roll_no, subject, number_of_questions, marks FROM marks")
    return c.fetchall()

@st.cache_data
def generate_quiz(skill, level, topic, num_questions):
    quiz_data_str = get_quiz_data(skill, level, topic, str(num_questions))
    return string_to_list(quiz_data_str)

def translate_text_cached(text, target_lang):
    key = f"{text}_{target_lang}"
    if key not in st.session_state:
        if target_lang=="English" or not text.strip():
            st.session_state[key] = text
        else:
            lang_map={"Telugu":"te","Tamil":"ta","Hindi":"hi"}
            try:
                st.session_state[key] = GoogleTranslator(source="auto", target=lang_map.get(target_lang,"en")).translate(text)
            except:
                st.session_state[key] = text
    return st.session_state[key]

# ===============================
# Admin Portal
# ===============================
def admin_portal():
    st.header("🧑‍💼 Admin Dashboard")
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.session_state.email = None
        st.stop()

    # ---------- Registered Students ----------
    st.subheader("📋 Registered Students")
    students = get_all_students()
    if students:
        df_students = pd.DataFrame(students, columns=["Email", "Phone", "Roll Number", "Name", "College"])
        st.dataframe(df_students)

        st.markdown("### Delete a Student")
        student_to_delete = st.selectbox("Select student to delete", df_students['Email'].tolist())
        if st.button("🗑️ Delete Student"):
            c.execute("DELETE FROM users WHERE email=?", (student_to_delete,))
            c.execute("DELETE FROM marks WHERE student_email=?", (student_to_delete,))
            conn.commit()
            st.success(f"Deleted student: {student_to_delete}")
            # Clear caches
            get_all_students.clear()
            get_all_marks.clear()
            st.stop()
    else:
        st.info("No students registered yet.")

    st.divider()

    # ---------- Student Scores ----------
    st.subheader("📊 Student Scores")
    marks = get_all_marks()
    if marks:
        df_marks = pd.DataFrame(marks, columns=["Student Email", "Roll Number", "Subject", "Number of Questions", "Marks"])
        st.dataframe(df_marks)

        st.markdown("### Delete Student Marks")
        mark_to_delete = st.selectbox("Select student email to delete marks", df_marks['Student Email'].unique().tolist())
        subject_to_delete = st.selectbox("Select subject", df_marks[df_marks['Student Email'] == mark_to_delete]['Subject'].tolist())
        if st.button("🗑️ Delete Marks"):
            c.execute("DELETE FROM marks WHERE student_email=? AND subject=?", (mark_to_delete, subject_to_delete))
            conn.commit()
            st.success(f"Deleted marks for {mark_to_delete} ({subject_to_delete})")
            # Clear caches
            get_all_marks.clear()
            st.stop()
    else:
        st.info("No marks data available.")

# ===============================
# Student Portal
# ===============================
def student_portal():
    st.header("🧑‍🎓 Student Portal")
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.stop()

    st.subheader("🌐 Select Quiz Language")
    st.session_state.language = st.selectbox(
        "Choose language", ["English","Telugu","Tamil","Hindi"],
        index=["English","Telugu","Tamil","Hindi"].index(st.session_state.language)
    )

    st.subheader("🧩 Generate Your Quiz")
    with st.form("quiz_form_input"):
        col1,col2=st.columns(2)
        skill=col1.text_input("Skill")
        topic=col2.text_input("Topic in Skill")
        col3,col4=st.columns(2)
        level=col3.selectbox("Skill Level", ["Beginner","Intermediate","Advanced"])
        num_questions=col4.number_input("Number of Questions", value=5, min_value=1)
        submitted=st.form_submit_button("Generate Quiz")

    if submitted:
        with st.spinner("Generating quiz..."):
            st.session_state.quiz_data_list = generate_quiz(skill, level, topic, num_questions)
            st.session_state.user_answers = [None]*len(st.session_state.quiz_data_list)
            st.session_state.correct_answers = []
            st.session_state.translated_questions = []
            st.session_state.explanations = []

            for q in st.session_state.quiz_data_list:
                options, correct_answer = get_randomized_options(q[1:])
                explanation = q[-1] if len(q)>2 else "No explanation provided."
                tq = translate_text_cached(q[0], st.session_state.language)
                topts = [translate_text_cached(opt, st.session_state.language) for opt in options]
                tcorr = translate_text_cached(correct_answer, st.session_state.language)
                texp = translate_text_cached(explanation, st.session_state.language)
                st.session_state.translated_questions.append((tq, topts, tcorr))
                st.session_state.correct_answers.append(tcorr)
                st.session_state.explanations.append(texp)

    if st.session_state.quiz_data_list:
        with st.form("quiz_form"):
            st.subheader("🧠 Quiz Time!")
            for i,(q_text,options,_) in enumerate(st.session_state.translated_questions):
                key=f"quiz_q{i}"
                if key not in st.session_state:
                    st.session_state[key] = None
                st.radio(q_text, options, key=key)
            submitted_quiz = st.form_submit_button("Submit My Answers")

            if submitted_quiz:
                user_choices = [st.session_state[f"quiz_q{i}"] for i in range(len(st.session_state.quiz_data_list))]
                correct = st.session_state.correct_answers
                score = sum([1 for i in range(len(correct)) if user_choices[i]==correct[i]])
                st.success(f"✅ Your Score: {score}/{len(correct)}")

                st.subheader("📖 Detailed Explanation")
                for i, (q_text, options, correct_answer) in enumerate(st.session_state.translated_questions):
                    st.markdown(f"**Q{i+1}: {q_text}**")
                    st.markdown(f"- **Your Answer:** {user_choices[i]}")
                    st.markdown(f"- **Correct Answer:** {correct_answer}")
                    st.markdown(f"- **Explanation:** {st.session_state.explanations[i]}")
                    st.divider()

                # Save marks
                c.execute('''
                    INSERT OR REPLACE INTO marks (student_email, roll_no, subject, number_of_questions, marks)
                    VALUES (?, ?, ?, ?, ?)
                ''',(st.session_state.email,"N/A",topic,len(st.session_state.quiz_data_list),score))
                conn.commit()
                # Clear marks cache
                get_all_marks.clear()

# ===============================
# Login/Register
# ===============================
if not st.session_state.logged_in:
    tab1,tab2 = st.tabs(["🔑 Login","📝 Register"])
    with tab1:
        email = st.text_input("Email ID")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if email=="admin@admin.com" and password=="admin123":
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.success("Welcome Admin!")
                st.stop()
            elif authenticate_user(email,password):
                st.session_state.logged_in = True
                st.session_state.email = email
                st.session_state.is_admin = False
                st.success("Login successful!")
                st.stop()
            else:
                st.error("Invalid email or password.")

    with tab2:
        name = st.text_input("Full Name")
        email = st.text_input("Email ID", key="reg_email")
        phone = st.text_input("Phone Number")
        roll_no = st.text_input("Roll Number")
        college = st.text_input("College Name")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register"):
            if register_user(email, phone, roll_no, password, name, college):
                st.success("Registration successful! Please login.")
                # Clear student cache
                get_all_students.clear()
            else:
                st.error("Email already registered.")
    st.stop()

# ===============================
# Routing
# ===============================
if st.session_state.is_admin:
    admin_portal()
elif st.session_state.logged_in:
    student_portal()
else:
    st.info("Please log in or register to continue.")
