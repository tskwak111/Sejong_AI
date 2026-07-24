"use client";

/**
 * 토스트 - DESIGN.md v2 §11 모션 허용 목록 3번 (등장 150ms).
 * role="status"로 스크린리더에 알린다. 표시 시간은 호출부가 결정(기본 2초).
 */
import { useEffect } from "react";

export default function Toast({
  message,
  onDone,
  durationMs = 2000,
}: {
  message: string;
  onDone: () => void;
  durationMs?: number;
}) {
  useEffect(() => {
    const t = setTimeout(onDone, durationMs);
    return () => clearTimeout(t);
  }, [onDone, durationMs]);

  return (
    <div
      role="status"
      className="toast-enter fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-btn-s bg-text px-4 py-2.5 text-note text-white shadow-raised"
    >
      {message}
    </div>
  );
}
