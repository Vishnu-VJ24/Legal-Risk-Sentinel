import { useParams } from 'react-router-dom';
import { ResultsDashboard } from '../components/dashboard/ResultsDashboard';
import { useResults } from '../hooks/useResults';

export const ResultsPage = () => {
  const { sessionId } = useParams();
  const { data, error, isLoading } = useResults(sessionId);

  if (error) {
    return (
      <section className="flex flex-1 items-center justify-center py-16">
        <div className="w-full max-w-2xl rounded-[28px] border border-border bg-surface/75 p-10">
          <h1 className="text-3xl font-bold">Shared Results</h1>
          <p className="mt-4 text-risk-critical">We could not load that shared result.</p>
        </div>
      </section>
    );
  }

  if (isLoading || !data) {
    return (
      <section className="flex flex-1 items-center justify-center py-16">
        <div className="w-full max-w-2xl rounded-[28px] border border-border bg-surface/75 p-10">
          <h1 className="text-3xl font-bold">Shared Results</h1>
          <p className="mt-4 text-text-secondary">Loading session {sessionId}…</p>
        </div>
      </section>
    );
  }

  return <div className="py-8"><ResultsDashboard results={data} /></div>;
};
