import tkinter as tk

class inputElement():
    def __init__(self, id, value):
        self.id = id
        self.value = value

def isCommented(line):
    return True if line.split()[0] == '#' else False

def getInputs(dirpath):
    # set variables
    cfgfn = dirpath + "/inputcfg.txt"
    fontname = "helvetica"
    fontsize = 10
    fontwidth = 10
    gap = 20
    xcoord = 10
    index = 0
    textLength = 0
    textColor = "#ebebeb"
    
    with open(cfgfn, "r") as fd:
        for line in fd:
            if isCommented(line): continue
            if len(line.split()[2]) * fontwidth > textLength:
                textLength = len(line.split()[2]) * fontwidth
            index += 1
    
    height = (index + 1) * fontsize * 2 + 2 * gap 
    width = textLength + 150
    
    # set the window
    root = tk.Tk()
    root.resizable(False, False)
    root.title("Input menu")
    root.iconbitmap(dirpath + '/menu.ico')

    bg = tk.PhotoImage( file = dirpath + "/bgImage.png")
    scaleFactor = min(int(bg.width() / width), int(bg.height() / height))
    bg = bg.subsample(scaleFactor)
    canvas = tk.Canvas(root, width=width, height=height, bg="white")
    canvas.pack(expand = tk.YES, fill = tk.BOTH)
    canvas.create_image(0, 0, image = bg, anchor = tk.NW)

    entries = []
    ids = []
    types = []
    index = 0
    
    with open(cfgfn,"r") as fd:
        for line in fd:
            if isCommented(line): continue
            ycoord = index * fontsize * 2 + gap
            words = line.split()
            type = int(words[0])
            default = words[1]
            id = words[2]
            name = line.split(" ", 3)[3]
            
            entry = None
            
            canvas.create_text(xcoord, ycoord, text=name, anchor=tk.NW, fill=textColor, font=(fontname, fontsize))

            if type != 2:
                entry = tk.Entry(root, textvariable=tk.StringVar(root, value=default))
                entries.append(entry)
                entry.place(x=textLength, y=ycoord)
            elif type == 2:
                var = tk.BooleanVar(value=(True if (int(default) == 1) else False))
                entry = tk.Checkbutton(root, variable=var, onvalue=True, offvalue=False)
                entries.append(var)
                entry.place(x=textLength, y=ycoord)
                
            ids.append(id)
            types.append(type)
            
            index += 1
    
    resInputs = []
    
    def onClose():
        for id, type, entry in zip(ids, types, entries):
            value = None
            if type == 1:
                value = float(entry.get())
            else:
                value = entry.get()
            input = inputElement(id, value)
            resInputs.append(input)
        root.destroy()
    
    def enterPressed(event):
        onClose()

    def onExit():# when 'X' button is pressed
        for id, type, entry in zip(ids, types, entries):
            value = None
            if type == 1:
                value = float(entry.get())
            else:
                value = entry.get()
            if id == "Text": 
                value = ""
            input = inputElement(id, value)
            resInputs.append(input)
        root.destroy()

    
    tk.Button(root, text = "Run", command = onClose).place(x=xcoord, y=ycoord + fontsize * 2)
    root.bind('<Return>', enterPressed)

    root.protocol("WM_DELETE_WINDOW", onExit)

    root.mainloop()
    
    return resInputs

if __name__ == '__main__':
    import os
    inputs = getInputs(os.path.dirname(os.path.realpath(__file__)))
    for input in inputs:
        print(str(input.value) + " " + input.id)