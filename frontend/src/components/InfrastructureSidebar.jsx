import React from 'react';
import { Box, ChevronDown, ChevronRight, Cloud, Database, HardDrive, Layers, LoaderCircle, LogOut, Network, RefreshCw, Server, ShieldCheck } from 'lucide-react';
import { inventoryConfigured, connectionPath } from '../api';
import { resourceKey, services } from '../resources';
const icons = { ec2: Server, ebs: HardDrive, rds: Database, s3: Box, vpc: Network, elb: Layers };

export default function InfrastructureSidebar({ inventoryLoading, sending, setReload, inventoryError, supported, inventory, collapsed, setCollapsed, selected, setSelected, setSidebar, inventoryReady, connect, connecting, connectionError, username, signOut, signingOut, signOutError }) {
  return (<aside className="infrastructure-sidebar" aria-label="AWS infrastructure explorer">
      <a className="brand" href="./"><span className="brand-cube"><img className="app-emblem" src="/recon-cloud-search.png" alt=""/></span><span>RECON <b>AI</b><small>CLOUD INTELLIGENCE</small></span></a>
      <div className="explorer-title"><h2>Cloud provider</h2>{inventoryConfigured && <button className="icon-button" onClick={() => setReload(n => n + 1)} disabled={inventoryLoading || sending} aria-label="Refresh inventory"><RefreshCw size={15} className={inventoryLoading ? 'spin' : ''}/></button>}</div>
      <div className="provider-card"><div className="provider-card-heading"><span className="provider-overline">CURRENTLY SUPPORTED</span><span className="provider-badge">AWS</span></div><div className="sidebar-aws-brand"><img src="/aws-mark.svg" alt="Amazon Web Services"/></div><div className="provider-card-footer"><span>Amazon Web Services</span><ShieldCheck size={15}/></div></div>
      <div className="inventory-content" aria-live="polite">
        {!inventoryConfigured ? null : inventoryLoading ? <div className="sidebar-state"><LoaderCircle size={22} className="spin"/><p>Retrieving infrastructure…</p></div> : inventoryError ? <div className="sidebar-state"><Cloud size={32}/><h3>Infrastructure unavailable</h3><p>{inventoryError}</p><button className="text-button" onClick={() => setReload(n => n + 1)}>Try again</button></div> : <>
          {supported.map(service => {
            const ServiceIcon = icons[service];
            const all = inventory.filter(resource => resource.service === service);
            const filtered = all;
            return <section className="resource-group" key={service}><button className="category-toggle" aria-expanded={!collapsed[service]} onClick={() => setCollapsed(previous => ({ ...previous, [service]: !previous[service] }))}>{collapsed[service] ? <ChevronRight size={14}/> : <ChevronDown size={14}/>}<ServiceIcon size={16}/><span>{services[service]}</span><span className="count">{all.length}</span></button>
              {!collapsed[service] && (filtered.length ? filtered.map(resource => <button className={`resource-item${selected && resourceKey(selected) === resourceKey(resource) ? ' active' : ''}`} key={resourceKey(resource)} onClick={() => { setSelected(resource); if (window.innerWidth <= 1100) setSidebar(false); }}><span className="resource-item-name">{resource.name || resource.resource_id}</span><span>{resource.service.toUpperCase()} · {resource.region}</span>{resource.status && <small>{resource.status}</small>}</button>) : <p className="category-empty">No resources discovered</p>)}
            </section>;
          })}
          {!inventory.length && <div className="sidebar-state"><Box size={30}/><h3>No resources discovered</h3><p>The backend has not returned any AWS resources.</p></div>}
        </>}
      </div>
      <div className="sidebar-footer">
        {connectionPath && <div className="connection-card"><span className="connection-label"><span className={`connection-dot${inventoryReady ? ' connected' : ''}`}/>{inventoryReady ? 'Inventory retrieved' : 'AWS account'}</span><button className="connect-button" onClick={connect} disabled={connecting}>{connecting ? <LoaderCircle size={15} className="spin"/> : <Cloud size={16}/>}Connect AWS account</button>{connectionError && <p role="alert">{connectionError}</p>}</div>}
        <div className="sidebar-access"><ShieldCheck size={14}/><span>Read-only infrastructure access</span></div>
        <div className="account-controls"><span className="account-avatar" aria-hidden="true">{username.slice(0, 1).toUpperCase()}</span><div className="account-identity"><span className="account-name" title={username}>{username}</span><small>Personal workspace</small></div><button className="account-signout" onClick={signOut} disabled={signingOut} aria-label={signingOut ? 'Signing out' : 'Sign out'} title="Sign out">{signingOut ? <LoaderCircle className="spin" size={17}/> : <LogOut size={17}/>}</button>{signOutError && <p role="alert">{signOutError}</p>}</div>
      </div>
    </aside>);
}
