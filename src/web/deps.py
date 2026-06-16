"""Shared Jinja environment for the blackboard workspace."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from src.web.tooltips import get_tooltip

WEB_ROOT = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(WEB_ROOT / "templates"))
TEMPLATES.env.globals["get_tooltip"] = get_tooltip
