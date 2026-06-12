# modules/ml_pipeline/notebook_gen.py
import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def generate_notebook(
    session_dir: str,
    template_name: str,
    context: dict,
) -> str:
    """
    Render a Jinja2 .ipynb.j2 template and write the result to session_dir.
    Returns the absolute path to the generated .ipynb file.
    """
    templates_dir = Path(__file__).parent.parent.parent / "templates" / "ml_notebooks"

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )
    # Use json.dumps directly as the tojson filter
    env.filters["tojson"] = json.dumps

    # Validate template_name
    _VALID_TEMPLATES = {"regression", "classification", "clustering", "timeseries"}
    if template_name not in _VALID_TEMPLATES:
        raise ValueError(f"template_name must be one of {_VALID_TEMPLATES}, got: {template_name!r}")

    template = env.get_template(f"{template_name}.ipynb.j2")
    rendered = template.render(**context)

    # Validate it's valid JSON before writing
    nb_dict = json.loads(rendered)

    # Create session_dir if it doesn't exist
    os.makedirs(session_dir, exist_ok=True)

    out_path = os.path.join(session_dir, "notebook.ipynb")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(nb_dict, f, ensure_ascii=False, indent=1)

    return out_path
