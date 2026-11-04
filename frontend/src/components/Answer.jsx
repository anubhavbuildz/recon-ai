import React from 'react';
import { Database, Box, AlertCircle } from 'lucide-react';
import { verifiedReference } from '../resources';
import Markdown from './Markdown';
export default function Answer({ answer, inventory, inspect }) {
  return <div className="answer-content">
    {(answer.sources?.length ? answer.sources : answer.source ? [answer.source] : []).map(source => <p className="answer-source" key={source}><Database size={13}/>Source: <span>{source}</span></p>)}
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

