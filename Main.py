import requests , json, hmac, hashlib, time
from datetime import datetime, timezone
import PySimpleGUI as sg



key = 'riimt7skcm5p7218itgprlsc8hsrd6f'
secret = 'ctuiec4uo71brmco03145k6j0r4ig3rf' 
api_url = 'https://printos.api.hp.com/printbeat'



def get_request_real_data():
    path = '/externalApi/v1/RealTimeData'
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    headers  = create_headers("GET", path, timestamp) 

    # Setting up the parameters need for the get request
    parameters = {
        'devices' : ['47200165'],
        'resolution' : 'Shift',
        'unitSystem' : 'Metric'
    }

    # Creating a url variable that is the finial url that is going to pass through the request
    url = api_url + path
    
    try:
        # Make a GET request
        response = requests.get(url, headers= headers, params=parameters)

        # Check if the request was successful
        if response.status_code == 200:
            print("Succesfully call the api")
            data_file = open("impressions.txt", 'a')
            data = response.json()
            data_file.writelines("Impression: "+str(data["data"][0]["value"])+ " Press Status: "+str(data["data"][0]["pressState"])+'\n')
            #print( data["data"][0]["value"])
            #print("API response:", data)
            return True
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


if __name__ == '__main__':
    get_request_kpi()