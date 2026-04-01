"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const FORMATS = [
  { value: "md", label: "Markdown", ext: ".md" },
  { value: "txt", label: "Plain Text", ext: ".txt" },
  { value: "docx", label: "Word", ext: ".docx" },
  { value: "xlsx", label: "Excel", ext: ".xlsx" },
  { value: "pdf", label: "PDF", ext: ".pdf" },
];

interface FormatModalProps {
  isOpen: boolean;
  filename: string;
  agentLabel: string;
  onClose: () => void;
  onConfirm: (format: string) => void;
}

export default function FormatModal({
  isOpen,
  filename,
  agentLabel: label,
  onClose,
  onConfirm,
}: FormatModalProps) {
  const [selected, setSelected] = useState("md");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-bg-secondary rounded-xl border border-border w-[400px] shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            <h2 className="text-base font-semibold text-text-primary">
              💾 บันทึกไฟล์
            </h2>
            <p className="text-xs text-text-secondary mt-0.5">
              {label} · {filename}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-bg-hover text-text-muted transition-colors"
            aria-label="ปิด"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5">
          <p className="text-sm text-text-secondary mb-3">เลือกรูปแบบไฟล์:</p>
          <div className="grid grid-cols-5 gap-2">
            {FORMATS.map((fmt) => (
              <button
                key={fmt.value}
                onClick={() => setSelected(fmt.value)}
                className={cn(
                  "flex flex-col items-center gap-1 px-3 py-3 rounded-lg border transition-colors",
                  selected === fmt.value
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border bg-bg-tertiary text-text-secondary hover:bg-bg-hover"
                )}
              >
                <span className="text-xs font-medium">{fmt.label}</span>
                <span className="text-[10px] text-text-muted">{fmt.ext}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            ยกเลิก
          </button>
          <button
            onClick={() => onConfirm(selected)}
            className="px-4 py-2 text-sm bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
          >
            บันทึก
          </button>
        </div>
      </div>
    </div>
  );
}
