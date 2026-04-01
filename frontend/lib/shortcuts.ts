import { useEffect } from "react";

interface ShortcutConfig {
  onSend?: () => void;
  onClosePanel?: () => void;
  onOpenWorkspace?: () => void;
}

export function useShortcuts({
  onSend,
  onClosePanel,
  onOpenWorkspace,
}: ShortcutConfig) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey && onSend) {
        const target = e.target as HTMLElement;
        if (target.tagName !== "TEXTAREA" && target.tagName !== "INPUT") {
          e.preventDefault();
          onSend();
        }
      }

      if (e.key === "Escape" && onClosePanel) {
        onClosePanel();
      }

      if ((e.ctrlKey || e.metaKey) && e.key === "k" && onOpenWorkspace) {
        e.preventDefault();
        onOpenWorkspace();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onSend, onClosePanel, onOpenWorkspace]);
}
