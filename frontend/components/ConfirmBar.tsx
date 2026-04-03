"use client";

import { Save, X, Pencil } from "lucide-react";

interface ConfirmBarProps {
  type: "save" | "discard" | "edit" | "replace";
  filename?: string;
  previewText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  onEdit?: () => void;
}

export default function ConfirmBar({
  type,
  filename,
  previewText,
  onConfirm,
  onCancel,
  onEdit,
}: ConfirmBarProps) {
  return (
    <div className="bg-bg-tertiary border-t border-border px-4 py-3 shrink-0">
      <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
        <p className="text-sm text-text-secondary truncate min-w-0">
          {type === "save" && `ต้องการบันทึกไฟล์ "${filename}" ไหม?`}
          {type === "discard" && "ต้องการยกเลิกเอกสารนี้ไหม?"}
          {type === "edit" && "ต้องการแก้ไขเอกสารนี้ไหม?"}
          {type === "replace" && (
            <>
              ✏️ แก้ไขส่วนที่เลือกใน{" "}
              <span className="font-medium text-text-primary">{filename}</span>
              {previewText && (
                <span className="text-text-muted">
                  {" "}— &ldquo;{previewText}&rdquo;
                </span>
              )}
              {" "}พร้อมเขียนทับ — พิมพ์{" "}
              <span className="font-mono text-accent">เขียนทับ</span> หรือกดปุ่ม
            </>
          )}
        </p>
        <div className="flex items-center gap-2 shrink-0">
          {type === "edit" && onEdit && (
            <button
              onClick={onEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary bg-bg-hover rounded transition-colors"
            >
              <Pencil className="w-3.5 h-3.5" />
              แก้ไข
            </button>
          )}
          {type === "save" && (
            <button
              onClick={onConfirm}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-accent hover:bg-accent-hover text-white rounded transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              บันทึก
            </button>
          )}
          {type === "replace" && (
            <button
              onClick={onConfirm}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-accent hover:bg-accent-hover text-white rounded transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              เขียนทับ
            </button>
          )}
          {type === "discard" && (
            <button
              onClick={onConfirm}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-error hover:bg-red-600 text-white rounded transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              ยกเลิก
            </button>
          )}
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            ยกเลิก
          </button>
        </div>
      </div>
    </div>
  );
}
