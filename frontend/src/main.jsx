import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { submitRecon } from './api';
import './style.css';

function App() {
  const [target, setTarget] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  async function submit(event) {
    event.preventDefault();
    setLoading(true); setResult(null); setError('');
    try { setResult(await submitRecon(target)); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return <main>
    <p className="eyebrow">RECON AI / FOUNDATION</p>
    <h1>Start with a target.</h1>
    <p>Submit a domain or HTTPS URL to the reconnaissance workflow.</p>
    <form onSubmit={submit}>
      <label htmlFor="target">Domain or HTTPS URL</label>
      <input id="target" value={target} onChange={e => setTarget(e.target.value)}
        placeholder="example.com" required maxLength={2048} disabled={loading} />
      <button disabled={loading || !target.trim()}>{loading ? 'Submitting…' : 'Submit target'}</button>
    </form>
    <section aria-live="polite" aria-busy={loading}>
      {loading && <p>Waiting for the backend…</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {result && <><h2>Request completed</h2><dl>
        <dt>Target</dt><dd>{result.target}</dd>
        <dt>Status</dt><dd>{result.status}</dd>
      </dl><p>{result.message}</p></>}
    </section>
    <p className="note">Boilerplate only. No scanning, tool execution or AI analysis is performed.</p>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
