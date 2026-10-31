"""Metadata only: no executables, shell access, or integrations."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    active: bool = False
    configured: bool = False


TOOLS = tuple(ToolDefinition(name, active=name == "Nmap") for name in (
    "Subfinder", "crt.sh", "Amass", "theHarvester", "Shodan", "Censys",
    "Nmap", "NVD", "CISA KEV",
))


def list_tools() -> tuple[ToolDefinition, ...]:
    return TOOLS
