import streamlit as st
from pathlib import Path
from PIL import Image

from afribooks_btw.engine.session_service import (
    get_afribooks_language,
)


def render_global_hero() -> None:
    lang = get_afribooks_language()

    project_root = Path(__file__).resolve().parent
    image_path = project_root / "assets" / f"afribooks_hero_{lang}.png"

    if not image_path.exists():
        st.warning(f"AfriBooks HERO image not found: {image_path}")
        return

    image = Image.open(image_path)

    st.image(
        image,
        use_container_width=True,
        caption=f"AfriBooks BTW - afribooks.io - {lang.upper()}",
    )
