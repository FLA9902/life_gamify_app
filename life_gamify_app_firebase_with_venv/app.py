import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import os
import firebase_admin
from firebase_admin import credentials, db

# Firebase project config
API_KEY = "AIzaSyAfc-XS006oylA3Eh96xvzw_CfsRlY_i6M"
DATABASE_URL = "https://gameify-life-8b668-default-rtdb.europe-west1.firebasedatabase.app/"
import json
import tempfile

if "FIREBASE_KEY_JSON" in st.secrets:
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write(st.secrets["FIREBASE_KEY_JSON"])
        FIREBASE_KEY_FILE = f.name

# Init Firebase Admin for DB access
if os.path.exists(FIREBASE_KEY_FILE) and not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_FILE)
    firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

# Authentication REST endpoints
FIREBASE_SIGNUP = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
FIREBASE_SIGNIN = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"

# Default data template
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

def xp_to_next_level(level):
    return int(100 * (level ** 1.5))

def gain_xp(data, amount):
    data["xp"] += amount
    while data["xp"] >= xp_to_next_level(data["level"]):
        data["xp"] -= xp_to_next_level(data["level"])
        data["level"] += 1

def update_streak(data):
    today = datetime.today().date()
    last = datetime.strptime(data["last_task_date"], "%Y-%m-%d").date() if data["last_task_date"] else None
    if last:
        if today == last + timedelta(days=1):
            data["streak"] += 1
        elif today > last + timedelta(days=1):
            data["streak"] = 1
    else:
        data["streak"] = 1
    data["last_task_date"] = today.isoformat()

# Auth + user session
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "id_token" not in st.session_state:
    st.session_state.id_token = None
if "user_data" not in st.session_state:
    st.session_state.user_data = default_user_data()

# UI Login/Register
st.title("🎮 LevelUp Life (Firebase REST)")
if not st.session_state.user_id:
    login_tab, register_tab = st.tabs(["🔐 Login", "🆕 Register"])

    with login_tab:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            resp = requests.post(FIREBASE_SIGNIN, json={"email": email, "password": password, "returnSecureToken": True})
            if resp.ok:
                data = resp.json()
                st.session_state.user_id = data["localId"]
                st.session_state.id_token = data["idToken"]
                user_ref = db.reference(f"users/{data['localId']}")
                st.session_state.user_data = user_ref.get() or default_user_data()
                st.experimental_rerun()
            else:
                st.error("Login failed.")

    with register_tab:
        email = st.text_input("New Email")
        password = st.text_input("New Password", type="password")
        if st.button("Register"):
            resp = requests.post(FIREBASE_SIGNUP, json={"email": email, "password": password, "returnSecureToken": True})
            if resp.ok:
                st.success("Registered! Please login.")
            else:
                st.error("Registration failed.")

else:
    user_data = st.session_state.user_data
    uid = st.session_state.user_id

    st.sidebar.title("👤 Profile")
    avatars = ["🐱", "🐸", "🦄", "🐢", "🐳"]
    selected_avatar = st.sidebar.selectbox("Avatar", avatars, index=avatars.index(user_data["avatar"]))
    user_data["avatar"] = selected_avatar

    st.sidebar.markdown(f"### {user_data['avatar']} Level {user_data['level']}")
    st.sidebar.progress(user_data["xp"] / xp_to_next_level(user_data["level"]))
    st.sidebar.text(f"XP: {user_data['xp']} / {xp_to_next_level(user_data['level'])}")
    st.sidebar.text(f"Coins: {user_data['coins']}")
    st.sidebar.text(f"🔥 Streak: {user_data['streak']} days")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Home", "📜 History", "🛒 Shop", "📈 Stats", "🚪 Logout"])

    with tab1:
        st.header("🧠 Today's Tasks")
        if st.button("➕ Add Habit"):
            user_data["tasks"].append({"title": "New Habit", "type": "habit", "completed": False})
        if st.button("➕ Add Goal"):
            user_data["tasks"].append({"title": "New Goal", "type": "goal", "completed": False})
        for task in user_data["tasks"]:
            if not task["completed"]:
                if st.button(f"✅ {task['title']}"):
                    task["completed"] = True
                    gain_xp(user_data, 50)
                    user_data["coins"] += 10
                    update_streak(user_data)
                    user_data["history"].append({"title": task["title"], "date": datetime.now().strftime("%Y-%m-%d")})

    with tab2:
        st.header("🕒 Task History")
        if user_data["history"]:
            df = pd.DataFrame(user_data["history"])
            st.dataframe(df)
        else:
            st.info("No completed tasks yet.")

    with tab3:
        st.header("🛍️ Avatar Shop")
        shop_items = [{"emoji": "🧙", "price": 50}, {"emoji": "🦊", "price": 100}]
        for item in shop_items:
            owned = item["emoji"] in user_data["purchased_avatars"]
            col1, col2 = st.columns([1, 2])
            col1.markdown(f"### {item['emoji']}")
            if owned:
                col2.success("Owned")
            elif user_data["coins"] >= item["price"]:
                if col2.button(f"Buy for {item['price']} coins", key=item["emoji"]):
                    user_data["coins"] -= item["price"]
                    user_data["purchased_avatars"].append(item["emoji"])
            else:
                col2.warning("Not enough coins")

    with tab4:
        st.header("📊 Weekly XP Chart")
        df = pd.DataFrame(user_data["history"])
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            weekly = df.groupby(df["date"].dt.day_name()).count()["title"]
            st.bar_chart(weekly)
        else:
            st.info("No data yet")

    with tab5:
        if st.button("Logout"):
            st.session_state.user_id = None
            st.session_state.id_token = None
            st.session_state.user_data = default_user_data()
            st.success("Logged out")
            st.experimental_rerun()

    db.reference(f"users/{uid}").set(user_data)
