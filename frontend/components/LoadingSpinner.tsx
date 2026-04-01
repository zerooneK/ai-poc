"use client";

export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-border border-t-accent rounded-full animate-spin" />
        <p className="text-sm text-text-muted">กำลังโหลด...</p>
      </div>
    </div>
  );
}
