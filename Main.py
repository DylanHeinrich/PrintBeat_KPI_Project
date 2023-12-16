import requests , json, hmac, hashlib, time
import pandas as pd
import csv
import os
from datetime import datetime, timezone



key = 'riimt7skcm5p7218itgprlsc8hsrd6f'
secret = 'ctuiec4uo71brmco03145k6j0r4ig3rf' 
api_url = 'https://printos.api.hp.com/printbeat'

job_key = 'pke0g35sukrk21u9ase9k24mk1b95ct4'
job_secret = 'v254bg7n6iqnmhaq110pojel42tj7lne'


press_list = ['47200165','60001071', '60001112']

currnetRunningJob = ''
#def checkForSameJob(job):


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
            pressName = data['data'][0]['pressName']
            #data_file = open(f'impressions_{pressName}.txt', 'a')
            #json_file = open(f'Real_Time_Press_{pressName}.json','w')
            #data_file.writelines(f'Impression: {str(data["data"][0]["value"])} Press Status: {str(data["data"][0]["pressState"])} {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n')
            #json.dump(data, json_file, indent=4)

            totalImps = data['data'][0]['totalImpsSinceInstallation']
            totalPrintedImps = data['data'][0]['totalPrintedImpsSinceInstallation']
            totalPrintedSheets = data['data'][0]['totalPrintedSheetsSinceInstallation']
            pressStatus = data['data'][0]['pressState']
            currentJob = data['data'][0]['currentJob']

            if currentJob == currnetRunningJob:
                currentJob = ''
            else:
                currnetRunningJob = currentJob

            csvFileName = f'impressions_{pressName}_{datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y_%m_%d %H-%M-%S")}'
            data = [totalImps, totalPrintedImps, totalPrintedSheets, pressStatus, currentJob, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            csvFilePath = f'{filePath}\\{csvFileName}.csv'


            if os.path.exists(csvFilePath):
                os.chdir(filePath)
                with open(f'{csvFileName}.csv', 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(data)
                    print("Done writing to csv file.")
            else:
                os.chdir(filePath)
                with open(f'{csvFileName}.csv', 'w', newline='') as file:
                    writer = csv.writer(file)
                    field = ['totalImpsSinceInstallation', 'totalPrintedImpsSinceInstallation', 'totalPrintedSheetsSinceInstallation', 'Press Status', 'currentJob', 'Time']
                    writer.writerow(field)
                    writer.writerow(data)
                    print(f'File did not exists...Created file {csvFileName}')

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

if __name__ == '__main__':
    folderPath = 'C:\\DylanH\\VSC_Projects\\Test'
    for i in range(3):
        get_request_real_data(press_list,folderPath)
        time.sleep(50)
        print(i)