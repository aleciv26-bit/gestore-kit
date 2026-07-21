import streamlit as st
import pandas as pd
from fpdf import FPDF
import zipfile
import io
import os

# Funzione per creare il PDF di un singolo CDU (con scelta carta intestata)
def crea_pdf_cdu(cdu, presidio, lista_kit_dati, carta_scelta):
    pdf = FPDF()
    pdf.add_page()
    
    # Se il file della carta intestata scelta esiste su GitHub, lo usa come sfondo
    if carta_scelta and os.path.exists(carta_scelta):
        pdf.image(carta_scelta, x=0, y=0, w=210)
        pdf.set_y(40) # Sposta il testo più in basso per non sovrapporlo all'intestazione
    
    def safe_str(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt=safe_str(f"PRESIDIO: {presidio} - CDU: {cdu}"), ln=True, align='C')
    pdf.ln(5)
    
    for nome_kit, sbs_val, df_comp in lista_kit_dati:
        pdf.set_font("Arial", 'B', 12)
        kit_label = f"Kit: {nome_kit}"
        if sbs_val and str(sbs_val).lower() != 'nan':
            kit_label += f" (SBS: {sbs_val})"
        pdf.cell(0, 8, txt=safe_str(kit_label), ln=True)
        
        # Intestazione tabella (escludendo l'ID)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 7, "FABBRICANTE", border=1)
        pdf.cell(40, 7, "CODICE", border=1)
        pdf.cell(110, 7, "DESCRIZIONE", border=1)
        pdf.ln()
        
        # Dati tabella
        pdf.set_font("Arial", '', 8)
        for _, row in df_comp.iterrows():
            pdf.cell(40, 6, safe_str(row.get('FABBRICANTE', '')), border=1)
            pdf.cell(40, 6, safe_str(row.get('CODICE', '')), border=1)
            pdf.cell(110, 6, safe_str(row.get('DESCRIZIONE', '')), border=1)
            pdf.ln()
        pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1')

# Configurazione Pagina
st.set_page_config(page_title="Generatore Distinte", layout="wide")
st.title("📦 Generatore Distinte Kit Chirurgici")

# Selezione della Carta Intestata
st.sidebar.header("Impostazioni Stampa")
tipo_carta = st.sidebar.selectbox(
    "Seleziona la carta intestata:",
    ["Nessuna", "cartaintestata-HE", "cartaintestata-SIS"]
)

# Mappa la scelta al nome file effettivo (supponendo siano in formato .png)
carta_file = None
if tipo_carta == "cartaintestata-HE":
    carta_file = "cartaintestata-HE.png"
elif tipo_carta == "cartaintestata-SIS":
    carta_file = "cartaintestata-SIS.png"

# Caricamento file Excel
uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_lista = pd.read_excel(xls, sheet_name='LISTA KIT')
    df_comp = pd.read_excel(xls, sheet_name='COMPOSIZIONE KIT')

    # Identificazione colonne QTA dinamica
    qta_cols = [c for c in df_lista.columns if str(c).upper().startswith(('QTA', 'Q.TA'))]
    selected_sigla = st.selectbox("Seleziona il presidio:", qta_cols)
    
    # Filtriamo per quantità > 0
    df_filtered = df_lista[pd.to_numeric(df_lista[selected_sigla], errors='coerce') > 0].copy()
    
    # Raggruppamento per CDU
    df_filtered['CDU_FINALE'] = df_filtered.apply(lambda row: row['NUOVO CDU'] if pd.notna(row.get('NUOVO CDU')) else row.get('CDU', 'N/A'), axis=1)
    
    # Prepariamo una struttura per raccogliere i dati di tutti i CDU
    tutti_i_cdu_dati = {}

    for cdu, group in df_filtered.groupby('CDU_FINALE'):
        lista_kit_per_pdf = []
        for _, row in group.iterrows():
            nome_kit = row['NUOVO NOME KIT'] if pd.notna(row.get('NUOVO NOME KIT')) else row.get('NOME KIT', 'N/A')
            
            # Cerca il valore SBS nel foglio composizione per questo kit
            comp = df_comp[df_comp['NOME KIT'] == row['NOME KIT']].copy()
            sbs_val = ""
            if 'SBS' in comp.columns and not comp['SBS'].dropna().empty:
                sbs_val = comp['SBS'].dropna().iloc[0]
            
            lista_kit_per_pdf.append((nome_kit, sbs_val, comp))
        
        tutti_i_cdu_dati[cdu] = lista_kit_per_pdf

    # --- TASTO SCARICA TUTTI IN ZIP ---
    if tutti_i_cdu_dati:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cdu, kit_data in tutti_i_cdu_dati.items():
                pdf_bytes = crea_pdf_cdu(cdu, selected_sigla, kit_data, carta_file)
                safe_cdu_name = str(cdu).replace("/", "_").replace("\\", "_")
                zip_file.writestr(f"{selected_sigla}_{safe_cdu_name}.pdf", pdf_bytes)
        
        st.markdown("### 📥 Download Globale")
        st.download_button(
            label="📦 Scarica TUTTI i PDF in un archivio ZIP",
            data=zip_buffer.getvalue(),
            file_name=f"Tutti_i_CDU_{selected_sigla}.zip",
            mime="application/zip"
        )
        st.markdown("---")

    # Visualizzazione a schermo per singolo CDU
    for cdu, lista_kit_per_pdf in tutti_i_cdu_dati.items():
        st.subheader(f"CDU: {cdu}")
        
        for nome_kit, sbs_val, comp in lista_kit_per_pdf:
            kit_text = f"**Kit:** {nome_kit}"
            if sbs_val and str(sbs_val).lower() != 'nan':
                kit_text += f" | **SBS:** {sbs_val}"
            st.write(kit_text)
            
            # Mostra la tabella pulita (escludendo l'ID)
            cols_to_show = [c for c in ['FABBRICANTE', 'CODICE', 'DESCRIZIONE'] if c in comp.columns]
            st.table(comp[cols_to_show])
        
        # Bottone singolo CDU
        pdf_data = crea_pdf_cdu(cdu, selected_sigla, lista_kit_per_pdf, carta_file)
        st.download_button(
            label=f"📥 Scarica PDF CDU: {cdu}",
            data=pdf_data,
            file_name=f"{selected_sigla}_{cdu}.pdf",
            mime="application/pdf",
            key=f"btn_{cdu}"
        )
        st.markdown("---")
