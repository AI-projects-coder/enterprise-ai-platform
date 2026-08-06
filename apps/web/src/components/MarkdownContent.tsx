"use client";

import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

// Shared renderer for any LLM-generated text shown to a user — chat replies,
// job drive results, and anywhere else a raw Gemini response is displayed.
// remarkGfm: tables/strikethrough/task lists (Gemini uses these constantly,
// e.g. the markdown tables in its security-review and cost-estimate replies).
// remarkMath + rehypeKatex: LaTeX (\(...\) / $$...$$) rendering via KaTeX.
// max-w-none overrides typography's default readable-width cap, which would
// otherwise fight with each usage's own container width (chat bubble,
// accordion body, etc.).
export function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Every link in AI-generated content (job drive sources, chat
          // citations, etc.) opens in a new tab — clicking one shouldn't
          // navigate the user away from this app.
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
