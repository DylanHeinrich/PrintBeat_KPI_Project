'''
TODO LIST:
    API TODO LIST:
    - [x] Find the best way to do a pull every minute
    - [x] Set up multithreading
    - [] If using a SQL database, if code to be able to connect to the sql server
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

currnetRunningJob = {}

t1 = None
t2 = None
app = None

programLocation = os.getcwd()

logger = logging.getLogger(__name__)

config = ConfigParser()
config.read('config_2.ini')
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
        formatter = logging.Formatter('%(asctime)s: %(message)s', '%m/%d/%Y %H:%M:%S') #datetime.now().strftime('%Y/%m/%d %H:%M:%S')
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
        global key, secret, api_url, job_key, job_secret, waitTime, plants
        self.sleepNumber = tk.IntVar(value= int(waitTime))
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

        self.saveButton = ttk.Button(self.newWin, text= 'Save', command=self.save, bootstyle = 'outline').place(x = windowWidth - 50, y = windowHeight - 50)
        self.cancelButton = ttk.Button(self.newWin, text= 'Cancel', command = self.cancel, bootstyle = 'outline').place(x = windowWidth - 115, y = windowHeight - 50)

        tk.Label(self.newWin, text= 'Time interval (Seconds):', width=25, font =('Arial', 10, 'bold')).place(x = 25, y = 95)
        tk.Entry(self.newWin, textvariable = self.sleepNumber, width = 5).place(x= 225, y = 95)
        tk.Label(self.newWin, text= 'PrintBeat Api Key:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 130)
        tk.Entry(self.newWin, textvariable = self.key, width = 35).place(x= 225, y = 130)
        tk.Label(self.newWin, text= 'PrintBeat Api Secret:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 165)
        tk.Entry(self.newWin, textvariable = self.secret, width = 35).place(x= 225, y = 165)
        tk.Label(self.newWin, text= 'PrintBeat Job Api Key:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 200)
        tk.Entry(self.newWin, textvariable = self.job_key, width = 35).place(x= 225, y = 200)
        tk.Label(self.newWin, text= 'PrintBeat Job Api Secret:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 235)
        tk.Entry(self.newWin, textvariable = self.job_secret, width = 35).place(x= 225, y = 235)
        #tk.Label(self.newWin, text= 'Chicago Press:', width= 25, font=('Arial', 10, 'bold')).place(x=25, y= 270)
        plantLocation = tk.OptionMenu(self.newWin, self.plant, *plants, command= lambda e: self.pressChange(self.plant))
        plantLocation.place(x=80, y = 270)
        
        self.pressEntry = tk.Entry(self.newWin, textvariable = self.pressId, width = 35)
        self.pressEntry.place(x= 275, y = 270)


        self.sumbitButton = ttk.Button(self.newWin, text= 'Submit', command= lambda: self.submitPress(self.plant.get()), bootstyle = 'outline')
        self.sumbitButton.place(x = 495, y = 270)
        self.deleteButton = ttk.Button(self.newWin, text= 'Delete', command= lambda: self.deletePress(self.plant.get()), bootstyle = 'outline')
        self.deleteButton.place(x = 560, y = 270)

        self.newWin.protocol('WM_DELETE_WINDOW', self.quit)
        self.newWin.bind('<Control-q>', self.quit)
        signal.signal(signal.SIGINT, self.quit)


    def pressChange(self, location):
        global press_list, ml_press_list, slc_press_list

        if location.get() == 'Chicago':
            self.v.set('Press')
            self.chi_option = tk.OptionMenu(self.newWin, self.v, *press_list, command= lambda e: self.setEntery(press_list[self.v.get()]))
            self.chi_option.place(x= 185, y = 270)
        elif location.get() == 'Mountain Lakes':
            self.v.set('Press')
            self.ml_option = tk.OptionMenu(self.newWin, self.v, *ml_press_list, command= lambda e: self.setEntery(ml_press_list[self.v.get()]))
            self.ml_option.place(x= 185, y = 270)
        elif location.get() == 'Salt Lake City':
            self.v.set('Press')
            self.slc_option = tk.OptionMenu(self.newWin, self.v, *slc_press_list, command= lambda e: self.setEntery(slc_press_list[self.v.get()]))
            self.slc_option.place(x= 185, y = 270)
    

    def submitPress(self, location):
        global press_list, ml_press_list, slc_press_list

        if location == 'Chicago':
            press_list[self.v.get()] = self.pressId.get()
        elif location == 'Mountain Lakes':
            ml_press_list[self.v.get()] = self.pressId.get()
        elif location == 'Salt Lake City':
            slc_press_list[self.v.get()] = self.pressId.get()

    def deletePress(self, location):
        global press_list, ml_press_list, slc_press_list, config
        try:
            if location == 'Chicago':
                del press_list[self.v.get()]
                config.remove_option('chicagoPlant', self.v.get())
                index = self.chi_option['menu'].index(self.v.get())
                self.chi_option['menu'].delete(index)
                self.v.set(self.chi_option['menu'].entrycget(0,'label'))
                self.setEntery(press_list[self.v.get()])

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
    def setEntery(self, pressNumber):
        self.pressEntry.delete(0, END)
        self.pressEntry.insert(0, pressNumber)

    def browseFolder(self, label, locType):
        if locType == 'Main Location':
            self.mainPath = filedialog.askdirectory(title='Path Location')
            logger.log(logging.DEBUG, msg = f'{locType} = {self.mainPath}')
            label.configure(text= self.mainPath)
        else:
            self.backUpPath = filedialog.askdirectory(title='Path Location')
            logger.log(logging.DEBUG, msg = f'{locType} = {self.backUpPath}')
            label.configure(text= self.backUpPath)

    def cancel(self, *args):
        self.newWin.destroy()
        self.root.deiconify()

    def save(self, *args):
        global mainPath, backUpPath, waitTime, key, secret, job_secret, job_key
        try:
            mainPath = self.mainPath
            backUpPath = self.backUpPath
        except AttributeError:
            logger.log(logging.DEBUG, msg='A path was not seleted')
            pass

        waitTime = str(self.sleepNumber.get())
        api_key = str(self.key.get())
        api_secret = str(self.secret.get())
        api_job_key = str(self.job_key.get())
        api_job_secret = str(self.job_secret.get())

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
        logger.log(logging.DEBUG, msg = f'Press Id Change to {self.pressId.get()}')
        self.newWin.destroy()
        self.root.deiconify()
    
    def quit(self, *args):
        self.newWin.destroy()
        self.root.deiconify()

class ThirdUi:

    def __init__(self, frame, root):
        self.frame = frame
        self.style = ttk.Style()

        self.chi = tk.BooleanVar()
        self.ml = tk.BooleanVar()
        self.slc = tk.BooleanVar()

        self.style.configure('W.TButton', font = ('calibri', 10, 'bold', 'underline'),foreground = 'red')
        button1 = ttk.Button(frame, text='Config Settings', width=25, bootstyle = 'outline')
        button1.bind("<Button>", lambda e: NewWindow(root))
        button1.pack()
        self.button2 = ttk.Button(frame, text='Start PrintBeat', width=25, command=buttonStart, state= 'disable', bootstyle = 'outline')
        self.button2.pack()
        button3 = ttk.Button(frame, text='Stop PrintBeat', width=25, command=stopPrintBeat, bootstyle = 'outline')
        button3.pack()
        buttoon4 = ttk.Button(frame, text='Test Button', width=25, command=testButton, bootstyle = 'outline')
        buttoon4.pack()

        checkbox1 = ttk.Checkbutton(frame, text= 'Chicago', variable=self.chi, onvalue= True, offvalue= False, command= self.plant, bootstyle='round-toggle')
        checkbox1.place(x = 550, y =2)
        checkbox1.invoke()
        ttk.Checkbutton(frame, text= 'Mountain Lakes', variable=self.ml, onvalue= True, offvalue= False,command=self.plant, bootstyle="round-toggle").place(x = 550, y = 25)
        ttk.Checkbutton(frame, text= 'Salt Lake City', variable=self.slc, onvalue= True, offvalue= False, command= self.plant, bootstyle="round-toggle").place(x = 550, y = 50)
        #ttk.Label(self.frame, text='This is just an example of a third frame').grid(column=0, row=1, sticky=W)
        #ttk.Label(self.frame, text='With another line here!').grid(column=0, row=4, sticky=W)


    def plant(self, *args):
        global chi_plant, ml_plant, slc_plant
        logger.log(logging.INFO, msg = f'Chi Valuse = {self.chi.get()}')
        logger.log(logging.INFO, msg = f'ML Valuse = {self.ml.get()}')
        logger.log(logging.INFO, msg = f'SLC Valuse = {self.slc.get()}\n')

        if self.chi.get() or self.slc.get() or self.ml.get():
            self.button2['state'] = 'normal'
        else:
            self.button2['state'] = 'disable'
        chi_plant, ml_plant, slc_plant = self.chi.get(), self.ml.get(), self.slc.get()


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
        #form_frame = ttk.Labelframe(horizontal_pane, text="MyForm")
        #form_frame.columnconfigure(1, weight=1)
        #horizontal_pane.add(form_frame, weight=1)
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

        #self.form = FormUi(form_frame)
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
        global key, secret, api_url, job_key, job_secret, mainPath, waitTime, backUpPath

        #config.read(f'{programLocation}\\config.ini')

        config['printBeatAPI']['key'] = key
        config['printBeatAPI']['secret'] =  secret

        config['printBeatJobAPI']['job_key'] = job_key
        config['printBeatJobAPI']['job_secret'] = job_secret

        config['configSettings']['main_location'] = mainPath
        config['configSettings']['back-up_location'] = backUpPath
        config['configSettings']['wait_time'] = waitTime

        with open(f'{programLocation}\\config_2.ini', 'w') as file:
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


        csvFileName = f'impressions_{pressName}_{datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y_%m_%d %H-%M-%S")}.csv'
        pressData = [totalImps, totalPrintedImps, totalPrintedSheets, pressStatus, currentJob, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        csvFilePath = f'{mainPath}/{csvFileName}'
        backUpCsvPath = f'{backUpPath}/{csvFileName}'
        
        createCsvFile(filePath=mainPath, csvFilePath=csvFilePath, csvFileName=csvFileName, pressData=pressData)
        #os.chdir(programLocation)
        createCsvFile(filePath=backUpPath, csvFilePath=backUpCsvPath, csvFileName=csvFileName, pressData=pressData)


def createCsvFile(filePath, csvFilePath, csvFileName, pressData):
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

def get_request_jobs():
    path = '/externalApi/jobs'
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    headers  = create_headers_job("GET", path, timestamp) 

    parameters = {
        'startMarker' : 156075288,
        'devices' : ['47200165'],
        'sortOrder' : 'DESC'
    }

    # Creating a url variable that is the finial url that is going to pass through the request
    url = api_url + path


    try:
        # Make a GET request
        response = requests.get(url, headers= headers, params=parameters)

        # Check if the request was successful
        if response.status_code == 200:
            print("Succesfully call the api")
            data = response.json()
            data_file = open('Jobs_Api_File.json', 'a')
            json.dump(data, data_file, indent=4)
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

class thread_with_exception(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
             
    def run(self):
 
        # target function of the thread class
        try:
            while True:
                printBeatStart()
        finally:
            logger.log(logging.INFO, 'Process has been stopped')
          
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
    sleepTimer = waitTime
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
        if timer >= int(sleepTimer):
            get_request_real_data(combineList)
            timer = 0
            sleepTimer = waitTime
        else:
            msg = f'Next pull in....{int(sleepTimer)-timer} seconds'
            logger.log(logging.INFO, msg= msg)
            time.sleep(5)
            timer += 5
        #schedule.every(1).minutes.do(lambda: get_request_real_data(press_list, folderPath))
        #schedule.run_pending()


def buttonStart():
    global t2
    global app
    msg = 'Starting the printBeat program'
    logger.log(logging.INFO, msg= msg)
    t2 = thread_with_exception('PrintBeat Api')
    t2.start()
    app.third.frame.children['!button2']['state'] = 'disable'
    app.third.frame.children['!checkbutton']['state'] = 'disable'
    app.third.frame.children['!checkbutton2']['state'] = 'disable'
    app.third.frame.children['!checkbutton3']['state'] = 'disable'

def testButton():
    global mainPath
    logger.log(level=logging.INFO, msg='This is a test button')
    logger.log(level=logging.INFO, msg=mainPath)


def stopPrintBeat():
    msg = 'Stop button has been press.....Stopping thread'
    logger.log(logging.INFO, msg = msg)
    app.third.frame.children['!button2']['state'] = 'normal'
    app.third.frame.children['!checkbutton']['state'] = 'normal'
    app.third.frame.children['!checkbutton2']['state'] = 'normal'
    app.third.frame.children['!checkbutton3']['state'] = 'normal'
    t2.raise_exception()
    t2.join()


def startUpSettings():
    global key, secret, api_url, job_key, job_secret, mainPath, waitTime, backUpPath
    config.read(f'{programLocation}\\config_2.ini')
    key = config['printBeatAPI']['key']
    secret = config['printBeatAPI']['secret']
    api_url = config['printBeatAPI']['api_url']

    job_key = config['printBeatJobAPI']['job_key']
    job_secret = config['printBeatJobAPI']['job_secret']

    mainPath = config['configSettings']['main_location']
    backUpPath = config['configSettings']['back-up_location']
    waitTime = config['configSettings']['wait_time']

    #print(len(config['chicagoPlant']))
    for press in config['chicagoPlant']:
        press_list[press] = config['chicagoPlant'][press]
    for press in config['mountainLakesPlant']:
        ml_press_list[press] = config['chicagoPlant'][press]
    for press in config['saltLakeCityPlant']:
        slc_press_list[press] = config['chicagoPlant'][press]


def main():
    global app
    logging.basicConfig(level=logging.DEBUG)
    root = tk.Tk()
    app = App(root)
    app.root.wm_iconbitmap(default=f'{programLocation}\\deluxe_logo.ico')
    app.root.mainloop()


if __name__ == '__main__':
    startUpSettings()
    main()