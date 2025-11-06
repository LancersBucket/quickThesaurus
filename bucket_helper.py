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
        for _ in range(0, 100 * 100):
            texture_data.append(255 / 255)
            texture_data.append(0)
            texture_data.append(255 / 255)
            texture_data.append(255 / 255)
        with dpg.texture_registry():
            dpg.add_static_texture(width=100, height=100, default_value=texture_data, tag=tag)

def scroll_to(item) -> None:
    """Scroll to specific object in window"""
    if dpg.does_item_exist(item):
        _, y = dpg.get_item_pos(item)
        dpg.set_y_scroll("main_window", y)

def version_compare(v1: str, v2: str) -> int:
    """Compares two versions: -1 if v1 is larger than v2,
       0 if they are the same, and 1 if v2 is larger than v1"""
    v1_parts = v1.split(".")
    v2_parts = v2.split(".")

    for i in range(min(len(v1_parts),len(v2_parts))):
        if v1_parts[i] > v2_parts[i]:
            return -1
        if v1_parts[i] < v2_parts[i]:
            return 1

    if len(v1_parts) > len(v2_parts):
        return -1
    if len(v1_parts) < len(v2_parts):
        return 1

    return 0
