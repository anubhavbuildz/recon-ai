# Project documentation

| Guide | Contents |
| --- | --- |
| [Demo setup](demo.md) | Local application setup, AWS collector deployment, optional EC2/RDS resources, validation and cleanup |
| [Architecture](architecture.md) | Current runtime components, authentication, model/tool exchange, history selection and boundaries |
| [Current diagrams](diagrams/README.md) | Mermaid diagrams of deployed-by-Terraform resources and application flows |
| [AWS setup](aws.md) | Collector deployment, optional EC2/RDS demo, IAM reader access, backend integration and cleanup |
| [Test cases](test_case.md) | Feature-wise unit, integration and end-to-end test matrix, methods and execution status |
| [Coverage](coverage.md) | Measured coverage, uncovered areas, report artifacts and reproduction commands |
| [Cloud API contracts](cloud-api-contract.md) | Built-in document chat versus optional inventory integrations |
| [Contributing](../CONTRIBUTING.md) | Local setup, change workflow, checks and pull requests |
| [Code of conduct](../CODE_OF_CONDUCT.md) | Community expectations and reporting |
| [Security](../security.md) | Current security boundaries and private vulnerability reporting |

The supplied [overview PNG](images/cloud-optimizer-overview.png) and
[detailed PNG](images/cloud-optimizer-architecture.png) illustrate the broader
intended platform. Their 24-hour schedule and some planned integrations differ
from the current implementation. Current source diagrams are in `diagrams/`;
PNG originals remain unchanged in `images/`.
