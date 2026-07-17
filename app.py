import streamlit as st
import pandas as pd
from fpdf import FPDF

# Funzione per creare il PDF dell'intero CDU
def crea_pdf_cdu(cdu, presidio, lista_kit_dati):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"PRESIDIO: {presidio} - CDU: {cdu}", ln=True, align='C')
    pdf.ln(10)
    
    for nome_kit, df_comp in lista_kit_dati:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=f"Kit: {nome_kit}", ln=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 7, "FABBRICANTE", border=1)
        pdf.cell(40, 7, "CODICE", border=1)
        pdf.cell(110, 7, "DESCRIZIONE", border=1)
        pdf.ln()
        
        pdf.set_font("Arial", '', 9)
        for _, row in df_comp.iterrows():
            pdf.cell(40, 7, str(row.get('FABBRICANTE', '')), border=1)
            pdf.cell(40, 7, str(row.get('CODICE', '')), border=1)
            pdf.cell(110, 7, str(row.get('DESCRIZIONE', '')), border=1)
            pdf.ln()
        pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="Generatore Distinte", layout="wide")
st.title("📦 Generatore Distinte Kit Chirurgici")

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_lista = pd.read_excel(xls, sheet_name='LISTA KIT')
    df_comp = pd.read_excel(xls, sheet_name='COMPOSIZIONE KIT')

    qta_cols = [c for c in df_lista.columns if str(c).upper().startswith(('QTA', 'Q.TA'))]
    selected_sigla = st.selectbox("Seleziona il presidio:", qta_cols)
    
    # Filtriamo per quantità > 0
    df_filtered = df_lista[pd.to_numeric(df_lista[selected_sigla], errors='coerce') > 0].copy()
    
    # Raggruppiamo per CDU (usando la logica di priorità definita)
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
