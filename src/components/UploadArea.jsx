import React, { useCallback, useRef, useState } from 'react';
import { UploadCloud, FileSpreadsheet } from 'lucide-react';

export default function UploadArea({ onFile, disabled }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const file = e.dataTransfer.files?.[0];
      if (file) onFile(file);
    },
    [onFile, disabled]
  );

  const handleSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) onFile(file);
    e.target.value = '';
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`group relative cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-200 ${
        dragging
          ? 'border-primary bg-primary/5 scale-[1.01]'
          : 'border-border hover:border-primary/50 hover:bg-muted/40'
      } ${disabled ? 'opacity-60 pointer-events-none' : ''}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls"
        onChange={handleSelect}
        className="hidden"
      />
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform group-hover:scale-110">
        {dragging ? <UploadCloud className="h-8 w-8" /> : <FileSpreadsheet className="h-8 w-8" />}
      </div>
      <p className="mt-4 text-base font-heading font-medium text-foreground">
        Trascina qui il file Excel o clicca per selezionarlo
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Formati supportati: .xlsx, .xls · Fogli richiesti: LISTA KIT, COMPOSIZIONE KIT
      </p>
    </div>
  );
}