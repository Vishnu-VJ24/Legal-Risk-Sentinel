import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MoveHorizontal } from 'lucide-react';
import { Card } from './ui/card';
import { DocumentState } from '../api/adapter';
import { injectSectionMarkdownLinks } from '../lib/sectionUtils';
import { usePipeline } from '../context/PipelineContext';
import { Badge } from './ui/badge';

interface FinalReportProps {
  data: Partial<DocumentState>;
}

type LinkButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

const ReportTable: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="not-prose my-6 overflow-hidden border border-slate-300 bg-white shadow-sm">
    <div className="flex items-center justify-end border-b border-slate-200 bg-slate-50 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
      <MoveHorizontal size={12} className="mr-1.5" aria-hidden="true" />
      Detailed findings
    </div>
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-[13px] leading-5" aria-label="Executive report findings table">
        {children}
      </table>
    </div>
  </div>
);

export const FinalReport: React.FC<FinalReportProps> = ({ data }) => {
  const { setSelectedSectionId } = usePipeline();

  const processedMarkdown = useMemo(() => {
    if (!data.reportMarkdown) return '';
    return injectSectionMarkdownLinks(data.reportMarkdown);
  }, [data.reportMarkdown]);

  return (
    <Card className="border border-slate-200/80 bg-white/95 p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.55)] backdrop-blur">
      <div className="mb-6 flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Executive Review</p>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Contract Risk Report</h2>
        </div>
        {(data.reportData?.overall_risk_score || data.reportData?.overall_document_risk) && (
          <div className="text-right">
            <span className="text-sm font-semibold uppercase text-muted-foreground">Overall Risk Profile</span>
            <div className="mt-1">
              <Badge className="border border-red-200 bg-red-50 text-sm uppercase text-red-600">
                {String(data.reportData!.overall_risk_score || data.reportData!.overall_document_risk)}
              </Badge>
            </div>
          </div>
        )}
      </div>

      <div className="prose prose-slate max-w-none prose-li:my-0 prose-ul:my-2 prose-p:m-0 marker:text-primary">
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          components={{
            table: ({ children }) => <ReportTable>{children}</ReportTable>,
            thead: ({ children }) => <thead className="bg-slate-900 text-white">{children}</thead>,
            tbody: ({ children }) => <tbody className="divide-y divide-slate-200">{children}</tbody>,
            tr: ({ children }) => <tr className="align-top even:bg-slate-50/80 hover:bg-sky-50/50">{children}</tr>,
            th: ({ children }) => (
              <th scope="col" className="border-b border-slate-700 px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-white">
                {children}
              </th>
            ),
            td: ({ children }) => <td className="max-w-[28rem] break-words px-4 py-3 align-top text-slate-700">{children}</td>,
            a: ({ href, children, ...props }) => {
              if (href?.startsWith('section://') || href?.startsWith('#')) {
                const sectionId = href.replace('section://', '').replace('#', '');
                const { ...restProps } = props as LinkButtonProps;
                if ('target' in restProps) delete restProps.target;
                
                return (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      setSelectedSectionId(sectionId);
                    }}
                    className="mx-1 inline-flex cursor-pointer items-center rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 align-baseline font-semibold text-sky-700 transition-colors hover:border-sky-300 hover:text-sky-800"
                    {...restProps}
                  >
                    {children}
                  </button>
                );
              }
              return <span className="font-semibold text-blue-700">{children}</span>;
            }
          }}
        >
          {processedMarkdown}
        </ReactMarkdown>
      </div>
    </Card>
  );
};
