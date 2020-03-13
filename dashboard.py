import matplotlib.pyplot as plt
import matplotlib.collections as collections
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
import numpy as np
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from datetime import datetime
import pickle
import os
import sensorlib

optVal = {
    "v400": 4000,
    "v40000": 1000,
    "lowCO2": 413,
    "highCO2": 2000,
    "veryHighCO2": 5000,
    "measurementInterval": 2
}
recordingStart = "00-01-01_at_00-00"
recordingEnd = "00-01-01_at_00-00"
recorded = []


"""
Returns specified number of ticks along an axis
"""
def generateTicks(axis, numTicks):
    tickGap = round(len(axis) / numTicks)
    ticks = []
    counter = 0
    for t in axis:
        if counter % tickGap == 0:
            ticks.append(t)
        counter += 1
    return ticks

def calculateAvg(values):
    return int(round(sum(values)/len(values)))

def setSaveDir():
    localPath = os.path.dirname(os.path.abspath(__file__))
    print('local directory:', localPath)
    # if localPath == "":
    #     localPath = "/home/pi/Documents/sensor"
    saveDirPath = localPath + "/saves"
    if not os.path.exists(saveDirPath):
        print("saves directory not found. Creating...")
        os.mkdir(saveDirPath)
    os.chdir(saveDirPath)
    print("set saves directory as cwd: ", os.getcwd())

"""
TK Main
"""
class Main(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.configure(background='white')
        # GUI Values
        # self.width = 1400
        # self.height = 768
        self.parent = parent
        self.title = parent.wm_title("CO2 Dashboard")
        # self.minimum_size = parent.minsize(width=self.width, height=self.height)

        menubar = ttk.Notebook(master=root)

        self.dashboardTab = DashboardTab(root)
        self.optionsTab = OptionsTab(root)
        self.recordTab = RecordingTab(root)

        menubar.add(self.dashboardTab, text="Live Dashboard")
        menubar.add(self.recordTab, text="Recording")
        menubar.add(self.optionsTab, text="Options & Calibration")
        menubar.pack()

    def updateAllFrames(self):
        self.dashboardTab.uiUpdate()
        self.optionsTab.uiUpdate()
        self.recordTab.uiUpdate()


class DashboardTab(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.configure(background='white')
        # GUI Values
        # self.width = 1400
        # self.height = 768
        self.parent = parent
        self.title = parent.wm_title("CO2 Dashboard")
        # self.minimum_size = parent.minsize(width=self.width, height=self.height)

        # GUI Self-Update Values
        # self.graphAutoUpdateIsRun = False
        self.graphAutoUpdateIsRun = tk.BooleanVar(value = False)
        self.graphAutoUpdateTime = 1000


        # CO2 Graph init
        self.graphCO2 = UIGraph(self, "Time (s)", "CO2 (ppm)", -600, 0, step=5, row=0, column=0, rowspan=1, columnspan=5, figx = 15)
        self.graphCO2.addHLine("veryHighCO2", "r", "solid", "very high")
        self.graphCO2.addHLine("highCO2", "orange", "dashed", "high")
        self.graphCO2.addHLine("lowCO2", "g", "dashed", "normal")
        self.graphCO2.enableBars()
        self.graphCO2.enableLegend()
        self.graphCO2.setYAxis(0, 8000)
        self.graphCO2.updatePlot()



        # Seperator
        ttk.Separator(master=self, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=12, sticky=tk.E + tk.W)

        # CO2 Delta Graph init
        self.graphCO2Delta = UIGraph(self, "Time (s)", "\u0394 CO2 (ppm)", -300, 0, step=5, row=2, column=0, rowspan=5, columnspan=2, figx = 9, figy=2)
        self.graphCO2Delta.zeroLine = True
        # self.graphCO2Delta.addHLine(0, "grey")
        self.lastRead = 0
        self.graphCO2Delta.updatePlot()

        # Seperator
        # ttk.Separator(master=self, orient=tk.VERTICAL).grid(row=0, column=1, rowspan=10, sticky=tk.N+tk.S)
        ttk.Label(master=self, text="Averages over the last 10 minutes").grid(column=2, columnspan=2, row=2, sticky=tk.E+tk.W, padx=105, pady=0)
        names = ["avgCO2",
                 "avgDeltaCO2"]
        texts = ["Average CO2 (in ppm):",
                 "Average \u0394CO2 (in ppm/step):"]
        warningTexts = ["Average CO2 is normal",
                        "Average CO2 is (almost) stable"]
        self.label = {}
        self.warningLabel = {}
        self.entry = {}
        rowCounter = 3
        for name, text, wtext in zip(names, texts, warningTexts):
            self.label[name] = ttk.Label(master=self, text=text)
            self.warningLabel[name] = tk.Label(master=self, text=wtext)
            self.entry[name] = ttk.Entry(master=self, width=10)
            self.label[name].grid(row=rowCounter, column=2, sticky=tk.E, padx=5, pady=0)
            self.entry[name].grid(row=rowCounter, column=3, sticky=tk.W, padx=5, pady=0)
            self.warningLabel[name].grid(row=rowCounter + 1, column=2, columnspan=2, sticky=tk.E + tk.W, padx=15,
                                         pady=0)
            self.entry[name].insert(0, 0)
            self.entry[name].configure(state='readonly')
            rowCounter += 2

        # Buttons innit
        self.autoUpdateCheckButton = ttk.Checkbutton(self, text ='Auto-Update',
                     takefocus = 0, variable=self.graphAutoUpdateIsRun)
        self.autoUpdateCheckButton.grid(row=2, column=4, sticky=tk.N+tk.S+tk.W+tk.E, padx=10, pady=7)
        #  self.graphAutoUpdateToggleButton = ttk.Button(master=self, text="Auto-Update", command=self.graphAutoUpdateToggle)
        # self.graphAutoUpdateToggleButton.grid(row=2, column=4, sticky=tk.N+tk.S+tk.W+tk.E, padx=10, pady=7)
        self.updatePlotButton = ttk.Button(master=self, text="Clear", command=self.clear)
        self.updatePlotButton.grid(row=3, column=4, sticky=tk.N+tk.S+tk.W+tk.E, padx=10, pady=7)


        self.lastUpdateTime = datetime.now()
        self.autoUpdate()

    def clear(self):
        self.graphCO2.buffer.clear()
        self.graphCO2Delta.buffer.clear()
        self.graphCO2.updatePlot()
        self.graphCO2Delta.updatePlot()
        self.lastRead = 0

    def graphTick(self):
        read = sensorlib.readPPM(optVal["v400"], optVal["v40000"])
        self.graphCO2.appendToBuffer(read)
        self.graphCO2Delta.appendToBuffer((read - self.lastRead))
        self.lastRead = read

        self.uiUpdate()

    def uiUpdate(self):
        self.graphCO2.updatePlot()
        self.graphCO2Delta.updatePlot()
        self.avgUpdate()

    def autoUpdate(self):
        if self.graphAutoUpdateIsRun.get():
            self.graphTick()
        self.after(5000, self.autoUpdate)

    def graphAutoUpdateToggle(self):
        self.graphAutoUpdateIsRun = not self.graphAutoUpdateIsRun

    def avgUpdate(self):
        # update avg
        avgCO2 = calculateAvg(self.graphCO2.buffer.buffer)
        self.entry["avgCO2"].configure(state="normal")
        self.entry["avgCO2"].delete(0, tk.END)
        self.entry["avgCO2"].insert(0, avgCO2)
        self.entry["avgCO2"].configure(state="readonly")

        # color avg label
        if avgCO2 <= optVal["lowCO2"]:
            self.warningLabel["avgCO2"].config(text="Average CO2 is low", bg="lightgreen")
        elif avgCO2 < optVal["highCO2"]:
            self.warningLabel["avgCO2"].config(text="Average CO2 is normal", bg="green")
        elif avgCO2 >= optVal["highCO2"]:
            self.warningLabel["avgCO2"].config(text="Average CO2 is high", bg="orange")
        elif avgCO2 >= optVal["veryHighCO2"]:
            self.warningLabel["avgCO2"].config(text="Average CO2 is very high", bg="red")

        avgDeltaCO2 = calculateAvg(self.graphCO2Delta.buffer.buffer)
        self.entry["avgDeltaCO2"].configure(state="normal")
        self.entry["avgDeltaCO2"].delete(0, tk.END)
        self.entry["avgDeltaCO2"].insert(0, avgDeltaCO2)
        self.entry["avgDeltaCO2"].configure(state="readonly")

        # color avg label
        if avgDeltaCO2 >= 200:
            self.warningLabel["avgDeltaCO2"].config(text="Average CO2 is increasing", bg="orange")
        elif avgDeltaCO2 <= -200:
            self.warningLabel["avgDeltaCO2"].config(text="Average CO2 is decreasing", bg="green")
        else:
            self.warningLabel["avgDeltaCO2"].config(text="Average CO2 is (almost) stable", bg="lightblue")


class RecordingTab(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.configure(background='white')
        # GUI Values
        # self.width = 1400
        # self.height = 768
        self.parent = parent
        self.title = parent.wm_title("Recording")
        # self.minimum_size = parent.minsize(width=self.width, height=self.height)

        # recording frame states function checks
        # states are: "clear", "recording", "loaded"
        self.state = "loaded"

        # Graphs innit
        self.figure1 = plt.Figure(figsize=(15, 4), dpi=100)
        self.figure2 = plt.Figure(figsize=(9, 2), dpi=100)
        self.subplot1 = self.figure1.add_subplot(111)
        self.subplot2 = self.figure2.add_subplot(111)
        self.canvas1 = FigureCanvasTkAgg(self.figure1, master=self)
        self.canvas2 = FigureCanvasTkAgg(self.figure2, master=self)
        self.canvas1.get_tk_widget().grid(row=0, column=0, rowspan=1, columnspan=6)
        self.canvas2.get_tk_widget().grid(row=2, column=0, rowspan=4, columnspan=1)




        # Seperators
        ttk.Separator(master=self, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=12, sticky=tk.E + tk.W)
        ttk.Separator(master=self, orient=tk.VERTICAL).grid(row=2, column=1, rowspan=4, sticky=tk.N + tk.S)
        ttk.Separator(master=self, orient=tk.VERTICAL).grid(row=2, column=4, rowspan=4, sticky=tk.N + tk.S)

        # Avg Boxes & labels innit
        self.entry = {}
        self.label = {}
        self.warningLabel = {}

        names = ["avgCO2",
                 "avgDeltaCO2"]
        texts =  ["Average CO2 (in ppm):",
                 "Average \u0394CO2 (in ppm/step):"]
        warningTexts = ["Start or load a recording to gain average evaluation",
                        "Start or load a recording to gain average evaluation"]
        rowCounter = 2
        for name, text, wtext in zip(names, texts, warningTexts):
            self.label[name] = ttk.Label(master=self, text=text)
            self.warningLabel[name] = tk.Label(master=self, text=wtext)
            self.entry[name] = ttk.Entry(master=self, width=10)
            self.label[name].grid(row=rowCounter, column=2, sticky=tk.E, padx=5, pady=0)
            self.entry[name].grid(row=rowCounter, column=3, sticky=tk.W, padx=5, pady=0)
            self.warningLabel[name].grid(row=rowCounter+1, column=2, columnspan=2, sticky=tk.E+tk.W, padx=15, pady=0)
            self.entry[name].insert(0, 0)
            self.entry[name].configure(state='readonly')
            rowCounter += 2

        # Buttons innit
        self.clearButton = ttk.Button(master=self, text="Clear", command=self.clear)
        self.clearButton.grid(row=2, rowspan=1, column=5, sticky=tk.N + tk.S + tk.W + tk.E, padx=10,
                                              pady=7)
        self.loadButton = ttk.Button(master=self, text="Load", command=self.load)
        self.loadButton.grid(row=3, rowspan=1, column=5, sticky=tk.N + tk.S + tk.W + tk.E, padx=10, pady=7)

        self.startRecordingButton = ttk.Button(master=self, text="Start Recording", command=self.startRecording)
        self.startRecordingButton.grid(row=4, rowspan=1, column=5, sticky=tk.N+tk.S+tk.W+tk.E, padx=10, pady=7)

        self.endRecordingButton = ttk.Button(master=self, text="End Recording & Save", command=self.stopRecording)
        self.endRecordingButton.grid(row=5, rowspan=1, column=5, sticky=tk.N+tk.S+tk.W+tk.E, padx=10, pady=7)

        # Set button states
        self.updateButtonStates()

        self.plotCO2Update()
        self.plotCO2DeltaUpdate()
        self.clear()

        self.recording = False
        # auto ui-updates
        self.autoUpdate()

    """
    enables/disables buttons according to frame state
    """
    def updateButtonStates(self):
        if self.state == "clear":
            self.clearButton.config(state="disabled")
            self.loadButton.config(state="enabled")
            self.startRecordingButton.config(state="enabled")
            self.endRecordingButton.config(state="disabled")

        elif self.state == "loaded":
            self.clearButton.config(state="enabled")
            self.loadButton.config(state="enabled")
            self.startRecordingButton.config(state="disabled")
            self.endRecordingButton.config(state="disabled")

        elif self.state == "recording":
            self.clearButton.config(state="disabled")
            self.loadButton.config(state="disabled")
            self.startRecordingButton.config(state="disabled")
            self.endRecordingButton.config(state="enabled")

        else:
            raise Exception("Invalid State: " + self.state)

    """
    clear all graphs and data
    """
    def clear(self):
        if self.state == "loaded" or self.state == "recording":
            self.state = "clear"
            self.updateButtonStates()
            # clear internal recording data
            global recorded
            recorded = []

            # clear plots
            self.subplot1.cla()
            self.subplot2.cla()
            self.subplot1.plot([0, 1], [0, 0], color="black")
            self.subplot2.plot([0, 1], [0, 0], color="black")
            self.subplot1.margins(0, 0)
            self.subplot2.margins(0, 0)
            self.figure1.tight_layout()
            self.figure2.tight_layout()
            self.canvas1.draw()
            self.canvas2.draw()

            # clear avg entrys
            self.entry["avgCO2"].configure(state="normal")
            self.entry["avgCO2"].delete(0, tk.END)
            self.entry["avgCO2"].insert(0, 0)
            self.entry["avgCO2"].configure(state="readonly")

            self.entry["avgDeltaCO2"].configure(state="normal")
            self.entry["avgDeltaCO2"].delete(0, tk.END)
            self.entry["avgDeltaCO2"].insert(0, 0)
            self.entry["avgDeltaCO2"].configure(state="readonly")

            # reset avg warning labels
            self.warningLabel["avgCO2"].config(text="Start or load a recording to gain average evaluation", bg="white")
            self.warningLabel["avgDeltaCO2"].config(text="Start or load a recording to gain average evaluation", bg="white")

    def save(self):
        filename = recordingStart + ".pickle"
        with open(filename, 'wb') as handle:
            pickle.dump(recorded, handle, protocol=pickle.HIGHEST_PROTOCOL)
            print("Recording saved: "+os.getcwd()+"\\"+filename)
            tk.messagebox.showinfo(title="Recording saved",
                                   message="Recording was saved at: "+os.getcwd()+"\\"+filename)

    def load(self):
        if self.state == "loaded" or self.state == "clear":
            global recorded
            # tk file picker
            filename = filedialog.askopenfilename(initialdir=os.getcwd(), title="Select file",
                                                       filetypes=(("pickle files", "*.pickle"), ("all files", "*.*")))
            # Check if file exists
            if filename != "":
                if os.path.exists(filename):
                    with open(filename, 'rb') as handle:
                        recorded = pickle.load(handle)

                    self.plotCO2Update()
                    self.plotCO2DeltaUpdate()

                    self.state = "loaded"
                    self.updateButtonStates()
                else:
                    tk.messagebox.showerror(title="Failed to load file",
                                   message="Failed to load file: file does not exist")

    def uiUpdate(self):
        self.plotCO2Update()
        self.plotCO2DeltaUpdate()


    def autoUpdate(self):
        if self.recording:
            self.recordCurrentMeasurement()
            self.uiUpdate()
        self.after(optVal["measurementInterval"]*60000, self.autoUpdate)

    def recordCurrentMeasurement(self):
        global recorded
        recorded.append((datetime.now().strftime("%H:%M"), sensorlib.readPPM(optVal["v400"], optVal["v40000"])))

    def startRecording(self):
        if self.state == "clear":
            self.state = "recording"
            self.updateButtonStates()
            # set global recording start date&time
            global recordingStart
            recordingStart = datetime.now().strftime("%y-%m-%d_at_%H-%M")
            self.state = "recording"
            self.recording = True

    def stopRecording(self):
        if self.state == "recording":
            # set global recording end date&time
            global recordingEnd
            recordingEnd = datetime.now().strftime("%y-%m-%d_at_%H-%M")
            self.recording = False
            # Check if saving recording makes sense
            if len(recorded) >= 2:
                self.state = "loaded"
                self.updateButtonStates()
                self.save()

            else:
                tk.messagebox.showwarning(title="Recording not saved",
                                          message="Recording was too short and not saved")
                self.clear()



    """
    Draws co2 plot and updates avg co2 entry
    """
    def plotCO2Update(self):
        if len(recorded) >= 2:
            # recorded data conversion
            timestamps = np.array([t for t, v in recorded])
            values = np.array([v for t, v in recorded])

            # clear & plot
            self.subplot1.cla()
            self.subplot1.plot(timestamps, values, label="Gradient")
            # set margins
            maxVal = np.amax(values)
            maxVal = maxVal * 1.1
            if maxVal < optVal["veryHighCO2"]:
                 maxVal = optVal["veryHighCO2"]*1.1
            self.subplot1.set_ylim(ymin = 0, ymax = maxVal)

            # hlines
            self.subplot1.hlines(optVal["veryHighCO2"], timestamps[0], timestamps[-1],
                                 "red", "solid", "Very High")
            self.subplot1.hlines(optVal["highCO2"], timestamps[0], timestamps[-1],
                                 "orange", "dashed", "High")
            self.subplot1.hlines(optVal["lowCO2"], timestamps[0], timestamps[-1],
                                 "green", "dashed", "Normal")

            # margins & labels
            self.subplot1.margins(x=0, y=0, tight=True)
            self.subplot1.set_ylabel("CO2 (ppm)")
            self.subplot1.set_xlabel("time")
                
            # fills
            zeroLine = [0 in range(len(values))]
            self.subplot1.fill_between(timestamps, values, zeroLine,
                                       where=values > optVal["highCO2"], color="orange", alpha=0.3)
            self.subplot1.fill_between(timestamps, values, zeroLine,
                                       where=values > optVal["veryHighCO2"], color="red", alpha=0.3)

            # manual xticks as matplotlib is retarded x2
            if len(timestamps) > 24:
                self.subplot1.set_xticks(generateTicks(timestamps, 24))

            # legend
            self.subplot1.legend()

            # grid, axis label tilt, tight layout & draw
            self.subplot1.grid()
            self.figure1.autofmt_xdate()
            self.figure1.tight_layout()
            self.canvas1.draw()

            # update avg
            avgCO2 = calculateAvg(values)
            self.entry["avgCO2"].configure(state="normal")
            self.entry["avgCO2"].delete(0, tk.END)
            self.entry["avgCO2"].insert(0, avgCO2)
            self.entry["avgCO2"].configure(state="readonly")

            # color avg label
            if avgCO2 <= optVal["lowCO2"]:
                self.warningLabel["avgCO2"].config(text="Average CO2 is low", bg="lightgreen")
            elif avgCO2 < optVal["highCO2"]:
                self.warningLabel["avgCO2"].config(text="Average CO2 is normal", bg="green")
            elif avgCO2 >= optVal["highCO2"]:
                self.warningLabel["avgCO2"].config(text="Average CO2 is high", bg="orange")
            elif avgCO2 >= optVal["veryHighCO2"]:
                self.warningLabel["avgCO2"].config(text="Average CO2 is very high", bg="red")


    """
    Draws delta co2 plot and updates avg delta co2 entry
    """
    def plotCO2DeltaUpdate(self):
        # Check if delta plot males sense (>=3)
        if len(recorded) >= 3:
            # recorded data conversion
            timestamps = [t for t, v in recorded]
            values = [v for t, v in recorded]

            # Calc deltas
            deltaValues = []
            prevVal = 0
            for v in values:
                deltaValues.append(v - prevVal)
                prevVal = v
            # Shorten axis as first delta is irrelevant
            timestamps.pop(0)
            deltaValues.pop(0)

            # clear & plot
            self.subplot2.cla()
            self.subplot2.plot(timestamps, deltaValues)

            # margins & labels
            self.subplot2.margins(x=0, y=0.1, tight=True)
            self.subplot2.set_ylabel("\u0394 CO2 (ppm)")
            self.subplot2.set_xlabel("time")

            # hlines
            self.subplot2.hlines(0, timestamps[0], timestamps[-1], "grey", "solid")

            # manual xticks as matplotlib is retarded x3
            if len(timestamps) > 24:
                self.subplot2.set_xticks(generateTicks(timestamps, 24))

            # grid, axis label tilt, tight layout & draw
            self.subplot2.grid()
            self.figure2.autofmt_xdate()
            self.figure2.tight_layout()
            self.canvas2.draw()

            # update avg entry
            avgDeltaCO2 = calculateAvg(deltaValues)
            self.entry["avgDeltaCO2"].configure(state="normal")
            self.entry["avgDeltaCO2"].delete(0, tk.END)
            self.entry["avgDeltaCO2"].insert(0, avgDeltaCO2)
            self.entry["avgDeltaCO2"].configure(state="readonly")

            # color avg label
            if avgDeltaCO2 >= 200:
                self.warningLabel["avgDeltaCO2"].config(text="Average CO2 is increasing", bg="orange")
            elif avgDeltaCO2 <= -200:
                self.warningLabel["avgDeltaCO2"].config(text="Average CO2 is decreasing", bg="green")
            else:
                self.warningLabel["avgDeltaCO2"].config(text="Average CO2 is (almost) stable", bg="lightblue")




class OptionsTab(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.configure(background='white')
        # GUI Values
        # self.width = 1400
        # self.height = 768
        self.parent = parent

        # Load settings file
        self.loadOptions()

        # Raw Voltage Graph
        self.graphRaw = UIGraph(self, "Time (s)", "Raw (Digitalised)", -300, 0, step=5, row=0, column=0, rowspan=20, columnspan=1,  figx = 10, figy=6)
        self.graphRaw.updatePlot()

        # Seperator
        ttk.Separator(master=self, orient=tk.VERTICAL).grid(row=0, column=1, rowspan=24, sticky=tk.N + tk.S)

        # Option labels and entries innit
        self.entry = {}
        self.label = {}
        text =  {"v400": "400 ppm calibration value:",
                "v40000": "40000 ppm calibration value:",
                "lowCO2": "Low CO2 (in ppm):",
                "highCO2": "High CO2 (in ppm):",
                "veryHighCO2": "Very High CO2 (in ppm):",
                "measurementInterval": "Interval for recording measurements (in min):"
                }

        rowCounter = 0
        for name, val in optVal.items():
            self.label[name] = ttk.Label(master=self, text=text[name])
            self.entry[name] = ttk.Entry(master=self, width=10)
            self.label[name].grid(row=rowCounter, column=3, sticky=tk.E, padx=25, pady=5)
            self.entry[name].grid(row=rowCounter, column=4, sticky=tk.W, padx=25, pady=5)
            self.entry[name].insert(0, val)
            rowCounter += 1

        # Save Button innit
        self.saveButton = ttk.Button(master=self, text="Save", command=self.saveOptions)
        self.saveButton.grid(row=rowCounter, column=3, columnspan=2, sticky=tk.W+tk.E, padx=25, pady=5)
        rowCounter += 1

        # Seperator
        ttk.Separator(master=self, orient=tk.HORIZONTAL).grid(row=rowCounter, column=3, columnspan=2, sticky=tk.E + tk.W)
        rowCounter += 1

        # Current value label and entry innit
        self.readOnlyEntry = {}
        self.readOnlyLabel = {}

        names = ["raw", "CO2"]
        texts = ["Current Sensor Raw:", "Corresponding ppm value:"]

        for name, text in zip(names, texts):
            self.readOnlyLabel[name] = ttk.Label(master=self, text=text)
            self.readOnlyLabel[name].grid(row=rowCounter, column=3, sticky=tk.E, padx=25, pady=5)
            self.readOnlyEntry[name] = ttk.Entry(master=self, width=10)
            self.readOnlyEntry[name].grid(row=rowCounter, column=4, sticky=tk.W, padx=25, pady=5)
            self.readOnlyEntry[name].insert(0, 0)
            self.readOnlyEntry[name].config(state="readonly")
            rowCounter += 1

        # auto-update button innit
        self.autoUpdateIsRun = tk.BooleanVar(value=False)
        self.autoUpdateCheckButton = ttk.Checkbutton(self, text ="Auto-Update",
                     takefocus = 0, variable=self.autoUpdateIsRun)
        self.autoUpdateCheckButton.grid(row=rowCounter, column=4, columnspan=1, sticky=tk.E, padx=25, pady=5)
        rowCounter += 1
        # clear button innit
        self.clearButton = ttk.Button(master=self, text="Clear Graph", command=self.clear)
        self.clearButton.grid(row=rowCounter, column=3, columnspan=2, sticky=tk.W+tk.E, padx=25, pady=5)
        rowCounter += 1
        # start auto ui updates
        self.autoUpdate()

    """
    auto-updates graph and read only entrys every 5s
    """
    def uiUpdate(self):
        self.graphRaw.updatePlot()
        self.readOnlyEntryUpdate()

    def autoUpdate(self):
        if self.autoUpdateIsRun.get():
            self.graphRaw.appendToBuffer(sensorlib.readRawCO2())
            self.uiUpdate()
        self.after(5000, self.autoUpdate)

    """
    updates read only entrys for raw and corresponding ppm
    """
    def readOnlyEntryUpdate(self):
        # Ensure that corresponding values are calculated using the same raw read
        rawRead = sensorlib.readRawCO2()
        correspondingPPM = int(round(sensorlib.rawToPPM(rawRead, optVal["v400"], optVal["v40000"])))
        # Update Entrys
        self.readOnlyEntry["raw"].config(state="default")
        self.readOnlyEntry["raw"].delete(0, tk.END)
        self.readOnlyEntry["raw"].insert(0, rawRead)
        self.readOnlyEntry["raw"].config(state="readonly")

        self.readOnlyEntry["CO2"].config(state="default")
        self.readOnlyEntry["CO2"].delete(0, tk.END)
        self.readOnlyEntry["CO2"].insert(0, correspondingPPM)
        self.readOnlyEntry["CO2"].config(state="readonly")

    """
    adopts options and saves them to settings file
    """
    def saveOptions(self):
        for name in optVal:
            newVal = self.entry[name].get()
            # validity check (int and >=1)
            if newVal.isdigit():
                if int(newVal) >= 1:
                    # adopt value
                    optVal[name] = int(newVal)
        # update other frames
        app.updateAllFrames()
        # save to settings file
        with open("settings.opt", "wb") as handle:
            pickle.dump(optVal, handle, protocol=pickle.HIGHEST_PROTOCOL)
            print("settings saved")

    """
    loads settings file if found (saves/settings.opt)
    """
    def loadOptions(self):
        print("loading settings...")
        if os.path.exists(os.getcwd()+"/settings.opt"):
            with open("settings.opt", "rb") as handle:
                global optVal
                optVal = pickle.load(handle)
                print("settings loaded")
        else:
            print("no settings file found")

    def clear(self):
        self.graphRaw.buffer.clear()
        self.graphRaw.updatePlot()


class UIGraph:
    def __init__(self, master, xName, yName, xStart, xEnd, step = 1, row=0, column=0, rowspan=60, columnspan=100, figx = 8, figy = 4):
        self.master = master
        self.buffer = GraphBuffer(abs(xEnd - xStart) + 1, step)
        self.xName = xName
        self.yName = yName
        self.xStart = xStart
        self.xEnd = xEnd
        self.hLine = {}
        self.zeroLine = False
        self.t = np.arange(xStart, xEnd+1, step)

        self.figure = plt.Figure(figsize=(figx, figy), dpi=100)

        self.subplot = self.figure.add_subplot(111)
        # self.subplot.axis([xStart, xEnd, 0, 7000])
        self.subplot.set_ylabel(yName)
        self.subplot.set_xlabel(xName)
        self.canvas = FigureCanvasTkAgg(self.figure, master=master)  # A tk.DrawingArea.


        self.canvas.get_tk_widget().grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan)

        self.barsEnabled = False
        self.legendEnabled  = False
        self.fixedY = False
        self.yStart = 0
        self.yEnd = 0

    def enableBars(self):
        self.barsEnabled = True

    def enableLegend(self):
        self.legendEnabled = True

    def setYAxis(self, yStart, yEnd):
        self.yStart = yStart
        self.yEnd = yEnd
        self.fixedY = True


    def addHLine(self, name, colors='k', linestyles='solid', label=''):
        self.hLine[name] = [self.xStart, self.xEnd, colors, linestyles, label]

    def drawHLines(self):
        for name, line in self.hLine.items():
            self.subplot.hlines(optVal[name], *line)
            # self.subplot.text(0, line[0], line[5])

    def drawAreaBars(self):
        collection = collections.BrokenBarHCollection.span_where(
            self.t, ymin=0, ymax=8000, where=np.array(self.buffer.buffer) > optVal["veryHighCO2"], facecolor='red', alpha=0.3)
        self.subplot.add_collection(collection)

        collection = collections.BrokenBarHCollection.span_where(
            self.t, ymin=0, ymax=8000, where=np.array(self.buffer.buffer) > optVal["highCO2"], facecolor='orange', alpha=0.3)
        self.subplot.add_collection(collection)

    def appendToBuffer(self, newVal):
        self.buffer.append(newVal)
        self.updatePlot()

    def updatePlot(self):
        self.subplot.cla()

        self.subplot.plot(self.t, self.buffer.buffer)
        self.subplot.margins(0, 0.2)

        if self.barsEnabled:
            self.drawAreaBars()

        self.subplot.set_ylabel(self.yName)
        self.subplot.set_xlabel(self.xName)
        self.drawHLines()

        if self.zeroLine:
            self.subplot.hlines(0, self.xStart, self.xEnd, "grey")

        if self.legendEnabled:
            self.subplot.legend(loc="upper left")
        if self.fixedY:
            self.subplot.axis([self.xStart, self.xEnd, self.yStart, self.yEnd])
        self.subplot.set_xticks(np.arange(self.xStart, self.xEnd+1, 50))
        self.subplot.grid()
        self.figure.tight_layout()
        self.canvas.draw()




class GraphBuffer:
    def __init__(self, length, step = 1):
        self.step = step
        self.length = length
        self.buffer = [0 for i in range(0, length, step)]

    def __str__(self):
        return str(self.buffer)

    def append(self, newValue):
        self.buffer.pop(0)
        self.buffer.append(newValue)

    def clear(self):
        self.buffer = [0 for i in range(0, self.length, self.step)]

    def changeLength(self, newLength):
        deltaL = newLength - self.length
        if deltaL == 0:
            pass

        elif deltaL > 0:
            self.buffer = [0 for i in range(deltaL)] + self.buffer
            self.length = newLength

        elif deltaL < 0:
            deltaL = -deltaL
            for i in range(deltaL):
                self.buffer.pop(0)
            self.length = newLength

    def mean(self):
        totalPPM = 0
        for val in self.buffer:
            totalPPM += val
        meanPPM = totalPPM / self.length
        return meanPPM

if __name__ == "__main__":
    setSaveDir()
    root = tk.Tk()
    root.configure(background='white')

    #ttk.Style().configure("TButton", padding=6, relief="flat",
                          #background="#ccc")

    print(ttk.Style().theme_names())
    ttk.Style().theme_use("clam")
    ttk.Style().configure("TLabel", background="white")
    ttk.Style().configure("TButton", background="white")
    ttk.Style().configure("Notebook", background="white", active="white")
    ttk.Style().configure("TCheckbutton", background="white")

    app = Main(root)
    # app.pack(side="top", fill="both", expand=True)
    root.mainloop()
    # root.protocol("WM_DELETE_WINDOW", app.on_closing())