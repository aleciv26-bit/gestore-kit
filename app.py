import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Generatore Distinte", layout="wide")
st.title("📦 Generatore Distinte Kit Chirurgici")

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_lista = pd.read_excel(xls, sheet_name='LISTA KIT')
    df_comp = pd.read_excel(xls, sheet_name='COMPOSIZIONE KIT')

    # Pulizia nomi kit per evitare errori di sistema
    def sanitize_filename(name):
        return re.sub(r'[^\w\s-]', '', str(name)).strip().replace(" ", "_")

    # Identificazione colonne Q.TA
    qta_cols = [c for c in df_lista.columns if str(c).startswith('Q.TA')]
    
    selected_sigla = st.selectbox("Seleziona sigla (es. LC, ME)", qta_cols)
    
    # Filtra kit con quantità > 0
    df_filtered = df_lista[df_lista[selected_sigla] > 0]
    
    for _, row in df_filtered.iterrows():
        nome_kit = row['NUOVO NOME KIT'] if pd.notna(row['NUOVO NOME KIT']) else row['NOME KIT']
        st.write(f"### Kit: {nome_kit}")
        
        # Filtra componenti
        comp = df_comp[df_comp['NOME KIT'] == row['NOME KIT']]
        st.table(comp[['FABBRICANTE', 'CODICE', 'DESCRIZIONE']])