import tkinter as tk
from tkinter import ttk

def meter2feet(*args):
    try:
        m=float(mval.get())
        f=m*3.281
        fval.set(f"{f:.3f}")
    except:
        pass

root=tk.Tk()
root.title("Distance converter")
root.columnconfigure(0,weight=1)
main=ttk.Frame(root,padding=(30,15))
main.grid()

mval=tk.StringVar();
fval=tk.StringVar(value="Feet shown here");

mlabel=ttk.Label(main,text="Meter: ")

minput=ttk.Entry(main,textvariable=mval)
minput.focus()

flabel=ttk.Label(main,text="Feet: ")

# finput=ttk.Entry(main,textvariable=fval)
fout=ttk.Label(main,textvariable=fval)

cal_buuton=ttk.Button(main,text="Calculate",command=meter2feet)


mlabel.grid(row=0,column=0,sticky="W")
minput.grid(row=0,column=1,sticky="EW")
flabel.grid(row=1,column=0,sticky="W")
fout.grid(row=1,column=1,sticky="EW")
cal_buuton.grid(row=2,column=0,columnspan=2,sticky="EW")

for child in main.winfo_children():
    child.grid_configure(padx=10,pady=10)


root.bind("<Return>",meter2feet)
root.bind("<KP_Enter>",meter2feet)

root.mainloop()