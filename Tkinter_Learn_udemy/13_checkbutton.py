import tkinter as tk 
from tkinter import ttk 


root=tk.Tk() 
root.geometry("600x400")
root.resizable(False,False)
root.title("Checkbutton Widget")


selected_options=tk.StringVar() 

def print_selected_options():
    print("Selected Option is {}".format(selected_options.get()))

checkbutton=ttk.Checkbutton(
    root,
    text="CheckButton Example",
    variable=selected_options,
    onvalue="ON",
    offvalue="OFF",
    command=print_selected_options
)

checkbutton.pack()

root.mainloop()