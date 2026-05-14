import type { LevelPrediction, Severity } from "@/types/api";

const SEVERITY_CLASSES: Record<Severity, string> = {
  "Normal/Mild": "text-green-400",
  "Moderate": "text-yellow-400",
  "Severe": "text-red-400",
};

function Cell({ severity, confidence }: { severity: Severity; confidence: number }) {
  return (
    <td className="p-3 border-b border-slate-800">
      <div className={`font-semibold text-sm ${SEVERITY_CLASSES[severity]}`}>
        {severity}
      </div>
      <div className="text-slate-500 text-xs">{Math.round(confidence * 100)}%</div>
    </td>
  );
}

interface Props {
  predictions: LevelPrediction[];
}

export function SeverityTable({ predictions }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-slate-400 text-xs uppercase tracking-wider">
            <th className="p-3 text-left border-b border-slate-700">Level</th>
            <th className="p-3 text-left border-b border-slate-700">SCS</th>
            <th className="p-3 text-left border-b border-slate-700">NFN Left</th>
            <th className="p-3 text-left border-b border-slate-700">NFN Right</th>
            <th className="p-3 text-left border-b border-slate-700">SS Left</th>
            <th className="p-3 text-left border-b border-slate-700">SS Right</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((item) => (
            <tr key={item.level} className="hover:bg-slate-800/30 transition-colors">
              <td className="p-3 border-b border-slate-800 font-semibold text-slate-300">
                {item.level}
              </td>
              <Cell {...item.spinal_canal_stenosis} />
              <Cell {...item.neural_foraminal_narrowing.left} />
              <Cell {...item.neural_foraminal_narrowing.right} />
              <Cell {...item.subarticular_stenosis.left} />
              <Cell {...item.subarticular_stenosis.right} />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
