import tkinter as tk 
from tkinter import ttk 

root=tk.Tk() 
root.geometry("600x400")
root.resizable(False,False)
root.title("Listbox Widget")

prog_langs=("C","C++","Java","Python",".Net","PHP","Javascript")

lbox=tk.Listbox(root,height=6,selectmode="extended") #browse

for i in range(len(prog_langs)):
    lbox.insert(i+1,prog_langs[i])

lbox.pack()

def handel_select(event):
    selected=lbox.curselection()
    print("Selected options are: ")
    for i in selected:
        print(lbox.get(i))
        
lbox.bind("<<ListboxSelect>>",handel_select)

root.mainloop()