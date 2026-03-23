import { useQuery } from '@tanstack/react-query';
import { fetchResults } from '../api/contracts';

export const useResults = (sessionId?: string) =>
  useQuery({
    queryKey: ['shared-results', sessionId],
    queryFn: async () => {
      if (!sessionId) {
        return null;
      }
      return fetchResults(sessionId);
    },
    enabled: Boolean(sessionId),
    refetchInterval: (query) => (query.state.data ? false : 1500),
  });
