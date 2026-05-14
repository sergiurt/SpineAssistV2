"use client";
import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import { MriViewer } from "@/components/MriViewer";
import { ProgressLog } from "@/components/ProgressLog";
import { SeverityTable } from "@/components/SeverityTable";
import type { PredictionResult } from "@/types/api";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:7860";

type PageState = "idle" | "processing" | "done" | "error";

export default function AnalyzePage() {
  const [state, setState] = useState<PageState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    if (!f.name.endsWith(".zip")) {
      alert("Please upload a .zip file containing DICOM files.");
      return;
    }
    setFile(f);
    setLogs([]);
    setResult(null);
    setError(null);
    setState("idle");
  }, []);

  const handleAnalyze = async () => {
    if (!file) return;
    setState("processing");
    setLogs([]);
    setResult(null);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${BACKEND_URL}/api/predict/stream`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail ?? "Request failed");
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const eventLine = part.split("\n").find((l) => l.startsWith("event:"));
          const dataLine = part.split("\n").find((l) => l.startsWith("data:"));
          if (!eventLine || !dataLine) continue;
          const eventType = eventLine.replace("event:", "").trim();
          const data = JSON.parse(dataLine.replace("data:", "").trim());
          if (eventType === "progress") {
            setLogs((prev) => [...prev, data.message]);
          } else if (eventType === "result") {
            setResult(data);
            setState("done");
          } else if (eventType === "error") {
            throw new Error(data.message);
          }
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  };

  const reset = () => {
    setFile(null);
    setLogs([]);
    setResult(null);
    setError(null);
    setState("idle");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-sky-400 font-bold text-xl tracking-tight">
          SpineAssist
        </Link>
        <span className="text-slate-400 text-sm">Lumbar Spine Analysis</span>
      </header>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {/* IDLE / ERROR */}
        {(state === "idle" || state === "error") && (
          <div className="flex flex-col items-center justify-center h-[70vh] gap-6">
            {error && (
              <div className="bg-red-950 border border-red-800 text-red-300 px-6 py-3 rounded-lg text-sm max-w-md text-center">
                {error}
              </div>
            )}
            <div
              className={`w-full max-w-lg border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors ${
                file
                  ? "border-sky-500 bg-sky-950/20"
                  : "border-slate-700 hover:border-slate-500"
              }`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const f = e.dataTransfer.files[0];
                if (f) handleFile(f);
              }}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFile(e.target.files[0]);
                }}
              />
              {file ? (
                <p className="text-sky-300 font-medium">{file.name}</p>
              ) : (
                <>
                  <p className="text-slate-300 font-medium">
                    Drop patient DICOM .zip here
                  </p>
                  <p className="text-slate-500 text-sm mt-1">or click to browse</p>
                </>
              )}
            </div>
            {file && (
              <button
                onClick={handleAnalyze}
                className="bg-sky-500 hover:bg-sky-600 text-white font-semibold px-8 py-3 rounded-xl transition-colors"
              >
                Run Analysis
              </button>
            )}
          </div>
        )}

        {/* PROCESSING */}
        {state === "processing" && (
          <div className="max-w-2xl mx-auto mt-16">
            <ProgressLog messages={logs} done={false} />
          </div>
        )}

        {/* RESULTS */}
        {state === "done" && result && (
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                Patient{" "}
                <span className="text-sky-400">{result.patient_id}</span>
              </h2>
              <button
                onClick={reset}
                className="text-slate-400 hover:text-white text-sm border border-slate-700 px-4 py-2 rounded-lg transition-colors"
              >
                Analyse another scan
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
                <h3 className="text-slate-300 font-semibold mb-4">MRI Views</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {(["Sagittal T2", "Sagittal T1", "Axial T2"] as const).map(
                    (view) => {
                      const src = result.images[view];
                      if (!src) return null;
                      return (
                        <MriViewer
                          key={view}
                          imageSrc={src}
                          predictions={
                            view.includes("Sagittal") ? result.predictions : []
                          }
                          title={view}
                        />
                      );
                    }
                  )}
                </div>
              </div>

              <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
                <h3 className="text-slate-300 font-semibold mb-4">
                  Severity Assessment
                </h3>
                <SeverityTable predictions={result.predictions} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
