import jsPDF from 'jspdf';
import type { AnalysisResult, ClauseResult } from '../../types/contracts';

interface ExportBarProps {
  results?: AnalysisResult | null;
}

const buildShareUrl = (sessionId: string) => `${window.location.origin}/Legal-Risk-Sentinel/results/${sessionId}`;

const addWrappedText = (
  doc: jsPDF,
  text: string,
  x: number,
  y: number,
  width: number,
  lineHeight = 6,
) => {
  const lines = doc.splitTextToSize(text, width);
  doc.text(lines, x, y);
  return y + lines.length * lineHeight;
};

const renderClauseSection = (doc: jsPDF, clause: ClauseResult, startY: number) => {
  let y = startY;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  y = addWrappedText(
    doc,
    `${clause.type} | Risk ${clause.risk_score.toFixed(1)} (${clause.risk_level.toUpperCase()}) | Page ${clause.page_number}`,
    16,
    y,
    178,
  );

  if (clause.section_title) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    y = addWrappedText(doc, `Section: ${clause.section_title}`, 16, y + 1, 178, 5);
  }

  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  y = addWrappedText(doc, 'Clause Text', 16, y + 3, 178, 5);
  doc.setFont('helvetica', 'normal');
  y = addWrappedText(doc, clause.text, 16, y + 1, 178);

  doc.setFont('helvetica', 'bold');
  y = addWrappedText(doc, 'Explanation', 16, y + 3, 178, 5);
  doc.setFont('helvetica', 'normal');
  y = addWrappedText(doc, clause.explanation, 16, y + 1, 178);

  if (clause.renegotiation_suggestion) {
    doc.setFont('helvetica', 'bold');
    y = addWrappedText(doc, 'Negotiation Suggestion', 16, y + 3, 178, 5);
    doc.setFont('helvetica', 'normal');
    y = addWrappedText(doc, clause.renegotiation_suggestion, 16, y + 1, 178);
  }

  if (clause.similar_safe_clause) {
    doc.setFont('helvetica', 'bold');
    y = addWrappedText(doc, 'Safer Clause Pattern', 16, y + 3, 178, 5);
    doc.setFont('helvetica', 'normal');
    y = addWrappedText(doc, clause.similar_safe_clause, 16, y + 1, 178);
  }

  doc.setFont('helvetica', 'normal');
  doc.setTextColor(90, 90, 90);
  y = addWrappedText(
    doc,
    `Risk axes | Liability: ${clause.risk_axes.liability}, Indemnity: ${clause.risk_axes.indemnity}, IP: ${clause.risk_axes.ip_rights}, Termination: ${clause.risk_axes.termination}`,
    16,
    y + 3,
    178,
    5,
  );
  doc.setTextColor(20, 20, 20);
  return y + 6;
};

const downloadPdfReport = (results: AnalysisResult) => {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const clauses = [...(results.clauses ?? [])].sort((a, b) => b.risk_score - a.risk_score);
  let y = 18;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(22);
  doc.text('LexAI Contract Review Report', 16, y);

  y += 10;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(11);
  y = addWrappedText(doc, `Document: ${results.document_name}`, 16, y, 178);
  y = addWrappedText(doc, `Session ID: ${results.session_id}`, 16, y + 1, 178, 5);
  y = addWrappedText(
    doc,
    `Overall Risk Score: ${results.overall_risk_score} | Total Clauses Reviewed: ${results.total_clauses} | Processing Time: ${results.processing_time_seconds.toFixed(1)}s`,
    16,
    y + 1,
    178,
  );
  y = addWrappedText(
    doc,
    `Risk Distribution | Critical: ${results.risk_distribution.critical}, High: ${results.risk_distribution.high}, Medium: ${results.risk_distribution.medium}, Low: ${results.risk_distribution.low}`,
    16,
    y + 1,
    178,
  );

  for (const clause of clauses) {
    if (y > 245) {
      doc.addPage();
      y = 18;
    }
    y = renderClauseSection(doc, clause, y + 5);
  }

  doc.save(`${results.document_name.replace(/\.[^.]+$/, '') || 'lexai-report'}-report.pdf`);
};

export const ExportBar = ({ results }: ExportBarProps) => {
  const clauses = results?.clauses ?? [];
  const sessionId = results?.session_id ?? '';

  const downloadReport = () => {
    if (!results) {
      return;
    }
    downloadPdfReport(results);
  };

  const copyHighRiskClauses = async () => {
    const content = clauses
      .filter((clause) => clause.risk_score >= 7)
      .map(
        (clause) =>
          `${clause.section_title ? `${clause.section_title}\n` : ''}${clause.type}\n${clause.text}\nExplanation: ${clause.explanation}`,
      )
      .join('\n\n');
    await navigator.clipboard.writeText(content);
  };

  const shareResults = async () => {
    const url = buildShareUrl(sessionId);
    await navigator.clipboard.writeText(url);
  };

  return (
    <section className="flex flex-col gap-3 rounded-[28px] border border-border bg-surface/85 p-5 sm:flex-row">
      <button type="button" onClick={downloadReport} className="rounded-full bg-primary px-5 py-3 text-sm font-semibold text-white">
        Download PDF Report
      </button>
      <button type="button" onClick={copyHighRiskClauses} className="rounded-full border border-border px-5 py-3 text-sm font-semibold">
        Copy all high-risk clauses
      </button>
      <button type="button" onClick={shareResults} className="rounded-full border border-border px-5 py-3 text-sm font-semibold">
        Share results
      </button>
    </section>
  );
};
