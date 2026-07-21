import streamlit as st
import pandas as pd
from fpdf import FPDF
import zipfile
import io
import os

# Classe personalizzata per applicare la carta intestata su TUTTE le pagine automaticamente
class PDFConCartaIntestata(FPDF):
    def __init__(self, carta_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.carta_file = carta_file

    def header(self):
        # Stampa l'immagine di sfondo su ogni pagina se il file esiste
        if self.carta_file and os.path.exists(self.carta_file):
            self.image(self.carta_file, x=0, y=0, w=210)
        # Imposta un margine superiore sicuro (es. 45mm) per evitare che il testo scriva sopra l'intestazione
        self.set_y(45)

    def footer(self):
        # Posiziona il numero di pagina in basso a destra, sopra il piè di pagina della carta intestata
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'R')

def crea_pdf_cdu(cdu, presidio, lista_kit_dati, carta_file):
    pdf = PDFConCartaIntestata(carta_file=carta_file)
    # Impostiamo margini laterali (10mm) e superiore/inferiore puliti
    pdf.set_margins(10, 45, 10)
    pdf.add_page()
    
    def safe_str(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, txt=safe_str(f"PRESIDIO: {presidio} - CDU: {cdu}"), ln=True, align='C')
    pdf.ln(3)
    
    for nome_kit, sbs_val, df_comp in lista_kit_dati:
        pdf.set_font("Arial", 'B', 11)
        kit_label = f"Kit: {nome_kit}"
        if sbs_val and str(sbs_val).lower() != 'nan' and str(sbs_val).strip() != '':
            kit_label += f" - SBS: {sbs_val}"
        pdf.cell(0, 7, txt=safe_str(kit_label), ln=True)
        
        # Intestazione tabella
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 6, "FABBRICANTE", border=1)
        pdf.cell(40, 6, "CODICE", border=1)
        pdf.cell(120, 6, "DESCRIZIONE", border=1)
        pdf.ln()
        
        # Dati tabella
        pdf.set_font("Arial", '', 8)
        for _, row in df_comp.iterrows():
            pdf.cell(40, 5, safe_str(row.get('FABBRICANTE', '')), border=1)
            pdf.cell(40, 5, safe_str(row.get('CODICE', '')), border=1)
            pdf.cell(120, 5, safe_str(row.get('DESCRIZIONE', '')), border=1)
            pdf.ln()
        pdf.ln(4)
    
    return pdf.output(dest='S').encode('latin-1')

# Configurazione Pagina Streamlit
st.set_page_config(page_title="Generatore Distinte", layout="wide")
st.title("📦 Generatore Distinte Kit Chirurgici")

# Sidebar per scelta Carta Intestata
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
    
    tutti_i_cdu_dati = {}

    for cdu, group in df_filtered.groupby('CDU_FINALE'):
        lista_kit_per_pdf = []
        for _, row in group.iterrows():
            nome_kit = row['NUOVO NOME KIT'] if pd.notna(row.get('NUOVO NOME KIT')) else row.get('NOME KIT', 'N/A')
            
            # Ricerca SBS: prima in COMPOSIZIONE KIT, se non c'è, controlla in LISTA KIT (la riga corrente)
            sbs_val = ""
            comp = df_comp[df_comp['NOME KIT'] == row['NOME KIT']].copy()
            
            if 'SBS' in comp.columns and not comp['SBS'].dropna().empty:
                sbs_val = comp['SBS'].dropna().iloc[0]
            elif 'SBS' in row and pd.notna(row['SBS']):
                sbs_val = row['SBS']
            
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
            if sbs_val and str(sbs_val).lower() != 'nan' and str(sbs_val).strip() != '':
                kit_text += f" | **SBS:** {sbs_val}"
            st.write(kit_text)
            
            cols_to_show = [c for c in ['FABBRICANTE', 'CODICE', 'DESCRIZIONE'] if c in comp.columns]
            st.table(comp[cols_to_show])
        
        # Bottone singolo CDU
        pdf_data = crea_pdf_cdu(cdu, selected_sigla, lista_kit_per_pdf, carta_file)
        st.download_button(
            label=f"📥 Scarica PDF CDU: {cdu}",
            data=pdf_data,
            file_name=f"{selected_sigla}_{cdu}.pdf",
            mime="application/zip", # mimetipi corretti
            key=f"btn_{cdu}"
        )
        st.markdown("---")
