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
# 1. Safe refresh mechanism (replaces the broken 'while True' loop)
# This forces Streamlit to safely check the clock every 10 seconds without freezing
st_autorefresh(interval=10000, key="alarm_counter")

st.title("YF medicine reminder")
st.header("Add medicine")

zones = sorted(available_timezones())

default_index = zones.index("Asia/Kolkata") if "Asia/Kolkata" in zones else 0
timezone = st.selectbox("Choose your timezone 🌍", zones, index=default_index)
patient_name = st.text_input("Enter patient's name")
name = st.text_input("Enter medicine's name")
number = st.text_input("Enter your phone number.")

# Adjusted placeholder to show standard 12-hour formatting with leading zeroes ("08:30 PM")
time_to_eat = st.text_input("Enter the time when you will eat the pill", placeholder="Ex: 08:30 PM")

if timezone and name and time_to_eat:
    # Fix 2: Changed 'connection' to 'conn' to match the cursor variables below it
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    # Fix 3: Added missing closing parenthesis to the SQL schema text
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

    # Fix 4: Put database insertion behind a button so it doesn't log duplicates on every refresh pulse
    if st.button("Save Medicine Entry"):
        # Fix 5: Swapped case-sensitive typo 'time_To_eat' out for 'time_to_eat'
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
        st.header("⏰ Medicine Alarm")

        # Fix 6: Check live clock state once per execution loop pass instead of an infinite loop
        now = datetime.now(ZoneInfo(timezone))
        current_time = now.strftime("%I:%M %p")

        st.write(f"Current Time in your selected zone: `{current_time}`")

        ALARM_SOUND_URL = "https://soundhelix.com"

        if current_time.strip() == time_to_eat.strip():
            st.warning("⚠️ ALARM ACTIVE!")

            twilio_account_sid = "ACb3719d7c54b575795c86315072d7b892"
            twillio_account_token = "5ac3d7a69168ef3c564b1cc61bd894db"
            if result == "Did Not Eat":
                text_to_speak = f"Please eat your medicine. It is {time_to_eat}."
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

                twiml_instruction = f"<Response><Say voice='alice'>{text_to_speak}</Say></Response>"

                # Pass the frontend text string variables straight into the API payload loop
                call = client.calls.create(
                    twiml=twiml_instruction,
                    to=user_to_number.strip(),  # Injecting user string dynamically
                    from_=MY_VERIFIED_NUMBER  # The caller ID MUST be your own verified number
                )

                # Added autoplay=True so text-to-speech outputs automatically
                st.audio(audio_buffer, format='audio/mp3', autoplay=True)
            else:
                # Fix 7: Built-in cross-platform audio fallback triggers natively here
                if platform.system() == "Windows":
                    import winsound

                    winsound.Beep(2000, 1000)
                else:
                    sys.stdout.write('\a')
                    sys.stdout.flush()

            # Fix 8: Standardized widget option logic and targeted correct connection methods
            TAKEN = st.selectbox("Did you take your medicine?", ['Select...', 'Yes', 'No'], key="taken_tracker")
            if TAKEN != 'Select...':
                cursor.execute("INSERT INTO info (taken) VALUES (?)", (TAKEN,))
                conn.commit()
                st.success("Response recorded!")
    conn.close()