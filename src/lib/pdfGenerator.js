import { jsPDF } from 'jspdf';

const s = (v) => String(v ?? '');

// Genera un PDF per un CDU. All'inizio un titolo ben visibile con il nome del CDU,
// poi per ogni kit: etichetta "Kit: <nome>" + tabella componenti con colonna SBS.
export function generateKitPdf(kits, cdu, presidio, letterhead) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth  = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 12;
  const usableW = pageWidth - margin * 2;

  // --- Carta intestata (logo in header + testo in footer) ---
  const lh = letterhead || null;
  const headerImgFormat = lh && lh.headerMime === 'image/png' ? 'PNG' : 'JPEG';
  const headerMm = lh && lh.headerMm ? lh.headerMm : { w: 60, h: 20 };
  const headerY = 8;
  const contentTopY = lh ? headerY + headerMm.h + 9 : 15;
  const footerLines = (lh && Array.isArray(lh.footerLines)) ? lh.footerLines : [];
  const fLineH = 3.8;
  const footerStartY = pageHeight - 12 - footerLines.length * fLineH;
  const bottomLimit = lh ? Math.min(pageHeight - 15, footerStartY - 6) : pageHeight - 15;

  const drawLetterhead = () => {
    if (!lh) return;
    if (lh.headerImage) {
      try { doc.addImage(lh.headerImage, headerImgFormat, margin, headerY, headerMm.w, headerMm.h); } catch (e) { /* ignore */ }
    }
    if (footerLines.length) {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(90, 90, 90);
      footerLines.forEach((line, i) => {
        doc.text(line, pageWidth / 2, footerStartY + i * fLineH + 3, { align: 'center' });
      });
      doc.setTextColor(0, 0, 0);
    }
  };

  const cols = [
    { label: 'Q.TÀ',        w: usableW * 0.07 },
    { label: 'FABBRICANTE', w: usableW * 0.16 },
    { label: 'CODICE',      w: usableW * 0.13 },
    { label: 'DESCRIZIONE', w: usableW * 0.50 },
    { label: 'SBS',         w: usableW * 0.14 },
  ];
  const tableHeadH = 7;
  const minRowH = 7.5;
  const lineHeight = 3.6;

  const colX = (i) => {
    let x = margin;
    for (let k = 0; k < i; k++) x += cols[k].w;
    return x;
  };

  const drawVerticals = (yPos, h) => {
    doc.setDrawColor(200);
    doc.setLineWidth(0.2);
    for (let i = 1; i < cols.length; i++) doc.line(colX(i), yPos, colX(i), yPos + h);
  };

  const drawTableHeader = (yPos) => {
    doc.setFillColor(235, 235, 235);
    doc.rect(margin, yPos, usableW, tableHeadH, 'F');
    doc.setDrawColor(150);
    doc.setLineWidth(0.3);
    doc.rect(margin, yPos, usableW, tableHeadH, 'S');
    drawVerticals(yPos, tableHeadH);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(0, 0, 0);
    cols.forEach((col, i) => {
      const x = colX(i);
      if (i === 0) doc.text(col.label, x + col.w / 2, yPos + tableHeadH / 2 + 2.5, { align: 'center' });
      else doc.text(col.label, x + 2, yPos + tableHeadH / 2 + 2.5);
    });
    return yPos + tableHeadH;
  };

  const newPage = () => { doc.addPage(); drawLetterhead(); return contentTopY; };

  // Carta intestata sulla prima pagina
  drawLetterhead();
  let y = contentTopY;

  // Titolo interno: nome del CDU di riferimento (ben visibile)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(15);
  doc.setTextColor(0, 0, 0);
  doc.text(s(cdu), margin, y);
  y += 7;
  if (presidio) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(90, 90, 90);
    doc.text(`Presidio: ${s(presidio)}`, margin, y);
    y += 6;
  }
  doc.setDrawColor(120);
  doc.setLineWidth(0.4);
  doc.line(margin, y - 2, pageWidth - margin, y - 2);
  y += 4;
  doc.setTextColor(0, 0, 0);

  const drawRows = (components, sbs) => {
    let ri = 0;
    components.forEach((comp) => {
      const descRaw = s(comp['DESCRIZIONE'] || comp['DESCRIZIONE SW']);
      const descLines = doc.splitTextToSize(descRaw, cols[3].w - 4);
      const sbsLines = doc.splitTextToSize(sbs, cols[4].w - 4);
      const rowH = Math.max(minRowH, Math.max(descLines.length, sbsLines.length) * lineHeight + 2);
      if (y + rowH > bottomLimit) { y = newPage(); y = drawTableHeader(y); ri = 0; }
      if (ri % 2 === 0) doc.setFillColor(248, 248, 248);
      else doc.setFillColor(255, 255, 255);
      doc.rect(margin, y, usableW, rowH, 'F');
      doc.setDrawColor(200);
      doc.setLineWidth(0.2);
      doc.rect(margin, y, usableW, rowH, 'S');
      drawVerticals(y, rowH);
      doc.setTextColor(0, 0, 0);
      const cellY = y + minRowH / 2 + 2.5;
      doc.text(s(comp['Q.TÀ'] ?? comp['Q.TA'] ?? comp['QTA'] ?? ''), colX(0) + cols[0].w / 2, cellY, { align: 'center' });
      doc.text(doc.splitTextToSize(s(comp['FABBRICANTE']), cols[1].w - 4)[0], colX(1) + 2, cellY);
      doc.text(doc.splitTextToSize(s(comp['CODICE']), cols[2].w - 4)[0], colX(2) + 2, cellY);
      doc.text(descLines, colX(3) + 2, y + lineHeight + 1);
      doc.text(sbsLines, colX(4) + 2, y + lineHeight + 1);
      y += rowH;
      ri++;
    });
  };

  kits.forEach((kit, idx) => {
    // Intestazione kit
    if (y + 6 > bottomLimit) y = newPage();
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(0, 0, 0);
    doc.text(`Kit: ${s(kit.kit_name)}`, margin, y);
    y += 5;

    // Tabella componenti del kit (con colonna SBS)
    if (y + tableHeadH > bottomLimit) y = newPage();
    y = drawTableHeader(y);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    drawRows(kit.components || [], kit.sbs);

    y += 6; // stacco tra un kit e il successivo
    if (y > bottomLimit) y = newPage();
  });

  return doc.output('blob');
}

export function sanitizeFileName(name) {
  return String(name || '')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .trim();
}