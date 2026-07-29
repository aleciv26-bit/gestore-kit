import streamlit as st
import pandas as pd
from fpdf import FPDF
import zipfile
import io
import os

class PDFConPaginazioneEIntestata(FPDF):
    def __init__(self, carta_file=None, is_prima_pagina=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.carta_file = carta_file
        self.is_prima_pagina = is_prima_pagina

    def header(self):
        if self.carta_file and os.path.exists(self.carta_file):
            self.image(self.carta_file, x=0, y=0, w=210)
        
        if not self.is_prima_pagina:
            self.set_y(40)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", '', 8)
        self.set_text_color(100, 100, 100)
        page_str = f"Pag. {self.page_no()} di {{nb}}"
        self.cell(0, 10, page_str, align='C')

def crea_pdf_cdu(cdu, presidio, lista_kit_dati, carta_file, titolo_custom, sottotitolo_custom, mostra_qta_richieste):
    pdf = PDFConPaginazioneEIntestata(carta_file=carta_file, is_prima_pagina=True)
    pdf.alias_nb_pages()
    pdf.set_margins(10, 20, 10)
    pdf.add_page()
    
    def safe_str(text):
        if pd.isna(text):
            return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    # --- PAGINA 1: FRONTESPIZIO (Centrato nello spazio utile) ---
    pdf.set_y(68)

    if titolo_custom:
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(26, 54, 93)
        pdf.multi_cell(0, 8, txt=safe_str(titolo_custom), align='C')
        pdf.ln(10)

    if sottotitolo_custom:
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(26, 54, 93)
        pdf.multi_cell(0, 5.5, txt=safe_str(sottotitolo_custom), align='C')
        pdf.ln(12)

    nome_presidio_pulito = presidio.replace("QTA_", "").replace("QTA.", "").replace("QUANTITA_", "").replace("QUANTITA", "").strip().upper()
    if not nome_presidio_pulito:
        nome_presidio_pulito = presidio.upper()
    
    pdf.set_font("Arial", 'B', 13)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(0, 7, txt=safe_str(f"PRESIDIO OSPEDALIERO DI {nome_presidio_pulito}"), ln=True, align='C')
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 13)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(0, 7, txt=safe_str(str(cdu)), ln=True, align='C')

    pdf.set_y(225)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0, 0, 0)
    
    y_firma = pdf.get_y()
    pdf.line(30, y_firma, 90, y_firma)
    pdf.line(120, y_firma, 180, y_firma)
    
    pdf.set_y(y_firma + 2)
    pdf.set_x(30)
    pdf.cell(60, 5, "Data", align='C')
    pdf.set_x(120)
    pdf.cell(60, 5, "Firma per approvazione", align='C')

    # --- PAGINA 2+: TABELLA RIEPILOGATIVA KIT E SBS (Con gestione multi-pagina) ---
    pdf.is_prima_pagina = False
    pdf.set_margins(10, 40, 10)
    pdf.add_page()

    col_w_nome_kit = 140
    col_w_sbs = 50
    table_w_summary = col_w_nome_kit + col_w_sbs
    left_margin_summary = (210 - table_w_summary) / 2

    def stampa_intestazione_summary():
        pdf.set_x(left_margin_summary)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(col_w_nome_kit, 6, "NOME KIT", border=1)
        pdf.cell(col_w_sbs, 6, "SBS", border=1)
        pdf.ln()

    stampa_intestazione_summary()

    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(0, 0, 0)
    
    row_height = 6.0
    for nome_kit, sbs_val, _, _, _ in lista_kit_dati:
        if pdf.get_y() + row_height > 250:
            pdf.add_page()
            stampa_intestazione_summary()
            pdf.set_font("Arial", '', 9)
            pdf.set_text_color(0, 0, 0)

        pdf.set_x(left_margin_summary)
        pdf.cell(col_w_nome_kit, row_height, safe_str(nome_kit), border=1)
        pdf.cell(col_w_sbs, row_height, safe_str(sbs_val), border=1)
        pdf.ln()

    # --- PAGINA SUCCESSIVA: TESTO INTRODUTTIVO DELLE DISTINTE ---
    pdf.add_page()
    pdf.set_y(44)
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, txt=safe_str("Di seguito si riportano le distinte di composizione di quanto precedentemente elencato, definite in accordo con i rappresentati delle specialità durante gli incontri effettuati con i nostri esperti di ottimizzazione dello strumentario chirurgico."), align='L')

    # --- DALLE PAGINE SUCCESSIVE: COMPOSIZIONE DETTAGLIATA KIT ---
    col_w_qta = 18
    col_w_fab = 35
    col_w_cod = 35
    col_w_desc = 102
    
    table_total_width = col_w_qta + col_w_fab + col_w_cod + col_w_desc
    left_margin = (210 - table_total_width) / 2

    def stampa_intestazione_dettaglio():
        pdf.set_x(left_margin)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(col_w_qta, 6, "Q.TA", border=1, align='C')
        pdf.cell(col_w_fab, 6, "FABBRICANTE", border=1, align='C')
        pdf.cell(col_w_cod, 6, "CODICE", border=1, align='C')
        pdf.cell(col_w_desc, 6, "DESCRIZIONE", border=1, align='C')
        pdf.ln()

    pdf.set_margins(left_margin, 40, left_margin)

    for nome_kit, sbs_val, df_comp, qta_col_nome, qta_richiesta in lista_kit_dati:
        pdf.add_page()

        titolo_stringa = f"Kit: {nome_kit}"
        if mostra_qta_richieste and qta_richiesta is not None and str(qta_richiesta).strip() != '':
            titolo_stringa += f"  -  Quantità kit richiesti: {qta_richiesta}"

        pdf.set_font("Arial", 'B', 15)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 7, txt=safe_str(titolo_stringa), ln=True)
        
        dm_totali = 0
        if qta_col_nome and not df_comp.empty and qta_col_nome in df_comp.columns:
            try:
                dm_totali = pd.to_numeric(df_comp[qta_col_nome], errors='coerce').fillna(0).sum()
                dm_totali = int(dm_totali)
            except:
                dm_totali = 0

        sbs_stringa = ""
        if sbs_val and str(sbs_val).lower() != 'nan' and str(sbs_val).strip() != '':
            sbs_stringa = f"SBS: {sbs_val}"
        
        dm_stringa = f"DM TOTALI: {dm_totali}"
        
        sottotitolo_finale = sbs_stringa
        if sottotitolo_finale:
            sottotitolo_finale += f"  -  {dm_stringa}"
        else:
            sottotitolo_finale = dm_stringa

        if sottotitolo_finale:
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, txt=safe_str(sottotitolo_finale), ln=True)
        
        pdf.ln(3)
        stampa_intestazione_dettaglio()
        
        pdf.set_font("Arial", '', 8)
        pdf.set_text_color(0, 0, 0)
        for _, row in df_comp.iterrows():
            fab = safe_str(row.get('FABBRICANTE', ''))
            cod = safe_str(row.get('CODICE', ''))
            desc = safe_str(row.get('DESCRIZIONE', ''))
            
            qta_raw = row.get(qta_col_nome, '') if qta_col_nome else ''
            try:
                if pd.notna(qta_raw) and str(qta_raw).strip() != '':
                    qta_val = str(int(float(qta_raw)))
                else:
                    qta_val = ""
            except:
                qta_val = safe_str(qta_raw)

            chars_per_line = 48
            lines_count = max(1, int(len(desc) / chars_per_line) + (1 if len(desc) % chars_per_line > 0 else 0))
            row_h = max(6, lines_count * 4.5 + 2)

            if pdf.get_y() + row_h > 245:
                pdf.add_page()
                stampa_intestazione_dettaglio()
                pdf.set_font("Arial", '', 8)

            x_start = left_margin
            y_start = pdf.get_y()
            current_x = x_start
            
            # Q.TA (Centrato)
            pdf.rect(current_x, y_start, col_w_qta, row_h)
            pdf.set_xy(current_x, y_start + (row_h - 4) / 2)
            pdf.cell(col_w_qta, 4, qta_val, border=0, align='C')
            current_x += col_w_qta

            # FABBRICANTE (Allineato a sinistra nel contenuto, intestazione centrata)
            pdf.rect(current_x, y_start, col_w_fab, row_h)
            pdf.set_xy(current_x + 1, y_start + (row_h - 4) / 2)
            pdf.cell(col_w_fab - 2, 4, fab, border=0, align='L')
            current_x += col_w_fab

            # CODICE (Allineato a sinistra nel contenuto, intestazione centrata)
            pdf.rect(current_x, y_start, col_w_cod, row_h)
            pdf.set_xy(current_x + 1, y_start + (row_h - 4) / 2)
            pdf.cell(col_w_cod - 2, 4, cod, border=0, align='L')
            current_x += col_w_cod

            # DESCRIZIONE (Allineato a sinistra nel contenuto, intestazione centrata)
            pdf.rect(current_x, y_start, col_w_desc, row_h)
            if lines_count <= 1:
                pdf.set_xy(current_x + 1, y_start + (row_h - 4) / 2)
                pdf.cell(col_w_desc - 2, 4, desc, border=0, align='L')
            else:
                pdf.set_xy(current_x + 1, y_start + 1.5)
                pdf.multi_cell(col_w_desc - 2, 4, desc, border=0, align='L')

            pdf.set_xy(x_start, y_start + row_h)
            pdf.ln(0)
    
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

st.sidebar.markdown("---")
st.sidebar.subheader("Opzioni PDF")
mostra_qta_richieste = st.sidebar.checkbox("Mostra quantità kit richiesti", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("Personalizzazione Frontespizio")
titolo_default = "Azienda ULSS n. 5 Polesana"
sottotitolo_default = "PROGETTAZIONE, CON TECNICHE DI OTTIMIZZAZIONE, DEL PARCO DI DISPOSITIVI MEDICI RIUTILIZZABILI ED ACCESSORI DEI PRESIDI OSPEDALIERI DELLA AZIENDA ULSS N.5 POLESANA\nCIG B83F8F3019"

titolo_custom = st.sidebar.text_input("Titolo Principale", value=titolo_default)
sottotitolo_custom = st.sidebar.text_area("Sottotitolo / Oggetto", value=sottotitolo_default, height=100)

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
            
            qta_richiesta = row.get(selected_sigla, '')
            
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
            
            lista_kit_per_pdf.append((nome_kit, sbs_val, comp, comp_qta_col, qta_richiesta))
        
        tutti_i_cdu_dati[cdu] = lista_kit_per_pdf

    if tutti_i_cdu_dati:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cdu, kit_data in tutti_i_cdu_dati.items():
                pdf_bytes = crea_pdf_cdu(cdu, selected_sigla, kit_data, carta_file, titolo_custom, sottotitolo_custom, mostra_qta_richieste)
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
        pdf_data = crea_pdf_cdu(cdu, selected_sigla, lista_kit_per_pdf, carta_file, titolo_custom, sottotitolo_custom, mostra_qta_richieste)
        
        with st.expander(f"CDU: {cdu}"):
            col_info, col_btn = st.columns([3, 1])
            with col_btn:
                st.download_button(
                    label=f"📥 Scarica PDF CDU: {cdu}",
                    data=pdf_data,
                    file_name=f"{selected_sigla}_{cdu}.pdf",
                    mime="application/pdf",
                    key=f"btn_{cdu}"
                )
            
            st.markdown("---")
            
            for nome_kit, sbs_val, comp, qta_col_nome, qta_richiesta in lista_kit_per_pdf:
                kit_text = f"**Kit:** {nome_kit}"
                if mostra_qta_richieste and str(qta_richiesta).strip() != '':
                    kit_text += f" (Quantità kit richiesti: {qta_richiesta})"
                if sbs_val and str(sbs_val).lower() != 'nan' and str(sbs_val).strip() != '':
                    kit_text += f" | **SBS:** {sbs_val}"
                st.write(kit_text)
                
                if qta_col_nome and qta_col_nome in comp.columns:
                    other_cols = [c for c in ['FABBRICANTE', 'CODICE', 'DESCRIZIONE'] if c in comp.columns]
                    cols_to_show = [qta_col_nome] + other_cols
                else:
                    cols_to_show = [c for c in ['FABBRICANTE', 'CODICE', 'DESCRIZIONE'] if c in comp.columns]
                    
                st.table(comp[cols_to_show])
        
        st.markdown("---")
