"""Simple Streamlit chat for Interview Coach."""

import sys
import streamlit as st
from interview_coach.graph import InterviewSession
from interview_coach.schemas import CandidateProfile


def log(msg: str):
    """Print to terminal (bypasses Streamlit's stdout capture)."""
    print(msg, file=sys.stderr, flush=True)


st.title("Interview Coach")

# Форма профиля (один раз в начале)
if "session" not in st.session_state:
    with st.form("profile"):
        name = st.text_input("Имя", "Алекс")
        role = st.selectbox("Позиция", ["Backend Developer", "ML Engineer", "Frontend Developer"])
        grade = st.selectbox("Уровень", ["Junior", "Middle", "Senior"])
        if st.form_submit_button("Начать интервью"):
            profile = CandidateProfile(name=name, role=role, grade_target=grade, experience="")
            st.session_state.session = InterviewSession(profile)
            st.session_state.messages = []
            log(f"\n{'='*60}")
            log(f"🎤 Новое интервью: {name} ({role}, {grade})")
            log(f"{'='*60}")
            st.rerun()

# Чат
if "session" in st.session_state:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    if prompt := st.chat_input("Ваш ответ"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        log(f"\n👤 User: {prompt}")
        
        with st.chat_message("assistant"):
            with st.spinner("Думаю..."):
                response = st.session_state.session.process_message(prompt)
            st.write(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        log(f"\n🤖 Interviewer: {response}")
        
        # Log internal thoughts
        session = st.session_state.session
        if session.state.turns:
            last_turn = session.state.turns[-1]
            log(f"\n📝 Internal thoughts:\n{last_turn.internal_thoughts}")
            log(f"   Difficulty: {session.state.difficulty}, Topic: {last_turn.topic}")
        
        if session.is_finished():
            st.success("Интервью завершено!")
            feedback = session.get_final_feedback()
            st.markdown(feedback)
            path = session.save_log()
            log(f"\n{'='*60}")
            log(f"✅ Интервью завершено. Лог: {path}")
            log(f"{'='*60}")
