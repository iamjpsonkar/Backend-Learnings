import tkinter as tk
from tkinter import ttk

def greetme():
    print("Hello {}!!!".format(name.get() or "World"))

root=tk.Tk()
name=tk.StringVar()
name_l=ttk.Label(root,text="Name: ")
name_l.pack(side="left")
name_e=ttk.Entry(root,textvariable=name, width=15)
name_e.pack(side="left")
name_e.focus()
greet_b=ttk.Button(root,text="Greet",command=greetme)
greet_b.pack(side="left")
quit_b=ttk.Button(root,text="Quit",command=root.destroy)
quit_b.pack(side="right")


root.mainloop()