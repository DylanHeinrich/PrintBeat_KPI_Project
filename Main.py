'''
TODO LIST:
    API TODO LIST:
    - [] Find the best way to do a pull every minute
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
    - [] Might need to add multithreading
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
from tkinter import *
import ctypes



key = 'riimt7skcm5p7218itgprlsc8hsrd6f'
secret = 'ctuiec4uo71brmco03145k6j0r4ig3rf' 
api_url = 'https://printos.api.hp.com/printbeat'

job_key = 'pke0g35sukrk21u9ase9k24mk1b95ct4'
job_secret = 'v254bg7n6iqnmhaq110pojel42tj7lne'


press_list = ['47200165','60001071', '60001112']

currnetRunningJob = {}
#def checkForSameJob(job):

t1 = None
t2 = None



def RealTimeDataProcess(data, filePath):
    global currnetRunningJob
    path = '/externalApi/v1/RealTimeData'

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
                print("Done writing to csv file.")
        else:
            os.chdir(filePath)
            with open(f'{csvFileName}.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                field = ['totalImpsSinceInstallation', 'totalPrintedImpsSinceInstallation', 'totalPrintedSheetsSinceInstallation', 'Press Status', 'currentJob', 'Time']
                writer.writerow(field)
                writer.writerow(pressData)
                print(f'File did not exists...Created file {csvFileName}')

def get_request_real_data(press, filePath):
    global currnetRunningJob
    path = '/externalApi/v1/RealTimeData'
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
            print('done')
            

        else:
            print("Request failed with status code:", response.status_code)
            print("Response content:", response.content)

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
            print('ended')
          
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
            time.sleep(5)
            timer += 5
        #schedule.every(1).minutes.do(lambda: get_request_real_data(press_list, folderPath))
        #schedule.run_pending()


def buttonStart():
    global t2
    print('Starting the printBeat program')
    t2 = thread_with_exception('Thread 1')
    t2.start()
    #time.sleep(2)
    #t2.raise_exception()
    #t2.join()

def button1Command():
    print('Button 1 is working')


def stopPrintBeat():
    print('Stop button has been press.....Stoping thread')
    t2.raise_exception()
    t2.join()

def testGui():
    r = Tk()
    r.title('PrintBeat Api GUI')
    r.geometry('300x300')
    Button(r, text='Button 1', width=25, command=button1Command)
    Button(r, text='Start PrintBeat', width=25, command=buttonStart)
    Button(r, text='Stop PrintBeat', width=2, command=stopPrintBeat)
    #button2.pack()
    r.mainloop()


r = Tk()
r.title('PrintBeat Api GUI')
r.geometry('300x300')
button1 = Button(r, text='Button 1', width=25, command=button1Command)
button2 =Button(r, text='Start Print Beat', width=25, command=buttonStart)
button3 = Button(r, text='Stop PrintBeat', width=25, command=stopPrintBeat)
button1.pack()
button2.pack()
button3.pack()
r.mainloop()