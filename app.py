import streamlit as st
import pandas as pd
from fpdf import FPDF

# Funzione per creare il PDF gestendo i caratteri speciali
def crea_pdf_cdu(cdu, presidio, lista_kit_dati):
    pdf = FPDF()
    pdf.add_page()
    
    def safe_str(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt=safe_str(f"PRESIDIO: {presidio} - CDU: {cdu}"), ln=True, align='C')
    pdf.ln(10)
    
    for nome_kit, df_comp in lista_kit_dati:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt=safe_str(f"Kit: {nome_kit}"), ln=True)
        
        # Intestazione tabella
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 10, "FABBRICANTE", border=1)
        pdf.cell(40, 10, "CODICE", border=1)
        pdf.cell(110, 10, "DESCRIZIONE", border=1)
        pdf.ln()
        
        # Dati tabella
        pdf.set_font("Arial", '', 9)
        for _, row in df_comp.iterrows():
            # Usiamo multi_cell o controlliamo l'altezza per evitare che il testo esca
            pdf.cell(40, 10, safe_str(row.get('FABBRICANTE', '')), border=1)
            pdf.cell(40, 10, safe_str(row.get('CODICE', '')), border=1)
            pdf.cell(110, 10, safe_str(row.get('DESCRIZIONE', '')), border=1)
            pdf.ln()
        pdf.ln(10) # Spazio tra un kit e l'altro
    
    return pdf.output(dest='S').encode('latin-1')

# Configurazione Pagina
st.set_page_config(page_title="Generatore Distinte", layout="wide")
st.title("📦 Generatore Distinte Kit Chirurgici")

# Caricamento file
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
    
    for cdu, group in df_filtered.groupby('CDU_FINALE'):
        st.markdown("---")
        st.subheader(f"CDU: {cdu}")
        
        lista_kit_per_pdf = []
        for _, row in group.iterrows():
            nome_kit = row['NUOVO NOME KIT'] if pd.notna(row.get('NUOVO NOME KIT')) else row.get('NOME KIT', 'N/A')
            st.write(f"**Kit:** {nome_kit}")
            
            comp = df_comp[df_comp['NOME KIT'] == row['NOME KIT']]
            st.table(comp[['FABBRICANTE', 'CODICE', 'DESCRIZIONE']])
            lista_kit_per_pdf.append((nome_kit, comp))
        
        # Bottone per scaricare l'intero CDU
        pdf_data = crea_pdf_cdu(cdu, selected_sigla, lista_kit_per_pdf)
        st.download_button(
            label=f"📥 Scarica PDF CDU: {cdu}",
            data=pdf_data,
            file_name=f"{selected_sigla}_{cdu}.pdf",
            mime="application/pdf"
        )
