import React, { useEffect, useRef, useState } from 'react';
import { Box, X, LoaderCircle, Sparkles } from 'lucide-react';
import { getResource } from '../api';
import { contextFor, isResource, resourceKey } from '../resources';
function DetailValues({ value }) {
  if (value == null || (Array.isArray(value) && !value.length) || (typeof value === 'object' && !Object.keys(value).length)) return <p className="muted">Not available from the backend.</p>;
  if (typeof value !== 'object') return <p>{String(value)}</p>;
  if (Array.isArray(value)) return <ul>{value.map((item, i) => <li key={i}><DetailValues value={item}/></li>)}</ul>;
  return <dl className="detail-values">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd><DetailValues value={item}/></dd></div>)}</dl>;
}

export default function ResourceDrawer({ resource, close, attach }) {
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

