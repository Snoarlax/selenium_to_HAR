#!/usr/bin/env python3
import os
import json
import time
import importlib.util
import sys
from browsermobproxy import Server
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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

def cleanup():
    # remove bmp.log and server.log if exists
    try:
        os.remove("bmp.log")
    except FileNotFoundError:
        pass

    try:
        os.remove("server.log")
    except FileNotFoundError:
        pass

def main():
    # Load configuration
    config = load_config()
    
    # Extract configuration values
    browsermob_path = config['browsermob_proxy_path']
    selenium_script_path = config['selenium_script_path']
    output_filename = config['output_har_filename']
    wait_time = config.get('wait_time_after_script', 0)
    
    # Verify paths exist
    if not os.path.exists(browsermob_path):
        print(f"Error: BrowserMob Proxy not found at {browsermob_path}")
        print("Please update the 'browsermob_proxy_path' in config.json")
        exit(1)
    
    if not os.path.exists(selenium_script_path):
        print(f"Error: Selenium script not found at {selenium_script_path}")
        print("Please update the 'selenium_script_path' in config.json")
        exit(1)
    
    # Start the proxy server
    options = {"log_path":"/dev/","log_file":"null"}
    print(f"Starting BrowserMob Proxy from {browsermob_path}")
    server = Server(browsermob_path, options)
    server.start()
    proxy = server.create_proxy()
    
    # Configure Chrome to use the proxy
    chrome_options = Options()
    chrome_options.add_argument(f'--proxy-server={proxy.proxy}')
    chrome_options.add_argument('--ignore-certificate-errors')
    # TODO: add option for running the apps in a headless mode, left off for debugging for now
    
    # Start the browser
    print("Starting Chrome browser with proxy")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Start recording HAR
        proxy.new_har(os.path.splitext(output_filename)[0])
        
        # Load and run the external Selenium script
        print(f"Loading and running Selenium script: {selenium_script_path}")
        selenium_script = load_selenium_script(selenium_script_path)
        
        # If the script has a run function, execute it with the driver
        if hasattr(selenium_script, 'run'):
            selenium_script.run(driver)
        else:
            print("Warning: The Selenium script does not have a 'run' function.")
            print("Make sure your script defines a function called 'run(driver)' that accepts a webdriver instance.")
        
        # Wait a bit to capture final network requests if needed
        if wait_time > 0:
            print(f"Waiting {wait_time} seconds to capture final network requests")
            time.sleep(wait_time)
        
        # Get the HAR data
        har = proxy.har
        
        # Save the HAR to a file
        with open(output_filename, 'w') as har_file:
            json.dump(har, har_file)
        
        print(f"HAR file saved to {os.path.abspath(output_filename)}")
    
    finally:
        # Clean up
        print("Closing browser and proxy")
        driver.quit()
        server.stop()
        cleanup()

if __name__ == "__main__":
    main()
