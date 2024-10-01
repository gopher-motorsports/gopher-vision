# this file browser code works on mac, so it is a problem integrating TK with DPG

from tkinter import filedialog
import tkinter as tk

root = tk.Tk()
root.withdraw()
path = filedialog.askopenfilename(
    title='Open GopherCAN configuration',
    filetypes=[('YAML', '*.yaml')]
)
root.destroy()

print(path)