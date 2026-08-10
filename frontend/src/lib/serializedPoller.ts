export interface SerializedPoller {
  stop: () => void;
}

export function startSerializedPolling(
  task: () => Promise<boolean>,
  intervalMs: number,
  onError: (error: unknown) => void,
): SerializedPoller {
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const stop = () => {
    stopped = true;
    if (timer) clearTimeout(timer);
    timer = null;
  };

  const tick = async () => {
    try {
      const shouldContinue = await task();
      if (!shouldContinue) stop();
    } catch (error) {
      onError(error);
    } finally {
      if (!stopped) timer = setTimeout(tick, intervalMs);
    }
  };

  void tick();
  return { stop };
}
