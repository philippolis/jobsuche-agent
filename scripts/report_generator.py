from typing import List, Dict, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def generate_html(jobs: List[Dict[str, Any]], template_path: Path) -> str:
    """Render the HTML report using Jinja2."""
    env = Environment(loader=FileSystemLoader(template_path.parent))
    template = env.get_template(template_path.name)
    return template.render(job_count=len(jobs), jobs=jobs)
