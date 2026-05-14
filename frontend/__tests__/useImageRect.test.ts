import { renderHook } from "@testing-library/react";
import { useImageRect } from "@/hooks/useImageRect";

// Mock ResizeObserver (not available in jsdom)
const observeMock = jest.fn();
const disconnectMock = jest.fn();
beforeEach(() => {
  global.ResizeObserver = jest.fn().mockImplementation(() => ({
    observe: observeMock,
    disconnect: disconnectMock,
  }));
});

function makeRef(width: number, height: number) {
  return {
    current: {
      getBoundingClientRect: () => ({
        width, height, top: 0, left: 0, right: width, bottom: height,
      }),
    },
  };
}

test("returns zero rect when ref is null", () => {
  const { result } = renderHook(() =>
    useImageRect({ current: null } as any, 400, 300)
  );
  expect(result.current.renderedWidth).toBe(0);
  expect(result.current.renderedHeight).toBe(0);
  expect(result.current.offsetTop).toBe(0);
  expect(result.current.offsetLeft).toBe(0);
});

test("returns zero rect when naturalWidth is 0", () => {
  const { result } = renderHook(() =>
    useImageRect(makeRef(200, 200) as any, 0, 0)
  );
  expect(result.current.renderedWidth).toBe(0);
});

test("letterboxes a wide image (2:1) in a square container (1:1)", () => {
  // Image 400×200 in container 200×200
  // → renderedWidth=200, renderedHeight=100, offsetTop=50, offsetLeft=0
  const { result } = renderHook(() =>
    useImageRect(makeRef(200, 200) as any, 400, 200)
  );
  expect(result.current.renderedWidth).toBe(200);
  expect(result.current.renderedHeight).toBe(100);
  expect(result.current.offsetTop).toBe(50);
  expect(result.current.offsetLeft).toBe(0);
});

test("pillarboxes a tall image (1:2) in a square container (1:1)", () => {
  // Image 100×200 in container 200×200
  // → renderedWidth=100, renderedHeight=200, offsetTop=0, offsetLeft=50
  const { result } = renderHook(() =>
    useImageRect(makeRef(200, 200) as any, 100, 200)
  );
  expect(result.current.renderedWidth).toBe(100);
  expect(result.current.renderedHeight).toBe(200);
  expect(result.current.offsetTop).toBe(0);
  expect(result.current.offsetLeft).toBe(50);
});

test("square image in square container fills exactly", () => {
  const { result } = renderHook(() =>
    useImageRect(makeRef(300, 300) as any, 300, 300)
  );
  expect(result.current.renderedWidth).toBe(300);
  expect(result.current.renderedHeight).toBe(300);
  expect(result.current.offsetTop).toBe(0);
  expect(result.current.offsetLeft).toBe(0);
});
