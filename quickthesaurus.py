import win32gui
import win32con
import json
import dearpygui.dearpygui as dpg
from spellchecker import SpellChecker
import threading
import keyboard
from get_syn_ant import SynAnt
import os
import ctypes
from ctypes import c_int
import time

TRANSPARENT = True
spell = SpellChecker()

def get_word_data(word):
    try:
        thesaurus = check_cache(word)
    except KeyError:
        word_data: SynAnt = SynAnt(word)
        thesaurus = word_data.get_thesaurus()
        save_cache(word_data)
    return thesaurus

def check_cache(word):
    with open("cache.json", "r") as file:
        cache = json.load(file)
        if word in cache:
            return cache[word]
        raise KeyError(f"'{word}' not found in cache.")

def save_cache(word_data):
    with open("cache.json", "r") as file:
        cache = json.load(file)
    with open("cache.json", "w") as file:
        cache[word_data.get_word()] = word_data.get_thesaurus()
        file.write(json.dumps(cache, indent=4))

def search_callback(sender, app_data, user_data):
    word = dpg.get_value("input_word").strip()
    if not word:
        dpg.set_value("output", "Please enter a word.")
        return

    # Spell check
    corrected = spell.correction(word)
    if corrected != word:
        dpg.set_value("output", f"Did you mean: {corrected}?")
        return

    word_data = get_word_data(word)
    if not word_data:
        dpg.set_value("output", f"No results found for '{word}'.")
        return

    output = ""
    counter = 1
    for key in word_data:
        output += f"{counter}. as in {key}\n"
        output += f"\t{word_data[key]['def']}\n"
        output += f"\tSynonyms: {', '.join(word_data[key]['syn'])}\n"
        output += f"\tAntonyms: {', '.join(word_data[key]['ant'])}\n"
        counter += 1

    dpg.set_value("output", output)

def toggle_window():
    hwnd = win32gui.FindWindow(None, "Quick Thesaurus")
    if hwnd:
        placement = win32gui.GetWindowPlacement(hwnd)
        # placement[1] == 2 means minimized, 1 means normal
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            dpg.focus_item("input_word")
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

toggle_event = threading.Event()

def hotkey_listener():
    while True:
        keyboard.wait("ctrl+alt+t")
        toggle_event.set()
        # Wait for keys to be released before listening again
        while keyboard.is_pressed("t"):
            time.sleep(0.05)  # Add a short sleep to prevent busy-waiting

def poll_toggle():
    if toggle_event.is_set():
        toggle_window()
        toggle_event.clear()
    dpg.set_frame_callback(dpg.get_frame_count() + 1, poll_toggle)

def main():
    dwm = ctypes.windll.dwmapi

    class MARGINS(ctypes.Structure):
        _fields_ = [("cxLeftWidth", c_int),
                    ("cxRightWidth", c_int),
                    ("cyTopHeight", c_int),
                    ("cyBottomHeight", c_int)
                    ]

    if not os.path.exists("cache.json"):
        with open("cache.json", "w") as file:
            file.write("{}")

    dpg.create_context()
    if TRANSPARENT:
        dpg.create_viewport(title='Quick Thesaurus', x_pos=1372, y_pos=230, width=525, height=800, decorated=False, always_on_top=True, clear_color=(0.0,0.0,0.0,0.0))
    else:
        dpg.create_viewport(title='Quick Thesaurus', x_pos=1372, y_pos=230, width=525, height=800, always_on_top=True)

    with dpg.window(label="Quick Thesaurus", tag="main_window", no_close=True, no_collapse=True):
        dpg.add_input_text(label="Enter a word", tag="input_word", on_enter=True, callback=search_callback)
        dpg.add_button(label="Search", callback=search_callback)
        dpg.add_separator()
        dpg.add_text("", tag="output", wrap=450)

    threading.Thread(target=hotkey_listener, daemon=True).start()
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()
    
    if TRANSPARENT:
        hwnd = win32gui.FindWindow(None, "Quick Thesaurus")
        margins = MARGINS(-1, -1, -1, -1)
        dwm.DwmExtendFrameIntoClientArea(hwnd, margins)

    poll_toggle()  # Start polling for the toggle event
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    main()