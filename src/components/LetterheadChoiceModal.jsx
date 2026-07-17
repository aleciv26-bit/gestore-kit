import React from 'react';
import { Loader2, X, FileText } from 'lucide-react';

export default function LetterheadChoiceModal({ fileName, loading, onChoose, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-2xl bg-card p-6 shadow-2xl">
        <div className="mb-1 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <h3 className="font-heading text-lg font-semibold text-foreground">Carta intestata</h3>
          </div>
          <button
            onClick={onCancel}
            disabled={loading}
            className="text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="mb-5 text-sm text-muted-foreground">
          Seleziona la carta intestata da applicare ai PDF di{' '}
          <span className="font-medium text-foreground">{fileName}</span>.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => onChoose('HE')}
            disabled={loading}
            className="flex flex-col items-center gap-2 rounded-xl border border-border bg-background px-4 py-6 transition-colors hover:border-primary hover:bg-primary/5 disabled:opacity-50"
          >
            <span className="font-heading text-base font-semibold text-foreground">HE</span>
            <span className="text-center text-xs text-muted-foreground">Hospital Engineering</span>
          </button>
          <button
            onClick={() => onChoose('SIS')}
            disabled={loading}
            className="flex flex-col items-center gap-2 rounded-xl border border-border bg-background px-4 py-6 transition-colors hover:border-primary hover:bg-primary/5 disabled:opacity-50"
          >
            <span className="font-heading text-base font-semibold text-foreground">SIS</span>
            <span className="text-center text-xs text-muted-foreground">Surgical Instruments Services</span>
          </button>
        </div>
        {loading && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Caricamento carta intestata…
          </div>
        )}
      </div>
    </div>
  );
}