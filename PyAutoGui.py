from datetime import datetime
from pathlib import Path
import time
import urllib.parse

import pyautogui
import pygetwindow
import pyperclip
import os
import subprocess

# Change this to the city you want in the daily weather report.
CITY = "London"

pyautogui.FAILSAFE = True  # Move the mouse to the upper-left corner to stop.
pyautogui.PAUSE = 0.25


def normalize_title(title: str) -> str:
    # Edge titles contain a zero-width space: "Microsoft​ Edge".
    return title.replace("​", "").lower()


def wait_for_window(title_part: str, timeout: int = 45, ignore_handles=()):
    """Wait for a window whose title contains title_part, skipping ignore_handles."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        matches = [
            window
            for window in pygetwindow.getAllWindows()
            if window._hWnd not in ignore_handles
            and normalize_title(title_part) in normalize_title(window.title)
        ]
        if matches:
            window = matches[0]
            try:
                window.activate()
                window.maximize()
            except Exception:
                pass
            return window
        time.sleep(0.5)

    raise TimeoutError(f"Timed out waiting for a window containing {title_part!r}.")


def open_from_start_menu(app_name: str, title_part: str):
    """Launch Microsoft Edge directly; launch other apps through Start search."""
    # Remember windows that are already open so we return the newly launched one.
    existing_handles = {window._hWnd for window in pygetwindow.getAllWindows()}

    if app_name == "Microsoft Edge":
        candidates = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
        ]
        edge = next((path for path in candidates if path.is_file()), None)

        if edge is None:
            raise FileNotFoundError(
                "Microsoft Edge was not found in the standard Windows install locations."
            )

        subprocess.Popen([str(edge)])
    else:
        pyautogui.press("win")
        time.sleep(0.7)
        pyperclip.copy(app_name)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.5)
        pyautogui.press("enter")

    return wait_for_window(title_part, ignore_handles=existing_handles)


def fetch_weather() -> str:
    """Open the weather page in Edge and copy its displayed text."""
    edge_window = open_from_start_menu("Microsoft Edge", "Microsoft Edge")

    time.sleep(1)
    pyautogui.click(
        edge_window.left + edge_window.width // 2,
        edge_window.top + edge_window.height // 2,
    )
    time.sleep(0.5)

    city = urllib.parse.quote(CITY)
    url = f"https://wttr.in/{city}?format=3"

    pyautogui.hotkey("ctrl", "l")
    pyperclip.copy(url)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")

    time.sleep(5)
    for _ in range(8):
        sentinel = f"clipboard-check-{time.time()}"
        pyperclip.copy(sentinel)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.7)

        copied_text = pyperclip.paste().strip()
        if copied_text and copied_text != sentinel:
            lines = [line.strip() for line in copied_text.splitlines() if line.strip()]
            if lines:
                return lines[0].replace("\t", " ").replace("\r", " ").replace("\n", " ")

        time.sleep(1)

    raise RuntimeError("Could not copy weather text from the Edge page.")


def main():
    report_dir = Path(__file__).resolve().parent
    run_time = datetime.now()
    date_stamp = run_time.strftime("%Y-%m-%d")
    report_path = report_dir / f"daily_report_{date_stamp}.txt"
    screenshot_path = report_dir / f"daily_report_{date_stamp}.png"
    report_already_exists = report_path.exists()

    weather = fetch_weather()

    open_from_start_menu("Notepad", "Notepad")

    # Start from a blank document in case Notepad restored a previous session.
    pyautogui.hotkey("ctrl", "n")
    time.sleep(1)

    # Paste the report text into the new Notepad document.
    timestamp = run_time.strftime("%Y-%m-%d %H:%M:%S")
    comment = "Check conditions before planning outdoor activities."
    lines = [
        "Daily Weather Report",
        f"Date & Time: {timestamp}",
        f"Fetched data: {weather}",
        f"Comment: {comment}",
    ]
    pyperclip.copy("\r\n".join(lines))
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1)

    # Ctrl+Shift+S opens Save As in Notepad.
    pyautogui.hotkey("ctrl", "shift", "s")
    time.sleep(2)
    pyautogui.hotkey("alt", "n")  # Focus the File name field.
    pyautogui.hotkey("ctrl", "a")
    pyperclip.copy(str(report_path))
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")
    time.sleep(2)

    # Confirm replacing today's report if it already exists.
    if report_already_exists:
        pyautogui.hotkey("alt", "y")
        time.sleep(2)

    # Wait for Notepad to finish writing the file.
    deadline = time.time() + 30
    while time.time() < deadline and not report_path.exists():
        time.sleep(0.5)
    if not report_path.exists():
        raise RuntimeError(f"Notepad did not create the report: {report_path}")

    # Capture the maximized Notepad window with the report visible.
    wait_for_window(report_path.stem)
    time.sleep(1)
    pyautogui.screenshot().save(screenshot_path)

    print(f"Report saved: {report_path}")
    print(f"Screenshot saved: {screenshot_path}")


if __name__ == "__main__":
    main()