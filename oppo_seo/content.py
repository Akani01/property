import json
from pathlib import Path
GUIDES = json.loads(Path(__file__).with_name("content.json").read_text(encoding="utf-8"))
GUIDE_BY_SLUG = {guide["slug"]: guide for guide in GUIDES}
