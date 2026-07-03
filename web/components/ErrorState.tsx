interface ErrorStateProps {
  error: string | null;
}

export default function ErrorState({ error }: ErrorStateProps) {
  return (
    <div>
      <p className="rounded-md border border-red-300 bg-red-50 px-4 py-3 font-medium text-red-800">
        Pipeline failed.
      </p>
      {error && (
        <details className="mt-4">
          <summary className="cursor-pointer text-secondary select-none">
            Error details
          </summary>
          <pre className="mt-2 overflow-x-auto rounded-md border border-card-border bg-card p-4 text-xs text-text whitespace-pre-wrap">
            {error}
          </pre>
        </details>
      )}
    </div>
  );
}
