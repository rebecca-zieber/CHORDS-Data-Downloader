"""
Kenya April 2024 Visit 

Original dataset pulled by UCSB calculated daily rainfall from 00:00Z -> 00:00Z.
We need the dataset to compare rainfall totals from 06:00Z -> 06:00Z to line up with KMZ.
We also need January data in order to do pentad rainfall comparison.
"""
import requests
from json import dumps
from json import loads
import numpy as np
from datetime import datetime, timedelta
import sys
import resources


# User Parameters ----------------------------------------------------------------------------------------------------------------

null_value = ''
include_test = False
portal_url = r"https://3d-fewsnet.icdp.ucar.edu/" 
portal_name = "FEWSNET" 
data_path = r"/Users/rzieber/Desktop/Station_Data/3DPAWS_Oct2023-Jan2024/"
instrument_IDs = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24
]

user_email = 'rzieber@ucar.edu'
api_key = 'QSy8irrRowbi6ys-5PHe' 
start = '2023-10-01 00:00:00' # Pull rainy season dataset for analysis via previous day's rainfall total Oct - Jan
end = '2024-02-02 06:00:00'

columns_desired = [] # it is important that the list be empty if no columns are to be specified!
time_window_start = '' # it is important that these be empty strings if no time window is to be specified!
time_window_end = '' 
  

# MAIN PROGRAM ------------------------------------------------------------------------------------------------------------------------

def main():
    # user input validation
    format_str = "%Y-%m-%d %H:%M:%S"
    timestamp_start = datetime.strptime(start, format_str) 
    timestamp_end = datetime.strptime(end, format_str)
    if timestamp_start > timestamp_end:
            raise ValueError(f"Starting time cannot be after end time.\n\t\t\tStart: {timestamp_start}\t\tEnd: {timestamp_end}")
    if timestamp_start < datetime.now() - timedelta(days=365*2):
        print("\t ========================= WARNING =========================")
        print(f"\t timestamp_start before CHORDS cutoff (2 years): {timestamp_start}\n\t Will pull 2 year archive only.\n")
    if timestamp_end > datetime.now():
        print("\t ========================= WARNING =========================")
        print(f"\t timestamp_end in the future: {timestamp_end}\n\t Will pull up to today's date only.\n")

    if time_window_start != "" or time_window_end != "":
        format_str = "%H:%M:%S"
        timestamp_window_start = datetime.strptime(time_window_start, format_str).time()
        timestamp_window_end = datetime.strptime(time_window_end, format_str).time()
        if time_window_start > time_window_end:
            raise ValueError(f"The start time for the time window is after the end time: {time_window_start} > {time_window_end}")
        if time_window_start == "" or time_window_end == "":
            raise ValueError(f"Both the 'time_window_start' and 'time_window_end' variables must be populated to specify a collection timeframe.")

    portal_lookup = [
        'Barbados', 'Trinidad', '3D PAWS', '3D Calibration', 'FEWSNET', 'Kenya', 'Cayman Islands', 'Dominican Republic'
    ]
    if portal_name not in portal_lookup:
        raise ValueError(f"Please enter one of the following portal names as they appear here (case sensitive):\n\t \
                            Barbados, Trinidad, 3D PAWS, 3D Calibration, FEWSNET, Kenya, Cayman Islands")
    
    # processing loop
    for iD in instrument_IDs:
        if not isinstance(iD, int):
            raise TypeError(f"The instrument id's must be integers, passed {type(iD)} for id {iD}")

        print(f"---> Reading instrument ID {iD}\t\t\t\t\t\t\t{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if time_window_start == "" and time_window_end == "":
            time = [] # list of datetime objects
            measurements = [] # list of dictionaries  (e.g. {'t1': 25.3, 'uv1': 2, 'rh1': 92.7, 'sp1': 1007.43, 't2': 26.9, 'vis1': 260, 'ir1': 255, 'msl1': 1013.01, 't3': 26.1})
            test = [] # list of strings of whether data point is a test value (either 'true' or 'false')

            total_num_measurements = 0
            total_num_timestamps = 0

            url = f"{portal_url}/api/v1/data/{iD}?start={start}&end={end}&email={user_email}&api_key={api_key}"
            response = requests.get(url=url)
            all_fields = loads(dumps(response.json())) # dictionary containing deep copy of JSON-formatted CHORDS data
            if resources.has_errors(all_fields):
                sys.exit(1)
            
            if resources.has_excess_datapoints(all_fields): # reduce timeframe in API call
                print("\t Large data request -- reducing.")
                reduced_data = resources.reduce_datapoints(all_fields['errors'][0], int(iD), timestamp_start, timestamp_end, \
                                                    portal_url, user_email, api_key, null_value)    # list
                                                                                        # e.g. [time, measurements, test, total_num_measurements]
                time = reduced_data[0]
                measurements = reduced_data[1]
                test = reduced_data[2]
                total_num_measurements = reduced_data[3]
            else:
                data = all_fields['features'][0]['properties']['data']  # list of dictionaries 
                                                                        # ( e.g. {'time': '2023-12-17T18:45:56Z', 'test': 'false', 'measurements': {'ws': 1.55, 'rain': 1}} )
                for i in range(len(data)):
                    t = resources.get_timestamp(data[i]['time'])
                    time.append(t)
                    total_num_measurements += len(data[i]['measurements'].keys())
                    total_num_timestamps += 1
                    to_append = resources.write_compass_direction(dict(data[i]['measurements']), null_value)
                    measurements.append(to_append)
                    test.append(str(data[i]['test']))

        else: # if a time window was specified by user
            print(f"\t\t Time window specified.\n\t\t Returning data from {time_window_start} -> {time_window_end}")
            window_data = resources.time_window(int(iD), timestamp_start, timestamp_end, timestamp_window_start, timestamp_window_end, \
                                        portal_url, user_email, api_key, null_value) # a list [time, measurements, test, total_num_measurements]
            time = window_data[0]
            measurements = window_data[1]
            test = window_data[2]
            total_num_measurements = window_data[3]

        headers = resources.build_headers(measurements, columns_desired, include_test, portal_name) # list of strings 
        time = np.array(time)
        measurements = np.array(measurements)
        test = np.array(test)
        
        if resources.struct_has_data(measurements, time, test): 
            csv = f"\\{portal_name}_instrumentID_{iD}.csv"
            file_path = data_path + csv
            resources.csv_builder(headers, time, measurements, test, file_path, include_test, null_value)
            print(f"\t Finished writing to file.\t\t\t\t\t\t{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\t Total number of measurements: {total_num_measurements}")
        else:
            print("\t ========================= WARNING =========================")
            print(f"\t No data found at specified timeframe for {portal_name} Instrument ID: {iD}\n")
            txt = f"\\{portal_name}_instrumentID_{iD}_[WARNING].txt"
            file_path = data_path + txt
            with open(file_path, 'w') as file:
                file.write("No data was found for the specified time frame.\nCheck the CHORDS portal to verify.")

    resources.create_README(portal_name, data_path)


if __name__ == "__main__":
    main()
