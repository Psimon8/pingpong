import streamlit as st
import sqlite3
import hashlib
import math

# Connexion à la base de données
conn = sqlite3.connect('pingpong.db')
c = conn.cursor()

# Création des tables si elles n'existent pas
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, elo INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS matches
             (id INTEGER PRIMARY KEY, player1 INTEGER, player2 INTEGER, score1 INTEGER, score2 INTEGER)''')
conn.commit()

# Fonction pour calculer le nouveau classement Elo
def calculate_elo(rating1, rating2, score1, score2):
    expected1 = 1 / (1 + math.pow(10, (rating2 - rating1) / 400))
    expected2 = 1 / (1 + math.pow(10, (rating1 - rating2) / 400))
    
    result1 = 1 if score1 > score2 else (0.5 if score1 == score2 else 0)
    result2 = 1 - result1
    
    k = 32
    new_rating1 = rating1 + k * (result1 - expected1)
    new_rating2 = rating2 + k * (result2 - expected2)
    
    return round(new_rating1), round(new_rating2)

# Fonction pour hacher le mot de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Fonction pour vérifier les identifiants
def check_credentials(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    return c.fetchone() is not None

# Fonction pour créer un nouvel utilisateur
def create_user(username, password):
    try:
        c.execute("INSERT INTO users (username, password, elo) VALUES (?, ?, 1500)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Fonction pour ajouter un match
def add_match(player1, player2, score1, score2):
    c.execute("SELECT elo FROM users WHERE username=?", (player1,))
    rating1 = c.fetchone()[0]
    c.execute("SELECT elo FROM users WHERE username=?", (player2,))
    rating2 = c.fetchone()[0]
    
    new_rating1, new_rating2 = calculate_elo(rating1, rating2, score1, score2)
    
    c.execute("UPDATE users SET elo=? WHERE username=?", (new_rating1, player1))
    c.execute("UPDATE users SET elo=? WHERE username=?", (new_rating2, player2))
    c.execute("INSERT INTO matches (player1, player2, score1, score2) VALUES (?, ?, ?, ?)",
              (player1, player2, score1, score2))
    conn.commit()

# Interface utilisateur Streamlit
def main():
    st.title("Application de classement Ping-Pong")

    if 'user' not in st.session_state:
        st.session_state.user = None

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
        if st.sidebar.button("Se déconnecter"):
            st.session_state.user = None
            st.experimental_rerun()

        st.subheader("Ajouter un match")
        player1 = st.selectbox("Joueur 1", [user[0] for user in c.execute("SELECT username FROM users").fetchall()])
        player2 = st.selectbox("Joueur 2", [user[0] for user in c.execute("SELECT username FROM users").fetchall() if user[0] != player1])
        score1 = st.number_input("Score Joueur 1", min_value=0, step=1)
        score2 = st.number_input("Score Joueur 2", min_value=0, step=1)
        if st.button("Enregistrer le match"):
            add_match(player1, player2, score1, score2)
            st.success("Match enregistré et classements mis à jour")

        st.subheader("Classement actuel")
        ranking = c.execute("SELECT username, elo FROM users ORDER BY elo DESC").fetchall()
        for i, (player, elo) in enumerate(ranking, 1):
            st.write(f"{i}. {player}: {elo}")

if __name__ == "__main__":
    main()
