import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import os

import pyrebase
import firebase_admin
from firebase_admin import credentials, db

# Firebase configuration (you must provide your actual config here)
firebase_config = {
    "apiKey": "your-api-key",
    "authDomain": "your-project.firebaseapp.com",
    "databaseURL": "https://your-project.firebaseio.com",
    "storageBucket": "your-project.appspot.com"
}

FIREBASE_KEY_PATH = "firebase_key.json"

# Initialize pyrebase for auth
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# Initialize firebase-admin for database
if os.path.exists(FIREBASE_KEY_PATH) and not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred, {'databaseURL': firebase_config["databaseURL"]})

# Default user data template
def default_user_data():
    return {
        "xp": 0,
        "coins": 0,
        "level": 1,
        "streak": 0,
        "last_task_date": "",
        "avatar": "🐱",
        "tasks": [],
        "history": [],
        "purchased_avatars": []
    }

# Firebase helpers
def fetch_user_data(user_id):
    ref = db.reference(f"users/{user_id}")
    data = ref.get()
    return data if data else default_user_data()

def save_user_data(user_id, data):
    ref = db.reference(f"users/{user_id}")
    ref.set(data)

# XP logic
def xp_to_next_level(level):
    return int(100 * (level ** 1.5))

def gain_xp(user_data, amount):
    user_data["xp"] += amount
    while user_data["xp"] >= xp_to_next_level(user_data["level"]):
        user_data["xp"] -= xp_to_next_level(user_data["level"])
        user_data["level"] += 1

def update_streak(user_data):
    today = datetime.today().date()
    last_date = datetime.strptime(user_data["last_task_date"], "%Y-%m-%d").date() if user_data["last_task_date"] else None
    if last_date:
        if today == last_date + timedelta(days=1):
            user_data["streak"] += 1
        elif today > last_date + timedelta(days=1):
            user_data["streak"] = 1
    else:
        user_data["streak"] = 1
    user_data["last_task_date"] = today.isoformat()

# Session state
if "user" not in st.session_state:
    st.session_state.user = None
if "user_data" not in st.session_state:
    st.session_state.user_data = default_user_data()

# Login/Register UI
st.title("🚀 LevelUp Life - Web")
st.markdown("Gamify your goals and habits!")

if not st.session_state.user:
    login_tab, register_tab = st.tabs(["🔐 Login", "🆕 Register"])

    with login_tab:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                st.success("Logged in!")
                st.session_state.user = user
                st.session_state.user_data = fetch_user_data(user["localId"])
                st.experimental_rerun()
            except:
                st.error("Login failed.")

    with register_tab:
        email = st.text_input("New Email")
        password = st.text_input("New Password", type="password")
        if st.button("Register"):
            try:
                user = auth.create_user_with_email_and_password(email, password)
                st.success("Registered! Please login.")
            except:
                st.error("Registration failed.")

else:
    user = st.session_state.user
    data = st.session_state.user_data

    st.sidebar.title("👤 Profile")
    avatars = ["🐱", "🐸", "🦄", "🐢", "🐳"]
    selected_avatar = st.sidebar.selectbox("Avatar", avatars, index=avatars.index(data["avatar"]))
    data["avatar"] = selected_avatar

    st.sidebar.markdown(f"### {data['avatar']} Level {data['level']}")
    st.sidebar.progress(data["xp"] / xp_to_next_level(data["level"]))
    st.sidebar.text(f"XP: {data['xp']} / {xp_to_next_level(data['level'])}")
    st.sidebar.text(f"Coins: {data['coins']}")
    st.sidebar.text(f"🔥 Streak: {data['streak']} days")

    tabs = st.tabs(["🏠 Home", "📜 History", "🛒 Shop", "📈 Stats", "🔔 Reminder", "🚪 Logout"])

    with tabs[0]:
        st.header("🧠 Tasks")
        if st.button("➕ Add Habit"):
            data["tasks"].append({"title": "New Habit", "type": "habit", "completed": False})
        if st.button("➕ Add Goal"):
            data["tasks"].append({"title": "New Goal", "type": "goal", "completed": False})
        for task in data["tasks"]:
            if not task["completed"]:
                if st.button(f"✅ {task['title']}"):
                    task["completed"] = True
                    gain_xp(data, 50)
                    data["coins"] += 10
                    update_streak(data)
                    data["history"].append({
                        "title": task["title"],
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })

    with tabs[1]:
        st.header("🕒 Task History")
        if data["history"]:
            st.dataframe(pd.DataFrame(data["history"]))
        else:
            st.info("No completed tasks yet.")

    with tabs[2]:
        st.header("🛍️ Shop")
        shop_items = [{"emoji": "🧙", "price": 50}, {"emoji": "🦊", "price": 100}]
        for item in shop_items:
            owned = item["emoji"] in data["purchased_avatars"]
            col1, col2 = st.columns([1, 2])
            col1.markdown(f"### {item['emoji']}")
            if owned:
                col2.success("Owned")
            elif data["coins"] >= item["price"]:
                if col2.button(f"Buy for {item['price']} coins", key=item["emoji"]):
                    data["coins"] -= item["price"]
                    data["purchased_avatars"].append(item["emoji"])
            else:
                col2.warning("Not enough coins")

    with tabs[3]:
        st.header("📊 Weekly XP Chart")
        df = pd.DataFrame(data["history"])
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            weekly = df.groupby(df["date"].dt.day_name()).count()["title"]
            st.bar_chart(weekly)
        else:
            st.info("No data yet")

    with tabs[4]:
        st.header("🔔 Reminders")
        if st.button("Send Daily Reminder"):
            st.toast("🌟 Time to level up your life!")

    with tabs[5]:
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.user_data = default_user_data()
            st.success("Logged out")
            st.experimental_rerun()

    save_user_data(user["localId"], data)
