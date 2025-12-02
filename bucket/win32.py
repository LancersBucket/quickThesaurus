"""Win32 calls"""
import ctypes
import win32gui
import win32con
import win32api

def toggle_window(appname: str) -> str | None:
    """Thread-safe toggle using only win32 calls (safe to call from hotkey thread)"""
    try:
        hwnd = win32gui.FindWindow(None, appname)
        if not hwnd:
            # Fallback: try to find any top-level window that contains the appname in its title
            def _enum(hwnd_enum, result):
                title = win32gui.GetWindowText(hwnd_enum)
                if title and appname in title:
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
            return "restore"

        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return "minimize"
    except Exception as e:
        print(f"Error in toggle_window_win32: {e}")
        return None

def screen_width() -> int:
    """Get screen width"""
    return win32api.GetSystemMetrics(win32con.SM_CXSCREEN)

def screen_height() -> int:
    """Get screen height"""
    return win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

def move_window(appname, x_pos, y_pos, width, height) -> None:
    """Move window"""
    win32gui.MoveWindow(win32gui.FindWindow(None, appname),
                        x_pos, y_pos, width, height, True)

def respect_dpi() -> None:
    """Set process to be DPI aware"""
    ctypes.windll.user32.SetProcessDPIAware()
