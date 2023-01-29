#!/usr/bin/env python3

import io
import locale
import logging
import shutil
import tkinter  # type: ignore[import]
import tkinter.filedialog  # type: ignore[import]
import tkinter.messagebox  # type: ignore[import]
import tkinter.scrolledtext  # type: ignore[import]
import tkinter.ttk  # type: ignore[import]
from contextlib import contextmanager
from pathlib import Path

import gchat_converter


def load_zip():
    global inpath
    inpath = tkinter.filedialog.askopenfilename(
        title="We're probably lookin' for a Takeout.zip here",
        filetypes=[("zipfile", "*.zip")],
    )
    if inpath:
        load()


def load_folder():
    global inpath
    inpath = tkinter.filedialog.askdirectory(
        title="Either the Takeout or Google Chat folder should do it",
        mustexist=True,
    )
    if inpath:
        load()


def _cleanup_filter(filter_str: str) -> set[str]:
    return (
        set(em.strip().lower() for em in filter_str.split(","))
        if filter_str
        else set()
    )


def load():
    global search_path
    search_path = gchat_converter.get_search_path(Path(inpath))

    strio = io.StringIO()
    with controls_disabled():
        try:
            global group_filter, sender_filter, summary_data
            group_filter = _cleanup_filter(gfe_var.get())
            sender_filter = _cleanup_filter(sfe_var.get())
            summary_data = gchat_converter.make_summary_data(
                search_path, gfch_var.get(), group_filter, sender_filter
            )
            gchat_converter.write_summary(summary_data, strio)

            # Now show relevant controls
            gfe_label.grid(row=1, column=0)
            gfe.grid(row=2, column=0, sticky="ew")
            gfch.grid(row=3, column=0)
            sfe_label.grid(row=4, column=0)
            sfe.grid(row=5, column=0, sticky="ew")
            reload_btn.grid(row=6, column=0)
            generate_btn.grid(row=7, column=0)

            t.grid(row=1, column=0)

            try:
                t["state"] = "normal"
                t.replace("1.0", "end", strio.getvalue())
            finally:
                t["state"] = "disabled"

        except Exception as e:
            logging.exception("Error generating summary")
            tkinter.messagebox.showerror(title="oops", message=str(e))


def gen_html():
    if "summary_data" not in globals():
        tkinter.messagebox.showerror(
            title="oops", message="Hmm, better generate summary first"
        )
        return

    with controls_disabled():
        try:
            outpath = Path(
                tkinter.filedialog.askdirectory(
                    title="Make a folder for output (a new/empty one is good)",
                    mustexist=False,
                )
            )
            if not outpath:
                return

            if outpath.exists():
                if outpath.is_file() or outpath.is_symlink():
                    raise Exception("This seems to not be a folder")

                if outpath.is_dir() and any(outpath.iterdir()):
                    if tkinter.messagebox.askyesno(
                        message="Do you want to delete existing files in this folder?"
                    ):
                        shutil.rmtree(outpath)

            gchat_converter.write_html(
                search_path, sender_filter, outpath, summary_data
            )
            tkinter.messagebox.showinfo(message="Done!")

        except Exception as e:
            logging.exception("Error writing HTML")
            tkinter.messagebox.showerror(title="oops", message=str(e))


if __name__ == "__main__":
    # Note comment on util.TIME_FORMAT
    locale.setlocale(locale.LC_TIME, "en_US")

    root = tkinter.Tk()
    main_frame = tkinter.ttk.Frame(root, padding=10)
    main_frame.grid()
    topbar = tkinter.ttk.Frame(main_frame)
    topbar.grid(row=0, column=0)
    tkinter.ttk.Label(topbar, text="GChat Takeout Converter").grid(
        row=0, column=0
    )
    zb = tkinter.ttk.Button(topbar, text="Load .zip", command=load_zip)
    zb.grid(row=0, column=1)
    fb = tkinter.ttk.Button(topbar, text="Load folder", command=load_folder)
    fb.grid(row=0, column=2)
    qb = tkinter.ttk.Button(topbar, text="Quit", command=root.destroy)
    qb.grid(row=0, column=3)

    inpath: str = ""

    # Controls we aren't showing yet
    t = tkinter.scrolledtext.ScrolledText(main_frame)
    t["state"] = "disabled"

    gfe_label = tkinter.ttk.Label(
        topbar,
        text="Only include chats with these members (comma-separated)",
        anchor="w",
    )
    gfe_var = tkinter.StringVar(value="")
    gfe = tkinter.ttk.Entry(topbar, textvariable=gfe_var)

    gfch_var = tkinter.BooleanVar(value=False)
    gfch = tkinter.ttk.Checkbutton(
        topbar,
        variable=gfch_var,
        text="Exclude groups with other members",
    )

    sfe_label = tkinter.ttk.Label(
        topbar,
        text="Only include messages by these senders (comma-separated)",
        anchor="w",
    )
    sfe_var = tkinter.StringVar(value="")
    sfe = tkinter.ttk.Entry(topbar, textvariable=sfe_var)

    reload_btn = tkinter.ttk.Button(
        topbar, text="Reload with new settings", command=load
    )

    generate_btn = tkinter.ttk.Button(
        topbar, text="GENERATE HTML", command=gen_html
    )

    controls_to_disable = zb, fb, qb, gfe, gfch, sfe, reload_btn, generate_btn

    @contextmanager
    def controls_disabled():
        for c in controls_to_disable:
            c["state"] = "disabled"
        try:
            yield
        finally:
            for c in controls_to_disable:
                c["state"] = "normal"

    root.mainloop()
