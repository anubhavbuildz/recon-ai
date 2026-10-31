# Cloud optimizer frontend integration contract

## Implementation status

The frontend now presents an infrastructure-aware chatbot. The existing backend still implements only `GET /api/v1/health` and `POST /api/v1/recon`. No AWS authentication, inventory, detail, evidence, pricing, or AI chat integration exists. The reconnaissance endpoint and its client remain intact; it is not used as a cloud API.

The browser attempts the inventory endpoint below. HTTP 404/501 shows integration unavailable; it never falls back to a hardcoded resource list. Chat sending is disabled until inventory is retrieved. The Connect AWS action is disabled until `VITE_AWS_CONNECT_PATH` is configured. An empty successfully retrieved inventory is shown as empty, with no inferred resource categories.

The remaining endpoints are proposed contracts, not claims of working integrations. Paths can be configured in `frontend/.env`. Values prefixed by `VITE_` are public browser configuration and must never contain credentials.

## Authorization boundary

The future backend must authorize the account, region, resources, and evidence on every request, independently of client validation. Use a server-managed read-only AWS integration; never request AWS keys in the UI. Frontend requests include browser credentials. A future authenticated cross-origin backend must explicitly configure credentialed CORS and its own CSRF protections; the current unauthenticated backend is unchanged.

A canonical resource identity has four mandatory strings: `resource_id`, `service`, `account_id` (12 digits), and `region` (`global` for genuinely global resources). Display names are not identities. Supported service codes are `ec2`, `ebs`, `rds`, `s3`, `vpc`, and `elb`. A backend adapter must map its service taxonomy to these codes explicitly.

## Inventory — GET `/api/v1/aws/inventory`

Return an object with `supported_services` (array of implemented service codes) and `resources` (array of discovered resources). Each resource contains the four identity fields, plus optional `name`, `type`, and `status`. Only supported services appear in the explorer; counts are calculated from the inventory actually returned. The current contract expects a complete inventory, not a paginated subset. Add pagination support before using a paginated backend.

Example of a valid empty response:

```json
{"supported_services": [], "resources": []}
```

Failures must return meaningful HTTP statuses. An empty inventory does not prove an AWS account connection; the UI says only that inventory was retrieved.

## Details and evidence — GET `/api/v1/aws/resource`

Supply all four canonical fields as URL query parameters. Return the same identity, optional inventory metadata, and available `configuration`, `metrics`, `cost`, `recommendations`, and `evidence` fields. These fields may contain labeled objects, arrays, or scalar values; the UI renders labeled content rather than raw JSON. Include units, measurement windows, timestamps, evidence sources, currency, and cost period in the returned labels/data where available. Missing data is shown as unavailable. No cost calculations are made in the browser.

The returned identity must exactly match the requested resource. The detail drawer rejects mismatches and aborts stale requests when the selection changes.

## Chat — POST `/api/v1/cloud/chat`

Request shape:

```text
{
  question: string,
  resources: Array<{resource_id, service, account_id, region}>,
  messages: Array<{role: "user" | "assistant", content: string, resources: Array<identity>}>
}
```

The `messages` field contains previous turns, excluding the new question. Attachments persist for follow-ups until explicitly removed or a new conversation starts. Conversation state is in browser memory only.

Response shape:

```text
{
  message: string,
  parts: Array<
    {type: "text", text: string} |
    {type: "resource", reference_id: string}
  >,
  references: Array<{
    id: string, resource_id: string, service: string,
    account_id: string, region: string, label?: string,
    evidence_ids?: Array<string>
  }>,
  evidence?: Array<string>,
  recommendations?: Array<string>,
  limitations?: Array<string>,
  savings?: Array<{
    amount: string, is_estimate: boolean, assumptions: Array<string>
  }>
}
```

`message` is the plain-text transcript; `parts` supplies the exact ordering of text and reference tokens in the displayed response. Text parts support Markdown. No resource references are extracted from text, URLs, or Markdown. Reference tokens are clickable only when the canonical identity exactly matches the current discovered inventory; unverified references appear as plain text with an availability label. External Markdown links are ordinary web links, never inventory-reference actions. Raw HTML and external images are not rendered.

Evidence details are expandable. Savings must indicate whether they are estimates and supply assumptions; unavailable assumptions are explicitly labeled. The backend must ground recommendations in authorized AWS metrics, configurations, and pricing, and explain missing data. It must validate model-produced references and evidence IDs server-side. This frontend check does not establish AWS authorization or validate recommendation accuracy.

## Connection — POST configured `VITE_AWS_CONNECT_PATH`

A future authorized backend connection flow should return `{"authorization_url": "https://..."}`. The UI redirects to the HTTPS URL; the backend owns provider URL validation, session binding, state verification, callback handling, and AWS role authorization. Reloading after return retrieves inventory. The frontend never receives AWS access keys.

## Validation and limits

Run `npm test` and `npm run build` inside `frontend/`. Tests use explicit contract fixtures outside the application bundle to check identity matching, structured tokens, request context, follow-up history, missing APIs, and error responses. They do not establish a working AWS integration or validate browser interactions.

Live journey remains blocked at inventory retrieval with the current backend. Resource inspection, real evidence-backed answers, and clickable references require compatible authorized endpoints. No browser automation is available in the current environment; responsive styles and keyboard behavior still need manual browser verification.
