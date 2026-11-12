import tkinter as tk
from tkinter import ttk 

def greetme():
    print("Hello {}!!!".format(name.get() or "World"))
    
root=tk.Tk()
name=tk.StringVar()

frame_0=ttk.Frame(root)
frame_0.pack(side="top",expand=True,fill="both")
name_l=ttk.Label(frame_0,text="Name: ",background="red");
name_l.pack(side="left",fill="both",expand=True)
name_e=ttk.Entry(frame_0,textvariable=name,background="red")
name_e.pack(side="left", fill="both",expand=True)

frame_1=ttk.Frame(root)
frame_1.pack(side="top",expand=True,fill="both")
greet_b=ttk.Button(frame_1,text="Greet",command=greetme)
greet_b.pack(fill="x",expand=True)
quit_b=ttk.Button(frame_1,text="Quit!",command=root.destroy)
quit_b.pack(fill="x",expand=True)

root.mainloop()


