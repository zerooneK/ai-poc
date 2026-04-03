"use client";

import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ChevronLeft, ChevronRight } from "lucide-react";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerProps {
  url: string;
}

export default function PdfViewer({ url }: PdfViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfError, setPdfError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(388);

  useEffect(() => {
    setPageNumber(1);
    setNumPages(0);
    setPdfError(false);
  }, [url]);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) setContainerWidth(width);
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  if (pdfError) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted text-sm px-6 text-center">
        <span className="text-3xl opacity-40">❌</span>
        ไม่สามารถแสดงตัวอย่าง PDF ได้
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div ref={containerRef} className="flex-1 overflow-y-auto bg-bg-primary">
        <Document
          file={url}
          onLoadSuccess={({ numPages }) => setNumPages(numPages)}
          onLoadError={() => setPdfError(true)}
          loading={
            <div className="flex flex-col items-center justify-center h-64 gap-2 text-text-muted text-sm">
              <span className="text-3xl opacity-40">📄</span>
              กำลังโหลด PDF...
            </div>
          }
        >
          <Page
            pageNumber={pageNumber}
            width={containerWidth}
            renderTextLayer={true}
            renderAnnotationLayer={true}
          />
        </Document>
      </div>

      {numPages > 0 && (
        <div className="flex items-center justify-between px-4 py-2 border-t border-border shrink-0">
          <button
            onClick={() => setPageNumber((p) => Math.max(p - 1, 1))}
            disabled={pageNumber <= 1}
            className="p-1 rounded hover:bg-bg-hover text-text-muted disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs text-text-muted">
            หน้า {pageNumber} / {numPages}
          </span>
          <button
            onClick={() => setPageNumber((p) => Math.min(p + 1, numPages))}
            disabled={pageNumber >= numPages}
            className="p-1 rounded hover:bg-bg-hover text-text-muted disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
