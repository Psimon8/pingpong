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

# Fonctions existantes (calculate_elo, hash_password, check_credentials, create_user, add_match)
# ... (garder ces fonctions telles quelles)

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

        # Le reste du code pour l'ajout de match et l'affichage du classement
        # ... (garder cette partie telle quelle)

if __name__ == "__main__":
    main()
