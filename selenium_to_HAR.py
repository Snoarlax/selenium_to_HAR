#!/usr/bin/env python3
import os
import json
import time
import importlib.util
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import pdb

def load_config(config_path='config.json'):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Configuration file '{config_path}' contains invalid JSON.")
        exit(1)

def load_selenium_script(script_path):
    """Load the external Selenium script as a module."""
    try:
        spec = importlib.util.spec_from_file_location("selenium_script", script_path)
        selenium_script = importlib.util.module_from_spec(spec)
        sys.modules["selenium_script"] = selenium_script
        spec.loader.exec_module(selenium_script)
        return selenium_script
    except FileNotFoundError:
        print(f"Error: Selenium script file '{script_path}' not found.")
        exit(1)
    except Exception as e:
        print(f"Error loading Selenium script: {e}")
        exit(1)

def read_logs(driver):
    # Reads logs from drivers, returns the request data to form the HAR
    original_logs = [json.loads(log['message']) for log in driver.get_log('performance')]
    request_data = {}

    # Get list containing logs with relevant data
    relevant_methods = ['Network.requestWillBeSent', 'Network.responseReceived']
    logs = [log['message'] for log in original_logs if log['message'].get('method') in relevant_methods]

    
    for log in logs:
        params = log.get('params', {})
        request_id = params.get('requestId')
        request = params.get('request', {})
        timestamp = params.get('timestamp', 0)
        #TODO: seems like the url+method part isn't working, figure out how to get that data from the request
        
        request_data[request_id] = {
            'request': {
                'method': request.get('method', ''),
                'url': request.get('url', ''),
                'httpVersion': 'HTTP/1.1',
                'cookies': [],
                'headers': [{'name': k, 'value': v} for k, v in request.get('headers', {}).items()],
                'queryString': [],
                'postData': {
                    'mimeType': request.get('headers', {}).get('Content-Type', ''),
                    'text': request.get('postData', '')
                } if 'postData' in request else None,
                'headersSize': -1,
                'bodySize': len(request.get('postData', '')) if 'postData' in request else 0
            },
            #TODO: maybe get the other parts of the response too
            'response': {
                'text': ''
            },
            'cache': {},
            'timings': {
                'send': 0,
                'wait': 0,
                'receive': 0
            }
        }
        # Try fetch the response...
        try:
            request_data[request_id]['response'] = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
        except:
            print("{0} on URL {1} failed. Continuing...".format(request_data[request_id].get('method', "NOMETHOD"),request_data[request_id].get('url', "NOURL")))
    return request_data

def main():
    # Load configuration
    config = load_config()
    
    # Extract configuration values
    selenium_script_path = config['selenium_script_path']
    output_filename = config['output_har_filename']
    wait_time = config.get('wait_time_after_script', 0)
    
    if not os.path.exists(selenium_script_path):
        print(f"Error: Selenium script not found at {selenium_script_path}")
        print("Please update the 'selenium_script_path' in config.json")
        exit(1)
   
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})   

    # Create a driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd('Network.enable', {})
    input("Press a key once the window has appeared... ")
    
    try:
        # Enable network tracking
        driver.execute_cdp_cmd('Network.enable', {})
        # Create HAR structure
        har_dict = {
            'log': {
                'version': '1.2',
                'creator': {
                    'name': 'Selenium Performance Logs',
                    'version': '1.0'
                },
                'pages': [{
                    'id': 'page_1',
                    'title': driver.title,
                    'pageTimings': {
                        'onContentLoad': -1,
                        'onLoad': -1
                    }
                }],
                'entries': []
            }
        }
        
        # Set up event listeners to capture network traffic
        performance_logs = []
        
        # Load and run the external Selenium script
        print(f"Loading and running Selenium script: {selenium_script_path}")
        selenium_script = load_selenium_script(selenium_script_path)

        args = ["value1"]
        # Logic where the script can rerun the same selenium script with a different argument and produce a different HAR for each one.
        for arg in args:
            # If the script has a run function, execute it with the driver
            if hasattr(selenium_script, 'run'):
                args = {'driver': driver, 'args': arg}
                selenium_script.run(**args)
            else:
                print("Warning: The Selenium script does not have a 'run' function.")
                print("Make sure your script defines a function called 'run(driver)' that accepts a webdriver instance.")
            
            # Wait a bit to capture final network requests if needed
            if wait_time > 0:
                print(f"Waiting {wait_time} seconds to capture final network requests")
                time.sleep(wait_time)
            
            # Get performance logs
            request_data = read_logs(driver)


            # Add entries to HAR
            for _, entry in request_data.items():
                har_dict['log']['entries'].append(entry)

            output_location = f"./out/{output_filename}_{arg}.har"

            # Save to file
            with open(output_location, 'w') as f:
                json.dump(har_dict, f, indent=2)

            print(f"HAR file created: {output_location}")        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
