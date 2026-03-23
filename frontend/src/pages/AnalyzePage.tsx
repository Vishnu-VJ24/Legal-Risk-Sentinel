import { useEffect, useState } from 'react';
import { AxiosError } from 'axios';
import { useQuery } from '@tanstack/react-query';
import { checkApiHealth } from '../api/contracts';
import { FileDropzone } from '../components/analyze/FileDropzone';
import { PipelineProgress } from '../components/analyze/PipelineProgress';
import { SectionHeading } from '../components/common/SectionHeading';
import { ResultsDashboard } from '../components/dashboard/ResultsDashboard';
import { Vortex } from '../components/ui/Vortex';
import { useAnalyzePipeline } from '../hooks/useAnalyzePipeline';

const getErrorMessage = (error: unknown) => {
  const axiosError = error as AxiosError<{ detail?: string }>;
  return axiosError.response?.data?.detail ?? axiosError.message ?? 'Unable to analyze this document.';
};

export const AnalyzePage = () => {
  const [customError, setCustomError] = useState<string>();
  const { analyze, error, file, isAnalyzing, isWarmingUp, progress, reset, results, stage } = useAnalyzePipeline();
  const [documentUrl, setDocumentUrl] = useState<string>();

  const healthQuery = useQuery({
    queryKey: ['api-health'],
    queryFn: checkApiHealth,
    retry: 1,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!file) {
      setDocumentUrl(undefined);
      return;
    }
    const nextUrl = URL.createObjectURL(file);
    setDocumentUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [file]);

  return (
    <div className="relative flex min-h-[calc(100vh-72px)] flex-1 flex-col overflow-hidden bg-[#07070c]">
      <Vortex
        particleCount={300}
        baseHue={296}
        containerClassName="absolute inset-0 min-h-full"
        className="hidden"
      />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(191,90,242,0.16),transparent_30%),radial-gradient(circle_at_80%_18%,rgba(236,72,153,0.12),transparent_24%),linear-gradient(180deg,rgba(7,7,12,0.24)_0%,rgba(7,7,12,0.72)_45%,rgba(7,7,12,0.92)_100%)]" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Analyze Contract"
          title="Upload once. Review every clause with context."
          description="LexAI simulates a production-style contract intelligence pipeline, from parsing to explanation generation, with a polished review workflow."
        />
        <FileDropzone
          disabled={isAnalyzing}
          error={error ? getErrorMessage(error) : customError}
          onSelect={(selectedFile) => {
            reset();
            setCustomError(undefined);
            analyze(selectedFile, {
              onError: (uploadError) => setCustomError(getErrorMessage(uploadError)),
            });
          }}
        />
        {healthQuery.isError ? (
          <p className="text-sm text-risk-critical">
            Backend is unreachable. Verify the Space is running and `VITE_API_BASE_URL` points to the live API.
          </p>
        ) : null}
        {(isAnalyzing || results) && <PipelineProgress isWarmingUp={isWarmingUp} progress={progress} stage={stage} />}
        {results ? <ResultsDashboard results={results} documentUrl={documentUrl} isPdf={file?.type === 'application/pdf'} /> : null}
      </div>
    </div>
  );
};
