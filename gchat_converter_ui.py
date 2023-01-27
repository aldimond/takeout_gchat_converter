#!/usr/bin/env python3

import io
import tkinter  # type: ignore[import]
import tkinter.filedialog  # type: ignore[import]
import tkinter.messagebox  # type: ignore[import]
import tkinter.scrolledtext  # type: ignore[import]
import tkinter.ttk  # type: ignore[import]
from pathlib import Path

import gchat_converter


def load_zip():
    inpath = tkinter.filedialog.askopenfilename(
        title="We're probably lookin' for a Takeout.zip here",
        filetypes=[("zipfile", "*.zip")],
    )
    load(inpath)


def load_folder():
    inpath = tkinter.filedialog.askdirectory(
        title="Either the Takeout or Google Chat folder should do it",
        mustexist=True,
    )
    load(inpath)


def load(inpath: str):
    search_path = gchat_converter.get_search_path(Path(inpath))

    strio = io.StringIO()
    try:
        for b in (zb, fb, qb):
            b["state"] = "disabled"

        gchat_converter.summarize(search_path, strio, set(), set())
        t = tkinter.scrolledtext.ScrolledText(frm)
        t.grid(column=0, row=1)
        t.insert("1.0", strio.getvalue())
        t["state"] = "disabled"
    except Exception as e:
        tkinter.messagebox.showerror(title="oops", message=str(e))
    finally:
        for b in (zb, fb, qb):
            b["state"] = "normal"


if __name__ == "__main__":
    root = tkinter.Tk()
    frm = tkinter.ttk.Frame(root, padding=10)
    frm.grid()
    tkinter.ttk.Label(frm, text="GChat Takeout Converter").grid(column=0, row=0)
    zb = tkinter.ttk.Button(frm, text="Load .zip", command=load_zip)
    zb.grid(column=1, row=0)
    fb = tkinter.ttk.Button(frm, text="Load folder", command=load_folder)
    fb.grid(column=2, row=0)
    qb = tkinter.ttk.Button(frm, text="Quit", command=root.destroy)
    qb.grid(column=3, row=0)

    root.mainloop()
