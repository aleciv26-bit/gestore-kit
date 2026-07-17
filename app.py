import streamlit as st
import pandas as pd
from fpdf import FPDF
import io

# Funzione per creare PDF
def crea_pdf(cdu, nome_kit, df_comp):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"CDU: {cdu}", ln=True, align='L')
    pdf.cell(200, 10, txt=f"Kit: {nome_kit}", ln=True, align='L')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "FABBRICANTE", border=1)
    pdf.cell(40, 10, "CODICE", border=1)
    pdf.cell(110, 10, "DESCRIZIONE", border=1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    for _, row in df_comp.iterrows():
        pdf.cell(40, 10, str(row['FABBRICANTE']), border=1)
        pdf.cell(40, 10, str(row['CODICE']), border=1)
        pdf.cell(110, 10, str(row['DESCRIZIONE']), border=1)
        pdf.ln()
    
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
    
    df_filtered = df_lista[pd.to_numeric(df_lista[selected_sigla], errors='coerce') > 0]
    
    for _, row in df_filtered.iterrows():
        cdu = row.get('CDU', 'N/A')
        nome_kit = row.get('NOME KIT', 'N/A')
        
        st.markdown("---")
        st.subheader(f"CDU: {cdu}")
        st.write(f"### Kit: {nome_kit}")
        
        comp = df_comp[df_comp['NOME KIT'] == row['NOME KIT']]
        st.table(comp[['FABBRICANTE', 'CODICE', 'DESCRIZIONE']])
        
        # Pulsante Download PDF
        pdf_data = crea_pdf(cdu, nome_kit, comp)
        st.download_button(
            label=f"Scarica PDF: {nome_kit}",
            data=pdf_data,
            file_name=f"{nome_kit}.pdf",
            mime="application/pdf"
        )
