import tkinter as tk 
from tkinter import ttk 

root=tk.Tk()
root.geometry("600x400")
root.resizable(False,False)
root.title("RadioButton Widget")

r_option=tk.StringVar() 

op1=ttk.Radiobutton(
    root,
    text="Option1",
    variable=r_option,
    value="Option 1"    
)

op2=ttk.Radiobutton(
    root,
    text="Option2",
    variable=r_option,
    value="Option 2"    
)

op3=ttk.Radiobutton(
    root,
    text="Option3",
    variable=r_option,
    value="Option 3"    
)

op1.pack()
op2.pack()
op3.pack()


root.mainloop()