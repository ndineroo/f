import os

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

import time
import numpy as np

from pprint import pprint

import csv

import requests

"""
 Project originally made for Data Collection and Visualization class
 now being adapted for my Undergraduate Capstone project.

 This is a refactored version of the webscraper, hoping to make it more readable and easily edited
 as well as expanding on it's original features

 This web-scraper goes to www.stockx.com and gathers information about sneaker
 resell prices (across various brands)

 It selects a sneaker category from the dropdown menu
 and creates a list of all the subcategories (different shoe models)

 Within these subcategories there are links to individual shoe colorways, 
 information about resell price history, retail price, release date and more 
 is within this page. The program pulls this data from this page

 This scraper does NOT scrape information related to size differences and 
 instead relies on the average sale price as an estimate of the shoes perceived value
 however, it may be important to recognize that size does affect the price of a shoe.
 It is generally understood in the community that small sizes and very very large sizes are more rare
 and thus more valuable. There may be anomalies within the dataset where certain sizes are extremely rare
 and sales of those sizes on the site pull the average sale upwards, or other similar size-related anomalies.
"""
skip_page = "https://stockx.com/nike/sb?page=2"
first_category = True # skips to start on a specified page if set to true

BREAKS = False # if true, gets data for one sneaker per page

# after opening a link, wait this long
PAGE_WAIT = 30

# number of links before long wait
THRESHOLD = 50

# after opening THRESHOLD number of links wait this long
THRESHOLD_WAIT = 3600

# after encountering the "Are you a robot?" page wait this long
ROBOT_PAGE_WAIT = 3600

num_opened = 0

"""
Gathers desired information about the sneaker at the given url.

@param url: url to a sneaker's stockX listing
@param driver: reference to selenium webdriver object
@param directory: path to directory the raw image will be stored in
@return: dictionary of information
    The returned dictionary has these features:
        url: url of the shoe on stockx
        image_path: string path to raw image provided by stockx of the shoe
        name: name of the shoe on stockx
        ticker: A shorthand of the shoes name, used by stockx for their ticker reel feature

        *release_date: MM/DD/YYYY formatted date of the sneakers original release date
        *retail_price: MSRP of the sneaker on it's release date and as sold by retail stores (not on stockx)
        *style_code: Style code of the sneaker provided by stockx
        *colorway: list of colors used in the shoe seperated by '/'
        *number_of_sales: number of sales in the stockx database
        *price_premium: should roughly be  (average_sale_price - retail_value)/(retail_price) as a percentage
        *average_sale_price: average sale price of all sales in the database

          * if not available on the page, default to N/A

    If this were to be expanded, there is more intricate information that can be extracted.
    For example the same sneaker can be categorized in many different sections 
    on the site such as nike, basketball and lifestyle. Perhaps nike basketball 
    shoes have a tendency to sell better if they use the color red, whereas adidas 
    basketball shoes sell better if they use blue.

"""
def get_shoe_data(url, driver, directory,page_wait=PAGE_WAIT,complex_image_path=True):
    output = {}

    # open link to shoe
    open_link(driver,url,page_wait=page_wait)

    # store url in dictionary
    output.update({'url' : url})

    try:
        # save name of sneaker
        name = {'name' : driver.find_element_by_xpath("//div[@class='col-md-12']/h1").text}
        output.update(name)

        # save ticker code
        ticker = {'ticker' : driver.find_element_by_css_selector('.soft-black').text}
        output.update(ticker)

        # save image of the shoe and store the path to it
        # make path just to directory that will contain the image to see if it needs to be made
        if complex_image_path:
            image_path = directory[:6] + "/images" + directory[6:]
        else:
            image_path = directory

        if (not os.path.isdir(image_path)):
            # create the desired directory if it doesn't exist
            os.makedirs(image_path, exist_ok=True)

        # add the filename
        image_path = image_path + ticker['ticker'] + ".jpg"

        if complex_image_path:
            output.update({'image_path' : image_path[6:]}) # save path
        else:
            output.update({'image_path' : image_path}) # save path

        r = requests.get(
            	driver.find_element_by_xpath("//img[@data-testid='product-detail-image']").get_attribute('src'))
        with open(image_path, 'wb') as f:
            f.write(r.content) # save image to image_path
    except:
        # close tab
        driver.close()
        # switch back to shoe listings page
        driver.switch_to.window(driver.window_handles[-1])
        return {}

    # save release date
    try:
        release_date = {
            'release_date'  : driver.find_element_by_xpath(
                                  "//span[@data-testid='product-detail-release date']").text
            }
    except:
        release_date = {'release_date'	: 'N/A'}
    output.update(release_date)

    # save retail price
    try:
        retail_price = {
            'retail_price'  : driver.find_element_by_xpath(
                                  "//span[@data-testid='product-detail-retail price']").text
            }

    except:
        retail_price = {'retail_price' : 'N/A'}
    output.update(retail_price)

    gauges = driver.find_elements_by_xpath("//div[@class='gauges']/div[@class='gauge-container']")
    print(gauges)

    driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
    # old code; not sure why I did it this way but it still works so I'm gonna leave it
    for gauge in gauges:
        gauge_text = gauge.find_element_by_css_selector("div:nth-child(2)").text.lower()
        print(gauge_text)
        if gauge_text == "# of sales":
            # get # of sales
            number_of_sales = gauge.find_element_by_css_selector("div:nth-child(3)").text
            if number_of_sales != "--":
                output.update({'number_of_sales' : number_of_sales})
            else:
                output.update({'number_of_sales' : "N/A"})

        elif "price premium" in gauge_text:
            # get price premium
            price_premium = gauge.find_element_by_css_selector("div:nth-child(3)").text
            if price_premium != "--":
                output.update({'price_premium' : price_premium})
            else:
                output.update({'price_premium' : "N/A"})

        elif gauge_text == "average sale price":
            # get average sale price
            average_sale_price = gauge.find_element_by_css_selector("div:nth-child(3)").text
            if average_sale_price != "--":
                output.update({'average_sale_price' : average_sale_price})
            else:
                output.update({'average_sale_price' : "N/A"})

    # save style code
    try:
        style_code = {'style_code' : driver.find_element_by_xpath("//span[@data-testid='product-detail-style']").text}
    except:
        style_code = {'style_code' : 'N/A'}
    output.update(style_code)

    # save colorway of the shoe
    try:
        colorway = {'colorway' : driver.find_element_by_xpath("//span[@data-testid='product-detail-colorway']").text}
    except:
        colorway = {'colorway' : 'N/A'}
    output.update(colorway)

    # close tab
    driver.close()
    # switch back to shoe listings page
    driver.switch_to.window(driver.window_handles[-1])

    return output

"""
helper function that gets all shoe data on the current open page and returns it in a list of dictionaries

@param driver: reference to selenium webdriver object
@param directory: passed to get_shoe_data for organized image storage
@return: list of the gathered data from all shoes on a page
"""
def get_all_data_on_page(driver, directory):
    page_dicts = []
    # grab all links to shoes on the page
    list_of_shoes = driver.find_elements_by_xpath(
            "//div[@class='browse-grid']/div[contains(@class,'tile browse-tile')]/*/a"
            )
    print("This page has ", len(list_of_shoes), " shoe listings")
#    pprint(list_of_shoes)

    for i, shoe in enumerate(list_of_shoes):
        shoe_link = shoe.get_attribute('href')
        shoe_dict = get_shoe_data(shoe_link, driver, directory)

        pprint(shoe_dict, indent=12)
        # add to page's dictionary
        page_dicts.append(shoe_dict)

        if BREAKS:
            break


    return page_dicts

"""
helper function that gets all of the data within one category and writes them 
to files in the data directory

@param shoe_category: shoe category web element
@param driver: reference to selenium webdriver object
@return: dictionary of all data within that category
"""
def get_category_data(shoe_category,driver):
    global first_category
    link_to_shoe_category = shoe_category.get_attribute('href')

    if first_category:
        print("First pass detected skipping to", skip_page)
        link_to_shoe_category = skip_page
        first_category = False

    #link_to_shoe_category = "https://stockx.com/adidas/yeezy?page=5"

    category_directory = link_to_shoe_category[19:(link_to_shoe_category.find('?'))]

    category_directory = "./data/sneakers/" + category_directory + "/"
    # if the desired directory doesn't exist
    if (not os.path.isdir("./data/sneakers/" + category_directory)):
        # create the desired directory
        os.makedirs(category_directory, exist_ok=True)

    # go to next page if there is another page

    loc = link_to_shoe_category.find('?page=')
    if loc != -1:
        page_num = int(link_to_shoe_category[loc+6:])
    else:
        page_num = 1

    page_url = link_to_shoe_category

    # get all data on the page, if there is a next page get the info on that page too
    while True:
        # open link to category in new tab
        open_link(driver,page_url)

        page_dicts = get_all_data_on_page(driver, category_directory)
        save_dict_to_file(category_directory, page_num, page_dicts)

        # check if the right arrow refers to stockx home page because for some 
        # reason that's what the right arrow does if there isn't a next page
        right_arrows = driver.find_elements_by_xpath(
        	"//ul[contains(@class,'ButtonList')]/a[contains(@class,'NavigationButton')]")
        #print(right_arrows)

        page_url = right_arrows[1].get_attribute('href')
        if (page_url == 'https://stockx.com/') or BREAKS:
            pass
            #break

        # before going to next page, close the current page
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])

        page_num += 1



"""
Traverses a list of categories and finds every shoe in that category
saving the dictionary of data scraped from that shoe's page

Ex:
    <traverse_model_category_list>
    Brand:Jordan
    (pointer to category information)
        <get_category_data>
        Category:1
            <get_all_data_on_page>
            Page:3
                <get_shoe_data>
                shoe1
                <get_shoe_data>
                shoe2
                ...
                <get_shoe_data>
                shoen

@param category_list: list of all shoe categories
@param driver: reference to selenium webdriver object
"""
def traverse_model_category_list(brand_category_list, driver):
    for brand_category in brand_category_list:
        shoe_models = brand_category.find_elements_by_xpath("./li/a")

        for model in shoe_models:
            get_category_data(model, driver)

            #close category page
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

#            if BREAKS:
#                break


"""
helper function to save lists of dictionaries to the correct file

@param directory: directory to be saved in
@param page_num: number of the page it was pulled from
@param page_dicts: list of data-containing dictionaries
"""
def save_dict_to_file(directory, page_num, page_dicts):
    with open(directory + "page" + str(page_num) + ".csv", 'w') as f:
        w = csv.DictWriter(f, page_dicts[0].keys())
        w.writeheader()
        w.writerows(page_dicts)


"""
Obtains a list of all brand web elements using the "browse" dropdown at the top of the site

@param: reference to selenium webdriver object
"""
def get_brands(driver):

    browse_sneakers_dropdown(driver)

# I want to make a list of all clickable elements underneath the sneakers node in the dropdown menu
# 
# However, the html of the dropdown menu doesn't function as a tree with each clickable element as a node and instead 
# puts them all on the same level with the same class name. This means that we can't use xpath to simply 
# grab all clickable subelements underneath the element we have selected (there will be none)
#
# the element ul[contains(@class, 'category-level-2')] doesn't exist until 
# sneaker_dropdown is hovered over once it is hovered the element is there and we can use xpath to make a 
# list of all clickable elements in that category

    brand_list_dropdown = driver.find_element_by_xpath("//ul[contains(@class, 'category-level-2')]")
    brand_list_dropdown = brand_list_dropdown.find_elements_by_xpath('./li/a')

    # delete upcoming releases page
    del brand_list_dropdown[-1]

    return brand_list_dropdown

"""
browse_sneakers_dropdown

Hovers over Browse->Sneakers
"""
def browse_sneakers_dropdown(driver):
    action = ActionChains(driver)

    wait = WebDriverWait(driver, 10)
    # hover over  browse menu
    browse_dropdown = driver.find_element_by_xpath("//li[@class='dropdown browse-dropdown']") 
    action.move_to_element(browse_dropdown).perform()
    print("browser_dropdown")
#    time.sleep(1)

    # hover over sneakers menu
    sneaker_dropdown = driver.find_element_by_xpath("//a[contains(@data-testid,'submenu-sneakers')]")
    action.move_to_element(sneaker_dropdown).perform()
    print("sneaker_dropdown")

"""
open_link

Opens a link in a new tab
Before returning, check to see if that page is the "are you a robot?" page
If it is, wait 30 minutes and try again, repeat until you get a different page

@param driver: reference to selenium webdriver object
@param url: url of the new tab that you're trying to open
"""
def open_link(driver, url, page_wait=PAGE_WAIT):

    # set local num_opened to reference of global num_opened
    global num_opened
    num_opened += 1
    if num_opened % THRESHOLD == 0:
        print("MEET OPENED LINK THRESHOLD. Sleeping for ", THRESHOLD_WAIT,  "seconds...")
        time.sleep(THRESHOLD_WAIT)

    while True:
        # open new tab
        driver.execute_script("window.open();")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(.5)

        # open link
        print("Opening ", url)
        print("num_opened", num_opened, "\t num_opened%THRESHOLD",num_opened%THRESHOLD)
        driver.get(url)
        # check page for robot deterrent
        if not check_for_robot(driver):
            # return if it's not the robot page
            time.sleep(page_wait) # wait for a little bit so as to not make too many requests
            return
        else:
            #print("Detected robot page, waiting ", ROBOT_PAGE_WAIT, "seconds...")
            #time.sleep(ROBOT_PAGE_WAIT)

            input("hit enter to restart")
            # close tab
            driver.close()
            # switch back to previous page
            driver.switch_to.window(driver.window_handles[-1])

"""
check_for_robot

returns True if the current open page is the "are you a robot?" page
else return false

@param driver: reference to selenium webdriver object
"""
def check_for_robot(driver):
    try:
        print(driver.find_element_by_xpath('//h1').text.lower().strip())
        if driver.find_element_by_xpath('//h1').text.lower().strip() == "Please verify you are a human".lower().strip():
            return True
        else:
            return False
    except NoSuchElementException as e:
        return False


"""
Main function
Calls get_brands to obtain elements
"""
def main():
    #profile = webdriver.FirefoxProfile()
    #profile.set_preference("general.useragent.override"
    #    , "Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0")
    #profile.set_preference("javascript.enabled", True)
    driver = webdriver.Firefox()
    action = ActionChains(driver)

    url = 'https://stockx.com/'
    driver.get(url)

    print("done waiting\n\n")

    brands = get_brands(driver)

    # delete adidas (don't do if you want to scrape adidas) I'm just focusing on Jordans
    del brands[0]

    for brand_element in brands:
        browse_sneakers_dropdown(driver)
        print(brand_element.text)
        # hover over brand menu element
        action.move_to_element(brand_element).perform()
        print("hovering on ",brand_element.text)
        time.sleep(1)

        #generate list of models/categories
        brand_categories = driver.find_elements_by_xpath("//ul[contains(@class, 'category-level-3')]")

        # cleans out fake/empty links that wouldn't be accessible to normal users
        brand_categories = [x for x in brand_categories if x.text.strip() != '']

        traverse_model_category_list(brand_categories, driver)

        print("All Done!")

out = None
if __name__ == '__main__':
    out = main()

#driver = webdriver.Firefox()
#driver.get("https://stockx.com")
#brands = get_brands(driver)
##driver.execute_script("window.open('');")
##driver.switch_to.window(driver.window_handles[-1])
##driver.get("https://stockx.com/adidas/yeezy?page=6")
#pprint(get_category_data(brands[0], driver))