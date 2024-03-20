'''
TODO LIST:
    API TODO LIST:
    - [x] Find the best way to do a pull every minute
    - [x] Set up multithreading
    
    UI TODO LIST:
    - [x] Create a file explorer so it easer for the user to pick the location for the file to be created in.
    - [x] Have it create a config file to use when the program is close
    - [x] Have a stop and start button
    - [x] ? Have a refresh button if the config file has been update/ Have it check to see if the config file has been updated
    - [x] Have a status box on what it is doing/ report out any errors
    - [x] Have it print a log on when it incouters a error
    - [x] Be able to update api key and secret
    - [x] Have a way to select each plant
    - [x] Add a way to update or delete presses


'''





import requests , json, hmac, hashlib, time
import pandas as pd
import csv
import os
from datetime import datetime, timezone
import schedule
import threading
import tkinter as tk
import ctypes
from tkinter.scrolledtext import ScrolledText
from tkinter import VERTICAL, HORIZONTAL, N, S, E, W, Menu, filedialog, font, PhotoImage, END
import ttkbootstrap as ttk
import signal
import logging
import queue
from configparser import ConfigParser


key = None
secret = None
api_url = None

job_key = None
job_secret = None

mainPath = None
backUpPath = None
waitTime = None

plants = ['Chicago', 'Mountain Lakes', 'Salt Lake City']
press_list = {} #['47200165','60001071', '60001112']
ml_press_list = {} #['60001073', '47200177']
slc_press_list = {} #['47200304', '60001067', '60002010']


chi_plant = None
slc_plant = None
ml_plant = None

autoRun = None

currnetRunningJob = {}

chi_last_marker = None
jobs_main_path = None
job_data = None
job_wait_time = None

t1 = None
t2 = None
t3 = None
app = None


programLocation = os.getcwd()

logger = logging.getLogger(__name__)

config = ConfigParser()
config.read('config.ini')
class QueueHandler(logging.Handler):
    """Class to send logging records to a queue

    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    """

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


class ConsoleUi:
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):
        self.frame = frame
        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(frame, state='disabled', height=12)
        self.scrolled_text.grid(row=0, column=0, sticky="nswe")
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=True)
        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s: %(message)s', '%m/%d/%Y %H:%M:%S')
        self.queue_handler.setFormatter(formatter)
        logger.addHandler(self.queue_handler)
        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')
        # Autoscroll to the bottom
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)

class NewWindow():
    
    def __init__(self, root):
        #Grabbing global variables
        global key, secret, api_url, job_key, job_secret, waitTime, plants, job_wait_time
        self.sleepNumber = tk.IntVar(value= int(waitTime))
        self.jobsSleepNumber = tk.IntVar(value= int(job_wait_time))
        self.key = tk.StringVar()
        self.secret = tk.StringVar()
        self.job_key = tk.StringVar()
        self.job_secret = tk.StringVar()
        self.pressId = tk.StringVar()
        self.root = root
        windowHeight = 500
        windowWidth = 700
        postion = root.winfo_geometry().split('+')

        self.root.withdraw()

        self.newWin = tk.Toplevel(root)

        self.v = tk.StringVar(self.newWin)
        self.v.set('PRESS')
        self.plant = tk.StringVar()
        self.plant.set('Plant')

        self.newWin.lift()
        self.newWin.title('Config settings')
        self.newWin.geometry(f'{windowWidth}x{windowHeight}+{(int(postion[1]) +200)}+{postion[2]}')
        self.newWin.resizable(False, False)
        self.newWin.wm_iconbitmap(f'{programLocation}\\deluxe_logo.ico')
        tk.Label(self.newWin, text = 'Config settings').pack()

        self.landingLocationLabel = tk.Label(self.newWin, text= mainPath, width= 50, height=1, fg='white', bg='gray')
        self.landingLocationLabel.place(x=225, y = 25)
        ttk.Button(self.newWin, text='File Location', width=25, command= lambda: self.browseFolder(self.landingLocationLabel, 'Main Location'), bootstyle = 'outline').place(x=25, y = 25)

        self.backUpLocationLabel = tk.Label(self.newWin, text= backUpPath, width= 50, height=1, fg='white', bg='gray')
        self.backUpLocationLabel.place(x=225, y = 60)
        ttk.Button(self.newWin, text='Back-up Location', width=25, command= lambda: self.browseFolder(self.backUpLocationLabel, 'Back-up Location'), bootstyle = 'outline').place(x=25, y = 60)

        self.job_file_location_label = tk.Label(self.newWin, text= jobs_main_path, width= 50, height=1, fg='white', bg='gray')
        self.job_file_location_label.place(x=225, y = 95)
        ttk.Button(self.newWin, text='Job\'s File Location', width=25, command= lambda: self.browseFolder(self.job_file_location_label, 'Job\'s Main Path'), bootstyle = 'outline').place(x=25, y = 95)

        self.saveButton = ttk.Button(self.newWin, text= 'Save', command=self.save, bootstyle = 'outline').place(x = windowWidth - 65, y = windowHeight - 50)
        self.cancelButton = ttk.Button(self.newWin, text= 'Cancel', command = self.cancel, bootstyle = 'outline').place(x = windowWidth - 130, y = windowHeight - 50)

        tk.Label(self.newWin, text= 'Time interval (Minutes):', width=25, font =('Arial', 10, 'bold')).place(x = 25, y = 130)
        tk.Entry(self.newWin, textvariable = self.sleepNumber, width = 5).place(x= 225, y = 130)
        tk.Label(self.newWin, text= 'Job\'s Time interval (Minutes):', width=25, font =('Arial', 10, 'bold')).place(x = 25, y = 165)
        tk.Entry(self.newWin, textvariable = self.jobsSleepNumber, width = 5).place(x= 225, y = 165)
        tk.Label(self.newWin, text= 'PrintBeat Api Key:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 200)
        tk.Entry(self.newWin, textvariable = self.key, width = 35).place(x= 225, y = 200)
        tk.Label(self.newWin, text= 'PrintBeat Api Secret:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 235)
        tk.Entry(self.newWin, textvariable = self.secret, width = 35).place(x= 225, y = 235)
        tk.Label(self.newWin, text= 'PrintBeat Job Api Key:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 270)
        tk.Entry(self.newWin, textvariable = self.job_key, width = 35).place(x= 225, y = 270)
        tk.Label(self.newWin, text= 'PrintBeat Job Api Secret:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 305)
        tk.Entry(self.newWin, textvariable = self.job_secret, width = 35).place(x= 225, y = 305)
        #tk.Label(self.newWin, text= 'Chicago Press:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 270)
        plantLocation = tk.OptionMenu(self.newWin, self.plant, *plants, command= lambda e: self.pressChange(self.plant.get()))
        plantLocation.place(x=80, y = 340)
        
        self.pressEntry = tk.Entry(self.newWin, textvariable = self.pressId, width = 20)
        self.pressEntry.place(x= 320, y = 340)


        self.savePressButton = ttk.Button(self.newWin, text= 'Save', command= lambda: self.savePress(self.plant.get()), bootstyle = 'outline')
        self.savePressButton.place(x = 320, y = 365)
        self.deletePressButton = ttk.Button(self.newWin, text= 'Delete', command= lambda: self.deletePress(self.plant.get()), bootstyle = 'outline')
        self.deletePressButton.place(x = 380, y = 365)
        
        self.listBox = tk.Listbox(self.newWin, height=3)
        self.listBox.place(x = 190, y =340)
        self.listBox.bind('<<ListboxSelect>>', self.setEntery)
        self.v.set(self.listBox.curselection())

        self.newWin.protocol('WM_DELETE_WINDOW', self.quit)
        self.newWin.bind('<Control-q>', self.quit)
        signal.signal(signal.SIGINT, self.quit)


    def pressChange(self, location):
        global press_list, ml_press_list, slc_press_list

        if location == 'Chicago':
            self.listBox.delete(0,END)
            self.listBox.insert(1, *press_list.values())
        elif location == 'Mountain Lakes':
            self.listBox.delete(0,END)
            self.listBox.insert(1, *ml_press_list.values())
        elif location == 'Salt Lake City':
            self.listBox.delete(0,END)
            self.listBox.insert(1, *slc_press_list.values())
    

    def savePress(self, location):
        global press_list, ml_press_list, slc_press_list
        testVariable = self.v.get()
        testVariable2 = self.pressId.get()
        if location == 'Chicago':
            for press in press_list:
                if press_list[press] == self.v.get():
                    press_list[press] = self.pressId.get()
                    self.pressChange(location)
                    break
        elif location == 'Mountain Lakes':
            for press in ml_press_list:
                if ml_press_list[press] == self.v.get():
                    ml_press_list[press] = self.pressId.get()
                    self.pressChange(location)
                    break
        elif location == 'Salt Lake City':
            for press in slc_press_list:
                if slc_press_list[press] == self.v.get():
                    slc_press_list[press] = self.pressId.get()
                    self.pressChange(location)
                    break

    def deletePress(self, location):
        global press_list, ml_press_list, slc_press_list, config
        try:
            if location == 'Chicago':
                del press_list[self.v.get()]
                #config.remove_option('chicagoPlant', self.v.get())
                test = self.v.get()
                self.listBox.delete(self.v.get())
                self.pressChange(location)
            elif location == 'Mountain Lakes':
                del ml_press_list[self.v.get()]
                config.remove_option('chicagoPlant', self.v.get())
                index = self.ml_option['menu'].index(self.v.get())
                self.ml_option['menu'].delete(index)
                self.v.set(self.ml_option['menu'].entrycget(0,'label'))
                self.setEntery(ml_press_list[self.v.get()])

            elif location == 'Salt Lake City':
                del slc_press_list[self.v.get()]
                config.remove_option('chicagoPlant', self.v.get())
                index = self.slc_option['menu'].index(self.v.get())
                self.slc_option['menu'].delete(index)
                self.v.set(self.slc_option['menu'].entrycget(0,'label'))
                self.setEntery(slc_press_list[self.v.get()])
        except KeyError:
            logger.log(logging.ERROR, msg= 'You have deleted all the options')
            pass
    def setEntery(self, event):
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            data = event.widget.get(index)
            self.pressEntry.delete(0, END)
            self.pressEntry.insert(0, data)
            self.v.set(data)
        else:
            pass

    def browseFolder(self, label, locType):
        self.mainPath = mainPath
        self.backUpPath = backUpPath
        self.jobs_main_path = jobs_main_path
        if locType == 'Main Location':
            self.mainPath = filedialog.askdirectory(title='Path Location')
            logger.log(logging.DEBUG, msg = f'{locType} = {self.mainPath}')
            label.configure(text= self.mainPath)
        elif 'Job\'s' in locType:
            self.jobs_main_path = filedialog.askdirectory(title='Path Location')
            logger.log(logging.DEBUG, msg = f'{locType} = {self.jobs_main_path}')
            label.configure(text = self.jobs_main_path)
        else:
            self.backUpPath = filedialog.askdirectory(title='Path Location')
            logger.log(logging.DEBUG, msg = f'{locType} = {self.backUpPath}')
            label.configure(text= self.backUpPath)

    def cancel(self, *args):
        self.newWin.destroy()
        self.root.deiconify()

    def save(self, *args):
        global mainPath, backUpPath, waitTime, key, secret, job_secret, job_key, jobs_main_path, job_wait_time
        try:
            mainPath = self.mainPath
        except AttributeError:
            logger.log(logging.DEBUG, msg='A path was not seleted')
            pass

        try:
            backUpPath = self.backUpPath
        except AttributeError:
            logger.log(logging.DEBUG, msg='A path was not seleted')
            pass

        try:
            jobs_main_path = self.jobs_main_path
        except AttributeError:
            logger.log(logging.DEBUG, msg='A path was not seleted')
            pass

        waitTime = str(self.sleepNumber.get())
        api_key = str(self.key.get())
        api_secret = str(self.secret.get())
        api_job_key = str(self.job_key.get())
        api_job_secret = str(self.job_secret.get())
        job_wait_time = str(self.jobsSleepNumber.get())



        if api_key == '':
            pass
        else:
            key = api_key
            logger.log(logging.DEBUG, msg= 'New API key = '+ api_key)

        if api_secret == '':
            pass
        else:
            secret = api_secret
            logger.log(logging.DEBUG, msg= 'New API Secret = ' + api_secret)
        
        if api_job_key == '':
            pass
        else:
            job_key = api_job_key
            logger.log(logging.DEBUG, msg= 'New API Job key = '+ api_job_key)

        if api_secret == '':
            pass
        else:
            job_secret = api_job_secret
            logger.log(logging.DEBUG, msg= 'New API Job Secret = ' + api_job_secret)
        
        logger.log(logging.DEBUG, msg= 'Wait Time = ' + waitTime)
        logger.log(logging.INFO, msg='Config settings saved')
        self.newWin.destroy()
        self.root.deiconify()
    
    def quit(self, *args):
        self.newWin.destroy()
        self.root.deiconify()

class ThirdUi:
    global autoRun
    def __init__(self, frame, root):
        self.frame = frame
        self.style = ttk.Style()

        self.chi = tk.BooleanVar()
        self.ml = tk.BooleanVar()
        self.slc = tk.BooleanVar()
        self.autoStart = tk.BooleanVar()

        self.style.configure('W.TButton', font = ('calibri', 10, 'bold', 'underline'),foreground = 'red')
        button1 = ttk.Button(frame, text='Config Settings', width=25, bootstyle = 'outline')
        button1.bind("<Button>", lambda e: NewWindow(root))
        button1.pack()
        self.printBeat_start_button = ttk.Button(frame, text='Start PrintBeat', width=25, command=buttonStart, state= 'disable', bootstyle = 'outline')
        self.printBeat_start_button.pack()

        printBeat_stop_button = ttk.Button(frame, text='Stop PrintBeat', width=25, command=stopPrintBeat, bootstyle = 'outline')
        printBeat_stop_button.pack()
        
        self.jobStartButton = ttk.Button(frame, text='Start Jobs', width=25, command=job_start_button, bootstyle = 'outline')
        self.jobStartButton.pack()

        job_stop_button = ttk.Button(frame, text= 'Stop Jobs', width=25, command= stop_job, bootstyle = 'outline')
        job_stop_button.pack()

        buttoon4 = ttk.Button(frame, text='Test Button', width=25, command=testButton, bootstyle = 'outline')

        checkbox1 = ttk.Checkbutton(frame, text= 'Chicago', variable=self.chi, onvalue= True, offvalue= False, command= self.plant, bootstyle='round-toggle')
        checkbox1.place(x = 550, y =2)
        checkbox1.invoke()
        ttk.Checkbutton(frame, text= 'Mountain Lakes', variable=self.ml, onvalue= True, offvalue= False,command=self.plant, bootstyle="round-toggle").place(x = 550, y = 25)
        ttk.Checkbutton(frame, text= 'Salt Lake City', variable=self.slc, onvalue= True, offvalue= False, command= self.plant, bootstyle="round-toggle").place(x = 550, y = 50)
        autoStartCheck = ttk.Checkbutton(frame, text= 'Auto Start', variable=self.autoStart, onvalue=True, offvalue=False,command= self.autoCheck, bootstyle="round-toggle")
        autoStartCheck.place(x = 200, y=2)
        if autoRun:
            autoStartCheck.invoke()
            
        #jobTimerFrame = tk.LabelFrame(root, text= 'Job Timer').place(x= 100, y=100)
        ttk.Label(frame, text=None).place(x= 5, y=10)
        ttk.Label(frame, text=None).place(x= 5, y=35)
            


    def plant(self, *args):
        global chi_plant, ml_plant, slc_plants

        if self.chi.get() or self.slc.get() or self.ml.get():
            self.printBeat_start_button['state'] = 'normal'
        else:
            self.printBeat_start_button['state'] = 'disable'
        chi_plant, ml_plant, slc_plant = self.chi.get(), self.ml.get(), self.slc.get()
    def autoCheck(self):
        global autoRun
        logger.log(logging.INFO, msg=f'Auto start is: {self.autoStart.get()}')
        autoRun = self.autoStart.get()


class MenuTest:
    def __init__(self,root):
        menubar = Menu(root)
        root.config(menu = menubar)
        file = Menu(menubar, tearoff = 0)
        menubar.add_cascade(label = 'File', menu = file)
        file.add_command(label = 'New File', command = None)
        file.add_command(label = 'Open...', command = None)
        file.add_command(label = 'Save', command = None)
        file.add_separator()
        file.add_command(label = 'Exit', command = root.destroy)

class App:

    def __init__(self, root):
        self.root = root
        if os.path.exists(f'{programLocation}\\myapp.conf'):
            with open(f'{programLocation}\\myapp.conf', 'r') as file:
                postion = file.read()
            file.close()
        self.root.geometry(postion)
        root.resizable(False, False)
        root.title('PrintBeat API App')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        # Create the panes and frames
        vertical_pane = ttk.PanedWindow(self.root, orient=VERTICAL)
        vertical_pane.grid(row=0, column=0, sticky="nsew")
        horizontal_pane = ttk.PanedWindow(vertical_pane, orient=HORIZONTAL)
        vertical_pane.add(horizontal_pane)
        console_frame = ttk.Labelframe(vertical_pane, text="Log Console")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        vertical_pane.add(console_frame, weight=1)
        third_frame = ttk.Labelframe(horizontal_pane, text="PrintBeat Controls")
        third_frame.columnconfigure(0, weight=1)
        third_frame.rowconfigure(0, weight=1)
        horizontal_pane.add(third_frame, weight=1)

        #MenuBar

        # Initialize all frames

        self.console = ConsoleUi(console_frame)
        self.third = ThirdUi(third_frame, root)
        self.menubar = MenuTest(root)
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.bind('<Control-q>', self.quit)
        signal.signal(signal.SIGINT, self.quit)

    def retrieve_window_position(self, *args):
        if os.path.exists(f'{programLocation}\\myapp.conf'):
            with open(f'{programLocation}\\myapp.conf', 'rb') as file:
                postion = file.read()
            file.close()
        self.root.geometry(postion)

    def saveConfig(self, *args):
        global key, secret, api_url, job_key, job_secret, mainPath, waitTime, backUpPath, autoRun, chi_last_marker, jobs_main_path, job_wait_time

        #config.read(f'{programLocation}\\config_2.ini')

        config['printBeatAPI']['key'] = key
        config['printBeatAPI']['secret'] =  secret

        config['printBeatJobAPI']['job_key'] = job_key
        config['printBeatJobAPI']['job_secret'] = job_secret

        config['configSettings']['main_location'] = mainPath
        config['configSettings']['back-up_location'] = backUpPath
        config['configSettings']['wait_time'] = waitTime
        config['autoStartOnBootUp']['autoStart'] = str(autoRun)

        config['jobsSetting']['marker'] = str(chi_last_marker)
        config['jobsSetting']['file_path'] = jobs_main_path
        config['jobsSetting']['wait_time'] = job_wait_time

        i = 0
        i2 = 0 
        i3 = 0
        for press in press_list:
            i+= 1
            config['chicagoPlant'][f'press_{i}'] = press_list[press]
        for press in ml_press_list:
            i2+=1
            config['mountainLakesPlant'][f'press_{i2}'] = ml_press_list[press]
        for press in slc_press_list:
            i3+=1
            config['saltLakeCityPlant'][f'press_{i3}'] = slc_press_list[press] 
        with open(f'{programLocation}\\config.ini', 'w') as file:
            config.write(file)

    def quit(self, *args):
        #self.clock.stop()
        self.saveConfig()
        with open(f"{programLocation}\\myapp.conf", "w") as conf:
            conf.write(self.root.winfo_geometry()) # Assuming root is the root window
        conf.close()
        self.root.destroy()



def RealTimeDataProcess(data):
    global currnetRunningJob

    for i in range(len(data['data'])-1):
        pressName = data['data'][i]['pressName']

        totalImps = data['data'][i]['totalImpsSinceInstallation']
        totalPrintedImps = data['data'][i]['totalPrintedImpsSinceInstallation']
        totalPrintedSheets = data['data'][i]['totalPrintedSheetsSinceInstallation']
        pressStatus = data['data'][i]['pressState']
        currentJob = data['data'][i]['currentJob']

        if pressName not in currnetRunningJob:
            currnetRunningJob[pressName] = currentJob
        elif pressName in currnetRunningJob and currnetRunningJob[pressName] != currentJob:
            currnetRunningJob[pressName] = currentJob
        else:
            currentJob = ''


        csvName = f'impressions_{pressName}.csv'
        pressData = [totalImps, totalPrintedImps, totalPrintedSheets, pressStatus, currentJob, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        csvFilePath = f'{mainPath}/{csvName}'
        backUpCsvPath = f'{backUpPath}/{csvName}'
        
        createCsvFile(filePath=mainPath, csvFilePath=csvFilePath, csvFileName=csvName, pressData=pressData)
        #os.chdir(programLocation)
        createCsvFile(filePath=backUpPath, csvFilePath=backUpCsvPath, csvFileName=csvName, pressData=pressData)


def createCsvFile(filePath, csvFilePath, csvFileName, pressData):
    
    try:
        if os.path.exists(csvFilePath):
                os.chdir(filePath)
                with open(f'{csvFileName}', 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(pressData)
                    msg = f'Updated: {csvFilePath}'
                    logger.log(logging.INFO, msg)
        else:
            os.chdir(filePath)
            with open(f'{csvFileName}', 'w', newline='') as file:
                writer = csv.writer(file)
                field = ['totalImpsSinceInstallation', 'totalPrintedImpsSinceInstallation', 
                            'totalPrintedSheetsSinceInstallation', 'Press Status', 
                            'currentJob', 'Time']
                
                writer.writerow(field)
                writer.writerow(pressData)
                log = f'File did not exists at {filePath}...Creating file at {filePath}'
                logger.log(logging.INFO, log)
    except FileNotFoundError or PermissionError:
        logger.log(logging.ERROR, msg= f'Sorry the path {filePath}....Could not be accessed or does not exist. Please enter in another path.')
        stopPrintBeat()
        




def get_request_real_data(press):
    global currnetRunningJob
    path = '/externalApi/v1/RealTimeData' #'/externalApi/v1/RealTimeData'
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    headers  = create_headers("GET", path, timestamp) 

    # Setting up the parameters need for the get request
    parameters = {
        'devices' : press,
        'resolution' : 'Day',
        'unitSystem' : 'Metric'
    }

    # Creating a url variable that is the finial url that is going to pass through the request
    url = api_url + path
    
    try:
        # Make a GET request
        response = requests.get(url, headers= headers, params=parameters)

        # Check if the request was successful
        if response.status_code == 200:
            print("Succesfully called to the api")
            data = response.json()
            RealTimeDataProcess(data)
            logger.log(logging.INFO,'Done')
            

        else:
            logger.log(logging.ERROR,f"Request failed with status code:{response.status_code}")
            logger.log(logging.ERROR, f"Response content:{response.content}")
            stopPrintBeat()

    except Exception as e:
        logger.log(logging.ERROR, msg= e)
        logger.log(logging.INFO, msg= 'Stopping')

def get_request_kpi():
    path = '/externalApi/v1/Historic/OverallPerformance'
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    headers  = create_headers("GET", path, timestamp) 
    
    current_date = datetime.now()

    start_day = current_date.replace(hour= 0, minute=0, second=0,microsecond=0)

    format_start = start_day.strftime("%Y-%m-%d %H:%M:%S")

    # Setting up the parameters need for the get request
    parameters = {
        'devices' : ['47200165'],
        'from': format_start,
        'resolution' : 'Day',
        'unitSystem' : 'Imperial'
    }

    # Creating a url variable that is the finial url that is going to pass through the request
    url = api_url + path
    
    try:
        # Make a GET request
        response = requests.get(url, headers= headers, params=parameters)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            data_file = open("data_kpi_imperial.json", 'a')
            json.dump(data, data_file, indent=4)
            print("API response:", data)
        else:
            print("Request failed with status code:", response.status_code)
            print("Response content:", response.content)

    except Exception as e:
        print("An error occurred:", e)

def get_request_jobs(pressName, marker):
    global job_data
    path = '/externalApi/jobs'
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    headers  = create_headers_job("GET", path, timestamp) 


    if marker == None:
        #ASC = Ascending order 
        #DESC = Descending order
        parameters = {
        'devices' : [pressName],
        'sortOrder' : 'DESC'
        }
    else:
        parameters = {
        'startMarker': marker,
        'devices' : [pressName],
        'sortOrder' : 'ASC'
        }

    # Creating a url variable that is the finial url that is going to pass through the request
    url = api_url + path


    try:
        # Make a GET request
        response = requests.get(url, headers= headers, params=parameters)

        # Check if the request was successful
        if response.status_code == 200:
            print("Job Api call...Seccesful")
            job_data = response.json()
            pass
            data_file = open('Jobs_Api_File.json', 'w')
            json.dump(job_data, data_file, indent=4)
            #return True
        else:
            print("Request failed with status code:", response.status_code)
            print("Response content:", response.content)

    except Exception as e:
        print("An error occurred:", e)
# Creating as describe on the hp developers website
def create_headers(method, path, timestamp):
    string_to_sign = method + ' ' + path + timestamp
    local_secret = secret.encode('utf-8')
    string_to_sign = string_to_sign.encode('utf-8')
    signature = hmac.new(local_secret, string_to_sign, hashlib.sha256).hexdigest()
    auth = key + ':' + signature
    return {
        'content-type': 'application/json',
            'x-hp-hmac-authentication': auth,
            'x-hp-hmac-date': timestamp,
            'x-hp-hmac-algorithm': 'SHA256'
            }


def create_headers_job(method, path, timestamp):
    string_to_sign = method + ' ' + path + timestamp
    local_secret = job_secret.encode('utf-8')
    string_to_sign = string_to_sign.encode('utf-8')
    signature = hmac.new(local_secret, string_to_sign, hashlib.sha256).hexdigest()
    auth = job_key + ':' + signature
    return {
        'content-type': 'application/json',
            'x-hp-hmac-authentication': auth,
            'x-hp-hmac-date': timestamp,
            'x-hp-hmac-algorithm': 'SHA256'
            }

class jobsApi_thread_with_exception(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
             
    def run(self):
 
        # target function of the thread class
        try:
            while True:
                jobStart()
        finally:
            logger.log(logging.WARNING, 'Jobs process has been stopped')
          
    def get_id(self):
 
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id
  
    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
              ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')

class printBeat_thread_with_exception(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
             
    def run(self):
 
        # target function of the thread class
        try:
            while True:
                printBeatStart()
        finally:
            logger.log(logging.WARNING, 'Print Beat process has been stopped')
          
    def get_id(self):
 
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id
  
    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
              ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')


def printBeatStart():
    global mainPath, backUpPath, waitTime, app
    timer = 0
    sleepTimer = int(waitTime) * 60
    combineList = []
    if chi_plant:
        for press in press_list:
            combineList.append(press_list[press])
    if slc_plant:
        for press in slc_press_list:
            combineList.append(slc_press_list[press])
    if ml_plant:
        for press in ml_press_list:
            combineList.append(ml_press_list[press])

    while True:
        if timer >= sleepTimer:
            get_request_real_data(combineList)
            timer = 0
            sleepTimer = int(waitTime) * 60
        else:
            printbeat_minutes, printbeat_seconds = divmod(sleepTimer - timer, 60)
            app.third.frame.children['!label']['text'] = f'PrintBeat Timer: %02d:%02d' % (printbeat_minutes, printbeat_seconds)
            time.sleep(1)
            timer += 1

def buttonStart():
    global t2
    global app
    msg = 'Starting the printBeat program'
    logger.log(logging.INFO, msg= msg)
    t2 = printBeat_thread_with_exception('PrintBeat Api')
    t2.start()
    app.third.frame.children['!button2']['state'] = 'disable'
    app.third.frame.children['!checkbutton']['state'] = 'disable'
    app.third.frame.children['!checkbutton2']['state'] = 'disable'
    app.third.frame.children['!checkbutton3']['state'] = 'disable'

def autoStartProcess():
    #global t2, app, t3
    #msg = 'Auto Starting the printBeat program'
    #logger.log(logging.INFO, msg= msg)
    #t2 = printBeat_thread_with_exception('PrintBeat Api')
    #t2.start()
    #pp.third.frame.children['printBeat_start_button']['state'] = 'disable'
    #app.third.frame.children['!checkbutton']['state'] = 'disable'
    #app.third.frame.children['!checkbutton2']['state'] = 'disable'
    #app.third.frame.children['!checkbutton3']['state'] = 'disable'
    buttonStart()
    job_start_button()


def job_start_button():
    global t3, app
    msg = 'Starting up JobApi call'
    logger.log(logging.INFO, msg=msg)
    t3 = jobsApi_thread_with_exception('JobsApi')
    t3.start()
    app.third.frame.children['!button4']['state'] = 'disable'

def testButton():
    global mainPath
    logger.log(level=logging.INFO, msg='This is a test button')
    logger.log(level=logging.INFO, msg=mainPath)

def jobStart():
    global mainPath, backUpPath, job_wait_time, app, job_data, job_timer
    job_timer = 0
    sleepTimer = int(job_wait_time) * 60
    combineList = []
    if chi_plant:
        for press in press_list:
            combineList.append(press_list[press])
    
    while True:
        if job_timer >= sleepTimer:
                get_request_jobs(combineList, chi_last_marker)
                jobs_data_processing(job_data)
                data_size = len(job_data['attempts'])
                if data_size >= 100:
                    job_timer = 0
                    logger.log(logging.INFO, msg= 'Jobs pull had over 100 records doing another pull in 2 minutes')
                    while data_size >= 100:
                        data_size = len(job_data['attempts'])
                        if job_timer >= sleepTimer:
                            sleepTimer = 120
                            get_request_jobs(combineList, chi_last_marker)
                            jobs_data_processing(job_data)
                            job_timer = 0
                        else:
                            time.sleep(1)
                            job_minutes, job_seconds = divmod(sleepTimer - job_timer, 60)
                            app.third.frame.children['!label2']['text'] = f'Job Timer: %02d:%02d' % (job_minutes, job_seconds)
                            job_timer += 1

                sleepTimer = int(job_wait_time) * 60
                job_timer = 0
        else:
            time.sleep(1)
            job_minutes, job_seconds = divmod(sleepTimer - job_timer, 60)
            app.third.frame.children['!label2']['text'] = f'Job Timer: %02d:%02d' % (job_minutes, job_seconds)
            job_timer += 1
                

def stopPrintBeat():
    msg = 'Stop button has been press.....Stopping thread'
    logger.log(logging.INFO, msg = msg)
    app.third.frame.children['!button2']['state'] = 'normal'
    app.third.frame.children['!checkbutton']['state'] = 'normal'
    app.third.frame.children['!checkbutton2']['state'] = 'normal'
    app.third.frame.children['!checkbutton3']['state'] = 'normal'
    t2.raise_exception()
    t2.join()

def stop_job():
    msg = 'Jobs stop button has been press.....Stopping......'
    logger.log(logging.INFO, msg = msg)
    app.third.frame.children['!button4']['state'] = 'normal'
    t3.raise_exception()
    t3.join()

def startUpSettings():
    global key, secret, api_url, job_key, job_secret, mainPath, waitTime, backUpPath, jobs_main_path, chi_last_marker, autoRun, job_wait_time
    #config.read(f'{programLocation}\\config_2.ini')
    key = config['printBeatAPI']['key']
    secret = config['printBeatAPI']['secret']
    api_url = config['printBeatAPI']['api_url']

    job_key = config['printBeatJobAPI']['job_key']
    job_secret = config['printBeatJobAPI']['job_secret']

    mainPath = config['configSettings']['main_location']
    backUpPath = config['configSettings']['back-up_location']
    waitTime = config['configSettings']['wait_time']

    autoRun = config['autoStartOnBootUp']['autoStart']
    if autoRun == 'False':
        autoRun = False
    else:
        autoRun = True


    jobs_main_path = config['jobsSetting']['file_path']
    chi_last_marker = config['jobsSetting']['marker']
    job_wait_time = config['jobsSetting']['wait_time']

    #print(len(config['chicagoPlant']))
    for press in config['chicagoPlant']:
        press_list[press] = config['chicagoPlant'][press]
    for press in config['mountainLakesPlant']:
        ml_press_list[press] = config['mountainLakesPlant'][press]
    for press in config['saltLakeCityPlant']:
        slc_press_list[press] = config['saltLakeCityPlant'][press]


def jobs_data_processing(data_file):
    global chi_last_marker
    # Load JSON data from file
    #with open(json_file, 'r') as file:
        #data = json.load(file)
    
    csv_file_name = f'Jobs_{datetime.now().strftime("%Y_%m")}.csv'
    jobs_csv_path = f'{jobs_main_path}/{csv_file_name}'
    data = data_file['attempts']   

    # Flatten the JSON data
    flattened_data = [flatten_json(item) for item in data]
    extra_data = [addingExtraFields(item) for item in flattened_data]
    final_data = [addingNone(item) for item in extra_data]


    # Convert to DataFrame
    df = pd.DataFrame(final_data)

    # Write DataFrame to CSV file
    try:
        if os.path.exists(jobs_csv_path):
                logger.log(logging.INFO, msg= f'Successfully updated {csv_file_name}')
                os.chdir(jobs_main_path)
                df.to_csv(csv_file_name, index=False, header= False, mode='a')
        else:
            logger.log(logging.INFO, msg= 'successfully create Hp Jobs CSV file')
            os.chdir(jobs_main_path)
            df.to_csv(csv_file_name,index= False)
        if len(final_data) > 0:
            chi_last_marker = final_data[len(final_data)-1]['marker']
        print(chi_last_marker)
    except FileNotFoundError or PermissionError:
        logger.log(logging.ERROR, msg= f'Sorry the path {jobs_main_path}....Could not be accessed or does not exist. Please enter in another path.')
        stop_job()
    
def addingExtraFields(data_list):
    newdict = {}
    s = 0
    i = 0
    for key, value in data_list.items():
        if 'substrates' in key:
            if 'name' in key and str(int(s/2)+1) not in key:
                newdict[f'substrates_{s+1}_name'] = 'None'
                newdict[f'substrates_{s+1}_amountUsed'] = 'None'
                s += 2
            else:
                newdict[key] = value
                s+=1
        elif 'inks' in key:
            if 'color' in key and str(int(i/3)+1) not in key:
                    newdict[f'inks_{i+1}_color'] = 'None'
                    newdict[f'inks_{i+1}_amountUsed'] = 'None'
                    newdict[f'inks_{i+1}_inkSerialNumber'] = 'None'
                    i += 3
            else:
                newdict[key] = value
                i += 1
        else:
            newdict[key] = value
    if len(newdict) < 49:
        if s == 0 or i == 0:
            while s < 4:
                newdict[f'substrates_{s+1}_name'] = 'None'
                newdict[f'substrates_{s+1}_amountUsed'] = 'None'
                s += 1
            while i < 5:
                newdict[f'inks_{i+1}_color'] = 'None'
                newdict[f'inks_{i+1}_amountUsed'] = 'None'
                newdict[f'inks_{i+1}_inkSerialNumber'] = 'None'
                i += 1
        else:
            while int(s/2) < 4:
                newdict[f'substrates_{int(s/2)+1}_name'] = 'None'
                newdict[f'substrates_{int(s/2)+1}_amountUsed'] = 'None'
                s += 2
            while int(i/3) < 5:
                newdict[f'inks_{int(i/3)+1}_color'] = 'None'
                newdict[f'inks_{int(i/3)+1}_amountUsed'] = 'None'
                newdict[f'inks_{int(i/3)+1}_inkSerialNumber'] = 'None'
                i += 3

    return newdict


def flatten_json(json_data, prefix=''):
    flattened_dict = {}
    for key, value in json_data.items():
        if isinstance(value, dict):
            flattened_dict.update(flatten_json(value, prefix + key + '_'))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                flattened_dict.update(flatten_json(item, prefix + key + '_' + str(i+1) + '_'))
        else:
            flattened_dict[prefix + key] = value
    return flattened_dict


def addingNone(data_list):
    new_dict = {}
    for key,value in data_list.items():
        if value == None:
            new_dict[key] = 'None'
        else:
            new_dict[key] = value
    return new_dict


def main():
    global app
    logging.basicConfig(level=logging.DEBUG)
    root = tk.Tk()
    app = App(root)
    app.root.wm_iconbitmap(default=f'{programLocation}\\deluxe_logo.ico')
    if autoRun:
        autoStartProcess()
    app.root.mainloop()


if __name__ == '__main__':
    startUpSettings()
    main()
    