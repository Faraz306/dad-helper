import streamlit as st
from sklearn.ensemble import RandomForestClassifier
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones
import pandas as pd
from gtts import gTTS
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
import platform
import sys
from twilio.rest import Client

# 1. Safe refresh mechanism (checks clock every 10 seconds without freezing)
st_autorefresh(interval=10000, key="alarm_counter")

st.title("YF medicine reminder")
st.header("Add medicine")

zones = sorted(available_timezones())
default_index = zones.index("Asia/Kolkata") if "Asia/Kolkata" in zones else 0
timezone = st.selectbox("Choose your timezone 🌍", zones, index=default_index)

patient_name = st.text_input("Enter patient's name")
name = st.text_input("Enter medicine's name")
# Adjusted placeholder to show standard 12-hour formatting with leading zeroes ("08:30 PM")
time_to_eat = st.text_input("Enter the time when you will eat the pill", placeholder="Ex: 08:30 PM")

# Default fallback if machine learning prediction is skipped
result = "Did Not Eat"

if timezone and name and time_to_eat:
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS info(
            name TEXT, 
            time TEXT, 
            pill TEXT, 
            timezone TEXT, 
            taken TEXT
        )
    """)
    conn.commit()

    st.success("Details set up successfully!")

    uploader = st.file_uploader("Enter a file (optional) about user's routine.", type=['CSV', 'TXT'])
    st.text("The cols in the csv should be named: day (1 for Monday, 2 for Tuesday) and ate_or_not")

    if st.button("Save Medicine Entry"):
        cursor.execute(
            "INSERT INTO info (name, time, pill, timezone) VALUES (?, ?, ?, ?)",
            (patient_name, time_to_eat, name, timezone)
        )
        conn.commit()
        st.info("Entry saved to database.")

    if uploader:
        df = pd.read_csv(uploader)
        X = df[['day']]
        y = df['ate_or_not']

        model = RandomForestClassifier()
        model.fit(X, y)

        test_day = pd.DataFrame({'day': [3]})
        prediction = model.predict(test_day)

        result = "Eat" if prediction[0] == 1 else "Did Not Eat"
        st.write(f"Prediction for next day: **{result}**")

    # --- ALARM SYSTEM (Moved outside 'if uploader' so it works dynamically) ---
    st.header("⏰ Medicine Alarm")

    now = datetime.now(ZoneInfo(timezone))
    current_time = now.strftime("%I:%M %p")
    st.write(f"Current Time in your selected zone: `{current_time}`")

    if current_time.strip() == time_to_eat.strip():
        st.warning("⚠️ ALARM ACTIVE!")

        text_to_speak = f"Please eat your medicine {patient_name}. It is {time_to_eat}."

        # Fix: Generate the audio stream buffer using gTTS so st.audio doesn't crash
        tts = gTTS(text=text_to_speak, lang='en')
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        st.audio(audio_buffer, format='audio/mp3', autoplay=True)

        if result == "Did Not Eat":
            # Corrected parameter cases
            text_to_speak = f"Please eat your medicine {patient_name}. It is {time_to_eat}."

            # Fix: Generate the audio stream buffer using gTTS so st.audio doesn't crash
            tts = gTTS(text=text_to_speak, lang='en')
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            st.audio(audio_buffer, format='audio/mp3', autoplay=True)

        else:
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(2000, 1000)
            else:
                sys.stdout.write('\a')
                sys.stdout.flush()

        TAKEN = st.selectbox("Did you take your medicine?", ['Select...', 'Yes', 'No'], key="taken_tracker")
        if TAKEN != 'Select...':
            cursor.execute("INSERT INTO info (taken) VALUES (?)", (TAKEN,))
            conn.commit()
            st.success("Response recorded!")

    conn.close()
