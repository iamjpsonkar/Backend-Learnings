import tkinter as tk
from tkinter import Label, ttk 

root=tk.Tk() 
root.geometry("600x400")
root.resizable(False,False)
root.title("Separator Widget")

Label1=ttk.Label(root,text="I am first Label")
Label1.pack()

sep=ttk.Separator(root,orient="horizontal")
sep.pack(fill="x")

Label2=ttk.Label(root,text="I am second Label")
Label2.pack() 

root.mainloop()