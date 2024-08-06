import streamlit as st
import hashlib
import math
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import json
import base64

st.set_page_config(
    layout="wide",
    page_title="PrimeliPong",
    page_icon="🏓"
)

# GitHub configuration
GITHUB_TOKEN = "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"
GITHUB_REPO = "Psimon8/pingpong"
USERS_FILE_PATH = "users.json"
MATCHES_FILE_PATH = "matches.json"

def commit_to_github(file_path, content, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    get_response = requests.get(url, headers=headers)
    if get_response.status_code == 200:
        sha = get_response.json()['sha']
    else:
        sha = None

    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha
    }
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code in [201, 200]:
        return True
    else:
        st.error(f"Failed to commit to GitHub: {response.json()}")
        return False

def read_from_github(file_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode()
        return json.loads(content)
    else:
        return []

# Read data from GitHub
users = read_from_github(USERS_FILE_PATH)
matches = read_from_github(MATCHES_FILE_PATH)

# Save data to GitHub
def save_users_to_github(users):
    commit_to_github(USERS_FILE_PATH, json.dumps(users), "Update users")

def save_matches_to_github(matches):
    commit_to_github(MATCHES_FILE_PATH, json.dumps(matches), "Update matches")

def calculate_elo(rating1, rating2, score1, score2):
    expected1 = 1 / (1 + math.pow(10, (rating2 - rating1) / 400))
    expected2 = 1 / (1 + math.pow(10, (rating1 - rating2) / 400))
    result1 = 1 if score1 > score2 else 0
    result2 = 1 - result1
    k = 32
    new_rating1 = rating1 + k * (result1 - expected1)
    new_rating2 = rating2 + k * (result2 - expected2)
    return round(new_rating1), round(new_rating2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username, password):
    hashed_password = hash_password(password)
    st.write(f"Checking credentials for {username} with hashed password {hashed_password}")
    return any(user['username'] == username and user['password'] == hashed_password for user in users)

def create_user(username, password):
    if any(user['username'] == username for user in users):
        return False
    new_user = {'username': username, 'password': hash_password(password), 'elo': 1500}
    users.append(new_user)
    save_users_to_github(users)
    st.write(f"Created user {username} with hashed password {new_user['password']}")
    return True

def add_match(player1, player2, winner):
    player1_data = next(user for user in users if user['username'] == player1)
    player2_data = next(user for user in users if user['username'] == player2)
    rating1 = player1_data['elo']
    rating2 = player2_data['elo']
    score1 = 1 if winner == player1 else 0
    score2 = 1 - score1
    new_rating1, new_rating2 = calculate_elo(rating1, rating2, score1, score2)
    player1_data['elo'] = new_rating1
    player2_data['elo'] = new_rating2
    new_match = {
        'player1': player1,
        'player2': player2,
        'score1': score1,
        'score2': score2,
        'new_elo1': new_rating1,
        'new_elo2': new_rating2,
        'datetime': datetime.now().isoformat()
    }
    matches.append(new_match)
    save_matches_to_github(matches)
    save_users_to_github(users)

def get_user_stats(username):
    total_matches = len([m for m in matches if m['player1'] == username or m['player2'] == username])
    wins = len([m for m in matches if (m['player1'] == username and m['score1'] > m['score2']) or (m['player2'] == username and m['score2'] > m['score1'])])
    losses = total_matches - wins
    win_rate = (wins / total_matches) * 100 if total_matches > 0 else 0
    loss_rate = 100 - win_rate
    return total_matches, win_rate, loss_rate

def get_elo_history(username):
    history = [(m['new_elo1'] if m['player1'] == username else m['new_elo2'], m['datetime'])
               for m in matches if m['player1'] == username or m['player2'] == username]
    df = pd.DataFrame(history, columns=['elo', 'datetime'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df.sort_values('datetime')

def show_performance_view():
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Classement général")
        ranking_df = pd.DataFrame(users, columns=['username', 'elo']).sort_values(by='elo', ascending=False)
        st.dataframe(ranking_df)
    with col2:
        st.subheader("Statistiques du joueur")
        selected_user = st.selectbox("Sélectionner un joueur", [user['username'] for user in users], index=0)
        total_matches, win_rate, loss_rate = get_user_stats(selected_user)
        st.write(f"Nombre total de matchs : {total_matches}")
        fig_pie = px.pie(values=[win_rate, loss_rate], names=['Victoires', 'Défaites'], title=f"Taux de victoire/défaite de {selected_user}")
        st.plotly_chart(fig_pie)
        elo_history = get_elo_history(selected_user)
        if not elo_history.empty:
            fig_line = px.line(elo_history, x='datetime', y='elo', title=f"Évolution de l'ELO de {selected_user} (10 derniers matchs)")
            st.plotly_chart(fig_line)
        else:
            st.write("Pas assez de données pour afficher l'évolution de l'ELO.")

def show_add_match_view():
    st.subheader("Ajouter un match")
    users_list = [user['username'] for user in users]
    col1, col2 = st.columns(2)
    with col1:
        player1 = st.selectbox("Joueur 1", users_list)
    with col2:
        player1_result = st.radio("Résultat Joueur 1", ["Victoire", "Défaite"], horizontal=True)
    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        player2 = st.selectbox("Joueur 2", [u for u in users_list if u != player1])
    with col4:
        player2_result = "Défaite" if player1_result == "Victoire" else "Victoire"
        st.write(f"Résultat Joueur 2: {player2_result}")
    if st.button("Enregistrer le match"):
        winner = player1 if player1_result == "Victoire" else player2
        add_match(player1, player2, winner)
        st.success("Match enregistré et classements mis à jour")
        st.session_state.menu_choice = "Performances"
        st.experimental_rerun()

def main():
    st.title("Application de classement Ping-Pong")
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'menu_choice' not in st.session_state:
        st.session_state.menu_choice = "Performances"
    if st.session_state.user is None:
        st.subheader("Connexion / Création de compte")
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
        with col2:
            new_account = st.checkbox("Créer un nouveau compte")
        if new_account:
            if st.button("Créer le compte"):
                if create_user(username, password):
                    st.success("Compte créé avec succès. Vous pouvez maintenant vous connecter.")
                else:
                    st.error("Ce nom d'utilisateur existe déjà")
        else:
            if st.button("Se connecter"):
                if check_credentials(username, password):
                    st.session_state.user = username
                    st.success(f"Connecté en tant que {username}")
                    st.experimental_rerun()
                else:
                    st.error("Identifiants incorrects")
    else:
        st.sidebar.title(f"Bienvenue, {st.session_state.user}")
        st.session_state.menu_choice = st.sidebar.radio("Menu", ["Performances", "Ajouter un match"])
        if st.sidebar.button("Se déconnecter"):
            st.session_state.user = None
            st.experimental_rerun()
        if st.session_state.menu_choice == "Performances":
            show_performance_view()
        elif st.session_state.menu_choice == "Ajouter un match":
            show_add_match_view()

if __name__ == "__main__":
    main()
