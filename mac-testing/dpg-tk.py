# this file shows how you can use the tkinter file browser on DPG, by running it on the main thread

import dearpygui.dearpygui as dpg
from tkinter import filedialog
from tkinter import Tk
root = Tk()
root.withdraw()

dpg.create_context()


def open_file():
    file = filedialog.askopenfilename()  # Gives trace trap
    print(f"{file}")

with dpg.window(tag="Demo"):
    dpg.add_checkbox(tag='should_open_file', default_value=False, show=False)
    dpg.add_button(label="Open file", callback=lambda: dpg.set_value('should_open_file', True))

dpg.create_viewport(title="Demo", width=600, height=412)

dpg.setup_dearpygui()
dpg.show_viewport()

dpg.set_primary_window("Demo", True)

while dpg.is_dearpygui_running():
    if dpg.get_value('should_open_file'):
        dpg.set_value('should_open_file', False)
        open_file()
    dpg.render_dearpygui_frame()
    pass
    
dpg.destroy_context()