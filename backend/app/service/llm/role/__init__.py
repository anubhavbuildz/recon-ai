"""Load the cloud analyst role independently of the working directory."""

from importlib.resources import files


def load_system_prompt() -> str:
    prompt = files(__package__).joinpath("role.md").read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("Cloud analyst role prompt is empty")
    return prompt
