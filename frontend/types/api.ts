export type Severity = "Normal/Mild" | "Moderate" | "Severe";

export interface SeverityPrediction {
  severity: Severity;
  confidence: number; // 0–1
}

export interface BilateralPrediction {
  left: SeverityPrediction;
  right: SeverityPrediction;
}

export interface LevelPrediction {
  level: string; // e.g. "L1-L2"
  coordinates: { x: number; y: number }; // normalised 0–1 relative to image
  spinal_canal_stenosis: SeverityPrediction;
  neural_foraminal_narrowing: BilateralPrediction;
  subarticular_stenosis: BilateralPrediction;
}

export interface PredictionResult {
  patient_id: string;
  predictions: LevelPrediction[];
  images: {
    "Sagittal T2"?: string | null; // base64 data-URI
    "Sagittal T1"?: string | null;
    "Axial T2"?: string | null;
  };
}
