import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# ==================================================
# CONFIG STREAMLIT
# ==================================================
st.set_page_config(page_title="Dashboard Sécurité", layout="wide")

# ==================================================
# AUTO REFRESH (STREAMLIT CLOUD - FIABLE)
# ==================================================
REFRESH_INTERVAL = 60  # secondes

st.markdown(
    f"<meta http-equiv='refresh' content='{REFRESH_INTERVAL}'>",
    unsafe_allow_html=True
)


# ==================================================
# API CONFIG (NODE-RED)
# ==================================================
BASE_URL = "https://nodered.ruina.work.gd"

URL_LOGS = f"{BASE_URL}/api/access_logs"
URL_ENV  = f"{BASE_URL}/api/env"
URL_CMD  = f"{BASE_URL}/api/cmd"

# ==================================================
# API HELPERS
# ==================================================
@st.cache_data(ttl=2)
def get_json(url):
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()

def post_cmd(cmd):
    r = requests.post(URL_CMD, json={"cmd": cmd}, timeout=5)
    r.raise_for_status()
    return True

# ==================================================
# DATA FETCH
# ==================================================
try:
    logs = get_json(URL_LOGS)
except Exception as e:
    st.error(f"Erreur API logs: {e}")
    st.stop()

try:
    env = get_json(URL_ENV)
except Exception as e:
    st.error(f"Erreur API environnement: {e}")
    env = None

# ==================================================
# DATAFRAMES
# ==================================================
if not logs:
    st.warning("Aucune donnée disponible")
    st.stop()

df = pd.DataFrame(logs)
df["timestamp"] = pd.to_datetime(df["timestamp"])

if env:
    df_env = pd.DataFrame([env])
    df_env["timestamp"] = pd.to_datetime(df_env["timestamp"], unit="ms")
else:
    df_env = pd.DataFrame(columns=["timestamp", "temp", "hum", "lum", "mq", "fire"])

# ==================================================
# UI
# ==================================================
st.title("📊 Dashboard Chambre Forte")
st.caption("🔄 Rafraîchissement automatique toutes les 2 secondes")

tab1, tab2 = st.tabs(["Contrôle et Historique", "Données Environnementales"])

# ==================================================
# TAB 1 - CONTROLE + HISTORIQUE
# ==================================================
with tab1:
    st.subheader("🎛️ Contrôle ESP32")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        if st.button("🔴 LED ROUGE"):
            post_cmd("LED_ROUGE")
            st.success("Commande envoyée")

    with c2:
        if st.button("🟢 LED VERTE"):
            post_cmd("LED_VERTE")
            st.success("Commande envoyée")

    with c3:
        if st.button("🚪 OUVRIR PORTE"):
            post_cmd("OPEN")
            st.success("Commande envoyée")

    with c4:
        if st.button("🚪 FERMER PORTE"):
            post_cmd("CLOSE")
            st.success("Commande envoyée")

    with c5:  # Nouveau bouton pour reset
        if st.button("🔄 Redémarrage"):
            post_cmd("RESET")
            st.success("Commande de redémarrage envoyée")

    st.divider()

    # ETAT ACTUEL
    dernier = df.sort_values("timestamp").iloc[-1]
    etat_porte = dernier["porte"]
    etat_led = dernier["led"]

    col1, col2 = st.columns(2)

    with col1:
        if etat_porte == "OUVERTE":
            st.markdown("<h1 style='color:green;'>🟢 PORTE OUVERTE</h1>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='color:red;'>🔴 PORTE FERMÉE</h1>", unsafe_allow_html=True)

    with col2:
        colors = {"VERTE": "green", "ROUGE": "red", "ORANGE": "orange", "BLANC": "gray"}
        color = colors.get(etat_led, "gray")
        st.markdown(f"<h1 style='color:{color};'>💡 LED {etat_led}</h1>", unsafe_allow_html=True)

    st.divider()

    # STATS
    st.subheader("📈 Statistiques")
    st.metric("Nombre d'ouvertures", len(df[df["porte"] == "OUVERTE"]))

    # HISTORIQUE
    st.subheader("📜 Historique des badges")
    st.dataframe(
        df[["timestamp", "uid", "porte", "led"]]
        .sort_values(by="timestamp", ascending=False),
        use_container_width=True
    )

    # GRAPH
    st.subheader("📊 Nombre d'ouvertures par badge")
    st.bar_chart(df[df["porte"] == "OUVERTE"]["uid"].value_counts())

# ==================================================
# TAB 2 - ENVIRONNEMENT
# ==================================================
with tab2:
    st.subheader("🌡️ Données Environnementales")

    if not df_env.empty:
        dernier_env = df_env.sort_values("timestamp").iloc[-1]

        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric("Température (°C)", dernier_env["temp"])
        e2.metric("Humidité (%)", dernier_env["hum"])
        e3.metric("Luminosité", dernier_env["lum"])
        e4.metric("Qualité Air (MQ)", dernier_env["mq"])
        e5.metric("Feu", dernier_env["fire"])

        st.subheader("📜 Historique")
        st.dataframe(
            df_env.sort_values(by="timestamp", ascending=False),
            use_container_width=True
        )

        st.subheader("📉 Température")
        st.line_chart(df_env.set_index("timestamp")["temp"])

        st.subheader("📉 Humidité")
        st.line_chart(df_env.set_index("timestamp")["hum"])
    else:
        st.warning("Aucune donnée environnementale disponible.")
