import { useCallback, useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchResults, uploadContract } from '../api/contracts';
import type { AnalysisResult, PipelineStage } from '../types/contracts';

const progressSteps: Array<{ stage: PipelineStage; max: number }> = [
  { stage: 'parsing', max: 20 },
  { stage: 'extracting', max: 45 },
  { stage: 'scoring', max: 70 },
  { stage: 'explaining', max: 95 },
  { stage: 'done', max: 100 },
];

export const useAnalyzePipeline = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<PipelineStage>('parsing');

  const analyzeMutation = useMutation({
    mutationFn: async (uploadFile: File) => {
      setIsWarmingUp(false);
      const warmingTimer = window.setTimeout(() => {
        setIsWarmingUp(true);
      }, 6000);

      try {
        return await uploadContract(uploadFile);
      } finally {
        window.clearTimeout(warmingTimer);
        setIsWarmingUp(false);
      }
    },
    onSuccess: (data, uploadFile) => {
      console.log('[LexAI] analyze mutation success', data);
      setSessionId(data.session_id);
      setFile(uploadFile);
      setProgress(data.progress_pct);
      setStage(data.pipeline_stage);
    },
    onError: (error) => {
      console.error('[LexAI] analyze mutation error', error);
    },
  });

  const resultsQuery = useQuery({
    queryKey: ['analysis-results', sessionId],
    queryFn: async () => (sessionId ? fetchResults(sessionId) : null),
    enabled: Boolean(sessionId),
    refetchInterval: (query) => (query.state.data ? false : 1200),
  });

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    console.log('[LexAI] session_id stored, polling enabled', { sessionId });
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || resultsQuery.data) {
      if (resultsQuery.data) {
        console.log('[LexAI] results received, stopping polling', resultsQuery.data);
        setProgress(100);
        setStage('done');
      }
      return;
    }

    const timer = window.setInterval(() => {
      setProgress((current) => {
        const next = Math.min(current + 3, 95);
        const nextStage = progressSteps.find((step) => next <= step.max)?.stage ?? 'explaining';
        setStage(nextStage);
        return next;
      });
    }, 400);

    return () => window.clearInterval(timer);
  }, [resultsQuery.data, sessionId]);

  useEffect(() => {
    if (!resultsQuery.error) {
      return;
    }
    console.error('[LexAI] results query error', resultsQuery.error);
  }, [resultsQuery.error]);

  const reset = useCallback(() => {
    setSessionId(null);
    setFile(null);
    setIsWarmingUp(false);
    setProgress(0);
    setStage('parsing');
    analyzeMutation.reset();
  }, [analyzeMutation]);

  return {
    analyze: analyzeMutation.mutate,
    error: analyzeMutation.error ?? resultsQuery.error,
    file,
    isAnalyzing: analyzeMutation.isPending || (!!sessionId && !resultsQuery.data),
    isWarmingUp,
    progress,
    results: resultsQuery.data as AnalysisResult | null | undefined,
    reset,
    stage,
  };
};
