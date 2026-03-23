import { useMemo, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import type { ClauseResult } from '../../types/contracts';
import { cn } from '../../utils/cn';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerPanelProps {
  clauses: ClauseResult[];
  documentUrl?: string;
  isPdf?: boolean;
  onSelectClause: (clauseId: string) => void;
  selectedClauseId?: string;
}

const highlightColors = {
  low: 'bg-risk-low/30',
  medium: 'bg-risk-medium/30',
  high: 'bg-risk-high/30',
  critical: 'bg-risk-critical/30',
};

export const PdfViewerPanel = ({ clauses, documentUrl, isPdf, onSelectClause, selectedClauseId }: PdfViewerPanelProps) => {
  const [pageNumber, setPageNumber] = useState(1);
  const pageClauses = useMemo(() => clauses.filter((clause) => clause.page_number === pageNumber), [clauses, pageNumber]);

  if (!documentUrl || !isPdf) {
    return (
      <section className="rounded-[28px] border border-border bg-surface/85 p-6">
        <h2 className="text-xl font-semibold">Document Viewer</h2>
        <p className="mt-3 text-sm leading-7 text-text-secondary">
          Upload a PDF to preview highlighted clauses inline. DOCX and TXT analyses still render the full dashboard.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-[28px] border border-border bg-surface/85 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">PDF Viewer</h2>
        <span className="text-sm text-text-secondary">Page {pageNumber}</span>
      </div>
      <div className="overflow-hidden rounded-2xl border border-border bg-white/5 p-3">
        <Document file={documentUrl} loading={<p className="p-8 text-center text-sm text-text-secondary">Loading PDF...</p>}>
          <div className="relative mx-auto w-fit">
            <Page pageNumber={pageNumber} width={460} renderAnnotationLayer={false} renderTextLayer={false} />
            <div className="absolute inset-0">
              {pageClauses.map((clause) => {
                const [x1, y1, x2, y2] = clause.bbox;
                return (
                  <button
                    key={clause.id}
                    type="button"
                    aria-label={`Scroll to ${clause.type}`}
                    onClick={() => onSelectClause(clause.id)}
                    className={cn(
                      'absolute rounded-md border border-white/30 transition',
                      highlightColors[clause.risk_level],
                      selectedClauseId === clause.id && 'ring-2 ring-primary',
                    )}
                    style={{
                      left: `${(x1 / 595) * 100}%`,
                      top: `${(y1 / 842) * 100}%`,
                      width: `${((x2 - x1) / 595) * 100}%`,
                      height: `${((y2 - y1) / 842) * 100}%`,
                    }}
                  />
                );
              })}
            </div>
          </div>
        </Document>
      </div>
      <div className="mt-4 flex gap-3">
        <button
          type="button"
          disabled={pageNumber === 1}
          onClick={() => setPageNumber((page) => Math.max(1, page - 1))}
          className="rounded-full border border-border px-4 py-2 text-sm disabled:opacity-40"
        >
          Previous
        </button>
        <button
          type="button"
          onClick={() => setPageNumber((page) => page + 1)}
          className="rounded-full border border-border px-4 py-2 text-sm"
        >
          Next
        </button>
      </div>
    </section>
  );
};
