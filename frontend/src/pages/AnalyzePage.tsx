import { useEffect, useState } from 'react';
import { AxiosError } from 'axios';
import { FileDropzone } from '../components/analyze/FileDropzone';
import { PipelineProgress } from '../components/analyze/PipelineProgress';
import { SectionHeading } from '../components/common/SectionHeading';
import { ResultsDashboard } from '../components/dashboard/ResultsDashboard';
import { useAnalyzePipeline } from '../hooks/useAnalyzePipeline';

const getErrorMessage = (error: unknown) => {
  const axiosError = error as AxiosError<{ detail?: string }>;
  return axiosError.response?.data?.detail ?? axiosError.message ?? 'Unable to analyze this document.';
};

export const AnalyzePage = () => {
  const [customError, setCustomError] = useState<string>();
  const { analyze, error, file, isAnalyzing, progress, reset, results, stage } = useAnalyzePipeline();
  const [documentUrl, setDocumentUrl] = useState<string>();

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
    <div className="flex flex-1 flex-col gap-8 py-8">
      <SectionHeading
        eyebrow="Analyze Contract"
        title="Upload once. Review every clause with context."
        description="LexAI simulates a production-style contract intelligence pipeline, from parsing to explanation generation, with polished recruiter-demo UX."
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
      {(isAnalyzing || results) && <PipelineProgress progress={progress} stage={stage} />}
      {results ? <ResultsDashboard results={results} documentUrl={documentUrl} isPdf={file?.type === 'application/pdf'} /> : null}
    </div>
  );
};
