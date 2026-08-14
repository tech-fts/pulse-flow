export default function TelemetryLoading() {
  return (
    <div className="p-8 space-y-6 animate-pulse">
      <div className="h-10 w-64 bg-slate-800 rounded-lg" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 bg-slate-900 border border-slate-800 rounded-xl" />
        ))}
      </div>
      <div className="h-80 bg-slate-900 border border-slate-800 rounded-xl" />
    </div>
  );
}
