import streamlit as st
import pandas as pd
from fpdf import FPDF
import zipfile
import io
import os

class PDFConCartaIntestata(FPDF):
    def __init__(self, carta_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.carta_file = carta_file

    def header(self):
        if self.carta_file and os.path.exists(self.carta_file):
            self.image(self.carta_file, x=0, y=0, w=210)
        self.set_y(45)

    def footer(self):
        pass

def crea_pdf_cdu(cdu, presidio, lista_kit_dati, carta_file):
    pdf = PDFConCartaIntestata(carta_file=carta_file)
    pdf.set_margins(10, 45, 10)
    pdf.add_page()
    
    def safe_str(text):
        if pd.isna(text):
            return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, txt=safe_str(f"PRESIDIO: {presidio} - CDU: {cdu}"), ln=True, align='C')
    pdf.ln(3)
    
    col_w_fab = 35
    col_w_cod = 35
    col_w_desc = 105
    col_w_qta = 25

    def stampa_intestazione():
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(col_w_fab, 6, "FABBRICANTE", border=1)
        pdf.cell(col_w_cod, 6, "CODICE", border=1)
        pdf.cell(col_w_desc, 6, "DESCRIZIONE", border=1)
        pdf.cell(col_w_qta, 6, "Q.TA", border=1, align='C')
        pdf.ln()

    for nome_kit, sbs_val, df_comp, qta_col_nome in lista_kit_dati:
        if pdf.get_y() > 230:
            pdf.add_page()

        pdf.set_font("Arial", 'B', 11)
        kit_label = f"Kit: {nome_kit}"
        if sbs_val and str(sbs_val).lower() != 'nan' and str(sbs_val).strip() != '':
            kit_label += f" - SBS: {sbs_val}"
        pdf.cell(0, 7, txt=safe_str(kit_label), ln=True)
        
        stampa_intestazione()
        
        pdf.set_font("Arial", '', 8)
        for _, row in df_comp.iterrows():
            fab = safe_str(row.get('FABBRICANTE', ''))
            cod = safe_str(row.get('CODICE', ''))
            desc = safe_str(row.get('DESCRIZIONE', ''))
            qta_val = safe_str(row.get(qta_col_nome, '')) if qta_col_nome else ''

            # Calcolo sicuro delle righe per la descrizione (circa 50 caratteri per riga a 8pt su 105mm)
            chars_per_line = 50
            lines_count = max(1, int(len(desc) / chars_per_line) + (1 if len(desc) % chars_per_line > 0 else 0))
            
            # Altezza dinamica della riga (minimo 6 mm, oppure 4.5 mm per ogni riga di testo)
            row_h = max(6, lines_count * 4.5 + 2)

            if pdf.get_y() + row_h > 245:
                pdf.add_page()
                stampa_intestazione()
                pdf.set_font("Arial", '', 8)

            x_start = pdf.get_x()
            y_start = pdf.get_y()

            # Stampiamo le 4 celle con la stessa altezza 'row_h' in modo che FPDF gestisca i bordi e l'allineamento pulito
            # Per Fabbricante, Codice e Quantità usiamo il trucco di stampare cella con altezza riga e allineamento verticale centrale
            # Poiché FPDF standard non centra verticalmente in cell(), calcoliamo il padding verticale esatto:
            # un'altezza di riga standard o multi-riga viene gestita stampando con coordinate o cella multipla.
            
            # Usiamo multi_cell per la descrizione e cell per le altre con la stessa coordinata Y
            pdf.set_xy(x_start, y_start)
            
            # Salviamo la posizione X iniziale
            current_x = x_start
            
            # Fabbricante
            pdf.rect(current_x, y_start, col_w_fab, row_h)
            pdf.set_xy(current_x, y_start + (row_h - 4) / 2)
            pdf.cell(col_w_fab, 4, fab, border=0, align='L')
            current_x += col_w_fab

            # Codice
            pdf.rect(current_x, y_start, col_w_cod, row_h)
            pdf.set_xy(current_x, y_start + (row_h - 4) / 2)
            pdf.cell(col_w_cod, 4, cod, border=0, align='L')
            current_x += col_w_cod

            # Descrizione (se 1 riga la centriamo perfettamente, se più righe la distendiamo dall'alto con margine leggero)
            pdf.rect(current_x, y_start, col_w_desc, row_h)
            if lines_count <= 1:
                pdf.set_xy(current_x, y_start + (row_h - 4) / 2)
                pdf.cell(col_w_desc, 4, desc, border=0, align='L')
            else:
                pdf.set_xy(current_x, y_start + 1.5)
                pdf.multi_cell(col_w_desc, 4, desc, border=0, align='L')
            current_x += col_w_desc

            # Quantità
            pdf.rect(current_x, y_start, col_w_qta, row_h)
            pdf.set_xy(current_x, y_start + (row_h - 4) / 2)
            pdf.cell(col_w_qta, 4, qta_val, border=0, align='C')

            # Spostiamo il cursore alla riga successiva
            pdf.set_xy(x_start, y_start + row_h)
            pdf.ln(0)

        pdf.ln(4)
    
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="Generatore Distinte", layout="wide")
st.title("📦 Generatore Distinte Kit Chirurgici")

st.sidebar.header("Impostazioni Stampa")
tipo_carta = st.sidebar.selectbox(
    "Seleziona la carta intestata:",
    ["Nessuna", "cartaintestata-HE", "cartaintestata-SIS"]
)

carta_file = None
if tipo_carta == "cartaintestata-HE":
    carta_file = "cartaintestata-HE.png"
elif tipo_carta == "cartaintestata-SIS":
    carta_file = "cartaintestata-SIS.png"

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_lista = pd.read_excel(xls, sheet_name='LISTA KIT')
    df_comp = pd.read_excel(xls, sheet_name='COMPOSIZIONE KIT')

    qta_cols = [c for c in df_lista.columns if str(c).upper().startswith(('QTA', 'Q.TA'))]
    selected_sigla = st.selectbox("Seleziona il presidio:", qta_cols)
    
    df_filtered = df_lista[pd.to_numeric(df_lista[selected_sigla], errors='coerce') > 0].copy()
    df_filtered['CDU_FINALE'] = df_filtered.apply(lambda row: row['NUOVO CDU'] if pd.notna(row.get('NUOVO CDU')) else row.get('CDU', 'N/A'), axis=1)
    
    comp_cdu_col = 'CDU' if 'CDU' in df_comp.columns else ('NUOVO CDU' if 'NUOVO CDU' in df_comp.columns else None)
    comp_kit_col = 'NOME KIT' if 'NOME KIT' in df_comp.columns else ('NUOVO NOME KIT' if 'NUOVO NOME KIT' in df_comp.columns else None)
    
    possible_qta_names = [c for c in df_comp.columns if any(x in str(c).upper() for x in ['QTA', 'Q.TA', 'QUANTIT', 'QUANTITA', 'NUMERO'] )]
    comp_qta_col = possible_qta_names[0] if possible_qta_names else None

    if comp_cdu_col:
        df_comp['CDU_COMP'] = df_comp[comp_cdu_col].astype(str).str.strip()
    else:
        df_comp['CDU_COMP'] = 'N/A'

    tutti_i_cdu_dati = {}

    for cdu, group in df_filtered.groupby('CDU_FINALE'):
        lista_kit_per_pdf = []
        for _, row in group.iterrows():
            nome_kit = row['NUOVO NOME KIT'] if pd.notna(row.get('NUOVO NOME KIT')) else row.get('NOME KIT', 'N/A')
            nome_kit_orig = row.get('NOME KIT', 'N/A')
            
            if comp_kit_col:
                comp = df_comp[
                    (df_comp['CDU_COMP'] == str(cdu)) & 
                    ((df_comp[comp_kit_col] == nome_kit_orig) | (df_comp[comp_kit_col] == nome_kit))
                ].copy()
                
                if comp.empty:
                    comp = df_comp[
                        (df_comp[comp_kit_col] == nome_kit_orig) | (df_comp[comp_kit_col] == nome_kit)
                    ].copy()
            else:
                comp = pd.DataFrame()

            sbs_val = ""
            if 'SBS' in comp.columns and not comp['SBS'].dropna().empty:
                sbs_val = comp['SBS'].dropna().iloc[0]
            elif 'SBS' in row and pd.notna(row['SBS']):
                sbs_val = row['SBS']
            
            lista_kit_per_pdf.append((nome_kit, sbs_val, comp, comp_qta_col))
        
        tutti_i_cdu_dati[cdu] = lista_kit_per_pdf

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

    for cdu, lista_kit_per_pdf in tutti_i_cdu_dati.items():
        st.subheader(f"CDU: {cdu}")
        
        for nome_kit, sbs_val, comp, qta_col_nome in lista_kit_per_pdf:
            kit_text = f"**Kit:** {nome_kit}"
            if sbs_val and str(sbs_val).lower() != 'nan' and str(sbs_val).strip() != '':
                kit_text += f" | **SBS:** {sbs_val}"
            st.write(kit_text)
            
            cols_to_show = [c for c in ['FABBRICANTE', 'CODICE', 'DESCRIZIONE', qta_col_nome] if c and c in comp.columns]
            st.table(comp[cols_to_show])
        
        pdf_data = crea_pdf_cdu(cdu, selected_sigla, lista_kit_per_pdf, carta_file)
        st.download_button(
            label=f"📥 Scarica PDF CDU: {cdu}",
            data=pdf_data,
            file_name=f"{selected_sigla}_{cdu}.pdf",
            mime="application/pdf",
            key=f"btn_{cdu}"
        )
        st.markdown("---")
