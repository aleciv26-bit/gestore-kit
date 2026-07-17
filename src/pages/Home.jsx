import React, { useCallback, useEffect, useState } from 'react';
import { base44 } from '@/api/base44Client';
import UploadArea from '@/components/UploadArea';
import SessionItem from '@/components/SessionItem';
import LetterheadChoiceModal from '@/components/LetterheadChoiceModal';
import { parseExcel } from '@/lib/excelProcessor';
import { generateKitPdf, sanitizeFileName } from '@/lib/pdfGenerator';
import { getLetterhead } from '@/lib/letterhead';
import moment from 'moment';
import { Loader2, History, AlertCircle, FileSpreadsheet, X } from 'lucide-react';

export default function Home() {
  const [sessions, setSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0, label: '' });
  const [error, setError] = useState('');
  const [pendingFile, setPendingFile] = useState(null);
  const [lhLoading, setLhLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const data = await base44.entities.UploadSession.list('-created_date', 100);
      setSessions(data);
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const chooseLetterhead = async (type) => {
    setLhLoading(true);
    let lh;
    try {
      lh = await getLetterhead(type);
    } catch (e) {
      setError(e?.message || 'Impossibile caricare la carta intestata.');
      setLhLoading(false);
      return;
    }
    const file = pendingFile;
    setPendingFile(null);
    setLhLoading(false);
    if (file) handleFile(file, lh);
  };

  const handleFile = async (file, letterhead) => {
    setProcessing(true);
    setError('');
    setProgress({ current: 0, total: 0, label: 'Caricamento file...' });
    let session = null;
    try {
      // 1. Salva il file Excel in archiviazione privata
      const { file_uri } = await base44.integrations.Core.UploadPrivateFile({ file });
      const baseName = file.name.replace(/\.(xlsx|xls)$/i, '');
      const dateStr = moment().format('YYYYMMDD_HHmmss');
      const folderName = `${dateStr}_${baseName}`;

      // 2. Crea la sessione di upload
      session = await base44.entities.UploadSession.create({
        original_filename: file.name,
        folder_name: folderName,
        excel_file_uri: file_uri,
        status: 'processing',
      });

      // 3. Recupera il file per l'elaborazione
      setProgress({ current: 0, total: 0, label: 'Lettura fogli Excel...' });
      const { signed_url } = await base44.integrations.Core.CreateFileSignedUrl({
        file_uri,
        expires_in: 900,
      });
      const buffer = await (await fetch(signed_url)).arrayBuffer();

      // 4. Estrai le specifiche dei PDF
      const specs = parseExcel(buffer);
      if (!specs.length) {
        throw new Error('Nessun kit con quantità > 0 trovato nel foglio LISTA KIT.');
      }

      // 5. Genera e salva un PDF per ogni CDU NUOVO (contenente tutti i suoi kit)
      setProgress({ current: 0, total: specs.length, label: 'Avvio generazione PDF...' });
      let count = 0;
      for (const spec of specs) {
        const blob = generateKitPdf(spec.kits, spec.cdu, spec.presidio, letterhead);
        const fileName = `${sanitizeFileName(spec.presidio)}_${sanitizeFileName(spec.cdu)}.pdf`;
        const pdfFile = new File([blob], fileName, { type: 'application/pdf' });
        const { file_uri: pdfUri } = await base44.integrations.Core.UploadPrivateFile({ file: pdfFile });
        await base44.entities.GeneratedPdf.create({
          session_id: session.id,
          presidio: spec.presidio,
          cdu_nuovo: spec.cdu,
          file_name: fileName,
          file_uri: pdfUri,
          kit_count: spec.kits.length,
          component_count: spec.kits.reduce((sum, k) => sum + (k.components?.length || 0), 0),
        });
        count++;
        setProgress({
          current: count,
          total: specs.length,
          label: `Generazione ${count}/${specs.length}: ${spec.presidio} - ${spec.cdu}`,
        });
      }

      // 6. Aggiorna la sessione come completata
      await base44.entities.UploadSession.update(session.id, {
        status: 'completed',
        pdf_count: count,
        kit_count: specs.reduce((sum, sp) => sum + sp.kits.length, 0),
      });
      await loadSessions();
    } catch (e) {
      const msg = e?.message || 'Errore durante l\'elaborazione del file.';
      setError(msg);
      if (session) {
        try {
          await base44.entities.UploadSession.update(session.id, {
            status: 'failed',
            error_message: msg,
          });
        } catch {
          /* ignore */
        }
        await loadSessions();
      }
    } finally {
      setProcessing(false);
      setProgress({ current: 0, total: 0, label: '' });
    }
  };

  const pct = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Scelta carta intestata */}
      {pendingFile && !processing && (
        <LetterheadChoiceModal
          fileName={pendingFile.name}
          loading={lhLoading}
          onChoose={chooseLetterhead}
          onCancel={() => { setPendingFile(null); setLhLoading(false); }}
        />
      )}

      {/* Overlay elaborazione */}
      {processing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-2xl bg-card p-6 shadow-2xl">
            <div className="flex items-center gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <div>
                <p className="font-heading font-semibold text-foreground">Elaborazione in corso</p>
                <p className="text-sm text-muted-foreground">Generazione dei PDF...</p>
              </div>
            </div>
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="truncate pr-2 text-muted-foreground">{progress.label}</span>
                {progress.total > 0 && (
                  <span className="font-medium text-foreground">{pct}%</span>
                )}
              </div>
              {progress.total > 0 ? (
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              ) : (
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        {/* Header */}
        <header className="mb-10 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
            <FileSpreadsheet className="h-7 w-7" />
          </div>
          <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground">
            Distinte Kit Chirurgici
          </h1>
          <p className="mx-auto mt-2 max-w-xl text-muted-foreground">
            Carica un file Excel per generare automaticamente i PDF delle distinte, organizzati e sempre disponibili.
          </p>
        </header>

        {/* Errore */}
        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-medium">Errore durante l'elaborazione</p>
              <p className="text-sm text-red-600">{error}</p>
            </div>
            <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Upload */}
        <section className="mb-10">
          <UploadArea onFile={setPendingFile} disabled={processing || lhLoading} />
        </section>

        {/* Storico sessioni */}
        <section>
          <div className="mb-4 flex items-center gap-2">
            <History className="h-5 w-5 text-muted-foreground" />
            <h2 className="font-heading text-lg font-semibold text-foreground">Storico sessioni</h2>
          </div>

          {loadingSessions ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Caricamento storico...
            </div>
          ) : sessions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border py-12 text-center">
              <FileSpreadsheet className="mx-auto mb-3 h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                Nessuna sessione ancora. Carica il primo file Excel per iniziare.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <SessionItem key={session.id} session={session} />
              ))}
            </div>
          )}
        </section>

        <footer className="mt-12 text-center text-xs text-muted-foreground">
          I file vengono salvati in archiviazione privata e sono sempre scaricabili dallo storico.
        </footer>
      </div>
    </div>
  );
}