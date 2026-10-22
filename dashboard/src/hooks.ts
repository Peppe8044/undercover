import { useEffect, useState } from "react";
import { getJson } from "./api";

export function useHash(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const update = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", update);
    return () => {
      window.removeEventListener("hashchange", update);
    };
  }, []);
  return hash;
}

export interface Poll<T> {
  data: T | null;
  error: string | null;
  reload: () => void;
}

export function usePoll<T>(path: string, interval: number | null): Poll<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    const load = () => {
      getJson<T>(path).then(
        (value) => {
          if (active) {
            setData(value);
            setError(null);
          }
        },
        (reason: unknown) => {
          if (active) {
            setError(reason instanceof Error ? reason.message : String(reason));
          }
        },
      );
    };
    load();
    const timer = interval === null ? undefined : setInterval(load, interval);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [path, interval, version]);

  const reload = () => {
    setVersion((current) => current + 1);
  };
  return { data, error, reload };
}
