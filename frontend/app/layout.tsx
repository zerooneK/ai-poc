"use client";

import { Inter, JetBrains_Mono } from "next/font/google";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <html lang="th" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-bg-primary text-text-primary overflow-hidden`}
      >
        <div className="flex h-screen w-full">
          {/* Sidebar */}
          <aside
            className={cn(
              "flex flex-col bg-bg-secondary border-r border-border transition-all duration-200 ease-in-out",
              sidebarOpen ? "w-72" : "w-0 overflow-hidden"
            )}
          >
            <div className="flex items-center justify-between p-3 border-b border-border">
              <span className="text-sm font-medium text-text-secondary">
                ไฟล์และเซสชัน
              </span>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1 rounded hover:bg-bg-hover text-text-muted transition-colors"
                aria-label="ปิด sidebar"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              {/* Sidebar content — Phase 3 will populate this */}
              <p className="text-sm text-text-muted text-center mt-8">
                ยังไม่มีไฟล์
              </p>
            </div>
          </aside>

          {/* Main content */}
          <div className="flex flex-col flex-1 min-w-0">
            {/* Navbar */}
            <header className="flex items-center gap-3 px-4 py-2 bg-bg-secondary border-b border-border h-12 shrink-0">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="p-1 rounded hover:bg-bg-hover text-text-muted transition-colors"
                  aria-label="เปิด sidebar"
                >
                  <Menu className="w-5 h-5" />
                </button>
              )}
              <h1 className="text-sm font-semibold text-text-primary truncate">
                AI Assistant POC
              </h1>
              <span className="text-xs text-text-muted ml-auto">
                v0.32.1
              </span>
            </header>

            {/* Page content */}
            <main className="flex-1 overflow-hidden">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
