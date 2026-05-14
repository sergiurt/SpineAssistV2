import { render, screen } from "@testing-library/react";
import { SeverityTable } from "@/components/SeverityTable";
import type { LevelPrediction } from "@/types/api";

const mockPredictions: LevelPrediction[] = [
  {
    level: "L1-L2",
    coordinates: { x: 0.5, y: 0.2 },
    spinal_canal_stenosis: { severity: "Normal/Mild", confidence: 0.92 },
    neural_foraminal_narrowing: {
      left: { severity: "Moderate", confidence: 0.71 },
      right: { severity: "Normal/Mild", confidence: 0.88 },
    },
    subarticular_stenosis: {
      left: { severity: "Severe", confidence: 0.80 },
      right: { severity: "Normal/Mild", confidence: 0.95 },
    },
  },
];

test("renders level label", () => {
  render(<SeverityTable predictions={mockPredictions} />);
  expect(screen.getByText("L1-L2")).toBeInTheDocument();
});

test("renders all five column headers", () => {
  render(<SeverityTable predictions={mockPredictions} />);
  expect(screen.getByText("SCS")).toBeInTheDocument();
  expect(screen.getByText("NFN Left")).toBeInTheDocument();
  expect(screen.getByText("NFN Right")).toBeInTheDocument();
  expect(screen.getByText("SS Left")).toBeInTheDocument();
  expect(screen.getByText("SS Right")).toBeInTheDocument();
});

test("renders all severity values", () => {
  render(<SeverityTable predictions={mockPredictions} />);
  // Multiple cells may have Normal/Mild — just check all expected severities appear
  const normalMild = screen.getAllByText("Normal/Mild");
  expect(normalMild.length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("Moderate")).toBeInTheDocument();
  expect(screen.getByText("Severe")).toBeInTheDocument();
});

test("renders confidence as rounded percentage", () => {
  render(<SeverityTable predictions={mockPredictions} />);
  expect(screen.getByText("92%")).toBeInTheDocument();
  expect(screen.getByText("71%")).toBeInTheDocument();
});

test("renders all 5 level rows for full prediction set", () => {
  const fiveLevels: LevelPrediction[] = ["L1-L2","L2-L3","L3-L4","L4-L5","L5-S1"].map(
    (level) => ({
      level,
      coordinates: { x: 0.5, y: 0.3 },
      spinal_canal_stenosis: { severity: "Normal/Mild", confidence: 0.9 },
      neural_foraminal_narrowing: {
        left: { severity: "Normal/Mild", confidence: 0.9 },
        right: { severity: "Normal/Mild", confidence: 0.9 },
      },
      subarticular_stenosis: {
        left: { severity: "Normal/Mild", confidence: 0.9 },
        right: { severity: "Normal/Mild", confidence: 0.9 },
      },
    })
  );
  render(<SeverityTable predictions={fiveLevels} />);
  expect(screen.getByText("L3-L4")).toBeInTheDocument();
  expect(screen.getByText("L5-S1")).toBeInTheDocument();
});
