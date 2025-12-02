"""Quick Thesaurus"""
import threading, time, atexit, keyboard
from spellchecker import SpellChecker
import dearpygui.dearpygui as dpg
from mw_parser import SynAnt
from bucket.cache import Cache
from bucket.config import Config
import bucket.helper as bh
from bucket.helper import Color
import bucket.win32 as w32

class Global:
    """Global Variables"""
    spell: SpellChecker = SpellChecker(distance=2)
    config: Config = Config()
    cache: Cache = Cache()

    appname: str = "Quick Thesaurus"
    version: str = "0.1.0"

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

def autocorrect_callback(_sender, _app_data, user_data) -> None:
    """Tab to autocorrect to first result"""
    dpg.delete_item("autocorrect_handler")
    dpg.set_value("input_word", user_data)

def word_button_callback(sender) -> None:
    """Callback for word buttons"""
    word = dpg.get_item_configuration(sender)["label"]

    if dpg.is_key_down(dpg.mvKey_ModCtrl):
        # If ctrl is held, search the word instead of copying
        dpg.set_value("input_word", word)
        search_callback()
    else:
        # Otherwise, copy to clipboard
        bh.copy_clipboard(word)

        if Global.config.get("close_on_copy"):
            w32.toggle_window(Global.appname)
        else:
            dpg.set_value("err_txt", f"Copied '{word}' to clipboard")
            threading.Timer(1.0, lambda: dpg.set_value("err_txt", "")).start()

        # Ensure DPG input gets focus on the next frame (if restored)
        try:
            dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: dpg.focus_item("input_word"))
        except Exception as e:
            print(e)

def search_callback() -> None:
    """Callback for entering a word in the search bar"""
    dpg.delete_item("output", children_only=True)
    dpg.delete_item("autocorrect_handler")
    dpg.set_value("err_txt", "Loading...")

    word = dpg.get_value("input_word").strip().lower()
    if not word:
        dpg.set_value("err_txt", "Please enter a word.")
        return

    # Enhanced spell check with suggestions
    if not Global.spell.known([word]):
        suggestions = Global.spell.candidates(word)
        if suggestions:
            with dpg.handler_registry():
                dpg.add_key_press_handler(dpg.mvKey_Tab,callback=autocorrect_callback,
                                        user_data=list(suggestions)[0],tag="autocorrect_handler")
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
            dpg.add_text(word_data[key]['def'], parent="output", wrap=450, indent=27)

        column_count = Global.config.get("column_count")

        if (Global.config.get("show_synonyms") and len(word_data[key]['syn']) > 0):
            dpg.add_text("Synonyms:", parent="output",color=Color.GREEN)
            with dpg.table(header_row=False,parent="output", indent=27):
                bh.add_columns(column_count)
                for i in range(0,len(word_data[key]['syn'])//column_count):
                    with dpg.table_row():
                        for j in range(0,column_count):
                            dpg.add_button(label=word_data[key]['syn'][i*column_count+j],
                                            callback=word_button_callback)

        if (Global.config.get("show_antonyms") and len(word_data[key]['ant']) > 0):
            dpg.add_text("Antonyms:", parent="output",color=Color.RED)
            with dpg.table(header_row=False,parent="output", indent=27):
                bh.add_columns(column_count)
                for i in range(0,len(word_data[key]['ant'])//column_count):
                    with dpg.table_row():
                        for j in range(0,column_count):
                            dpg.add_button(label=word_data[key]['ant'][i*column_count+j],
                                            callback=word_button_callback)

        dpg.add_spacer(parent="output")
        dpg.add_separator(parent="output")

        counter += 1

    dpg.set_value("err_txt", "")

def window_toggle() -> None:
    """Toggles the window state between focused and minimized"""
    action = w32.toggle_window(Global.appname)

    # Schedule a DPG frame callback to focus the input when restored.
    if action == "restore":
        try:
            dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: dpg.focus_item("input_word"))
        except Exception as e:
            print(e)

def hotkey_listener() -> None:
    """Listens for the hotkey to toggle the window state"""
    while not Global.kill_event.is_set():
        keyboard.wait("ctrl+alt+a")
        window_toggle()
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
            window_toggle()
            Global.toggle_event.clear()
    except Exception as e:
        print(f"Error in poll_toggle: {e}")
        # If there's an error, clear the event to prevent getting stuck
        Global.toggle_event.clear()

def move_window() -> None:
    """Move and resize window"""
    alignment = Global.config.get("alignment")
    width, height = Global.config.get("window_size")
    screen_width, screen_height = w32.screen_width(), w32.screen_height()
    horizontal_offset, vertical_offset = Global.config.get("offset")
    y_pos = screen_height//2 - height//2 + vertical_offset

    if alignment == "right":
        x_pos = screen_width - width - horizontal_offset
    else:
        x_pos = 0 + horizontal_offset

    w32.move_window(appname=Global.appname, x_pos=x_pos,
                    y_pos=y_pos, width=width, height=height)

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
            width, height = dpg.get_value("width_input"), dpg.get_value("height_input")
            horizontal_offset = dpg.get_value("horizontal_offset_input")
            vertical_offset = dpg.get_value("vertical_offset_input")
            Global.config.save("alignment", alignment)
            Global.config.save("window_size", [width, height])
            Global.config.save("offset", [horizontal_offset, vertical_offset])
            move_window()
        case "reset":
            Global.config.set_default()
            move_window()
        case "column_count":
            count = int(dpg.get_value(sender))
            Global.config.save("column_count", count)
        case "cache_purge":
            Global.cache.purge()
        case "cache_trim":
            Global.cache.purge(invalid_only=True)
        case "cache_validate":
            Global.cache.revalidate_all()
        case _:
            raise NotImplementedError(f"Unknown option, {user_data}")

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
                             tag="align_radio", horizontal=True)
        dpg.add_input_int(label="Width", tag="width_input", width=150,
                            default_value=Global.config.get("window_size")[0])
        dpg.add_input_int(label="Height", tag="height_input", width=150,
                            default_value=Global.config.get("window_size")[1])
        dpg.add_input_int(label="Horizontal Offset", tag="horizontal_offset_input", width=150,
                            default_value=Global.config.get("offset")[0])
        dpg.add_input_int(label="Vertical Offset", tag="vertical_offset_input", width=150,
                            default_value=Global.config.get("offset")[1])

        dpg.add_button(label="Resize", callback=sconfig_callback, user_data="save_window")

        dpg.add_checkbox(label="Close on Copy", default_value=Global.config.get("close_on_copy"),
                         callback=sconfig_callback, user_data="close_on_copy")

        dpg.add_spacer(height=3)

        dpg.add_text("Display Settings:")
        dpg.add_checkbox(label="Show Synonyms", default_value=Global.config.get("show_synonyms"),
                         callback=sconfig_callback, user_data="show_synonyms")
        dpg.add_checkbox(label="Show Antonyms", default_value=Global.config.get("show_antonyms"),
                         callback=sconfig_callback, user_data="show_antonyms")
        with dpg.group(horizontal=True):
            dpg.add_text("Columns:")
            dpg.add_radio_button(["1", "2", "3"], default_value=Global.config.get("column_count"),
                                 tag="column_count", user_data="column_count", horizontal=True,
                                 callback=sconfig_callback)

        dpg.add_spacer(height=5)

        dpg.add_button(label="Reset to Default", callback=sconfig_callback, user_data="reset")

        dpg.add_separator()

        # Cache #
        dpg.add_text(f"Cache Size: {Global.cache.size()}")
        total, invalid = Global.cache.count()
        if total == 0:
            percent_invalid = 0.0
        else:
            percent_invalid = round((invalid / total) * 100, 1)
        dpg.add_text(f"Cache Entries: {total} (Total) | {invalid} [{percent_invalid}%] (Invalid)")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Purge Cache", callback=sconfig_callback, user_data="cache_purge")
            dpg.add_button(label="Trim Invalid Cache", callback=sconfig_callback, user_data="cache_trim")
            dpg.add_button(label="Revalidate Cache", callback=sconfig_callback, user_data="cache_validate")

        dpg.add_spacer(height=5)

        dpg.add_text(f"{Global.appname} v{Global.version} [cache/config v{Global.config.get_version()}]")

        dpg.add_spacer(height=5)

        dpg.add_button(label="Quit", callback=exit_handler)

def search_button_callback(sender) -> None:
    """Get word from button pressed and search it"""
    auto_search(dpg.get_item_configuration(sender)["label"])

def auto_search(word: str) -> None:
    """Search a word programatically"""
    dpg.set_value("input_word", word)
    search_callback()

def main() -> None:
    """Main func"""
    dpg.create_context()

    # Add the esc key as a valid way to minimize the program
    with dpg.handler_registry():
        dpg.add_key_release_handler(dpg.mvKey_Escape, callback=lambda: Global.toggle_event.set())

    bh.load_font("assets/NotoSerifCJKjp-Medium.otf", 24, set_default=True)
    bh.load_image("assets/cog.png", "cog")

    alignment = Global.config.get("alignment")
    width, height = Global.config.get("window_size")
    screen_width, screen_height = w32.screen_width(), w32.screen_height()
    horizontal_offset, vertical_offset = Global.config.get("offset")
    y_pos = screen_height//2 - height//2 + vertical_offset
    if alignment == "right":
        x_pos = screen_width - width - horizontal_offset
    else:
        x_pos = 0 + horizontal_offset

    dpg.create_viewport(title=Global.appname, x_pos=x_pos, y_pos=y_pos, width=width, height=height,
                        decorated=False, always_on_top=True, clear_color=Color.CLEAR)

    # Main window
    with dpg.window(label=Global.appname, tag="main_window", no_close=True, no_collapse=True):
        with dpg.group(horizontal=True):
            dpg.add_input_text(tag="input_word", hint="Enter a word",
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
    dpg.set_viewport_resize_callback(callback=bh.resize_elements)

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
    w32.respect_dpi()
    main()
