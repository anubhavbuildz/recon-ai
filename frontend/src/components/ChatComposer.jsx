import React from 'react';
import { AlertCircle, Database, Box, X, Paperclip, LoaderCircle, ArrowUp } from 'lucide-react';
import { structuredChat } from '../api';
import { resourceKey } from '../resources';

export default function ChatComposer({ chatError, send, attachments, sending, setAttachments, composer, prompt, setPrompt, inventoryReady, setSidebar }) {
  return (<div className="composer-dock">
        {chatError && <div role="alert" className="chat-error"><AlertCircle size={16}/><span>{chatError} Your question is restored below so you can retry.</span></div>}
        {!structuredChat && <p className="backend-notice"><Database size={14}/>Answers use the configured S3 document. Each question is analyzed independently.</p>}
        <form className="composer" onSubmit={send}><div className="attachment-chips">{attachments.map(resource => <span className="attachment-chip" key={resourceKey(resource)} title={`${resource.account_id} · ${resource.region}`}><Box size={14}/>{resource.name || resource.resource_id}<small>{resource.region}</small><button type="button" disabled={sending} aria-label={`Remove ${resource.name || resource.resource_id}`} onClick={() => setAttachments(previous => previous.filter(item => resourceKey(item) !== resourceKey(resource)))}><X size={13}/></button></span>)}</div><label className="sr-only" htmlFor="prompt">Ask about your AWS infrastructure</label><textarea ref={composer} id="prompt" placeholder="Ask anything about your AWS infrastructure..." value={prompt} onChange={event => setPrompt(event.target.value)} rows={2} maxLength={12000} disabled={sending} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(); } }}/><div className="composer-toolbar"><button type="button" className="attach-action" disabled={!structuredChat || !inventoryReady} onClick={() => setSidebar(true)}><Paperclip size={16}/><span>Attach resource</span></button><span className="keyboard-hint">Shift + Enter for a new line</span><button className="send-button" disabled={!prompt.trim() || sending} aria-label="Send question">{sending ? <LoaderCircle size={18} className="spin"/> : <ArrowUp size={20}/>}</button></div></form>
        <p className="composer-footnote">Grounded in available AWS evidence. Review recommendations before making changes.</p>
      </div>);
}
