"use client";
import { useRef, useState } from "react";
import { useImageRect } from "@/hooks/useImageRect";
import type { LevelPrediction, Severity } from "@/types/api";

const SEVERITY_COLORS: Record<Severity, string> = {
  "Normal/Mild": "#22c55e",
  "Moderate": "#eab308",
  "Severe": "#ef4444",
};

const SEVERITY_ORDER: Record<Severity, number> = {
  "Normal/Mild": 0,
  "Moderate": 1,
  "Severe": 2,
};

function worstSeverity(level: LevelPrediction): Severity {
  const all: Severity[] = [
    level.spinal_canal_stenosis.severity,
    level.neural_foraminal_narrowing.left.severity,
    level.neural_foraminal_narrowing.right.severity,
    level.subarticular_stenosis.left.severity,
    level.subarticular_stenosis.right.severity,
  ];
  return all.reduce((worst, s) =>
    SEVERITY_ORDER[s] > SEVERITY_ORDER[worst] ? s : worst
  );
}

interface Props {
  imageSrc: string;
  predictions: LevelPrediction[];
  title: string;
}

export function MriViewer({ imageSrc, predictions, title }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const rect = useImageRect(containerRef, naturalSize.width, naturalSize.height);

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm text-slate-400 font-semibold">{title}</span>
      <div
        ref={containerRef}
        className="relative bg-black rounded-lg overflow-hidden"
        style={{ aspectRatio: "1 / 1" }}
      >
        <img
          src={imageSrc}
          alt={title}
          className="w-full h-full object-contain"
          onLoad={(e) => {
            const img = e.currentTarget;
            setNaturalSize({ width: img.naturalWidth, height: img.naturalHeight });
          }}
        />
        {rect.renderedWidth > 0 &&
          predictions.map((level) => {
            const dotX = rect.offsetLeft + level.coordinates.x * rect.renderedWidth;
            const dotY = rect.offsetTop + level.coordinates.y * rect.renderedHeight;
            const color = SEVERITY_COLORS[worstSeverity(level)];
            return (
              <div
                key={level.level}
                className="absolute flex items-center pointer-events-none"
                style={{
                  top: dotY,
                  left: dotX,
                  transform: "translate(-50%, -50%)",
                }}
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{
                    backgroundColor: color,
                    boxShadow: `0 0 8px ${color}`,
                  }}
                />
                <span className="ml-2 text-xs font-bold bg-black/70 px-1.5 py-0.5 rounded text-white whitespace-nowrap">
                  {level.level}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
}
