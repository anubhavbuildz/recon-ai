import React, { useEffect, useRef, useState } from 'react';
import { askCloud, connectAWS, getInventory, inventoryConfigured, structuredChat } from './api';
import { contextFor, parseAnswer, parseInventory, resourceKey } from './resources';
import ResourceDrawer from './components/ResourceDrawer';
import InfrastructureSidebar from './components/InfrastructureSidebar';
import ChatHeader from './components/ChatHeader';
import Conversation from './components/Conversation';
import ChatComposer from './components/ChatComposer';

export default function App({ username, signOut, signingOut, signOutError }) {
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
    <InfrastructureSidebar inventoryLoading={inventoryLoading} sending={sending} setReload={setReload} inventoryError={inventoryError} supported={supported} inventory={inventory} collapsed={collapsed} setCollapsed={setCollapsed} selected={selected} setSelected={setSelected} setSidebar={setSidebar} inventoryReady={inventoryReady} connect={connect} connecting={connecting} connectionError={connectionError} username={username} signOut={signOut} signingOut={signingOut} signOutError={signOutError}/>

    <div className="chat-workspace">
      <ChatHeader sidebar={sidebar} setSidebar={setSidebar} darkMode={darkMode} setDarkMode={setDarkMode}/>
      <Conversation messages={messages} setPrompt={setPrompt} composer={composer} inventory={inventory} setSelected={setSelected} sending={sending} end={end}/>
      <ChatComposer chatError={chatError} send={send} attachments={attachments} sending={sending} setAttachments={setAttachments} composer={composer} prompt={prompt} setPrompt={setPrompt} inventoryReady={inventoryReady} setSidebar={setSidebar}/>
    </div>
    {selected && <ResourceDrawer key={resourceKey(selected)} resource={selected} close={() => setSelected(null)} attach={attach}/>}
  </div>;
}

