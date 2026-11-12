import tkinter as tk 
from tkinter import ttk 


root=tk.Tk()
root.geometry("600x400")
root.resizable(False,False)
root.title("Scale Widget")

def print_cur(event):
    print(scale.get())

cur_val=tk.DoubleVar()

scale=ttk.Scale(
    root,
    from_=0,
    to=100,
    variable=cur_val,
    command=print_cur
)


scale.pack(fill="x")

print(cur_val.get())



root.mainloop()