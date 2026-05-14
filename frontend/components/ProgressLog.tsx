interface Props {
  messages: string[];
  done: boolean;
}

export function ProgressLog({ messages, done }: Props) {
  return (
    <div className="bg-slate-950 rounded-xl border border-slate-800 p-6 font-mono text-sm min-h-64">
      <div className="text-slate-500 mb-4 text-xs uppercase tracking-widest">
        Analysis Log
      </div>
      {messages.map((msg, i) => (
        <div key={i} className="flex items-center gap-2 text-slate-300 mb-2">
          <span className="text-sky-400">▸</span>
          {msg}
        </div>
      ))}
      {!done && messages.length > 0 && (
        <div className="flex items-center gap-2 text-slate-500 mt-2">
          <span className="animate-pulse">■</span>
          <span>Running...</span>
        </div>
      )}
      {done && (
        <div className="flex items-center gap-2 text-green-400 mt-2 font-semibold">
          <span>✓</span>
          <span>Done</span>
        </div>
      )}
    </div>
  );
}
