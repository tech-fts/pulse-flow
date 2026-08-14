import TelemetryStream from "./TelemetryStream";

export default function TelemetryPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 p-6">
        <h1 className="text-2xl font-bold tracking-tight">Telemetry Stream</h1>
      </header>
      <TelemetryStream />
    </main>
  );
}
