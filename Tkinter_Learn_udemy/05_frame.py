import tkinter as tk
from tkinter import ttk

root=tk.Tk()

main_f=ttk.Frame(root)
main_f.pack(side="left",fill="both",expand=True)

lb1=ttk.Label(main_f, text="Label01", background="red")
lb1.pack(fill="both",expand=True)
lb2=ttk.Label(main_f, text="Label02", background="blue")
lb2.pack(fill="both",expand=True)

lb=ttk.Label(root,text="Label", background="green")
lb.pack(side="left",fill="both",expand=True)

root.mainloop()


