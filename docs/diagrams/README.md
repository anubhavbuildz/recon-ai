# Current architecture diagrams

These Mermaid diagrams describe code in this repository, not proof that its AWS
resources have been deployed. Terraform currently uses a five-minute test schedule.

## Application and collector

```mermaid
flowchart TB
    Schedule[EventBridge rule: every 5 minutes] --> Lambda[Python Lambda collector]
    EC2[EC2 instance metadata] --> Lambda
    EBS[EBS volume metadata] --> Lambda
    CW[CloudWatch: rolling 14-day CPU metrics] --> Lambda
    Lambda -->|Write timestamped JSON| Bucket[Private snapshot S3 bucket]
    Browser[React UI and local-storage JWT] -->|Bearer token and question| API[FastAPI auth middleware and chat route]
    API --> Workflow[LangChain workflow]
    Role[role/role.md system prompt] --> Workflow
    Workflow <-->|Two bounded model turns| Model[Configured LLM provider]
    Workflow --> Tool[call_s3 tool]
    Tool -->|Scoped read and optional date listing| Bucket
    Workflow -->|Answer and source URIs| Browser
```

The collector writes snapshots; the model tool only reads. S3 document contents
are sent to the model provider. RDS/S3 inventory and billing collection are not
implemented. The optional demo RDS database is not collected by this collector.

## Authentication

```mermaid
sequenceDiagram
    participant UI as React UI
    participant API as FastAPI
    participant DB as SQLite sessions
    UI->>API: POST auth/login with configured account credentials
    API->>API: Compare credentials and sign HS256 JWT
    API->>DB: Store token hash and credential fingerprint
    API-->>UI: username and JWT
    UI->>UI: Persist session in local storage
    UI->>API: Protected request with Bearer JWT
    API->>API: Validate signature, claims and configured account
    API->>DB: Verify active session
    API-->>UI: Response
    UI->>API: POST auth/logout
    API->>DB: Delete current session
    API-->>UI: signed_out
    UI->>UI: Remove stored session
```

Only login and valid browser CORS preflights bypass authentication. JWTs have no
automatic expiry. Changing credentials or signing keys invalidates sessions.

## Model tool exchange

```mermaid
sequenceDiagram
    participant API as Chat route
    participant W as LangChain workflow
    participant M as ChatOpenAI model
    participant T as call_s3
    API->>W: Validated question
    W->>M: SystemMessage and HumanMessage, tools with auto selection
    M-->>W: AIMessage requesting call_s3
    W->>W: Require one known tool, empty arguments and call ID
    W->>T: ainvoke with empty arguments
    T-->>W: Document or dated snapshot bundle
    W->>M: Full history with matching ToolMessage
    M-->>W: Final AIMessage
    W->>W: Reject further tool calls or empty answer
    W-->>API: message, source, sources
```

## Snapshot history selection

```mermaid
flowchart TD
    Tool[call_s3] --> Prefix{Snapshot prefix configured?}
    Prefix -->|No| Single[Read exact S3_OBJECT_KEY]
    Prefix -->|Yes| Dates[Last S3_HISTORY_DAYS UTC dates: 1 to 14]
    Dates --> List[List each date prefix with pagination]
    List --> Select[Latest timestamped JSON key per date]
    Select --> Read[Read JSON objects under combined byte limit]
    Read --> Bundle[Dated snapshots, source URIs and missing dates]
    Single --> Model[Model evidence]
    Bundle --> Model
```

History does not send every five-minute file. It reads the latest per UTC date,
reports missing dates and fails if none exist. CPU windows overlap between days:
these values are rolling 14-day aggregates, not independent daily measurements.

## Optional EC2/RDS demo

```mermaid
flowchart LR
    subgraph VPC[Isolated demo VPC]
        EC1[EC2 in public subnet: AZ 1] -->|TCP 3306| RDS[Private single-AZ MySQL RDS]
        EC2[EC2 in public subnet: AZ 2] -->|TCP 3306| RDS
        SG[Database security group: EC2 group only] -.-> RDS
        RDS --> Secret[RDS-managed Secrets Manager credential]
    end
    Operator[Authorized operator] --> SSM[Session Manager]
    EC1 -->|Outbound HTTPS| SSM
    EC2 -->|Outbound HTTPS| SSM
```

No EC2 inbound rules or SSH keys are configured. The bootstrap checks TCP
reachability, not authenticated SQL. See [AWS setup](../aws.md).
