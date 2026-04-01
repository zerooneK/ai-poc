"use client";

import { useEffect } from "react";
import { X, Trash2 } from "lucide-react";

interface DeleteConfirmModalProps {
  isOpen: boolean;
  filename: string;
  onClose: () => void;
  onConfirm: () => void;
}

export default function DeleteConfirmModal({
  isOpen,
  filename,
  onClose,
  onConfirm,
}: DeleteConfirmModalProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-bg-secondary rounded-xl border border-border w-[380px] shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
            <Trash2 className="w-4 h-4 text-error" />
            ยืนยันการลบ
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-bg-hover text-text-muted transition-colors"
            aria-label="ปิด"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm text-text-secondary">
            คุณต้องการลบไฟล์{" "}
            <span className="text-text-primary font-medium">{filename}</span>{" "}
            ใช่ไหม? การกระทำนี้ไม่สามารถย้อนกลับได้
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            ยกเลิก
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm bg-error hover:bg-red-600 text-white rounded-lg transition-colors"
          >
            ลบไฟล์
          </button>
        </div>
      </div>
    </div>
  );
}
