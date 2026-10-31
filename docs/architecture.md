# Architecture diagrams

These diagrams describe the backend reconnaissance boilerplate. The current frontend is a Cloud Resource Optimizer; see [Cloud API contracts](cloud-api-contract.md) for its separate, currently unimplemented backend integration. The frontend portion of the module diagram below represents the preserved reconnaissance client rather than the current screen. The workflow returns `not_executed`; tools and the optional LLM client are not invoked.

## Class diagram

Only actual Python classes and types are shown. The orchestrator and recon agent are modules containing async functions, so they appear in the module diagram below.

`service/provide/aws/base.py` is a module scaffold with no classes or implementation, so it appears only in the module diagram. Its package files are `service/provide/__init__.py` and `service/provide/aws/__init__.py`.

```mermaid
classDiagram
    class BaseModel {
        <<Pydantic>>
    }
    class Settings {
        +list~str~ cors_origins
        +str llm_api_key
        +str llm_base_url
        +str llm_model
        +float llm_timeout_seconds
    }
    class ReconRequest {
        +str target
        +normalize_target(value) str
    }
    class ReconResponse {
        +str target
        +Literal status
        +str message
        +list~str~ agents
    }
    class ReconState {
        <<TypedDict>>
        +str target
        +ReconResponse result
    }
    class ToolDefinition {
        <<frozen dataclass>>
        +str name
        +bool active
        +bool configured
    }
    class LLMClient {
        +str model
        +AsyncOpenAI client
        +__init__(settings)
        +invoke(prompt) str
        +close() None
    }
    class AsyncOpenAI {
        <<external SDK>>
    }
    class RuntimeError {
        <<Python builtin>>
    }
    class ModelError

    BaseModel <|-- Settings
    BaseModel <|-- ReconRequest
    BaseModel <|-- ReconResponse
    ReconState --> ReconResponse : optional result
    LLMClient ..> Settings : constructor configuration
    LLMClient *-- AsyncOpenAI : owns client
    LLMClient ..> ModelError : raises
    RuntimeError <|-- ModelError
```

`Settings.llm_api_key`, `llm_base_url`, and `llm_model` may be `None`. `ReconState.result` is absent before the agent node runs. `invoke()` and `close()` are async. Response defaults are `status="not_executed"`, the tools-not-configured message, and `agents=[]`. Tool definitions contain metadata only.

## Module diagram

Solid arrows show application calls or data use; dotted arrows show configuration, type dependencies, or optional components. The HTTPS target is validated locally without a network request.

```mermaid
flowchart TB
    subgraph Frontend["frontend/src"]
        UI["main.jsx: React form and response states"]
        API["api.js: submitRecon(target)"]
        UI --> API
    end

    subgraph Backend["backend/app"]
        MAIN["main.py: FastAPI, CORS, error handlers"]
        CONFIG["core/config.py: Settings, get_settings()"]
        ROUTES["api/routes.py: health(), recon()"]
        SCHEMAS["api/schemas.py: ReconRequest, ReconResponse"]

        subgraph Agents["service/agent"]
            ORCH["orchestrator.py: run_recon(target)"]
            AGENT["recon_agent.py: run_recon_agent(target)"]
        end

        subgraph Workflow["service/llm/workflow"]
            GRAPH["graph.py: ReconState, run_workflow(), recon_node()"]
            LANGGRAPH["Compiled LangGraph: START → recon → END"]
        end

        subgraph Tools["service/tools"]
            REGISTRY["registry.py: ToolDefinition, list_tools()"]
            POLICY["policy.py: require_execution_permission() — always denies"]
        end

        subgraph OptionalLLM["service/llm/base — optional, outside request flow"]
            CLIENT["client.py: LLMClient, ModelError"]
            SDK["OpenAI-compatible SDK client"]
        end

        subgraph Providers["service/provide"]
            AWS["aws/base.py: scaffold only, implementation pending"]
        end

        MAIN --> ROUTES
        MAIN -.-> CONFIG
        ROUTES --> SCHEMAS
        ROUTES --> ORCH
        ORCH --> GRAPH
        GRAPH --> LANGGRAPH
        LANGGRAPH --> AGENT
        AGENT --> REGISTRY
        AGENT --> SCHEMAS
        GRAPH -.-> SCHEMAS
        ORCH -.-> SCHEMAS
        POLICY -.-> REGISTRY
        CLIENT -.-> CONFIG
        CLIENT -.-> SDK
    end

    ENV["backend/.env and process environment"] -.-> CONFIG
    VITE["VITE_API_BASE_URL"] -.-> API
    API -->|"HTTP POST /api/v1/recon"| MAIN
```

API responses return through the same call chain to the React form. The policy module is a future execution boundary and is not called by the placeholder agent. No request-flow module calls `LLMClient`, and no tool execution handler exists.

The AWS provider scaffold is intentionally disconnected: no routes, agents, or workflows import it yet. AWS authentication, inventory, details, and cloud chat remain unimplemented.
