"""Quick Thesaurus"""
import threading, time, atexit, win32gui, win32con, keyboard
from spellchecker import SpellChecker
import dearpygui.dearpygui as dpg
from cache import Cache
from get_syn_ant import SynAnt

class Global():
    """Global Variables"""
    spell: SpellChecker = SpellChecker()
    cache: Cache = Cache()

    appname: str = "Quick Thesaurus"
    version: str = "v0.1.0"
    builddate: str = time.strftime("%m/%d/%Y")

    toggle_event = threading.Event()
    kill_event = threading.Event()

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

def search_callback(_sender=None, _app_data=None, search=None) -> None:
    """Callback for entering a word in the search bar"""
    dpg.delete_item("output",children_only=True)

    if search:
        word = search
    else:
        word = dpg.get_value("input_word").strip()
    if not word:
        dpg.set_value("output", "Please enter a word.")
        return

    # Spell check
    # TODO: This should be enhanced to provide suggestions in real time
    corrected = Global.spell.correction(word)
    if corrected != word and corrected is not None:
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
    counter = 1
    for key in word_data:
        # Ignore the cache validity key
        if key == "valid":
            continue

        dpg.add_text(f"{counter}. as in {key}", parent="output")
        dpg.add_text(f"{word_data[key]['def']}", parent="output", wrap=450, indent=27)
        dpg.add_text("Synonyms:", parent="output",color=(0,255,0,255))
        with dpg.table(header_row=False,parent="output", indent=27):
            dpg.add_table_column(indent_enable=True)
            dpg.add_table_column(indent_enable=True)
            dpg.add_table_column(indent_enable=True)
            for i in range(0,len(word_data[key]['syn'])//3):
                with dpg.table_row():
                    for j in range(0,3):
                        dpg.add_button(label=word_data[key]['syn'][i*3+j])

        dpg.add_text("Antoynms:", parent="output",color=(255,0,0,255))
        with dpg.table(header_row=False,parent="output", indent=27):
            dpg.add_table_column(indent_enable=True)
            dpg.add_table_column(indent_enable=True)
            dpg.add_table_column(indent_enable=True)
            for i in range(0,len(word_data[key]['ant'])//3):
                with dpg.table_row():
                    for j in range(0,3):
                        dpg.add_button(label=word_data[key]['ant'][i*3+j])

        dpg.add_spacer(parent="output")
        dpg.add_separator(parent="output")

        #dpg.add_text(f"Synonyms: {', '.join(word_data[key]['syn'])}", parent="output", wrap=450, indent=27)
        #dpg.add_text(f"Antonyms: {', '.join(word_data[key]['ant'])}", parent="output", wrap=450, indent=27)
        counter += 1

def toggle_window():
    """Toggles the window state between focused and minimized"""
    hwnd = win32gui.FindWindow(None, Global.appname)
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
    while not Global.kill_event.is_set():
        keyboard.wait("ctrl+alt+t")
        # DPG functions can't be run on another thread so we need to set an event so the main thread can pick it up
        Global.toggle_event.set()
        # Debouncing to prevent repeated openings/closings
        while keyboard.is_pressed("t"):
            time.sleep(0.05)

def poll_toggle():
    """Each frame, check and see if there is a key press, if so, toggle window state"""
    if Global.kill_event.is_set():
        return
    if Global.toggle_event.is_set():
        toggle_window()
        Global.toggle_event.clear()
    dpg.set_frame_callback(dpg.get_frame_count() + 1, poll_toggle)

def settings_callback(_sender, _app_data, user_data):
    """Callback for the settings modal, refreshes the settings page too"""
    match user_data:
        case "purge":
            Global.cache.purge()
        case "trim":
            Global.cache.purge(invalid_only=True)

    dpg.delete_item("settings")
    settings_modal()

def settings_modal():
    """Settings modal"""
    atexit.register(exit_handler)

    # TODO: Add more settings
    with dpg.window(label="Settings", no_move=True, no_resize=True, no_collapse=True, tag="settings",
                    width=525, height=800, on_close=lambda: dpg.delete_item("settings")):
        dpg.add_text(f"Cache Size: {Global.cache.size()}")
        total, invalid = Global.cache.count()
        dpg.add_text(f"Cache Entries: {total} (Total) | {invalid} (Invalid)")
        dpg.add_button(label="Purge Cache", callback=settings_callback, user_data="purge")
        dpg.add_button(label="Trim Invalid Cache", callback=settings_callback, user_data="trim")
        dpg.add_text(f"{Global.appname} {Global.version} - {Global.builddate}")

def main():
    """Main func"""
    dpg.create_context()

    # Add the esc key as a valid way to minimize the program
    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_Escape, callback=Global.toggle_event.set)

    # Load font
    with dpg.font_registry():
        dpg.bind_font(dpg.add_font("assets/NotoSerifCJKjp-Medium.otf", 24))

    # Load the settings icon
    load_image("assets/cog.png","cog")

    dpg.create_viewport(title=Global.appname, x_pos=1372, y_pos=230, width=525, height=800,
                        decorated=False, always_on_top=True, clear_color=(0.0,0.0,0.0,0.0))

    # Main window
    with dpg.window(label=Global.appname, tag="main_window", no_close=True, no_collapse=True):
        with dpg.group(horizontal=True):
            dpg.add_input_text(label="Enter a word", tag="input_word", on_enter=True, callback=search_callback)
            dpg.add_image_button("cog",width=24,height=24, frame_padding=0, callback=settings_modal)
        dpg.add_button(label="Search", callback=search_callback)
        dpg.add_spacer(parent="output")
        dpg.add_separator()
        dpg.add_group(tag="output")

    # Start a thread to listen to the hotkey
    threading.Thread(target=hotkey_listener, daemon=True).start()
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()

    search_callback(search="weird")
    # Start the main thread polling to listen for the hotkey
    poll_toggle()
    dpg.start_dearpygui()
    dpg.destroy_context()

def exit_handler():
    """Cleanup on quit"""
    # This might not be strictly necessary, since the keyboard listener is a daemon thread,
    # But this should still fire for the keyboard poll event loop
    Global.kill_event.set()

if __name__ == "__main__":
    main()
