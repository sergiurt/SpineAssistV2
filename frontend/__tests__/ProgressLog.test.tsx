import { render, screen } from "@testing-library/react";
import { ProgressLog } from "@/components/ProgressLog";

test("renders all log messages", () => {
  render(<ProgressLog messages={["Parsing DICOM...", "Predicting coordinates..."]} done={false} />);
  expect(screen.getByText("Parsing DICOM...")).toBeInTheDocument();
  expect(screen.getByText("Predicting coordinates...")).toBeInTheDocument();
});

test("shows Running indicator when not done", () => {
  render(<ProgressLog messages={["Step one"]} done={false} />);
  expect(screen.getByText("Running...")).toBeInTheDocument();
});

test("does not show Running when done", () => {
  render(<ProgressLog messages={["Step one"]} done={true} />);
  expect(screen.queryByText("Running...")).not.toBeInTheDocument();
});

test("shows Done indicator when complete", () => {
  render(<ProgressLog messages={["All done"]} done={true} />);
  expect(screen.getByText("Done")).toBeInTheDocument();
});

test("renders empty state without crashing", () => {
  render(<ProgressLog messages={[]} done={false} />);
  expect(screen.getByText("Analysis Log")).toBeInTheDocument();
});
