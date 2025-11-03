"""Helper functions"""
import dearpygui.dearpygui as dpg

def load_image(path: str, tag: str) -> None:
    """Loads an image into the texture registry"""
    width, height, _, data = dpg.load_image(path)
    with dpg.texture_registry():
        dpg.add_static_texture(width, height, data, tag=tag)
