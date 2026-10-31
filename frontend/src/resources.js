export const services = {
  ec2: 'EC2 Instances', ebs: 'EBS Volumes', rds: 'RDS Databases',
  s3: 'S3 Buckets', vpc: 'VPCs', elb: 'Load Balancers',
};

export function resourceKey(resource) {
  return JSON.stringify([resource.account_id, resource.region, resource.service, resource.resource_id]);
}

export function isResource(value) {
  return value && typeof value.resource_id === 'string' && value.resource_id.length > 0
    && Object.hasOwn(services, value.service) && /^\d{12}$/.test(value.account_id)
    && typeof value.region === 'string' && value.region.length > 0
    && ['name', 'type', 'status'].every(key => value[key] === undefined || typeof value[key] === 'string');
}

export function contextFor(resource) {
  return { resource_id: resource.resource_id, service: resource.service,
    account_id: resource.account_id, region: resource.region };
}

export function parseInventory(data) {
  if (!data || !Array.isArray(data.resources) || !Array.isArray(data.supported_services)
    || !data.resources.every(isResource)
    || !data.supported_services.every(service => Object.hasOwn(services, service))
    || data.resources.some(resource => !data.supported_services.includes(resource.service))) {
    throw new Error('The backend returned an invalid inventory response.');
  }
  if (new Set(data.resources.map(resourceKey)).size !== data.resources.length) {
    throw new Error('The backend returned duplicate resource identifiers.');
  }
  return data;
}

export function verifiedReference(reference, inventory) {
  if (!isResource(reference)) return null;
  return inventory.find(resource => resourceKey(resource) === resourceKey(reference)) || null;
}

export function parseAnswer(data) {
  if (!data || typeof data.message !== 'string' || !Array.isArray(data.references)
    || !data.references.every(ref => typeof ref.id === 'string' && isResource(ref)
      && (ref.label === undefined || typeof ref.label === 'string')
      && (ref.evidence_ids === undefined || (Array.isArray(ref.evidence_ids) && ref.evidence_ids.every(id => typeof id === 'string'))))
    || new Set(data.references.map(ref => ref.id)).size !== data.references.length
    || !Array.isArray(data.parts) || !data.parts.every(part =>
      (part.type === 'text' && typeof part.text === 'string') ||
      (part.type === 'resource' && typeof part.reference_id === 'string'))
    || (data.savings !== undefined && (!Array.isArray(data.savings) || !data.savings.every(item =>
      item && typeof item.amount === 'string' && typeof item.is_estimate === 'boolean'
      && Array.isArray(item.assumptions) && item.assumptions.every(value => typeof value === 'string'))))
    || ['evidence', 'recommendations', 'limitations'].some(key => data[key] !== undefined
      && (!Array.isArray(data[key]) || !data[key].every(item => typeof item === 'string')))) {
    throw new Error('The backend returned an invalid chat response.');
  }
  // Message is the accessible/plain-text transcript; parts explicitly place references.
  if (!data.parts.length && data.message) data = { ...data, parts: [{ type: 'text', text: data.message }] };
  return data;
}
