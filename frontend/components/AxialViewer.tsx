"use client";
import { useRef, useState } from "react";
import { useImageRect } from "@/hooks/useImageRect";
import type { AxialLevelPrediction, Severity } from "@/types/api";

const SEVERITY_COLORS: Record<Severity, string> = {
  "Normal/Mild": "#22c55e",
  "Moderate": "#eab308",
  "Severe": "#ef4444",
};

interface Props {
  axialLevel: AxialLevelPrediction;
  leftSeverity: Severity;
  rightSeverity: Severity;
}

function Dot({
  x,
  y,
  color,
  rect,
}: {
  x: number;
  y: number;
  color: string;
  rect: { offsetLeft: number; offsetTop: number; renderedWidth: number; renderedHeight: number };
}) {
  const px = rect.offsetLeft + x * rect.renderedWidth;
  const py = rect.offsetTop + y * rect.renderedHeight;
  return (
    <div
      className="absolute pointer-events-none"
      style={{ top: py, left: px, transform: "translate(-50%, -50%)" }}
    >
      <div
        className="w-3 h-3 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
      />
    </div>
  );
}

export function AxialViewer({ axialLevel, leftSeverity, rightSeverity }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const rect = useImageRect(containerRef, naturalSize.width, naturalSize.height);

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-slate-400 font-semibold">{axialLevel.level}</span>
      <div
        ref={containerRef}
        className="relative bg-black rounded-lg overflow-hidden"
        style={{ aspectRatio: "1 / 1" }}
      >
        <img
          src={axialLevel.image}
          alt={axialLevel.level}
          className="w-full h-full object-contain"
          onLoad={(e) => {
            const img = e.currentTarget;
            setNaturalSize({ width: img.naturalWidth, height: img.naturalHeight });
          }}
        />
        {rect.renderedWidth > 0 && (
          <>
            <Dot
              x={axialLevel.left.x}
              y={axialLevel.left.y}
              color={SEVERITY_COLORS[leftSeverity]}
              rect={rect}
            />
            <Dot
              x={axialLevel.right.x}
              y={axialLevel.right.y}
              color={SEVERITY_COLORS[rightSeverity]}
              rect={rect}
            />
          </>
        )}
      </div>
    </div>
  );
}
