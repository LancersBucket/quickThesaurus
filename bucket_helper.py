"""Helper functions"""
import dearpygui.dearpygui as dpg

class Color:
    """Colors"""
    GREEN = (0,255,0,255)
    RED = (255,0,0,255)
    CLEAR = (0,0,0,0)

def load_image(path: str, tag: str) -> None:
    """Loads an image into the texture registry"""
    try:
        width, height, _, data = dpg.load_image(path)
        with dpg.texture_registry():
            dpg.add_static_texture(width, height, data, tag=tag)
    except Exception:
        print(f"Failed to load image at {path}, using fallback texture.")
        texture_data = []
        for i in range(0, 100 * 100):
            texture_data.append(255 / 255)
            texture_data.append(0)
            texture_data.append(255 / 255)
            texture_data.append(255 / 255)
        with dpg.texture_registry():
            dpg.add_static_texture(width=100, height=100, default_value=texture_data, tag=tag)
