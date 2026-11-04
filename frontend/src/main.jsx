import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import LoginGate from './Login';
import './style.css';

createRoot(document.getElementById('root')).render(<LoginGate>{auth => <App {...auth}/>}</LoginGate>);
