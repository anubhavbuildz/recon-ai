import React, { useEffect, useState } from 'react';
import { LoaderCircle, ArrowRight, ShieldCheck, Cloud, Server, Database, Box, Network, Eye, EyeOff, UserRound, LockKeyhole, Sparkles } from 'lucide-react';
import { currentUser, savedSession, signIn, signOut } from './auth';

export default function LoginGate({ children }) {
  const [session, setSession] = useState(savedSession);
  const [verified, setVerified] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function verify() {
    setBusy(true); setError('');
    try { await currentUser(); setVerified(true); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  useEffect(() => { if (session && !verified) verify(); }, [session]);
  useEffect(() => {
    function sync() { setSession(savedSession()); setVerified(false); }
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const value = await signIn(username, password);
      setSession(value); setVerified(true); setPassword('');
    } catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  async function logout() {
    setBusy(true); setError('');
    try { await signOut(); setSession(null); setVerified(false); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  if (session && verified) return children({ username: session.username, signOut: logout, signingOut: busy, signOutError: error });
  return <main className="login-page">
    <div className="login-shell">
      <aside className="login-story" aria-label="About Recon AI">
        <a className="login-brand" href="./"><img src="/recon-cloud-search.png" alt=""/><span>RECON <b>AI</b></span></a>
        <div className="login-story-content">
          <span className="login-platform"><img src="/aws-mark.svg" alt="AWS"/><span>YOUR CLOUD. CONNECTED.</span></span>
          <h2>Your infrastructure.<br/><span>A clearer perspective.</span></h2>
          <p>Bring your AWS resources into focus. Explore your infrastructure, ask better questions, and find opportunities to optimize.</p>
          <div className="login-cloud-map" aria-hidden="true">
            <div className="cloud-map-grid"/>
            <svg className="cloud-map-lines" viewBox="0 0 400 220"><path d="M80 65H150L200 110L250 65H320M80 160H150L200 110L250 160H320M200 110V195"/></svg>
            <div className="cloud-map-hub"><Cloud size={37}/><span>AWS CLOUD</span></div>
            <div className="cloud-map-node node-compute"><Server size={23}/><span>Compute</span></div>
            <div className="cloud-map-node node-database"><Database size={23}/><span>Database</span></div>
            <div className="cloud-map-node node-storage"><Box size={23}/><span>Storage</span></div>
            <div className="cloud-map-node node-network"><Network size={23}/><span>Network</span></div>
          </div>
          <div className="login-story-caption"><Sparkles size={15}/><span>Less searching. More understanding.</span></div>
        </div>
        <div className="login-story-footer"><span className="login-status-dot"/>Built for your AWS infrastructure</div>
      </aside>
      <section className="login-form-panel" aria-label="Sign in">
        <div className="login-topline"><span>CLOUD RESOURCE OPTIMIZER</span><span className="login-preview">PREVIEW</span></div>
        <div className="login-card">
          <div className="login-lock"><LockKeyhole size={23}/></div>
          <span className="login-eyebrow">YOUR WORKSPACE AWAITS</span>
          <h1>Welcome back.</h1><p>Sign in to your Recon AI workspace.</p>
          {error && <p className="login-error" role="alert">{error}</p>}
          {session ? <div className="login-session"><p>Saved session for <strong>{session.username}</strong></p>
            <button className="primary-button" onClick={verify} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16}/> : <ArrowRight size={16}/>}Continue with saved session</button>
            <button className="text-button" onClick={logout} disabled={busy}>Sign out</button>
          </div> : <form onSubmit={submit}>
            <label htmlFor="login-username">Username</label>
            <div className="login-input-wrap"><UserRound size={17}/><input id="login-username" placeholder="Enter your username" autoComplete="username" required maxLength={256} value={username} onChange={e => setUsername(e.target.value)} disabled={busy}/></div>
            <label htmlFor="login-password">Password</label>
            <div className="login-input-wrap"><LockKeyhole size={17}/><input id="login-password" placeholder="Enter your password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required maxLength={4096} value={password} onChange={e => setPassword(e.target.value)} disabled={busy}/><button type="button" className="login-password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div>
            <p className="login-persistence"><ShieldCheck size={15}/>Stay signed in until you choose to sign out.</p>
            <button className="primary-button" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17}/> : <>Sign in to workspace<ArrowRight size={17}/></>}</button>
          </form>}
          <p className="login-note">Your cloud, a little more clarity.</p>
        </div>
        <footer className="login-form-footer"><span>RECON AI</span><span>Cloud intelligence, in context.</span></footer>
      </section>
    </div>
  </main>;
}
