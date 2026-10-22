import { usePoll } from "./hooks";

export function Instructions() {
  const { data, error } = usePoll<{ text: string }>("/api/instructions", null);

  if (!data) {
    return error ? (
      <p role="alert">The backend can't be reached: {error}</p>
    ) : (
      <p>Loading the instructions</p>
    );
  }

  return (
    <section>
      <h1>Agent instructions</h1>
      <p className="muted">
        Read only. The agent works every claim from these instructions, which
        end with the policy wording.
      </p>
      <pre className="panel instructions">{data.text}</pre>
    </section>
  );
}
