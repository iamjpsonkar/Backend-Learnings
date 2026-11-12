import tkinter as tk 
from tkinter import ttk 

root=tk.Tk() 
root.geometry("600x400")
root.resizable(False,False)
root.title("ComboBox Widget")

day=tk.StringVar()

cbox=ttk.Combobox(root,textvariable=day)
cbox['value']=("Sunday","Monday","Tuesday","Wednesday","Thurseday","Friday","Saturday")
cbox['state']="readonly" #normal
cbox.pack()

def handle_selection(event):
    print("Today is {}".format(day.get()))
    print("but we are going to change it to Friday")
    day.set("Friday")
    print(cbox.current(), day.get())
    
cbox.bind("<<ComboboxSelected>>",handle_selection)

root.mainloop()