import tkinter as tk
from tkinter import ttk 

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass 



def greetme():
    print("Hello {}!!!".format(name.get() or "World"))
    
root=tk.Tk()
name=tk.StringVar()
root.columnconfigure(0,weight=1)
root.rowconfigure(0,weight=1)
root.rowconfigure(1,weight=1)

frame_0=ttk.Frame(root)
frame_0.columnconfigure(0,weight=1)
frame_0.columnconfigure(1,weight=1)
frame_0.grid(row=0,column=0,sticky="EW")

name_l=ttk.Label(frame_0,text="Name: ",background="red");
name_l.grid(row=0,column=0,sticky="EW")
name_e=ttk.Entry(frame_0,textvariable=name,background="red")
name_e.grid(row=0,column=1,sticky="EW")

frame_1=ttk.Frame(root)
frame_1.columnconfigure(0,weight=1)
frame_1.columnconfigure(1,weight=1)
frame_1.grid(row=1,column=0,sticky="EW")

greet_b=ttk.Button(frame_1,text="Greet",command=greetme)
greet_b.grid(row=0,column=0,sticky="EW")
quit_b=ttk.Button(frame_1,text="Quit!",command=root.destroy)
quit_b.grid(row=0,column=1,sticky="EW")

root.mainloop()