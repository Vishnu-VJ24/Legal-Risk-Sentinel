import type { AnalysisResult } from '../../types/contracts';

interface ExportBarProps {
  results: AnalysisResult;
}

export const ExportBar = ({ results }: ExportBarProps) => {
  const downloadReport = () => {
    const reportWindow = window.open('', '_blank', 'noopener,noreferrer');
    if (!reportWindow) {
      return;
    }

    const clauseMarkup = results.clauses
      .map(
        (clause) => `
          <section style="margin-bottom:24px;padding:16px;border:1px solid #d9dbe8;border-radius:16px;">
            <h3 style="margin:0 0 8px;">${clause.type} • Risk ${clause.risk_score.toFixed(1)} (${clause.risk_level})</h3>
            <p style="margin:0 0 8px;line-height:1.6;">${clause.text}</p>
            <p style="margin:0 0 8px;line-height:1.6;"><strong>Explanation:</strong> ${clause.explanation}</p>
            <p style="margin:0;line-height:1.6;"><strong>Suggestion:</strong> ${clause.renegotiation_suggestion ?? 'N/A'}</p>
          </section>
        `,
      )
      .join('');

    reportWindow.document.write(`
      <html>
        <head>
          <title>LexAI Report</title>
          <style>
            body { font-family: Inter, Arial, sans-serif; padding: 32px; color: #111827; }
            h1 { margin-bottom: 8px; }
            p { color: #4b5563; }
          </style>
        </head>
        <body>
          <h1>LexAI Contract Analysis Report</h1>
          <p>Document: ${results.document_name}</p>
          <p>Overall Risk Score: ${results.overall_risk_score} | Total Clauses: ${results.total_clauses}</p>
          ${clauseMarkup}
        </body>
      </html>
    `);
    reportWindow.document.close();
    reportWindow.focus();
    reportWindow.print();
  };

  const copyHighRiskClauses = async () => {
    const content = results.clauses
      .filter((clause) => clause.risk_score >= 7)
      .map((clause) => `${clause.type}\n${clause.text}`)
      .join('\n\n');
    await navigator.clipboard.writeText(content);
  };

  const shareResults = async () => {
    const url = `${window.location.origin}/results/${results.session_id}`;
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
