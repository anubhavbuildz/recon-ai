import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import ReactMarkdown from 'react-markdown';
import { ArrowUp, Box, ChevronDown, ChevronRight, Cloud, Database, HardDrive, Layers,
  LoaderCircle, Menu, Network, Paperclip, Plus, RefreshCw, Search,
  Server, ShieldCheck, Sparkles, X, ExternalLink, AlertCircle, Sun, Moon } from 'lucide-react';
import { askCloud, connectAWS, connectionPath, getInventory, getResource, inventoryConfigured, structuredChat } from './api';
import { contextFor, parseAnswer, parseInventory, resourceKey, services, verifiedReference, isResource } from './resources';
import './style.css';
import LoginGate from './Login';

const icons = { ec2: Server, ebs: HardDrive, rds: Database, s3: Box, vpc: Network, elb: Layers };
const suggestions = ['Which AWS resources are underutilized?', 'Where can I reduce my monthly cloud costs?', 'Are there any unattached EBS volumes?', 'Analyze my EC2 instances.'];

function Markdown({ children, inline = false }) {
  return <ReactMarkdown components={{ p: ({ children }) => inline ? <span className="markdown-fragment">{children}</span> : <p>{children}</p>, a: ({ children, href }) => {
    // Resource links are rendered only through structured tokens below.
    if (!href || !/^https?:\/\//i.test(href)) return <span>{children}</span>;
    return <a href={href} target="_blank" rel="noopener noreferrer">{children}<ExternalLink size={12}/></a>;
  }, img: () => <span>[Image omitted]</span> }}>{children}</ReactMarkdown>;
}

function Answer({ answer, inventory, inspect }) {
  return <div className="answer-content">
    {answer.source && <p className="answer-source"><Database size={13}/>Source: <span>{answer.source}</span></p>}
    {answer.parts.map((part, index) => {
      if (part.type === 'text') return <Markdown inline key={index}>{part.text}</Markdown>;
      const reference = answer.references.find(item => item.id === part.reference_id);
      const resource = verifiedReference(reference, inventory);
      return resource ? <button key={index} className="resource-reference" onClick={() => inspect(resource)}><Box size={13}/>{reference.label || resource.name || resource.resource_id}</button>
        : <span key={index} className="unverified-reference">{reference?.label || reference?.resource_id || 'Unavailable resource'} (not in current inventory)</span>;
    })}
    {answer.recommendations?.length > 0 && <div className="recommendations"><h3>Recommendations</h3><ul>{answer.recommendations.map((text, i) => <li key={i}><Markdown>{text}</Markdown></li>)}</ul></div>}
    {answer.savings?.map((saving, index) => <div className="recommendations" key={index}><h3>{saving.is_estimate ? 'Estimated savings' : 'Reported savings'}: {saving.amount}</h3><p>Assumptions: {saving.assumptions.length ? saving.assumptions.join('; ') : 'Not supplied by the backend.'}</p></div>)}
    {answer.limitations?.length > 0 && <div className="limitations"><h3><AlertCircle size={15}/>Data limitations</h3>{answer.limitations.map((text, i) => <Markdown key={i}>{text}</Markdown>)}</div>}
    {answer.evidence?.length > 0 && <details className="evidence"><summary>Supporting evidence · {answer.evidence.length}</summary>{answer.evidence.map((text, i) => <Markdown key={i}>{text}</Markdown>)}</details>}
  </div>;
}

function DetailValues({ value }) {
  if (value == null || (Array.isArray(value) && !value.length) || (typeof value === 'object' && !Object.keys(value).length)) return <p className="muted">Not available from the backend.</p>;
  if (typeof value !== 'object') return <p>{String(value)}</p>;
  if (Array.isArray(value)) return <ul>{value.map((item, i) => <li key={i}><DetailValues value={item}/></li>)}</ul>;
  return <dl className="detail-values">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd><DetailValues value={item}/></dd></div>)}</dl>;
}

function ResourceDrawer({ resource, close, attach }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const closeRef = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    closeRef.current?.focus();
    const controller = new AbortController();
    setDetail(null); setError(''); setLoading(true);
    getResource(contextFor(resource), controller.signal).then(data => {
      if (!isResource(data) || resourceKey(data) !== resourceKey(resource)) throw new Error('The backend returned details for a different resource.');
      setDetail(data);
    }).catch(err => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); previous?.focus(); };
  }, [resource]);
  const data = detail || resource;
  return <aside className="resource-drawer" aria-label="Resource details" onKeyDown={e => { if (e.key === 'Escape') close(); }}>
    <div className="drawer-heading"><span>RESOURCE DETAILS</span><button ref={closeRef} className="icon-button" onClick={close} aria-label="Close resource details"><X size={20}/></button></div>
    <div className="drawer-scroll"><div className="resource-large-icon"><Box size={26}/></div><h2>{data.name || data.resource_id}</h2><p className="resource-id">{data.resource_id}</p><span className="service-tag">{data.service.toUpperCase()}</span>
      <dl className="identity"><div><dt>AWS account</dt><dd>{data.account_id}</dd></div><div><dt>Region</dt><dd>{data.region}</dd></div><div><dt>Status</dt><dd>{data.status || 'Not available'}</dd></div><div><dt>Resource type</dt><dd>{data.type || data.service}</dd></div></dl>
      {loading && <p className="loading-line"><LoaderCircle className="spin" size={16}/>Loading resource evidence…</p>}
      {error && <p className="inline-error" role="alert">{error} Showing inventory information.</p>}
      {['configuration', 'metrics', 'cost', 'recommendations', 'evidence'].map(key => <section key={key}><h3>{({ metrics: 'Utilization metrics', cost: 'Available cost information' })[key] || key}</h3><DetailValues value={data[key]}/></section>)}
    </div>
    <div className="drawer-footer"><button className="primary-button" onClick={() => attach(resource)}><Sparkles size={16}/>Ask AI about this resource</button></div>
  </aside>;
}

function App({ username, signOut, signingOut, signOutError }) {
  const [darkMode, setDarkMode] = useState(() => {
    try {
      const saved = localStorage.getItem('recon-ai-theme');
      if (saved === 'dark' || saved === 'light') return saved === 'dark';
    } catch { /* Theme still works when browser storage is unavailable. */ }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  useEffect(() => {
    document.documentElement.style.colorScheme = darkMode ? 'dark' : 'light';
    try { localStorage.setItem('recon-ai-theme', darkMode ? 'dark' : 'light'); }
    catch { /* Storage may be disabled; retain the preference for this session. */ }
  }, [darkMode]);
  const [inventory, setInventory] = useState([]);
  const [supported, setSupported] = useState([]);
  const [inventoryLoading, setInventoryLoading] = useState(true);
  const [inventoryError, setInventoryError] = useState('');
  const [reload, setReload] = useState(0);
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState({});
  const [sidebar, setSidebar] = useState(() => window.innerWidth > 1100);
  const [selected, setSelected] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState('');
  const composer = useRef(null);
  const end = useRef(null);
  const inFlight = useRef(false);

  useEffect(() => {
    if (!inventoryConfigured) { setInventoryLoading(false); return; }
    const controller = new AbortController();
    setInventoryLoading(true); setInventoryError('');
    getInventory(controller.signal).then(parseInventory).then(data => {
      setInventory(data.resources); setSupported(data.supported_services);
      setAttachments(previous => previous.filter(item => data.resources.some(resource => resourceKey(resource) === resourceKey(item))));
      setSelected(previous => previous ? data.resources.find(item => resourceKey(item) === resourceKey(previous)) || null : null);
    }).catch(error => {
      if (!controller.signal.aborted) { setInventoryError(error.message); setInventory([]); setSupported([]); setSelected(null); setAttachments([]); }
    }).finally(() => { if (!controller.signal.aborted) setInventoryLoading(false); });
    return () => controller.abort();
  }, [reload]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, sending]);

  function attach(resource) {
    if (!structuredChat) { setPrompt(`Explain resource ${resource.resource_id} in the configured S3 document.`); composer.current?.focus(); return; }
    setAttachments(previous => previous.some(item => resourceKey(item) === resourceKey(resource)) ? previous : [...previous, resource]);
    if (window.innerWidth < 900) { setSelected(null); setSidebar(false); }
    composer.current?.focus();
  }
  async function send(event) {
    event?.preventDefault();
    if (!prompt.trim() || inFlight.current) return;
    const question = prompt.trim();
    const resources = attachments.map(contextFor);
    const history = messages.map(item => ({ role: item.role, content: item.content, resources: item.resources || [] }));
    inFlight.current = true; setSending(true); setChatError(''); setPrompt('');
    setMessages(previous => [...previous, { role: 'user', content: question, resources }]);
    try {
      const answer = parseAnswer(await askCloud(question, resources, history));
      setMessages(previous => [...previous, { role: 'assistant', content: answer.message, answer }]);
    } catch (error) { setMessages(previous => previous.slice(0, -1)); setChatError(error.message); setPrompt(question); }
    finally { inFlight.current = false; setSending(false); }
  }
  async function connect() {
    setConnecting(true); setConnectionError('');
    try { await connectAWS(); } catch (error) { setConnectionError(error.message); }
    finally { setConnecting(false); }
  }
  const inventoryReady = inventoryConfigured && !inventoryLoading && !inventoryError;

  return <div className={`cloud-app${darkMode ? ' dark-mode' : ''}${sidebar ? ' sidebar-open' : ''}${selected ? ' has-drawer' : ''}`}>
    {sidebar && <button className="sidebar-backdrop" onClick={() => setSidebar(false)} aria-label="Close infrastructure explorer"/>}
    <aside className="infrastructure-sidebar" aria-label="AWS infrastructure explorer">
      <a className="brand" href="./"><span className="brand-cube"><img className="app-emblem" src="/recon-cloud-search.png" alt=""/></span><span>RECON <b>AI</b><small>CLOUD INTELLIGENCE</small></span></a>
      <button className="new-chat" disabled={sending} onClick={() => { setMessages([]); setChatError(''); setPrompt(''); setAttachments([]); }}><Plus size={17}/>New conversation</button>
      <div className="explorer-title"><h2>Infrastructure</h2><button className="icon-button" onClick={() => setReload(n => n + 1)} disabled={inventoryLoading || sending} aria-label="Refresh inventory"><RefreshCw size={15} className={inventoryLoading ? 'spin' : ''}/></button></div>
      <label className="resource-search"><Search size={15}/><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search resources..." aria-label="Search AWS resources"/></label>
      <div className="inventory-content" aria-live="polite">
        {!inventoryConfigured ? <div className="sidebar-state"><Database size={30}/><h3>S3 document chat</h3><p>Ask about the document configured on the backend. The model reads it through the S3 tool.</p><p>Live resource inventory is not connected.</p></div> : inventoryLoading ? <div className="sidebar-state"><LoaderCircle size={22} className="spin"/><p>Retrieving infrastructure…</p></div> : inventoryError ? <div className="sidebar-state"><Cloud size={32}/><h3>Infrastructure unavailable</h3><p>{inventoryError}</p><button className="text-button" onClick={() => setReload(n => n + 1)}>Try again</button></div> : <>
          {supported.map(service => {
            const ServiceIcon = icons[service];
            const all = inventory.filter(resource => resource.service === service);
            const filtered = all.filter(resource => `${resource.name || ''} ${resource.resource_id} ${resource.region} ${resource.account_id} ${resource.status || ''}`.toLowerCase().includes(search.toLowerCase()));
            if (search && !filtered.length) return null;
            return <section className="resource-group" key={service}><button className="category-toggle" aria-expanded={!collapsed[service]} onClick={() => setCollapsed(previous => ({ ...previous, [service]: !previous[service] }))}>{collapsed[service] ? <ChevronRight size={14}/> : <ChevronDown size={14}/>}<ServiceIcon size={16}/><span>{services[service]}</span><span className="count">{all.length}</span></button>
              {!collapsed[service] && (filtered.length ? filtered.map(resource => <button className={`resource-item${selected && resourceKey(selected) === resourceKey(resource) ? ' active' : ''}`} key={resourceKey(resource)} onClick={() => { setSelected(resource); if (window.innerWidth <= 1100) setSidebar(false); }}><span className="resource-item-name">{resource.name || resource.resource_id}</span><span>{resource.service.toUpperCase()} · {resource.region}</span>{resource.status && <small>{resource.status}</small>}</button>) : <p className="category-empty">No resources discovered</p>)}
            </section>;
          })}
          {!inventory.length && <div className="sidebar-state"><Box size={30}/><h3>No resources discovered</h3><p>The backend has not returned any AWS resources.</p></div>}
          {inventory.length > 0 && search && !inventory.some(resource => `${resource.name || ''} ${resource.resource_id} ${resource.region} ${resource.account_id} ${resource.status || ''}`.toLowerCase().includes(search.toLowerCase())) && <p className="sidebar-state">No matching resources.</p>}
        </>}
      </div>
      <div className="account-controls"><span>Signed in as {username}</span><button className="text-button" onClick={signOut} disabled={signingOut}>{signingOut ? 'Signing out…' : 'Sign out'}</button>{signOutError && <p role="alert">{signOutError}</p>}</div>
      <div className="connection-card"><span className="connection-label"><span className={`connection-dot${inventoryReady ? ' connected' : ''}`}/>{inventoryReady ? 'Inventory retrieved' : 'S3 document chat'}</span><button className="connect-button" onClick={connect} disabled={!connectionPath || connecting}>{connecting ? <LoaderCircle size={15} className="spin"/> : <Cloud size={16}/>}Connect AWS account</button>{!connectionPath && <p>Authorized connection API not configured.</p>}{connectionError && <p role="alert">{connectionError}</p>}<span className="read-only"><ShieldCheck size={12}/>Read-only infrastructure access</span></div>
    </aside>

    <div className="chat-workspace">
      <header className="chat-header"><div className="header-title"><button className="icon-button" onClick={() => setSidebar(!sidebar)} aria-label="Toggle infrastructure explorer" aria-expanded={sidebar}><Menu size={20}/></button><div><h1>Cloud Resource Optimizer</h1><p>Understand, analyze, and optimize your AWS infrastructure using AI.</p></div></div><div className="header-actions"><span className="preview-badge">Preview</span><button type="button" className="icon-button theme-toggle" onClick={() => setDarkMode(value => !value)} aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'} title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'} aria-pressed={darkMode}>{darkMode ? <Sun size={19}/> : <Moon size={19}/>}</button></div></header>
      <main className="conversation">
        {!messages.length ? <div className="welcome"><div className="welcome-icon"><img className="app-emblem" src="/recon-cloud-search.png" alt=""/><span><Sparkles size={16}/></span></div><span className="welcome-eyebrow">YOUR INFRASTRUCTURE. IN CONTEXT.</span><h2>A clearer view of your cloud.</h2><p>Ask a question, explore a resource, or find your next opportunity to optimize.</p><div className="suggestions">{suggestions.map((question, index) => <button key={question} onClick={() => { setPrompt(question); composer.current?.focus(); }}><span>{index % 2 ? <Sparkles size={17}/> : <Layers size={17}/>}</span>{question}<ChevronRight size={15}/></button>)}</div><p className="welcome-hint"><Paperclip size={14}/>Select a resource in the explorer to add context to your question.</p></div> : <div className="message-list">{messages.map((message, index) => <article className={`message ${message.role}`} key={index}><div className="message-avatar">{message.role === 'assistant' ? <img className="app-emblem" src="/recon-cloud-search.png" alt=""/> : 'You'}</div><div className="message-body"><span className="message-author">{message.role === 'assistant' ? 'Cloud assistant' : 'You'}</span>{message.role === 'assistant' ? <Answer answer={message.answer} inventory={inventory} inspect={setSelected}/> : <><p className="user-text">{message.content}</p><div className="message-resources">{message.resources.map(resource => <span key={resourceKey(resource)}><Box size={12}/>{resource.resource_id} · {resource.region}</span>)}</div></>}</div></article>)}</div>}
        {sending && <div role="status" className="assistant-loading"><LoaderCircle size={16} className="spin"/>Waiting for the cloud backend…</div>}<div ref={end}/>
      </main>
      <div className="composer-dock">
        {chatError && <div role="alert" className="chat-error"><AlertCircle size={16}/><span>{chatError} Your question is restored below so you can retry.</span></div>}
        {!structuredChat && <p className="backend-notice"><Database size={14}/>Answers use the configured S3 document. Each question is analyzed independently.</p>}
        <form className="composer" onSubmit={send}><div className="attachment-chips">{attachments.map(resource => <span className="attachment-chip" key={resourceKey(resource)} title={`${resource.account_id} · ${resource.region}`}><Box size={14}/>{resource.name || resource.resource_id}<small>{resource.region}</small><button type="button" disabled={sending} aria-label={`Remove ${resource.name || resource.resource_id}`} onClick={() => setAttachments(previous => previous.filter(item => resourceKey(item) !== resourceKey(resource)))}><X size={13}/></button></span>)}</div><label className="sr-only" htmlFor="prompt">Ask about your AWS infrastructure</label><textarea ref={composer} id="prompt" placeholder="Ask anything about your AWS infrastructure..." value={prompt} onChange={event => setPrompt(event.target.value)} rows={2} maxLength={12000} disabled={sending} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(); } }}/><div className="composer-toolbar"><button type="button" className="attach-action" disabled={!structuredChat || !inventoryReady} onClick={() => setSidebar(true)}><Paperclip size={16}/><span>Attach resource</span></button><span className="keyboard-hint">Shift + Enter for a new line</span><button className="send-button" disabled={!prompt.trim() || sending} aria-label="Send question">{sending ? <LoaderCircle size={18} className="spin"/> : <ArrowUp size={20}/>}</button></div></form>
        <p className="composer-footnote">Grounded in available AWS evidence. Review recommendations before making changes.</p>
      </div>
    </div>
    {selected && <ResourceDrawer key={resourceKey(selected)} resource={selected} close={() => setSelected(null)} attach={attach}/>}
  </div>;
}

createRoot(document.getElementById('root')).render(<LoginGate>{auth => <App {...auth}/>}</LoginGate>);
