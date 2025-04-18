"""
Example Selenium script that will be run by the HAR capture wrapper.
This script must define a 'run' function that accepts a webdriver instance.
"""

def run(driver):
    """
    This function will be called by the HAR capture wrapper.
    The driver is already configured with the proxy.
    
    Args:
        driver: A Selenium WebDriver instance with proxy configured
    """
    # Navigate to a website
    driver.get("https://www.example.com")
    
    # Example: Fill in a search form
    # search_box = driver.find_element_by_name("q")
    # search_box.send_keys("selenium automation")
    # search_box.submit()
    
    # Example: Click a button
    # button = driver.find_element_by_id("some-button-id")
    # button.click()
    
    # Example: Login to a site
    # username = driver.find_element_by_id("username")
    # username.send_keys("your_username")
    # password = driver.find_element_by_id("password")
    # password.send_keys("your_password")
    # login_button = driver.find_element_by_id("login")
    # login_button.click()
    
    print("Selenium script execution completed successfully!")
    
    # You don't need to close the driver - the wrapper will handle that
