import EventIngestForm from "@/components/EventIngestForm";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 p-6">
        <h1 className="text-2xl font-bold tracking-tight">Pulse Flow</h1>
        <p className="text-sm text-slate-400 mt-1">
          Ingest a notification event into the delivery pipeline.
        </p>
      </header>
      <div className="p-6">
        <EventIngestForm />
      </div>
    </main>
  );
}
