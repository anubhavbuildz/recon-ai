import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ExternalLink } from 'lucide-react';
export default function Markdown({ children, inline = false }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ table: ({ children }) => <div className="markdown-table-scroll" role="region" aria-label="Response table" tabIndex={0}><table>{children}</table></div>, p: ({ children }) => inline ? <span className="markdown-fragment">{children}</span> : <p>{children}</p>, a: ({ children, href }) => {
    // Resource links are rendered only through structured tokens below.
    if (!href || !/^https?:\/\//i.test(href)) return <span>{children}</span>;
    return <a href={href} target="_blank" rel="noopener noreferrer">{children}<ExternalLink size={12}/></a>;
  }, img: () => <span>[Image omitted]</span> }}>{children}</ReactMarkdown>;
}

