"""商品图缺失时使用注明用途的官方作品插画，不冒充商品实物图。"""
import json
from pathlib import Path

CONFIG = Path(__file__).with_name("reborn_image_sources.json")


def apply_reborn_image(event, config=None):
    if event.get("imageUrl"):
        return
    if config is None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
    image = config.get("items", {}).get(event["id"], config.get("default"))
    if image:
        event.update(image)
