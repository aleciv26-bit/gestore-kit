import JSZip from 'jszip';

// Carte intestate fornite (DOCX). L'app estrae logo (header) e testo (footer) a runtime.
export const LETTERHEAD_URLS = {
  SIS: 'https://media.base44.com/files/public/6a5890fc01fff6405b6e709d/ddf6f11ae_CartaintestataSIS_rev06.docx',
  HE: 'https://media.base44.com/files/public/6a5890fc01fff6405b6e709d/391c11c2b_CARTAINTESTATAHE.docx',
};

const cache = {};

function decodeXmlText(s) {
  return s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'");
}

function uint32BE(raw, off) {
  return (raw[off] << 24) | (raw[off + 1] << 16) | (raw[off + 2] << 8) | raw[off + 3];
}
function uint16BE(raw, off) {
  return (raw[off] << 8) | raw[off + 1];
}

function imageDim(raw) {
  if (raw[0] === 0x89 && raw[1] === 0x50) return { w: uint32BE(raw, 16), h: uint32BE(raw, 20), type: 'png' };
  if (raw[0] === 0xff && raw[1] === 0xd8) {
    let i = 2;
    while (i < raw.length - 9) {
      if (raw[i] !== 0xff) { i++; continue; }
      const mk = raw[i + 1];
      if (mk >= 0xc0 && mk <= 0xcf && mk !== 0xc4 && mk !== 0xc8 && mk !== 0xcc) {
        return { w: uint16BE(raw, i + 7), h: uint16BE(raw, i + 5), type: 'jpeg' };
      }
      i += 2 + uint16BE(raw, i + 2);
    }
  }
  return null;
}

function toDataUrl(raw, mime) {
  const chunks = [];
  const CHUNK = 0x8000;
  for (let i = 0; i < raw.length; i += CHUNK) {
    chunks.push(String.fromCharCode.apply(null, raw.subarray(i, i + CHUNK)));
  }
  return 'data:' + mime + ';base64,' + btoa(chunks.join(''));
}

// Estrae logo (header image) + righe di piè di pagina da un DOCX carta intestata.
export async function getLetterhead(type) {
  if (cache[type]) return cache[type];
  const url = LETTERHEAD_URLS[type];
  if (!url) throw new Error('Carta intestata non disponibile: ' + type);

  const buf = await (await fetch(url)).arrayBuffer();
  const zip = await JSZip.loadAsync(buf);
  const files = Object.keys(zip.files);

  // 1. Estensione (dimensione mm) dell'immagine nell'header Word
  const headerXmls = files.filter((f) => /word\/header\d+\.xml$/.test(f));
  let extent = null;
  for (const h of headerXmls) {
    const xml = await zip.file(h).async('string');
    const e = /<wp:extent\s+cx="(\d+)"\s+cy="(\d+)"/i.exec(xml);
    if (e) { extent = [Number(e[1]), Number(e[2])]; break; }
  }

  // 2. Immagini in word/media con dimensioni in pixel
  const media = files.filter((f) => f.startsWith('word/media/'));
  const imgs = [];
  for (const m of media) {
    const raw = await zip.file(m).async('uint8array');
    const dim = imageDim(raw);
    const ext = m.split('.').pop().toLowerCase();
    const mime = ext === 'png' ? 'image/png' : 'image/jpeg';
    imgs.push({ path: m, dim, mime, ext, dataUrl: toDataUrl(raw, mime) });
  }

  // 3. Logo header = immagine col aspect-ratio più vicino all'estensione (fallback jpeg)
  let pick = null;
  if (extent) {
    const target = extent[0] / extent[1];
    let best = null, bd = 999;
    for (const im of imgs) {
      if (!im.dim) continue;
      const d = Math.abs(im.dim.w / im.dim.h - target);
      if (d < bd) { bd = d; best = im; }
    }
    pick = best;
  }
  if (!pick) pick = imgs.find((i) => i.ext === 'jpg' || i.ext === 'jpeg') || imgs[0];

  // 4. Righe di piè di pagina (testo pulito, esclude page-number)
  const footerXmls = files.filter((f) => /word\/footer\d+\.xml$/.test(f));
  let footer = [];
  for (const f of footerXmls) {
    const xml = await zip.file(f).async('string');
    const lines = [];
    const re = /<w:p\b[^>]*>([\s\S]*?)<\/w:p>/g;
    let m;
    while ((m = re.exec(xml))) {
      const p = m[1];
      const ts = [];
      const tr = /<w:t[^>]*>([\s\S]*?)<\/w:t>/g;
      let t;
      while ((t = tr.exec(p))) ts.push(decodeXmlText(t[1]));
      lines.push(ts.join('').replace(/\s+/g, ' ').trim());
    }
    if (lines.filter((l) => l && !l.includes('<')).length > footer.length) footer = lines;
  }
  footer = footer.filter((l) => l && !l.includes('<') && !/^Pagina\s+\d/i.test(l));

  const headerMm = extent
    ? { w: extent[0] / 36000, h: extent[1] / 36000 }
    : (pick && pick.dim ? { w: pick.dim.w * 0.08, h: pick.dim.h * 0.08 } : { w: 60, h: 20 });

  const result = {
    type,
    headerImage: pick ? pick.dataUrl : null,
    headerMime: pick ? pick.mime : null,
    headerMm,
    footerLines: footer,
  };
  cache[type] = result;
  return result;
}