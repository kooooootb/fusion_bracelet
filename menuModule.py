import tkinter as tk

class inputElement():
    def __init__(self, id, value):
        self.id = id
        self.value = value

def getInputs(dirpath):
    # settings variables
    cfgfn = dirpath + "/inputcfg.txt"
    fontname = "helvetica"
    fontsize = 10
    fontwidth = 10
    gap = 20
    xcoord = 20
    index = 0
    textLength = 0
    
    fd = open(cfgfn, "r")
    for line in fd:
        if len(line.split()[2]) * fontwidth > textLength:
            textLength = len(line.split()[2]) * fontwidth
        index += 1
    fd.close()
    
    height = (index + 1) * fontsize * 2 + gap
    width = textLength + 300
    
    # set the window
    root = tk.Tk()
    
    # set background
    bg = tk.PhotoImage( file = dirpath + "/bgImage.png")
    scaleFactor = min(int(bg.width() / width), int(bg.height() / height)) - 1
    bg = bg.subsample(scaleFactor)
    # Show image using label
    label1 = tk.Label( root, image = bg)
    label1.place(x = 0,y = 0)

    entries = []
    ids = []
    types = []
    index = 0
    
    fd = open(cfgfn,"r")
    
    for line in fd:
        ycoord = index * fontsize * 2 + gap
        words = line.split()
        type = int(words[0])
        default = words[1]
        id = words[2]
        name = line.split(" ", 3)[3]
        
        entry = None
        
        tk.Label(root, text = name, font = (fontname, fontsize)).grid(row = index, column = 0)
        
        if type != 2:
            defString = tk.StringVar(root, value = default)
            entry = tk.Entry(root, textvariable = defString)
            entries.append(entry)
            entry.grid(row = index, column = 1)
        elif type == 2:
            var = tk.BooleanVar()
            entry = tk.Checkbutton(root, variable = var, onvalue = True, offvalue = False)
            entries.append(var)
            entry.grid(row = index, column = 1)
            
        ids.append(id)
        types.append(type)
        
        index += 1
    
    fd.close()
    
    resInputs = []
    
    def onClose():
        i = 0
        for id in ids:
            value = None
            if types[i] == 1:
                value = float(entries[i].get())
            else:
                value = entries[i].get()
            input = inputElement(id, value)
            resInputs.append(input)
            i += 1
        root.destroy()
    
    tk.Button(root, text = "Run", command = onClose).grid(row = index, column = 1)

    root.mainloop()
    
    return resInputs

# import os
# inputs = getInputs(os.path.dirname(os.path.realpath(__file__)))
# for input in inputs:
    # print(str(input.value) + " " + input.id)