import React from 'react';
import { Menu, Sun, Moon } from 'lucide-react';

export default function ChatHeader({ sidebar, setSidebar, darkMode, setDarkMode }) {
  return (<header className="chat-header"><div className="header-title"><button className="icon-button" onClick={() => setSidebar(!sidebar)} aria-label="Toggle infrastructure explorer" aria-expanded={sidebar}><Menu size={20}/></button><div><h1>Cloud Resource Optimizer</h1><p>Understand, analyze, and optimize your AWS infrastructure using AI.</p></div></div><div className="header-actions"><span className="preview-badge">Preview</span><button type="button" className="icon-button theme-toggle" onClick={() => setDarkMode(value => !value)} aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'} title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'} aria-pressed={darkMode}>{darkMode ? <Sun size={19}/> : <Moon size={19}/>}</button></div></header>);
}
