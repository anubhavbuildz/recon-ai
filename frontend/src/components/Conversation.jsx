import React from 'react';
import { Sparkles, Layers, ChevronRight, Paperclip, Box, LoaderCircle } from 'lucide-react';
import { resourceKey } from '../resources';
import Answer from './Answer';
const suggestions = ['Which AWS resources are underutilized?', 'Where can I reduce my monthly cloud costs?', 'Are there any unattached EBS volumes?', 'Analyze my EC2 instances.'];

export default function Conversation({ messages, setPrompt, composer, inventory, setSelected, sending, end }) {
  return (<main className="conversation">
        {!messages.length ? <div className="welcome"><div className="welcome-icon"><img className="app-emblem" src="/recon-cloud-search.png" alt=""/><span><Sparkles size={16}/></span></div><span className="welcome-eyebrow">YOUR INFRASTRUCTURE. IN CONTEXT.</span><h2>A clearer view of your cloud.</h2><p>Ask a question, explore a resource, or find your next opportunity to optimize.</p><div className="suggestions">{suggestions.map((question, index) => <button key={question} onClick={() => { setPrompt(question); composer.current?.focus(); }}><span>{index % 2 ? <Sparkles size={17}/> : <Layers size={17}/>}</span>{question}<ChevronRight size={15}/></button>)}</div><p className="welcome-hint"><Paperclip size={14}/>Select a resource in the explorer to add context to your question.</p></div> : <div className="message-list">{messages.map((message, index) => <article className={`message ${message.role}`} key={index}><div className="message-avatar">{message.role === 'assistant' ? <img className="app-emblem" src="/recon-cloud-search.png" alt=""/> : 'You'}</div><div className="message-body"><span className="message-author">{message.role === 'assistant' ? 'Cloud assistant' : 'You'}</span>{message.role === 'assistant' ? <Answer answer={message.answer} inventory={inventory} inspect={setSelected}/> : <><p className="user-text">{message.content}</p><div className="message-resources">{message.resources.map(resource => <span key={resourceKey(resource)}><Box size={12}/>{resource.resource_id} · {resource.region}</span>)}</div></>}</div></article>)}</div>}
        {sending && <div role="status" className="assistant-loading"><LoaderCircle size={16} className="spin"/>Waiting for the cloud backend…</div>}<div ref={end}/>
      </main>);
}
