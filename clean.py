"""
Close all open documents in SolidWorks without saving.
Useful for cleaning up after test runs.
"""

import win32com.client
import pythoncom
import sys


def main():
    pythoncom.CoInitialize()

    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
    except Exception:
        print("SolidWorks is not running.")
        return

    closed = 0
    while True:
        doc = sw.ActiveDoc
        if not doc:
            break
        title = doc.GetTitle()
        sw.QuitDoc(title)
        closed += 1

    if closed:
        print(f"Closed {closed} document(s).")
    else:
        print("No documents were open.")


if __name__ == "__main__":
    main()
