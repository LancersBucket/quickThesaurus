"""Quick Thesaurus"""
import threading, time, atexit, win32gui, win32con, keyboard, win32api, ctypes
from spellchecker import SpellChecker
import dearpygui.dearpygui as dpg
import pyperclip as ppc
from cache import Cache
from config import Config
from mw_parser import SynAnt
import bucket_helper as bh

class Global:
    """Global Variables"""
    spell: SpellChecker = SpellChecker(distance=2)
    cache: Cache = Cache()
    config: Config = Config()

    appname: str = "Quick Thesaurus"
    version: str = "Beta"
    builddate: str = time.strftime("%m/%d/%Y")

    toggle_event = threading.Event()
    kill_event = threading.Event()

def get_word_data(word: str) -> dict:
    """Attempts to get the word data from the cache, otherwise pull it from Merriam-Webster"""
    try:
        # Check cache first
        thesaurus = Global.cache.get(word)
        if thesaurus is not None:
            return thesaurus

        # Fetch from Merriam-Webster
        word_data: SynAnt = SynAnt(word)
        thesaurus = word_data.get_thesaurus()

        if thesaurus:
            # Only cache successful results
            Global.cache.save(word, thesaurus)
            return thesaurus
        return {}

    except Exception as e:
        print(f"Error fetching word data: {e}")
        return {}

def search_callback() -> None:
    """Callback for entering a word in the search bar"""
    dpg.delete_item("output", children_only=True)
    dpg.set_value("err_txt", "Loading...")

    word = dpg.get_value("input_word").strip().lower()
    if not word:
        dpg.set_value("err_txt", "Please enter a word.")
        return

    # Enhanced spell check with suggestions
    if not Global.spell.known([word]):
        suggestions = Global.spell.candidates(word)
        if suggestions:
            suggestion_text = ", ".join(list(suggestions)[:3])
            dpg.set_value("err_txt", f"Did you mean: {suggestion_text}?")
            return

    # If word data is none, then it isn't a real word
    word_data = get_word_data(word)
    if not word_data:
        dpg.set_value("err_txt", f"No results found for '{word}'.")
        return

    # Generate thesaurus
    counter = 1
    for key in word_data:
        # Ignore the cache validity key
        if key == "__valid":
            continue

        dpg.add_text(f"{counter}. as in {key}", parent="output", tag=f"scroll_{key}")
        if 'def' in word_data[key]:
            dpg.add_text(f"{word_data[key]['def']}", parent="output", wrap=450, indent=27)

        if Global.config.get("show_synonyms"):
            if len(word_data[key]['syn']) > 0:
                dpg.add_text("Synonyms:", parent="output",color=bh.Color.GREEN)
                with dpg.table(header_row=False,parent="output", indent=27):
                    dpg.add_table_column(indent_enable=True)
                    dpg.add_table_column(indent_enable=True)
                    dpg.add_table_column(indent_enable=True)
                    for i in range(0,len(word_data[key]['syn'])//3):
                        with dpg.table_row():
                            for j in range(0,3):
                                dpg.add_button(label=word_data[key]['syn'][i*3+j],callback=copy_clipboard)

        if Global.config.get("show_antonyms"):
            if len(word_data[key]['ant']) > 0:
                dpg.add_text("Antoynms:", parent="output",color=bh.Color.RED)
                with dpg.table(header_row=False,parent="output", indent=27):
                    dpg.add_table_column(indent_enable=True)
                    dpg.add_table_column(indent_enable=True)
                    dpg.add_table_column(indent_enable=True)
                    for i in range(0,len(word_data[key]['ant'])//3):
                        with dpg.table_row():
                            for j in range(0,3):
                                dpg.add_button(label=word_data[key]['ant'][i*3+j],callback=copy_clipboard)

        dpg.add_spacer(parent="output")
        dpg.add_separator(parent="output")

        counter += 1

    dpg.set_value("err_txt", "")

def toggle_window() -> None:
    """Toggles the window state between focused and minimized"""
    # Use the win32 implementation and, if called from the main thread,
    # schedule a DPG frame callback to focus the input when restored.
    action = toggle_window_win32()
    if action == "restore":
        try:
            dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: dpg.focus_item("input_word"))
        except Exception as e:
            print(e)

def toggle_window_win32() -> str | None:
    """Thread-safe toggle using only win32 calls (safe to call from hotkey thread)."""
    try:
        hwnd = win32gui.FindWindow(None, Global.appname)
        if not hwnd:
            # Fallback: try to find any top-level window that contains the appname in its title
            def _enum(hwnd_enum, result):
                title = win32gui.GetWindowText(hwnd_enum)
                if title and Global.appname in title:
                    result.append(hwnd_enum)
            found = []
            win32gui.EnumWindows(_enum, found)
            if found:
                hwnd = found[0]
            else:
                return None

        placement = win32gui.GetWindowPlacement(hwnd)
        # placement[1] == 2 means minimized, 1 means normal
        show_cmd = placement[1]
        is_minimized = show_cmd in (win32con.SW_SHOWMINIMIZED, win32con.SW_MINIMIZE)

        if is_minimized:
            # Restore and try to bring to foreground
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception as e:
                print(e)
            print(f"toggle: hwnd={hwnd} action=restore")
            return "restore"

        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        print(f"toggle: hwnd={hwnd} action=minimize")
        return "minimize"
    except Exception as e:
        print(f"Error in toggle_window_win32: {e}")
        return None

def hotkey_listener() -> None:
    """Listens for the hotkey to toggle the window state"""
    while not Global.kill_event.is_set():
        keyboard.wait("ctrl+alt+a")
        toggle_window()
        # Debouncing to prevent repeated openings/closings
        # Wait until the a key is released (so you can hold ctrl+alt and tap a)
        while keyboard.is_pressed("a"):
            time.sleep(0.05)

        time.sleep(0.05)

def poll_toggle() -> None:
    """Each frame, check and see if there is a key press, if so, toggle window state"""
    dpg.set_frame_callback(dpg.get_frame_count() + 1, poll_toggle)

    if Global.kill_event.is_set():
        return

    try:
        if Global.toggle_event.is_set():
            toggle_window()
            Global.toggle_event.clear()
    except Exception as e:
        print(f"Error in poll_toggle: {e}")
        # If there's an error, clear the event to prevent getting stuck
        Global.toggle_event.clear()

def scache_callback(_sender, _app_data, user_data: str) -> None:
    """Callback for the cache section in settings"""
    match user_data:
        case "purge":
            Global.cache.purge()
        case "trim":
            Global.cache.purge(invalid_only=True)
        case "validate":
            Global.cache.revalidate_all()

    dpg.delete_item("settings")
    settings_modal()

def move_window() -> None:
    """Move and resize window"""
    alignment = Global.config.get("alignment")
    width = Global.config.get("window_size")[0]
    height = Global.config.get("window_size")[1]
    screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    horizontal_offset = Global.config.get("offset")[0]
    vertical_offset = Global.config.get("offset")[1]
    y_pos = screen_height//2 - height//2 + vertical_offset

    if alignment == "right":
        win32gui.MoveWindow(win32gui.FindWindow(None, Global.appname),
                            screen_width-width-horizontal_offset, y_pos, width, height, True)
    else:
        win32gui.MoveWindow(win32gui.FindWindow(None, Global.appname),
                            0+horizontal_offset, y_pos, width, height, True)

def sconfig_callback(sender, _app_data, user_data: str) -> None:
    """Callback for the config section in settings"""
    match user_data:
        case "close_on_copy":
            Global.config.save("close_on_copy", dpg.get_value(sender))
        case "show_synonyms":
            Global.config.save("show_synonyms", dpg.get_value(sender))
        case "show_antonyms":
            Global.config.save("show_antonyms", dpg.get_value(sender))
        case "save_window":
            alignment = "left" if dpg.get_value("align_radio") == "Align Left" else "right"
            width = dpg.get_value("width_input")
            height = dpg.get_value("height_input")
            horizontal_offset = dpg.get_value("horizontal_offset_input")
            vertical_offset = dpg.get_value("vertical_offset_input")
            Global.config.save("alignment", alignment)
            Global.config.save("window_size", [width, height])
            Global.config.save("offset", [horizontal_offset, vertical_offset])
            move_window()
        case "reset":
            Global.config.set_default()
            move_window()
        case _:
            raise NotImplementedError("Unknown option")

    dpg.delete_item("settings")
    settings_modal()

def settings_modal() -> None:
    """Settings modal"""
    with dpg.window(label="Settings", no_move=True, no_resize=False,
                    no_collapse=True, tag="settings",
                    width=Global.config.get("window_size")[0],
                    height=Global.config.get("window_size")[1],
                    on_close=lambda: dpg.delete_item("settings")):
        # Settings #
        dpg.add_text("Window Settings:")

        dpg.add_radio_button(["Align Left", "Align Right"],
                             default_value=("Align Right" if Global.config.get("alignment") == "right" else "Align Left"),
                             tag="align_radio",horizontal=True)
        dpg.add_input_int(label="Width", tag="width_input", width=150,
                            default_value=Global.config.get("window_size")[0])
        dpg.add_input_int(label="Height", tag="height_input", width=150,
                            default_value=Global.config.get("window_size")[1])
        dpg.add_input_int(label="Horizontal Offset", tag="horizontal_offset_input", width=150,
                            default_value=Global.config.get("offset")[0])
        dpg.add_input_int(label="Vertical Offset", tag="vertical_offset_input", width=150,
                            default_value=Global.config.get("offset")[1])

        dpg.add_button(label="Save", callback=sconfig_callback, user_data="save_window")

        dpg.add_checkbox(label="Close on Copy", default_value=Global.config.get("close_on_copy"),
                         callback=sconfig_callback, user_data="close_on_copy")

        dpg.add_spacer(height=3)

        dpg.add_text("Display Settings:")
        dpg.add_checkbox(label="Show Synonyms", default_value=Global.config.get("show_synonyms"),
                         callback=sconfig_callback, user_data="show_synonyms")
        dpg.add_checkbox(label="Show Antonyms", default_value=Global.config.get("show_antonyms"),
                         callback=sconfig_callback, user_data="show_antonyms")

        dpg.add_spacer(height=5)

        dpg.add_button(label="Reset to Default", callback=sconfig_callback, user_data="reset")

        dpg.add_separator()

        # Cache #
        dpg.add_text(f"Cache Size: {Global.cache.size()}")
        total, invalid = Global.cache.count()
        if total == 0:
            percent_invalid = 0.0
        else:
            percent_invalid = (invalid / total) * 100
        dpg.add_text(f"Cache Entries: {total} (Total) | {invalid} [{percent_invalid}%] (Invalid)")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Purge Cache", callback=scache_callback, user_data="purge")
            dpg.add_button(label="Trim Invalid Cache", callback=scache_callback, user_data="trim")
            dpg.add_button(label="Revalidate Cache", callback=scache_callback, user_data="validate")
        dpg.add_text(f"{Global.appname} {Global.version} - {Global.builddate}")

        dpg.add_spacer(height=3)

        dpg.add_button(label="Quit", callback=exit_handler)

def search_button_callback(sender) -> None:
    """Get word from button pressed and search it"""
    auto_search(dpg.get_item_configuration(sender)["label"])

def auto_search(word) -> None:
    """Search a word programatically"""
    dpg.set_value("input_word", word)
    search_callback()

def scroll_to(item) -> None:
    """Scroll to specific object in window"""
    if dpg.does_item_exist(item):
        _, y = dpg.get_item_pos(item)
        dpg.set_y_scroll("main_window", y)

def copy_clipboard(sender) -> None:
    """Copies item to clipboard"""
    try:
        word = dpg.get_item_configuration(sender)["label"]
        ppc.copy(word)

        if Global.config.get("close_on_copy"):
            toggle_window_win32()
        else:
            dpg.set_value("err_txt", f"Copied '{word}' to clipboard")
            threading.Timer(1.0, lambda: dpg.set_value("err_txt", "")).start()

        # Ensure DPG input gets focus on the next frame (if restored)
        try:
            dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: dpg.focus_item("input_word"))
        except Exception as e:
            print(e)
    except Exception as e:
        print(f"Error copying to clipboard: {e}")
        dpg.set_value("err_txt", "Failed to copy to clipboard")

def main() -> None:
    """Main func"""

    # Purge Invalid Cache on startup
    Global.cache.purge(invalid_only=True)

    dpg.create_context()

    # Add the esc key as a valid way to minimize the program
    with dpg.handler_registry():
        dpg.add_key_release_handler(dpg.mvKey_Escape, callback=lambda: Global.toggle_event.set())

    # Load font with fallback
    try:
        with dpg.font_registry():
            dpg.bind_font(dpg.add_font("assets/NotoSerifCJKjp-Medium.otf", 24))
    except Exception as e:
        print(f"Failed to load custom font: {e}")

    # Load the settings icon with fallback
    try:
        bh.load_image("assets/cog.png", "cog")
    except Exception as e:
        print(f"Failed to load settings icon: {e}")

    alignment = Global.config.get("alignment")
    width = Global.config.get("window_size")[0]
    height = Global.config.get("window_size")[1]
    screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    horizontal_offset = Global.config.get("offset")[0]
    vertical_offset = Global.config.get("offset")[1]
    y_pos = screen_height//2 - height//2 + vertical_offset

    if alignment == "right":
        dpg.create_viewport(title=Global.appname, x_pos=(screen_width-width-horizontal_offset),
                            y_pos=y_pos, width=width, height=height,
                            decorated=False, always_on_top=True, clear_color=bh.Color.CLEAR)
    else:
        dpg.create_viewport(title=Global.appname, x_pos=0+horizontal_offset,
                            y_pos=y_pos, width=width, height=height,
                            decorated=False, always_on_top=True, clear_color=bh.Color.CLEAR)

    # Main window
    with dpg.window(label=Global.appname, tag="main_window", no_close=True, no_collapse=True):
        with dpg.group(horizontal=True):
            dpg.add_input_text(label="Enter a word", tag="input_word",
                               on_enter=True, callback=search_callback)
            dpg.add_image_button("cog", width=24, height=24, callback=settings_modal)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Search", callback=search_callback)
            dpg.add_text(tag="err_txt")

        dpg.add_spacer()
        dpg.add_separator()
        dpg.add_group(tag="output")

    # Start a thread to listen to the hotkey
    threading.Thread(target=hotkey_listener, daemon=True).start()
    atexit.register(exit_handler)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()

    dpg.focus_item("input_word")

    # Start the main thread polling to listen for the hotkey
    poll_toggle()
    dpg.start_dearpygui()
    dpg.destroy_context()

def exit_handler() -> None:
    """Cleanup on quit"""
    # This might not be strictly necessary, since the keyboard listener is a daemon thread,
    # But this should still fire for the keyboard poll event loop
    Global.kill_event.set()
    dpg.destroy_context()

if __name__ == "__main__":
    ctypes.windll.user32.SetProcessDPIAware()
    main()
