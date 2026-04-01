import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function fileIcon(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  const icons: Record<string, string> = {
    md: "📝",
    txt: "📄",
    docx: "📘",
    xlsx: "📊",
    pdf: "📕",
    py: "🐍",
    js: "📜",
    ts: "🔷",
    json: "📋",
    csv: "📈",
    html: "🌐",
    xml: "📰",
    yaml: "⚙️",
    yml: "⚙️",
    sql: "🗃️",
    sh: "⚡",
    bat: "⚡",
  };
  return icons[ext] || "📄";
}

export function agentLabel(agent: string): string {
  const labels: Record<string, string> = {
    hr: "HR Agent",
    accounting: "Accounting Agent",
    manager: "Manager Agent",
    pm: "PM Agent",
    chat: "Assistant",
    document: "Document Agent",
  };
  return labels[agent] || agent;
}

export function agentIcon(agent: string): string {
  const icons: Record<string, string> = {
    hr: "👤",
    accounting: "💰",
    manager: "📋",
    pm: "📦",
    chat: "💬",
    document: "📝",
  };
  return icons[agent] || "🤖";
}

export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("th-TH", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatSessionDate(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "วันนี้";
  if (diffDays === 1) return "เมื่อวาน";
  if (diffDays < 7) return `${diffDays} วันที่แล้ว`;
  return date.toLocaleDateString("th-TH", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function sanitizeHtml(html: string): string {
  if (typeof document === "undefined") return html;
  const temp = document.createElement("div");
  temp.innerHTML = html;
  const scripts = temp.querySelectorAll("script, iframe, object, embed, form");
  scripts.forEach((el) => el.remove());
  const allElements = temp.querySelectorAll("*");
  allElements.forEach((el) => {
    const attrs = el.attributes;
    for (let i = attrs.length - 1; i >= 0; i--) {
      const name = attrs[i].name;
      const value = attrs[i].value;
      if (name.startsWith("on")) {
        el.removeAttribute(name);
      }
      if (
        (name === "href" || name === "src") &&
        /^(data:)/i.test(value)
      ) {
        el.removeAttribute(name);
      }
      if (
        (name === "href" || name === "src") &&
        !/^(https?:|mailto:|tel:|#)/i.test(value)
      ) {
        el.removeAttribute(name);
      }
    }
  });
  return temp.innerHTML;
}
