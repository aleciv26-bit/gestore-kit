import * as XLSX from 'xlsx';

function findHeaderRow(rows, key) {
  const upperKey = key.toUpperCase();
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i] || [];
    if (row.some((cell) => String(cell ?? '').toUpperCase().includes(upperKey))) return i;
  }
  return -1;
}

function sheetToObjects(rows, headerIdx) {
  if (headerIdx < 0) return [];
  const headers = (rows[headerIdx] || []).map((h) => String(h ?? '').trim());
  const objs = [];
  for (let i = headerIdx + 1; i < rows.length; i++) {
    const row = rows[i] || [];
    if (row.every((c) => c === '' || c == null)) continue;
    const obj = {};
    headers.forEach((h, idx) => { obj[h] = row[idx] ?? ''; });
    objs.push(obj);
  }
  return objs;
}

function isLegacyQtaColumn(header) {
  return /^Q\.T[Àà A]/i.test(header.trim()) && header.trim().length > 4;
}

function normalizeStr(v) {
  return String(v ?? '')
    .toLowerCase()
    .replace(/[.,;:'°()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
function tokenSet(v) {
  return new Set(normalizeStr(v).split(' ').filter((t) => t.length > 1));
}
function sharedTokens(a, b) {
  const ta = tokenSet(a);
  const tb = tokenSet(b);
  let n = 0;
  ta.forEach((t) => { if (tb.has(t)) n++; });
  return n;
}

// Direttive:
// - Presidi: ogni colonna che inizia con "QTA_" (es. QTA_LECCO -> Presidio LECCO).
// - Gerarchia CDU: colonna "NUOVO CDU" -> fallback "CDU" (per riga).
// - Gerarchia NOME KIT: colonna "NUOVO NOME KIT" -> fallback "NOME KIT" (per riga).
// - Filtraggio: per ogni presidio, solo le righe con quantità del presidio corrente > 0.
// - Raggruppamento per CDU risolto; SBS letto da LISTA KIT (colonna "SBS"/"Sbs_description").
// - Componenti estratti da COMPOSIZIONE KIT collegandoli al kit (CDU + NOME KIT originari).
// - Un PDF per ogni combinazione (Presidio, CDU): file PRESIDIO_CDU.pdf (mai sovrascritto).
// Compatibilità: se non ci sono colonne QTA_, ricade sulle colonne "Q.tà <Presidio>"
// mappate per similarità alla colonna PRESIDIO.
export function parseExcel(arrayBuffer) {
  const wb = XLSX.read(arrayBuffer, { type: 'array' });

  const listaName = wb.SheetNames.find((n) => n.toUpperCase().includes('LISTA KIT'));
  const compName  = wb.SheetNames.find((n) => n.toUpperCase().includes('COMPOSIZIONE KIT'));
  if (!listaName || !compName) {
    throw new Error('Fogli "LISTA KIT" o "COMPOSIZIONE KIT" non trovati nel file Excel.');
  }

  const listaRows = XLSX.utils.sheet_to_json(wb.Sheets[listaName], { header: 1, defval: '' });
  const compRows  = XLSX.utils.sheet_to_json(wb.Sheets[compName],  { header: 1, defval: '' });

  // Riga intestazione LISTA KIT (robusta a file senza colonna PRESIDIO)
  let listaHeaderIdx = -1;
  ['PRESIDIO', 'NOME KIT', 'CDU'].forEach((k) => {
    const idx = findHeaderRow(listaRows, k);
    if (idx >= 0 && (listaHeaderIdx < 0 || idx < listaHeaderIdx)) listaHeaderIdx = idx;
  });
  if (listaHeaderIdx < 0) throw new Error('Intestazione non trovata nel foglio LISTA KIT.');
  const listaHeaders = (listaRows[listaHeaderIdx] || []).map((h) => String(h ?? '').trim());

  const presidioIdx = listaHeaders.findIndex((h) => h.toUpperCase() === 'PRESIDIO');
  // Gerarchia CDU: "NUOVO CDU" (fallback "CDU NUOVO") -> "CDU"
  const cduNuovoIdx = listaHeaders.findIndex((h) => h.toUpperCase() === 'NUOVO CDU' || h.toUpperCase() === 'CDU NUOVO');
  const cduIdx      = listaHeaders.findIndex((h) => h.toUpperCase() === 'CDU');
  // Gerarchia NOME KIT: "NUOVO NOME KIT" (fallback "NOME KIT NUOVO") -> "NOME KIT"
  const nomeKitIdx  = listaHeaders.findIndex((h) => h.toUpperCase() === 'NOME KIT');
  const nuovoNomeKitIdx = listaHeaders.findIndex((h) => h.toUpperCase() === 'NUOVO NOME KIT' || h.toUpperCase() === 'NOME KIT NUOVO');

  // SBS letto da LISTA KIT se presente una colonna "SBS" / "Sbs_description"
  const sbsIdx = listaHeaders.findIndex((h) => {
    const u = h.toUpperCase();
    return u === 'SBS' || u === 'SBS_DESCRIPTION' || u === 'SBS DESCRIPTION';
  });

  // Standard: colonne QTA_<PRESIDIO>
  const stdCols = [];
  listaHeaders.forEach((h, i) => {
    const upper = h.toUpperCase().replace(/\s+/g, '');
    if (upper.startsWith('QTA_')) {
      // Estrae il nome del presidio dall'intestazione originale (mantiene gli spazi, es. "VITTORIO VENETO")
      const usIdx = h.indexOf('_');
      const presidio = (usIdx >= 0 ? h.slice(usIdx + 1) : upper.slice(upper.indexOf('_') + 1)).trim();
      stdCols.push({ i, header: h, presidio });
    }
  });

  let qtyCols; // [{ i, presidio }]
  if (stdCols.length > 0) {
    qtyCols = stdCols;
  } else {
    // Legacy: colonne "Q.tà <Presidio>" mappate per similarità alla colonna PRESIDIO
    const legacyRaw = [];
    listaHeaders.forEach((h, i) => { if (isLegacyQtaColumn(h)) legacyRaw.push({ i, header: h }); });
    if (legacyRaw.length === 0) {
      throw new Error('Nessuna colonna "QTA_" trovata nel foglio LISTA KIT.');
    }
    const presidiSet = new Set();
    for (let i = listaHeaderIdx + 1; i < listaRows.length; i++) {
      const row = listaRows[i] || [];
      if (row.every((c) => c === '' || c == null)) continue;
      if (presidioIdx < 0) break;
      const p = String(row[presidioIdx] ?? '').trim();
      if (p) presidiSet.add(p);
    }
    const presidi = [...presidiSet];
    qtyCols = legacyRaw.map(({ i, header }) => {
      let best = null;
      let bestScore = 0;
      presidi.forEach((p) => {
        const sc = sharedTokens(header, p);
        if (sc <= 0) return;
        if (sc > bestScore || (sc === bestScore && best && p.length > best.length)) {
          bestScore = sc; best = p;
        }
      });
      return { i, presidio: best };
    });
  }

  // COMPOSIZIONE KIT: chiave di collegamento "CDU" (fallback "NUOVO CDU", "CDU NUOVO")
  let compHeaderIdx = findHeaderRow(compRows, 'CDU');
  if (compHeaderIdx < 0) compHeaderIdx = findHeaderRow(compRows, 'NUOVO CDU');
  const compObjects = sheetToObjects(compRows, compHeaderIdx);
  const compHeaders = compHeaderIdx >= 0 ? (compRows[compHeaderIdx] || []).map((h) => String(h ?? '').trim()) : [];
  const compLinkKey    = compHeaders.find((h) => h.toUpperCase() === 'CDU')
    || compHeaders.find((h) => h.toUpperCase() === 'NUOVO CDU')
    || compHeaders.find((h) => h.toUpperCase() === 'CDU NUOVO');
  const compNomeKitKey = compHeaders.find((h) => h.toUpperCase() === 'NOME KIT');

  const compsByLink = new Map();
  compObjects.forEach((obj) => {
    const link = compLinkKey ? String(obj[compLinkKey] ?? '').trim() : '';
    if (!link) return;
    if (!compsByLink.has(link)) compsByLink.set(link, []);
    compsByLink.get(link).push(obj);
  });

  // Un PDF per ogni (Presidio, CDU). Raggruppamento per CDU risolto (gerarchia NUOVO CDU -> CDU).
  // File di output: PRESIDIO_CDU.pdf (unico per ogni combinazione Presidio+CDU).
  const groups = new Map(); // `${presidio}||${cdu}` -> { presidio, cdu, kits }

  for (let i = listaHeaderIdx + 1; i < listaRows.length; i++) {
    const row = listaRows[i] || [];
    if (row.every((c) => c === '' || c == null)) continue;

    // Gerarchia nome kit: NUOVO NOME KIT -> NOME KIT (per riga)
    const origName     = nomeKitIdx >= 0 ? String(row[nomeKitIdx] ?? '').trim() : '';
    const resolvedName = nuovoNomeKitIdx >= 0 ? (String(row[nuovoNomeKitIdx] ?? '').trim() || origName) : origName;
    // Gerarchia CDU: NUOVO CDU -> CDU (per riga)
    const origCdu      = cduIdx >= 0 ? String(row[cduIdx] ?? '').trim() : '';
    const resolvedCdu  = cduNuovoIdx >= 0 ? (String(row[cduNuovoIdx] ?? '').trim() || origCdu) : origCdu;
    const sbs          = sbsIdx >= 0 ? String(row[sbsIdx] ?? '').trim() : '';

    // Per ogni colonna QTA_: filtra solo le righe con quantità del presidio corrente > 0.
    // Il kit va nel PDF del presidio corrispondente, nel gruppo del CDU risolto.
    qtyCols.forEach(({ i, presidio }) => {
      if (!presidio) return;
      const v = Number(String(row[i]).replace(',', '.'));
      if (isNaN(v) || v === 0) return;
      const key = `${presidio}||${resolvedCdu}`;
      if (!groups.has(key)) groups.set(key, { presidio, cdu: resolvedCdu, kits: [] });
      const g = groups.get(key);
      if (!g.kits.some((k) => k.kit_name === resolvedName)) {
        // link_value = CDU risolto (chiave usata da COMPOSIZIONE KIT); match_name = NOME KIT originario
        g.kits.push({ kit_name: resolvedName, sbs, link_value: resolvedCdu, match_name: origName, components: [] });
      }
    });
  }

  // Componenti per kit: collegamento per CDU risolto + NOME KIT.
  // COMPOSIZIONE KIT usa il NOME KIT corrente: match sul nome risolto, con fallback sul nome originario.
  for (const group of groups.values()) {
    group.kits.forEach((kit) => {
      const comps = (kit.link_value && compsByLink.has(kit.link_value)) ? compsByLink.get(kit.link_value) : [];
      kit.components = compNomeKitKey
        ? comps.filter((o) => {
            const n = String(o[compNomeKitKey] ?? '').trim();
            return n === kit.kit_name || n === kit.match_name;
          })
        : comps;
    });
  }

  const specs = [...groups.values()];
  if (!specs.length) {
    throw new Error('Nessun kit con quantità > 0 trovato nel foglio LISTA KIT.');
  }
  return specs;
}