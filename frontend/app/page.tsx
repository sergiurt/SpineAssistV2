import Link from "next/link";

const CONDITIONS = [
  {
    abbr: "SCS",
    name: "Spinal Canal Stenosis",
    description:
      "Narrowing of the spinal canal that can compress the spinal cord or nerve roots, assessed at each lumbar level.",
  },
  {
    abbr: "NFN",
    name: "Neural Foraminal Narrowing",
    description:
      "Narrowing of the openings where spinal nerves exit the canal, assessed separately for left and right sides.",
  },
  {
    abbr: "SS",
    name: "Subarticular Stenosis",
    description:
      "Narrowing beneath the facet joints that can compress nerve roots in the lateral recess, assessed for both sides.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 px-8 py-4 flex items-center justify-between">
        <span className="text-sky-400 font-bold text-xl tracking-tight">
          SpineAssist
        </span>
        <Link
          href="/analyze"
          className="bg-sky-500 hover:bg-sky-600 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
        >
          Try Demo
        </Link>
      </header>

      <main className="max-w-5xl mx-auto px-8 py-24">
        {/* Hero */}
        <div className="text-center mb-20">
          <h1 className="text-5xl font-bold tracking-tight mb-6 leading-tight">
            AI-Powered{" "}
            <span className="text-sky-400">Lumbar Spine</span> Analysis
          </h1>
          <p className="text-slate-400 text-xl max-w-2xl mx-auto leading-relaxed">
            Upload a patient MRI scan and get instant severity predictions across
            five lumbar vertebral levels — powered by models trained on the RSNA
            2024 competition dataset.
          </p>
          <Link
            href="/analyze"
            className="inline-block mt-10 bg-sky-500 hover:bg-sky-600 text-white font-semibold text-lg px-10 py-4 rounded-xl transition-colors"
          >
            Try the Demo →
          </Link>
        </div>

        {/* Condition cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-24">
          {CONDITIONS.map((c) => (
            <div
              key={c.abbr}
              className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
            >
              <span className="text-sky-400 font-mono text-sm font-bold">
                {c.abbr}
              </span>
              <h3 className="text-white font-semibold mt-2 mb-3">{c.name}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                {c.description}
              </p>
            </div>
          ))}
        </section>

        {/* Footer attribution */}
        <section className="border-t border-slate-800 pt-12 text-center text-slate-500 text-sm">
          <p>
            Models trained on the{" "}
            <a
              href="https://www.kaggle.com/competitions/rsna-2024-lumbar-spine-degenerative-classification"
              className="text-sky-400 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              RSNA 2024 Lumbar Spine Degenerative Classification
            </a>{" "}
            competition. Weights by{" "}
            <a
              href="https://www.kaggle.com/theoviel"
              className="text-sky-400 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Theo Viel
            </a>
            . For academic demonstration purposes only.
          </p>
        </section>
      </main>
    </div>
  );
}
