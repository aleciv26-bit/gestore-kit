import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Generatore Distinte", layout="wide")
st.title("📦 Generatore Distinte Kit Chirurgici")

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_lista = pd.read_excel(xls, sheet_name='LISTA KIT')
    
    # Verifica se esiste il foglio composizione, altrimenti gestisci l'errore
    if 'COMPOSIZIONE KIT' in xls.sheet_names:
        df_comp = pd.read_excel(xls, sheet_name='COMPOSIZIONE KIT')
    else:
        st.error("Foglio 'COMPOSIZIONE KIT' non trovato nel file.")
        st.stop()

    # Identificazione dinamica colonne QTA (cerca QTA o Q.TA)
    qta_cols = [c for c in df_lista.columns if str(c).upper().startswith(('QTA', 'Q.TA'))]
    
    if not qta_cols:
        st.error("Nessuna colonna che inizia con 'QTA' o 'Q.TA' trovata nel foglio 'LISTA KIT'.")
        st.stop()
    
    selected_sigla = st.selectbox("Seleziona il presidio:", qta_cols)
    
    # Filtra kit con quantità > 0 (usando to_numeric per sicurezza)
    df_filtered = df_lista[pd.to_numeric(df_lista[selected_sigla], errors='coerce') > 0]
    
    if df_filtered.empty:
        st.warning(f"Nessun kit trovato con quantità > 0 per {selected_sigla}.")
    else:
        for _, row in df_filtered.iterrows():
            # Logica priorità: NUOVO CDU/NOME KIT -> CDU/NOME KIT
            cdu = row['NUOVO CDU'] if 'NUOVO CDU' in row and pd.notna(row['NUOVO CDU']) else row.get('CDU', 'N/A')
            nome_kit = row['NUOVO NOME KIT'] if 'NUOVO NOME KIT' in row and pd.notna(row['NUOVO NOME KIT']) else row.get('NOME KIT', 'N/A')
            
            st.markdown(f"---")
            st.subheader(f"CDU: {cdu}")
            st.write(f"### Kit: {nome_kit}")
            
            # Filtra componenti (collega al NOME KIT originale o nuovo)
            # Nota: assicurati che il nome nel foglio composizione corrisponda
            comp = df_comp[df_comp['NOME KIT'] == row['NOME KIT']]
            
            if not comp.empty:
                # Mostra tabella componenti
                st.table(comp[['FABBRICANTE', 'CODICE', 'DESCRIZIONE']])
            else:
                st.write("Nessun componente trovato per questo kit.")
