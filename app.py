import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import firebase_admin
from firebase_admin import credentials, db
import paho.mqtt.publish as publish

# CONFIG
st.set_page_config(page_title="Dashboard Sécurité", layout="wide")
st_autorefresh(interval=3000, key="refresh")  # refresh auto 3s

# MQTT CONFIG
BROKER = "20.19.162.0"  # Utilise la même IP que dans le code ESP32
TOPIC = "salle_forte/commande"

# FIREBASE INIT
if not firebase_admin._apps:
    cred = credentials.Certificate(r"C:\streamlit_dashboard\firebase_key.json")
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://projet-final-dfe85-default-rtdb.europe-west1.firebasedatabase.app/"
    })

ref = db.reference("access_logs")
data = ref.get()

# RÉCUPÉRER LES DONNÉES ENVIRONNEMENTALES (ASSUMONS QU'ELLES SONT STOCKÉES DANS FIREBASE)
ref_env = db.reference("data_logs")  # Nouveau chemin pour les données environnementales
data_env = ref_env.get()

# CONVERTIR EN DATAFRAME POUR LES LOGS D'ACCÈS
if not data:
    st.warning("Aucune donnée dans Firebase")
    st.stop()

df = pd.DataFrame.from_dict(data, orient="index")
df["timestamp"] = pd.to_datetime(df["timestamp"])

# CONVERTIR EN DATAFRAME POUR LES DONNÉES ENVIRONNEMENTALES
if data_env:
    df_env = pd.DataFrame.from_dict(data_env, orient="index")
    df_env["timestamp"] = pd.to_datetime(df_env["timestamp"])
else:
    # Si aucune donnée, créer un DataFrame vide avec les colonnes attendues
    df_env = pd.DataFrame(columns=["timestamp", "temp", "hum", "lum", "mq", "fire"])

# TITRE
st.title(" Dashboard Chambre Forte")

# CRÉER DES ONGLETS POUR SÉPARER LES SECTIONS (UNE "FENÊTRE" POUR LES CONTRÔLES ET UNE AUTRE POUR LES DONNÉES ENVIRONNEMENTALES)
tab1, tab2 = st.tabs(["Contrôle et Historique", "Données Environnementales"])

with tab1:
    # CONTRÔLE ESP32
    st.subheader("Contrôle ESP32")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔴 LED ROUGE"):
            publish.single(TOPIC, "LED_ROUGE", hostname=BROKER)

    with col2:
        if st.button("🟢 LED VERTE"):
            publish.single(TOPIC, "LED_VERTE", hostname=BROKER)

    with col3:
        if st.button(" OUVRIR PORTE"):
            publish.single(TOPIC, "OPEN", hostname=BROKER)

    with col4:
        if st.button(" FERMER PORTE"):
            publish.single(TOPIC, "CLOSE", hostname=BROKER)

    st.markdown("---")

    # ÉTAT ACTUEL
    dernier_etat = df.sort_values("timestamp").iloc[-1]["porte"]
    dernier_led = df.sort_values("timestamp").iloc[-1]["led"]

    col1, col2 = st.columns(2)

    with col1:
        if dernier_etat == "OUVERTE":
            st.markdown("<h1 style='color:green;'>🟢 OUVERTE</h1>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='color:red;'>🔴 FERMÉE</h1>", unsafe_allow_html=True)

    with col2:
        color_dict = {"VERTE":"green", "ROUGE":"red", "ORANGE":"orange", "BLANC":"gray"}
        led_color = color_dict.get(dernier_led, "gray")
        st.markdown(f"<h1 style='color:{led_color};'>💡 {dernier_led}</h1>", unsafe_allow_html=True)

    st.markdown("---")

    # STATISTIQUES
    st.subheader(" Statistiques")

    nb_ouvertures = len(df[df["porte"] == "OUVERTE"])
    st.metric("Nombre d'ouvertures", nb_ouvertures)

    # HISTORIQUE
    st.subheader(" Historique des badges")
    st.dataframe(
        df[["timestamp","uid","porte","led"]]
        .sort_values(by="timestamp", ascending=False),
        use_container_width=True
    )

    # GRAPHIQUE
    st.subheader(" Nombre d'ouvertures par badge")
    st.bar_chart(
        df[df["porte"] == "OUVERTE"]["uid"].value_counts()
    )

with tab2:
    # NOUVELLE SECTION POUR LES DONNÉES ENVIRONNEMENTALES
    st.subheader("Données Environnementales en Temps Réel")
    
    if not df_env.empty:
        # AFFICHER LES DERNIÈRES VALEURS
        dernier_env = df_env.sort_values("timestamp").iloc[-1]
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Température (°C)", f"{dernier_env['temp']}")
        
        with col2:
            st.metric("Humidité (%)", f"{dernier_env['hum']}")
        
        with col3:
            st.metric("Luminosité (lux)", f"{dernier_env['lum']}")
        
        with col4:
            st.metric("Qualité de l'Air (AQI)", f"{dernier_env['mq']}")
        
        with col5:
            st.metric("Feu (0-1)", f"{dernier_env['fire']}")
        
        # HISTORIQUE DES DONNÉES ENVIRONNEMENTALES
        st.subheader("Historique des Données Environnementales")
        st.dataframe(
            df_env[["timestamp", "temp", "hum", "lum", "mq", "fire"]]
            .sort_values(by="timestamp", ascending=False),
            use_container_width=True
        )
        
        # GRAPHIQUES POUR LES DONNÉES ENVIRONNEMENTALES
        st.subheader("Évolution de la Température")
        st.line_chart(df_env.set_index("timestamp")["temp"])
        
        st.subheader("Évolution de l'Humidité")
        st.line_chart(df_env.set_index("timestamp")["hum"])
        
        # Ajouter des graphiques similaires pour luminosité et qualité de l'air si souhaité
    else:
        st.warning("Aucune donnée environnementale disponible dans Firebase.")