import tkinter as tk 
from tkinter import ttk 


class Root(tk.Tk):
    def __init__(self):
        super().__init__() 
        l=ttk.Label(self,text="Hello!!! I am ON.")
        l.pack()
        
        


class MyFrame(ttk.Frame):
    def __init__(self,container):
        print("I am on, INSIDE")
        super().__init__(container)
        self.pack()
        label=ttk.Label(container,text="I am on, inside Frame")
        
        label.pack()
        



root=Root()
mframe=MyFrame(root)
print("I am on")
# mframe.pack(side="left")
root.mainloop()