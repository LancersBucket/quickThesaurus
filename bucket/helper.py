"""Helper functions"""
import dearpygui.dearpygui as dpg
import pyperclip as ppc

class Color:
    """Colors"""
    # Color = (R,G,B,A)
    GREEN   = (0,255,0,255)
    RED     = (255,0,0,255)
    CLEAR   = (0,0,0,0)

def load_image(path: str, tag: str) -> None:
    """Loads an image into the texture registry"""
    try:
        width, height, _, data = dpg.load_image(path)
    except Exception:
        print(f"Failed to load image at {path}, using fallback texture.")
        width = 100
        height = 100
        data = []
        for _ in range(0, width * height):
            data.append(255 / 255)
            data.append(0)
            data.append(255 / 255)
            data.append(255 / 255)
    finally:
        with dpg.texture_registry():
            dpg.add_static_texture(width=width, height=height, default_value=data, tag=tag)

def load_font(path: str, size: int, set_default: bool = False) -> None:
    """Loads a font into the font registry, with error handling"""
    try:
        with dpg.font_registry():
            font = dpg.add_font(path, size)
            if set_default:
                dpg.bind_font(font)
    except Exception as e:
        print(f"Failed to load custom font: {e}")

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

def idi_div(integer: int, double: float) -> int:
    """// but returns an integer"""
    return round(integer // double)

def resize_elements() -> None:
    """Resize elements on viewport resize"""
    viewport_width = dpg.get_viewport_width()
    _viewport_height = dpg.get_viewport_height()
    dpg.set_item_width("input_word", idi_div(viewport_width, 1.2))

def add_columns(count: int) -> None:
    """Add columns to a table"""
    for _ in range(count):
        dpg.add_table_column()

def copy_clipboard(string: str) -> None:
    """Copies string to clipboard"""
    try:
        ppc.copy(string)
    except Exception as e:
        print(f"Error copying to clipboard: {e}")
        dpg.set_value("err_txt", "Failed to copy to clipboard")
