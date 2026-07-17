import React, { useState } from 'react';
import { base44 } from '@/api/base44Client';
import JSZip from 'jszip';
import moment from 'moment';
import {
  ChevronRight,
  ChevronDown,
  FileText,
  Download,
  Loader2,
  FolderArchive,
  CheckCircle2,
  AlertCircle,
  LoaderCircle,
} from 'lucide-react';

const STATUS_CONFIG = {
  processing: { label: 'In elaborazione', icon: LoaderCircle, className: 'text-amber-600 bg-amber-50' },
  completed: { label: 'Completato', icon: CheckCircle2, className: 'text-emerald-600 bg-emerald-50' },
  failed: { label: 'Errore', icon: AlertCircle, className: 'text-red-600 bg-red-50' },
};

export default function SessionItem({ session }) {
  const [open, setOpen] = useState(false);
  const [pdfs, setPdfs] = useState([]);
  const [loadingPdfs, setLoadingPdfs] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [zipping, setZipping] = useState(false);

  const status = STATUS_CONFIG[session.status] || STATUS_CONFIG.processing;

  const toggle = async () => {
    if (!open) {
      setOpen(true);
      setLoadingPdfs(true);
      try {
        const data = await base44.entities.GeneratedPdf.filter({ session_id: session.id });
        setPdfs(data);
      } finally {
        setLoadingPdfs(false);
      }
    } else {
      setOpen(false);
    }
  };

  const downloadPdf = async (pdf) => {
    setDownloadingId(pdf.id);
    try {
      const { signed_url } = await base44.integrations.Core.CreateFileSignedUrl({ file_uri: pdf.file_uri });
      const a = document.createElement('a');
      a.href = signed_url;
      a.download = pdf.file_name;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } finally {
      setDownloadingId(null);
    }
  };

  const downloadZip = async () => {
    setZipping(true);
    try {
      const zip = new JSZip();
      for (const pdf of pdfs) {
        const { signed_url } = await base44.integrations.Core.CreateFileSignedUrl({ file_uri: pdf.file_uri });
        const blob = await (await fetch(signed_url)).blob();
        const folder = (pdf.presidio || 'Senza presidio').replace(/[\\/:*?"<>|]/g, '_');
        zip.file(`${folder}/${pdf.file_name}`, blob);
      }
      const content = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(content);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${session.folder_name}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setZipping(false);
    }
  };

  const StatusIcon = status.icon;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <button
        onClick={toggle}
        className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/40"
      >
        <div className="text-muted-foreground">
          {open ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <FileText className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-foreground">{session.original_filename}</p>
          <p className="text-xs text-muted-foreground">
            {moment(session.created_date).format('DD/MM/YYYY HH:mm')} · {session.folder_name}
          </p>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${status.className}`}>
          <StatusIcon className="h-3.5 w-3.5" />
          {status.label}
        </span>
        {session.status === 'completed' && (
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {session.pdf_count} PDF
          </span>
        )}
      </button>

      {open && (
        <div className="border-t border-border bg-muted/20 px-5 py-4">
          {session.status === 'failed' && session.error_message && (
            <p className="mb-3 text-sm text-red-600">{session.error_message}</p>
          )}

          {loadingPdfs ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Caricamento PDF...
            </div>
          ) : pdfs.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Nessun PDF generato per questa sessione.</p>
          ) : (
            <>
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">
                  {pdfs.length} PDF generati
                </p>
                <button
                  onClick={downloadZip}
                  disabled={zipping}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {zipping ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderArchive className="h-4 w-4" />}
                  Scarica ZIP
                </button>
              </div>
              {Object.entries(
                pdfs.reduce((acc, pdf) => {
                  const key = pdf.presidio || 'Senza presidio';
                  (acc[key] = acc[key] || []).push(pdf);
                  return acc;
                }, {})
              ).map(([presidio, items]) => (
                <div key={presidio} className="mb-4 last:mb-0">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{presidio}</p>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {items.map((pdf) => (
                      <div
                        key={pdf.id}
                        className="flex items-center gap-3 rounded-lg border border-border bg-background px-3 py-2.5"
                      >
                        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
                          <FileText className="h-4.5 w-4.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-foreground">{pdf.file_name}</p>
                          <p className="text-xs text-muted-foreground">{pdf.kit_count} kit · {pdf.component_count} componenti</p>
                        </div>
                        <button
                          onClick={() => downloadPdf(pdf)}
                          disabled={downloadingId === pdf.id}
                          className="flex-shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
                          title="Scarica PDF"
                        >
                          {downloadingId === pdf.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}