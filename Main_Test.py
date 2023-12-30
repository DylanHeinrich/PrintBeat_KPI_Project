'''
TODO LIST:
    API TODO LIST:
    - [] Find the best way to do a pull every minute
    - [] Set up multithreading
    - [] 
    UI TODO LIST:
    - [] Create a file explorer so it easer for the user to pick the location for the file to be created in.
    - [] Have it create a config file to use when the program is close
    - [] Had errors in with error inputs and explain on what is wrong
    - [] Have a stop and start button
    - [] ? Have a refresh button if the config file has been update/ Have it check to see if the config file has been updated
    - [] Have a status box on what it is doing/ report out any errors
    - [] Have it print a log on when it incouters a error
    - [] Be able to update api key and secret
    - []


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
from tkinter import ttk, VERTICAL, HORIZONTAL, N, S, E, W, Menu, filedialog
import signal
import logging
import queue


key = 'riimt7skcm5p7218itgprlsc8hsrd6f'
secret = 'ctuiec4uo71brmco03145k6j0r4ig3rf' 
api_url = 'https://printos.api.hp.com/printbeat'

job_key = 'pke0g35sukrk21u9ase9k24mk1b95ct4'
job_secret = 'v254bg7n6iqnmhaq110pojel42tj7lne'


press_list = ['47200165','60001071', '60001112']

currnetRunningJob = {}

t1 = None
t2 = None
app = None
configPath = None

logger = logging.getLogger(__name__)


class QueueHandler(logging.Handler):
    """Class to send logging records to a queue

    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    """
    # Example from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    # (https://stackoverflow.com/questions/13318742/python-logging-to-tkinter-text-widget) is not thread safe!
    # See https://stackoverflow.com/questions/43909849/tkinter-python-crashes-on-new-thread-trying-to-log-on-main-thread

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


class FormUi:

    def __init__(self, frame):
        self.frame = frame
        # Create a combobbox to select the logging level
        values = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.level = tk.StringVar()
        ttk.Label(self.frame, text='Level:').grid(column=0, row=0, sticky=W)
        self.combobox = ttk.Combobox(
            self.frame,
            textvariable=self.level,
            width=25,
            state='readonly',
            values=values
        )
        self.combobox.current(0)
        self.combobox.grid(column=1, row=0, sticky="we")
        # Create a text field to enter a message
        self.message = tk.StringVar()
        ttk.Label(self.frame, text='Message:').grid(column=0, row=1, sticky=W)
        ttk.Entry(self.frame, textvariable=self.message, width=25).grid(column=1, row=1, sticky="we")
        # Add a button to log the message
        self.button = ttk.Button(self.frame, text='Submit', command=self.submit_message)
        self.button.grid(column=1, row=2, sticky=W)

    def submit_message(self):
        # Get the logging level numeric value
        lvl = getattr(logging, self.level.get())
        logger.log(lvl, self.message.get())


class ThirdUi:

    def __init__(self, frame, root):
        self.frame = frame
        self.style = ttk.Style()
        self.style.configure('W.TButton', font = ('calibri', 10, 'bold', 'underline'),foreground = 'red')
        button1 = ttk.Button(self.frame, text='Config Settings', width=25)
        button1.bind("<Button>", lambda e: NewWindow(root))
        button1.pack()
        button2 = ttk.Button(self.frame, text='Start PrintBeat', width=25, command=buttonStart)
        button2.pack()
        button3 = ttk.Button(self.frame, text='Stop PrintBeat', width=25, command=stopPrintBeat)
        button3.pack()
        buttoon4 = ttk.Button(self.frame, text='Test Button', width=25, command=testButton)
        buttoon4.pack()
        #ttk.Label(self.frame, text='This is just an example of a third frame').grid(column=0, row=1, sticky=W)
        #ttk.Label(self.frame, text='With another line here!').grid(column=0, row=4, sticky=W)

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


class NewWindow():

    def __init__(self, root):
        self.newWin = tk.Toplevel(root)
        self.newWin.title('New Window')
        self.newWin.geometry('200x200')
        tk.Label(self.newWin, text = 'This is a new window').pack()
        self.folderOpen = tk.Label(self.newWin, text='Folder Explorer', width=50, height=2, fg='white', bg='gray')
        folderLocation = tk.Button(self.newWin, text='Browse Folder', width=25, command=self.browseFolder)
        self.saveButton = tk.Button(self.newWin, text= 'Save', command=self.save)
        self.saveButton.pack()
        self.folderOpen.pack()
        folderLocation.pack()


    def browseFolder(self, *args):
        self.folderPath = filedialog.askdirectory(title='Path Location')
        logger.log(logging.INFO, self.folderPath)
        self.folderOpen.configure(text="Folder path: "+self.folderPath)

    def save(self, *args):
        global configPath

        configPath = self.folderPath
        logger.log(logging.INFO, msg='Config path saved')
        self.saveButton.bind('<Button>', self.quit)
        signal.signal(signal.SIGINT, self.quit)

    def quit(self, *args):
        #self.clock.stop()
        self.newWin.destroy

class App:

    def __init__(self, root):
        self.root = root
        root.title('Logging Handler')
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
        console_frame = ttk.Labelframe(vertical_pane, text="Console")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        vertical_pane.add(console_frame, weight=1)
        third_frame = ttk.Labelframe(horizontal_pane, text="PrintBeat Controls")
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

    def quit(self, *args):
        #self.clock.stop()
        self.root.destroy()



def RealTimeDataProcess(data, filePath):
    global currnetRunningJob

    for i in range(len(data['data'])-1):
        pressName = data['data'][i]['pressName']
        #data_file = open(f'impressions_{pressName}.txt', 'a')
        #json_file = open(f'Real_Time_Press_{pressName}.json','w')
        #data_file.writelines(f'Impression: {str(data["data"][0]["value"])} Press Status: {str(data["data"][0]["pressState"])} {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n')
        #json.dump(data, json_file, indent=4)

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


        csvFileName = f'impressions_{pressName}_{datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y_%m_%d %H-%M-%S")}'
        pressData = [totalImps, totalPrintedImps, totalPrintedSheets, pressStatus, currentJob, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        csvFilePath = f'{filePath}\\{csvFileName}.csv'


        if os.path.exists(csvFilePath):
            os.chdir(filePath)
            with open(f'{csvFileName}.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(pressData)
                msg = "Done writing to csv file."
                logger.log(logging.INFO, msg)
        else:
            os.chdir(filePath)
            with open(f'{csvFileName}.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                field = ['totalImpsSinceInstallation', 'totalPrintedImpsSinceInstallation', 
                         'totalPrintedSheetsSinceInstallation', 'Press Status', 
                         'currentJob', 'Time']
                
                writer.writerow(field)
                writer.writerow(pressData)
                log = f'File did not exists...Created file {csvFileName}'
                logger.log(logging.INFO, log)

def get_request_real_data(press, filePath):
    global currnetRunningJob
    path = '/externalApi/v1/RealTimeDate'
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    headers  = create_headers("GET", path, timestamp) 

    # Setting up the parameters need for the get request
    parameters = {
        'devices' : [press],
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
            RealTimeDataProcess(data, filePath)
            logger.log(logging.INFO,'Done')
            

        else:
            logger.log(logging.ERROR,f"Request failed with status code:{response.status_code}")
            logger.log(logging.ERROR, f"Response content:{response.content}")

    except Exception as e:
        print("An error occurred:", e)

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
    folderPath = 'C:\\DylanH\\VSC_Projects\\PrintBeat_KPI_Project'
    timer = 0
    while True:
        if timer >= 60:
            get_request_real_data(press_list, folderPath)
            timer = 0
        else:
            msg = f'Next pull in....{60-timer} seconds'
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
    #time.sleep(2)
    #t2.raise_exception()
    #t2.join()

def testButton():
    global configPath
    logger.log(level=logging.INFO, msg='This is a test button')
    logger.log(level=logging.INFO, msg=configPath)


def stopPrintBeat():
    msg = 'Stop button has been press.....Stopping thread'
    logger.log(logging.INFO, msg = msg)
    t2.raise_exception()
    t2.join()
    app.third.frame.children['!button2']['state'] = 'normal'

'''
r = tk.Tk()
r.title('PrintBeat Api GUI')
r.geometry('300x300')
button1 = tk.Button(r, text='Button 1', width=25, command=button1Command)
button2 = tk.Button(r, text='Start PrintBeat', width=25, command=buttonStart)
button3 = tk.Button(r, text='Stop PrintBeat', width=25, command=stopPrintBeat)
button1.pack()
button2.pack()
button3.pack()
r.mainloop()
'''

def main():
    global app
    logging.basicConfig(level=logging.DEBUG)
    root = tk.Tk()
    app = App(root)

    app.root.mainloop()


if __name__ == '__main__':
    main()