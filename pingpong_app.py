import streamlit as st
import hashlib
import math
import pandas as pd
import plotly.express as px
from datetime import datetime
import sqlite3
import os

st.set_page_config(
    layout="wide",
    page_title="PrimeliPong",
    page_icon="🏓"
)

# Ensure the directory for the database file exists
os.makedirs("database", exist_ok=True)

# SQLite database connection
db_path = os.path.join("database", "pingpong.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, 
              username TEXT UNIQUE, 
              password TEXT, 
              elo INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS matches
             (id INTEGER PRIMARY KEY, 
              player1 TEXT, 
              player2 TEXT, 
              score1 INTEGER, 
              score2 INTEGER, 
              new_elo1 INTEGER,
              new_elo2 INTEGER,
              datetime TEXT)''')
conn.commit()

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
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
    return c.fetchone() is not None

def create_user(username, password):
    try:
        hashed_password = hash_password(password)
        c.execute("INSERT INTO users (username, password, elo) VALUES (?, ?, 1500)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def add_match(player1, player2, winner):
    c.execute("SELECT elo FROM users WHERE username=?", (player1,))
    rating1 = c.fetchone()[0]
    c.execute("SELECT elo FROM users WHERE username=?", (player2,))
    rating2 = c.fetchone()[0]
    
    score1 = 1 if winner == player1 else 0
    score2 = 1 - score1
    
    new_rating1, new_rating2 = calculate_elo(rating1, rating2, score1, score2)
    
    c.execute("UPDATE users SET elo=? WHERE username=?", (new_rating1, player1))
    c.execute("UPDATE users SET elo=? WHERE username=?", (new_rating2, player2))
    c.execute("INSERT INTO matches (player1, player2, score1, score2, new_elo1, new_elo2, datetime) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (player1, player2, score1, score2, new_rating1, new_rating2, datetime.now().isoformat()))
    conn.commit()

def delete_last_match():
    c.execute("SELECT id FROM matches ORDER BY datetime DESC LIMIT 1")
    last_match = c.fetchone()
    if last_match:
        c.execute("DELETE FROM matches WHERE id=?", (last_match[0],))
        conn.commit()

def get_user_stats(username):
    c.execute("""
        SELECT 
            COUNT(*) as total_matches,
            SUM(CASE WHEN 
                (player1 = ? AND score1 > score2) OR 
                (player2 = ? AND score2 > score1) 
            THEN 1 ELSE 0 END) as wins
        FROM matches
        WHERE player1 = ? OR player2 = ?
    """, (username, username, username, username))
    result = c.fetchone()
    total_matches, wins = result
    losses = total_matches - wins
    win_rate = (wins / total_matches) * 100 if total_matches > 0 else 0
    loss_rate = 100 - win_rate
    return total_matches, win_rate, loss_rate

def get_elo_history(username):
    c.execute("""
        SELECT 
            CASE 
                WHEN player1 = ? THEN new_elo1
                WHEN player2 = ? THEN new_elo2
            END as elo,
            datetime
        FROM matches
        WHERE player1 = ? OR player2 = ?
        ORDER BY datetime DESC
        LIMIT 10
    """, (username, username, username, username))
    results = c.fetchall()
    df = pd.DataFrame(results, columns=['elo', 'datetime'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df.sort_values('datetime')

def show_performance_view():
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Classement général")
        c.execute("SELECT username, elo FROM users ORDER BY elo DESC")
        ranking = c.fetchall()
        ranking_df = pd.DataFrame(ranking, columns=['username', 'elo']).sort_values(by='elo', ascending=False)
        st.dataframe(ranking_df)
    with col2:
        st.subheader("Statistiques du joueur")
        c.execute("SELECT username FROM users")
        users_list = [row[0] for row in c.fetchall()]
        selected_user = st.selectbox("Sélectionner un joueur", users_list, index=0)
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
    c.execute("SELECT username FROM users")
    users_list = [row[0] for row in c.fetchall()]
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

def show_database_view():
    st.subheader("Visualiser la base de données SQLite")
    # Query all matches from the database
    c.execute("SELECT * FROM matches ORDER BY datetime DESC")
    matches = c.fetchall()
    if matches:
        df = pd.DataFrame(matches, columns=['ID', 'Player1', 'Player2', 'Score1', 'Score2', 'New_Elo1', 'New_Elo2', 'Datetime'])
        st.dataframe(df)
        
        if st.button("Supprimer le dernier match"):
            delete_last_match()
            st.experimental_rerun()
    else:
        st.write("No match data available.")

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
        st.session_state.menu_choice = st.sidebar.radio("Menu", ["Performances", "Ajouter un match", "Visualiser la base de données"])
        if st.sidebar.button("Se déconnecter"):
            st.session_state.user = None
            st.experimental_rerun()
        if st.session_state.menu_choice == "Performances":
            show_performance_view()
        elif st.session_state.menu_choice == "Ajouter un match":
            show_add_match_view()
        elif st.session_state.menu_choice == "Visualiser la base de données":
            show_database_view()

if __name__ == "__main__":
    main()
