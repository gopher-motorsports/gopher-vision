from tkinter import *
from tkinter import ttk
from tkinter import filedialog

def select_yaml():
    path = filedialog.askopenfilename(
        title='Select a GopherCAN configuration',
        filetypes=[('YAML', '*.yaml')]
    )
    print(path)

def select_gdat():
    path = filedialog.askopenfilename(
        title='Select a GDAT file',
        filetypes=[('GDAT', '*.gdat')]
    )
    print(path)

def convert():
    pass

root = Tk()
root.title('GopherVision')
root_frame = ttk.Frame(root)
root_frame.pack()

yaml_frame = ttk.Frame(root_frame, padding=10)
yaml_frame.pack(fill='x')
ttk.Label(yaml_frame, text="Select a GopherCAN config (.yaml):").grid(column=0, row=0)
ttk.Button(yaml_frame, text='Browse', command=select_yaml).grid(column=1, row=0)
ttk.Label(yaml_frame, text='PATH').grid(column=0, row=1, sticky='w')

gdat_frame = ttk.Frame(root_frame, padding=10)
gdat_frame.pack(fill='x')
ttk.Label(gdat_frame, text="Select a data file (.gdat):").grid(column=0, row=0)
ttk.Button(gdat_frame, text='Browse', command=select_gdat).grid(column=1, row=0)
ttk.Label(gdat_frame, text='PATH').grid(column=0, row=1, sticky='w')

convert_frame = ttk.Frame(root_frame, padding=10)
convert_frame.pack(fill='x')
ttk.Button(convert_frame, text='Convert', command=convert).grid(column=0, row=0)
ttk.Label(convert_frame, text='PATH').grid(column=0, row=1, sticky='w')

root.mainloop()