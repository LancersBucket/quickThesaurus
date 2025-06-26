import win32gui, win32con
import threading
import time
import dearpygui.dearpygui as dpg
from spellchecker import SpellChecker
import keyboard
from cache import Cache
from get_syn_ant import SynAnt

class Global():
    """Global Variables"""
    spell: SpellChecker = SpellChecker()
    cache: Cache = Cache()
    version: str = "Quick Thesaurus v0.0.0"

    toggle_event = threading.Event()

def load_image(path: str, tag: str) -> None:
    """Loads an image into the texture registry"""
    width, height, _, data = dpg.load_image(path)
    with dpg.texture_registry():
        dpg.add_static_texture(width, height, data, tag=tag)

def get_word_data(word: str) -> dict:
    """Attempts to get the word data from the cache, otherwise pull it from merriam-webster"""
    thesaurus = Global.cache.get(word)
    if thesaurus is None:
        word_data: SynAnt = SynAnt(word)
        thesaurus = word_data.get_thesaurus()
        Global.cache.save(word, thesaurus)
    return thesaurus

def search_callback() -> None:
    """Callback for entering a word in the search bar"""
    word = dpg.get_value("input_word").strip()
    if not word:
        dpg.set_value("output", "Please enter a word.")
        return

    # Spell check
    # TODO: This should be enhanced to provide suggestions in real time
    corrected = Global.spell.correction(word)
    if corrected != word:
        dpg.set_value("output", f"Did you mean: {corrected}?")
        return

    # If word data is none, then it isn't a real word
    word_data = get_word_data(word)
    if not word_data:
        dpg.set_value("output", f"No results found for '{word}'.")
        return

    # Generate thesaurus
    # TODO: Cleanup how the list looks to make it easier to read, each seperate entry should be it's
    #       own button that can autofill the search bar/pull up its definition
    output = ""
    counter = 1
    for key in word_data:
        # Ignore the cache validity key
        if key == "valid":
            continue

        output += f"{counter}. as in {key}\n"
        output += f"\t{word_data[key]['def']}\n"
        output += f"\tSynonyms: {', '.join(word_data[key]['syn'])}\n"
        output += f"\tAntonyms: {', '.join(word_data[key]['ant'])}\n"
        counter += 1
    dpg.set_value("output", output)

def toggle_window():
    """Toggles the window state between focused and minimized"""
    hwnd = win32gui.FindWindow(None, Global.version)
    if hwnd:
        placement = win32gui.GetWindowPlacement(hwnd)
        # placement[1] == 2 means minimized, 1 means normal
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)  # Bring to front
            dpg.focus_item("input_word")
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

def hotkey_listener():
    """Listens for the hotkey to toggle the window state"""
    while True:
        keyboard.wait("ctrl+alt+t")
        # DPG functions can't be run on another thread so we need to set an event so the main thread can pick it up
        Global.toggle_event.set()
        # Debouncing to prevent repeated openings/closings
        while keyboard.is_pressed("t"):
            time.sleep(0.05)

def poll_toggle():
    """Each frame, check and see if there is a key press, if so, toggle window state"""
    if Global.toggle_event.is_set():
        toggle_window()
        Global.toggle_event.clear()
    dpg.set_frame_callback(dpg.get_frame_count() + 1, poll_toggle)

def settings_modal():
    """Settings modal"""

    # TODO: Add more settings
    with dpg.window(label="Settings", no_move=True, no_resize=True, no_collapse=True, tag="settings", width=525, height=800, on_close=lambda: dpg.delete_item("settings")):
        dpg.add_button(label="Purge Cache", callback=lambda:Global.cache.purge())

def main():
    """Main func"""
    dpg.create_context()

    # Add the esc key as a valid way to minimize the program
    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_Escape, callback=Global.toggle_event.set)

    dpg.create_viewport(title=Global.version, x_pos=1372, y_pos=230, width=525, height=800, decorated=False, always_on_top=True, clear_color=(0.0,0.0,0.0,0.0))

    # Load the settings icon
    load_image("cog.png","cog")

    # Main window
    with dpg.window(label=Global.version, tag="main_window", no_close=True, no_collapse=True):
        with dpg.group(horizontal=True):
            dpg.add_input_text(label="Enter a word", tag="input_word", on_enter=True, callback=search_callback)
            dpg.add_image_button("cog",width=20,height=20, frame_padding=0, callback=settings_modal)
        dpg.add_button(label="Search", callback=search_callback)
        dpg.add_separator()
        dpg.add_text("", tag="output", wrap=450)

    # Start a thread to listen to the hotkey
    threading.Thread(target=hotkey_listener, daemon=True).start()
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()

    # Start the main thread polling to listen for the hotkey
    poll_toggle()
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    main()