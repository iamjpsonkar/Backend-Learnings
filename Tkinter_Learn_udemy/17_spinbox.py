import tkinter as tk 
from tkinter import ttk  

root=tk.Tk() 
root.geometry("600x400")
root.resizable(False,False)
root.title("Spibox Widget")

in_val=tk.IntVar(value=20)

sbox=ttk.Spinbox(
    root,
    from_=0,
    to=100, # values=(5,10,20,25)
    textvariable=in_val,
    wrap=False #True
)

sbox.pack()



root.mainloop()