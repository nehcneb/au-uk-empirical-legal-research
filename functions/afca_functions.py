# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Preliminaries

# %%
#Preliminary modules
import base64 
import json
import pandas as pd
import shutil
import numpy as np
import re
import datetime
from datetime import date
from dateutil import parser
#from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
from urllib.request import urlretrieve
import os
import pypdf
import io
from io import BytesIO

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
#import streamlit_ext as ste
from streamlit_extras.stylable_container import stylable_container

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb

# %%
#Import functions
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, date_parser, list_value_check, streamlit_cloud_date_format, streamlit_timezone, save_input, is_date
#Import variables
from functions.common_functions import today_in_nums, today, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # AFCA search engine

# %%
#Scrape javascript

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.print_page_options import PrintOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

#For post June 2024
options = uc.ChromeOptions()
download_dir = os.getcwd() + '/AFCA_PDFs'

#options.headless = True

#options = Options()
#options.add_argument("--disable-gpu")
#options.add_argument("--headless")
#options.add_argument('--no-sandbox')  
#options.add_argument('--disable-dev-shm-usage')  

#@st.cache_resource(show_spinner = False, ttl=600)
def get_driver():
    return uc.Chrome(options = options)
    #return webdriver.Chrome(options=options)

try:
    browser = get_driver()
    #browser.implicitly_wait(5)
    #browser.set_page_load_timeout(30)

    browser.minimize_window()#set_window_position(-2000,0)
    
except Exception as e:
    st.error('Sorry, your internet connection is not stable enough for this app. Please check or change your internet connection and try again.')
    print(e)
    quit()

#For pre June 2024
#Only works if running locally at the moment

if streamlit_timezone() == True:
        
    #For headlessness, see https://github.com/ultrafunkamsterdam/undetected-chromedriver/discussions/1768
    options_old = uc.ChromeOptions()
    options_old.add_experimental_option('prefs', {
    "download.default_directory": download_dir, #Change default directory for downloads
    "download.prompt_for_download": False, #To auto download the file
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True #It will not show PDF directly in chrome
    })
    
    #@st.cache_resource(show_spinner = False, ttl=600)
    def get_driver_old():
        
        return uc.Chrome(options = options_old)
    
    try:
        
        browser_old = get_driver_old()
        
        #browser_old.implicitly_wait(5)
        #browser_old.set_page_load_timeout(60)
        
        browser_old.minimize_window()#set_window_position(-2000,0)
    
    except Exception as e:
        st.error('Sorry, your internet connection is not stable enough for this app. Please check or change your internet connection and try again.')
        st.exception(e)
        quit()

# %%
#Pre June 2024 only works if running locally at the moment
if streamlit_timezone() == True:
    collection_options = ['Decisions published before 14 June 2024', 'Decisions published from 14 June 2024']
else:
    collection_options = ['Decisions published from 14 June 2024']

# %%
from functions.common_functions import link


# %% [markdown]
# ## Pre 14 June 2024

# %%
def afca_old_element_meta(inner_html):
    soup = BeautifulSoup(inner_html, "lxml")
    
    #Get url
    try:
        a_hrefs = soup.find_all('a', href=True)
        
        for a_ref in a_hrefs:
            if 'CaseFiles' in a_ref['href']:
                url = a_ref['href'].replace('..', 'https://service02.afca.org.au/')

    except:
        print('url not scrapped')
        url = ''

    #Case number
    try:
        case_number = soup.find(class_='casenumber').text
        while case_number[-1] == ' ':
            case_number = case_number[:-1]

    except:

        case_number = ''

    #Decision date and file size
    try:
        file_detail = soup.find(class_='fileDetails').text

        decision_date = file_detail.split('File size:')[0]
        
        while decision_date[0] == ' ':
            decision_date = decision_date[1:]
            
        while decision_date[-1] == ' ':
            decision_date = decision_date[:-1]

        file_size = file_detail.split('File size:')[1]
        
        while file_size[0] == ' ':
            file_size = file_size[1:]
            
        while file_size[-1] == ' ':
            file_size = file_size[:-1]

    except:
        decision_date = ''
        file_size = ''

    #Title, firm and page length
    
    title_raw = ''
    firm = ''
    page_length = ''
    page_length_num = ''

    try:
        abstract = soup.find(class_='abstract').text
        abstract_list = abstract.split('\n')
        
        #Title    
        for text in abstract_list:
            
            if 'determination' in text.lower():
                
                title_raw += text
         
                while title_raw[0] == ' ':
                    title_raw = title_raw[ 1:]
                    
                break
            
        #Financial firm
        
        for text in abstract_list:
            
            if 'firm' in text.lower():
                
                firm += text.replace('Financial', '').replace('financial', '').replace('firm', '')
         
                while firm[0] == ' ':
                    firm = firm[ 1:]
                    
                while firm[-1] == ' ':
                    firm = firm [ :-1]
        
                break

        #Page length
        
        for text in abstract_list:
            
            if 'page' in text.lower():
                
                page_length += text
         
                while page_length[0] == ' ':
                    page_length = page_length[ 1:]
                    
                while page_length[-1] == ' ':
                    page_length = page_length [ :-1]

                if ' ' in page_length:
                    page_length_num = page_length.split(' ')[-1]
                else:
                    page_length_num = page_length
                
                break
    
    except Exception as e:
        print(f'{case_number}: Title, firm and page length not scraped.')
        print(e)
        
    title = f"{title_raw.title()}Case Number: {case_number}"

    case_meta = {'Case name': title, 'Case number': case_number, 'Hyperlink to AFCA Portal': url, 'Date': decision_date, 'Finanical firm': firm, 'Page length': page_length_num, 'File size': file_size}

    return case_meta


# %%
#@st.cache_data(show_spinner = False)
def afca_old_search(
    earlier_t_o_r_input, 
    all_these_words_input, 
    this_exact_wording_or_phrase_input, 
    one_or_more_of_these_words_1_input, 
    one_or_more_of_these_words_2_input, 
    one_or_more_of_these_words_3_input, 
    any_of_these_unwanted_words_input, 
    case_number_input, 
    date_from_input, 
    date_to_input, 
    judgment_counter_bound
):
    #Open browser
    browser_old.get('https://service02.afca.org.au/fossic_search/')
    browser_old.delete_all_cookies()
    browser_old.refresh()

    # 'Include decisions made under earlier Terms of Reference'
    earlier_t_o_r = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_chbOldTOR')))

    #Input for whether to 'Include decisions made under earlier Terms of Reference'
    if earlier_t_o_r_input != False:
        earlier_t_o_r.click()
        pause.seconds(np.random.randint(10, 15))

    #'Search for published decisions'
    #NOT in use
    #keywordsearch = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tbKeywords')))
    
    #Advanced keyword search
    advanced_keyword_search_button = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'aAdvancedKw')))
    advanced_keyword_search_button.click()
    
    #'all these words'
    all_these_words = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tAllWords')))
    #'this exact wording or phrase'
    this_exact_wording_or_phrase = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tExactPhrase')))
    #'one or more of these words'
    one_or_more_of_these_words_1 = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tAnyWords1')))
    one_or_more_of_these_words_2 = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tAnyWords2')))
    one_or_more_of_these_words_3 = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tAnyWords3')))
    #'any of these unwanted words'
    any_of_these_unwanted_words = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tNoWords')))
    
    #'Case number'
    case_number = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_tCaseNumber')))
    #NOT DOING days/weeks/month/years from now
    #from_now_tick = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'timeBack')))
    
    #Date range
    date_range_tick = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='dateRange']")))
    date_range_tick.click()
    
    #date format is "dd/mm/yyyy"
    #eg date_from.send_keys("07/07/2023")
    date_from = browser_old.find_element(By.XPATH, "//input[@id='ctl00_body_tDate1']")
    date_to = browser_old.find_element(By.XPATH, "//input[@id='ctl00_body_tDate2']")
    #date format is "dd/mm/yyyy"
    #eg date_input.send_keys("07/07/2023")
    
    #NOT including the following filters because they would require constant changes of session states
    #'Product line'
    #product_line = browser_old.find_element(By.ID, 'sProductLineName')
    #dropdown_product_line = Select(product_line)
    
    #'Product category'
    #product_category = browser_old.find_element(By.ID, 'sProductCategory')
    #dropdown_product_category = Select(product_category)
    
    #'Product name'
    #product_name = browser_old.find_element(By.ID, 'sProductName')
    #dropdown_product_name = Select(product_name)
    
    #'Issue type'
    #issue_type = browser_old.find_element(By.ID, 'sIssueType')
    #dropdown_issue_type = Select(issue_type)
    
    #'Issue'
    #issue = browser_old.find_element(By.ID, 'sIssue')
    #dropdown_issue = Select(issue)
    
    #Submit and clear buttons
    submit_button = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_bSearch')))
    clear_button = Wait(browser_old, 45).until(EC.visibility_of_element_located((By.ID, 'ctl00_body_bClearSearch')))

    #Enter keyword and date input

    if ((all_these_words_input != None) and (all_these_words_input != '')):
        all_these_words.send_keys(all_these_words_input)

    if ((this_exact_wording_or_phrase_input != None) and (this_exact_wording_or_phrase_input != '')):
        this_exact_wording_or_phrase.send_keys(this_exact_wording_or_phrase_input)

    if ((one_or_more_of_these_words_1_input != None) and (one_or_more_of_these_words_1_input != '')):
        one_or_more_of_these_words_1.send_keys(one_or_more_of_these_words_1_input)

    if ((one_or_more_of_these_words_2_input != None) and (one_or_more_of_these_words_2_input != '')):
        one_or_more_of_these_words_2.send_keys(one_or_more_of_these_words_2_input)

    if ((one_or_more_of_these_words_3_input != None) and (one_or_more_of_these_words_3_input != '')):
        one_or_more_of_these_words_3.send_keys(one_or_more_of_these_words_3_input)
    
    if ((any_of_these_unwanted_words_input != None) and (any_of_these_unwanted_words_input != '')):
        any_of_these_unwanted_words.send_keys(any_of_these_unwanted_words_input)

    if ((case_number_input != None) and (case_number_input != '')):
        case_number.send_keys(case_number_input)
        
    #if date_from_input != 'DD/MM/YYYY':
    if ((date_from_input != None) and (date_from_input != '')):
        date_from_converted = streamlit_cloud_date_format(date_from_input)
        #date_from_converted = date_from_input

        date_from.send_keys(date_from_converted)
        
    #if date_to_input != 'DD/MM/YYYY':
    if ((date_to_input != None) and (date_to_input != '')):
        date_to_converted = streamlit_cloud_date_format(date_to_input)
        #date_to_converted = date_to_input
        
        date_to.send_keys(date_to_converted)

    #Get search results
    submit_button.click()

    #Number of cases message
    case_num_raw = Wait(browser_old,45).until(EC.presence_of_element_located((By.ID, "ctl00_body_pResults")))
    #case_sum = int(case_num_raw.text.replace('Your search found ', '').replace(' results.', '').replace(' A maximum of 500 results is returned (displayed as 10 results per page).', ''))
    case_sum_msg = case_num_raw.text.replace(' (displayed as 10 results per page)', '')

    #Case number

    case_sum = 0
    
    for word in case_sum_msg.split(' '):
        if word.isnumeric():
            case_sum = int(word)
            break

    #Number of pages of search results

    page_num_raw = case_sum/10

    if page_num_raw % 10 == 0:
        
        page_num = int(page_num_raw)
        
    else:
        
        page_num = int(round(page_num_raw + 0.5))

    #Get case details
    counter = 0
    case_list = []

    if page_num > 0:
        
        raw_cases = Wait(browser_old,45).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='results']")))
    
        for raw_case in raw_cases:
    
            if counter < judgment_counter_bound:
                
                case_meta = afca_old_element_meta(raw_case.get_attribute('innerHTML'))
        
                case_list.append(case_meta)
    
                counter += 1

    #Get cases from subsequent pages if there are any

    if ((page_num > 1) and (counter < judgment_counter_bound)):

        for page in list(range(2, page_num + 1)):
        
            subsequent_pages = Wait(browser_old,45).until(EC.presence_of_all_elements_located((By.XPATH, "//*[contains(@href, 'javascript:__doPostBack')]")))

            for subsequent_page in subsequent_pages:

                #Need this because of the need to click '...' button to get to page 11, 21, and so on
                if page % 10 != 1:

                    if subsequent_page.text.isnumeric():
                
                        if ((int(subsequent_page.text) == page) and (counter < judgment_counter_bound)):
        
                            subsequent_page.click()
                            
                            raw_cases = Wait(browser_old,45).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='results']")))
            
                            for raw_case in raw_cases:
                        
                                if counter < judgment_counter_bound:
                                    
                                    case_meta = afca_old_element_meta(raw_case.get_attribute('innerHTML'))
                            
                                    case_list.append(case_meta)
                        
                                    counter += 1

                            pause.seconds(np.random.randint(20, 40))

                            break

                else:
                    
                    if ((not subsequent_page.text.isnumeric()) and (counter < judgment_counter_bound)):

                        subsequent_page.click()
                        
                        raw_cases = Wait(browser_old,45).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='results']")))
        
                        for raw_case in raw_cases:
                    
                            if counter < judgment_counter_bound:
                                
                                case_meta = afca_old_element_meta(raw_case.get_attribute('innerHTML'))
                        
                                case_list.append(case_meta)
                    
                                counter += 1
                        
                        pause.seconds(np.random.randint(20, 40))

                        break

    #browser_old.close()
    
    return {'case_sum': case_sum, 'case_sum_message': case_sum_msg, 'case_list': case_list}
    


# %%
#Define function for judgment link containing PDF

def afca_old_pdf_judgment(case_meta):
    
    judgment_text = ''

    try:
        url = case_meta['Hyperlink to AFCA Portal']
        pdf_file = url.split('/')[-1]    
        browser_old.get(url)
        
        pdf_path = f"{download_dir}/{pdf_file}"
    
        #Limiting waiting time for downloading PDF to 1 min
    
        waiting_counter = 0
        
        while ((not os.path.exists(pdf_path)) and (waiting_counter < 10)):
            pause.seconds(5)
            waiting_counter += 1
            
        pdfdoc_remote = pypdf.PdfReader(pdf_path)
        
        text_list = []
    
        for page in pdfdoc_remote.pages:
            text_list.append(page.extract_text())
    
        os.remove(pdf_path)
    
        judgment_text = str(text_list)

        #browser_old.close()
    
    except Exception as e:
        print(f"{case_meta['Case name']}: judgment not scrapped")
        print(e)        

    return judgment_text



# %%
afca_old_meta_labels_droppable = ['Case number', 'Date', 'Finanical firm', 'Page length', 'File size']

# %% [markdown]
# ## Post 14 June 2024

# %% [markdown]
# ### Definitions of menu items

# %%
# For getting menu items from page source.

#make raw a massive string with each line in the form of <option value="49170f1f-f805-ee11-8f6e-000d3a6ad5b3" data-parent="a379125d-afc1-ed11-83fe-000d3a6ad49b">A fee or charge - eg premiums, excesses</option>'

raw = """"""

primary_keys_raw = re.findall(f'\>.*\<\/option\>', raw)

#Get keys of menu
primary_keys = []
for key_raw in primary_keys_raw:
    key = key_raw.replace('</option>', '').replace('>', '')

    #Avoid empty names
    if len(key.replace(' ', '')) > 0:

        #Deal with repetitive names
        while key in primary_keys:
            key += '*'
        
        primary_keys.append(key)
    
#primary_keys
#Get 'value' key of the value-dictionary of each key in menu
values_raw = re.findall(f'value\=\".+\"', raw)

values = []
for value_raw in values_raw:
    if 'label' not in value_raw:
        if ' data' in value_raw:
            value_raw = value_raw.split(' data')[0]
        value = value_raw.replace('value=', '').replace('"', '')
        values.append(value)

#Get any data parents
data_parents_raw = re.findall(f'parent\=\".*\"', raw)

data_parents = []
for data_parent_raw in data_parents_raw:
    if 'label' not in data_parent_raw:
        data_parent = data_parent_raw.replace('parent=', '').replace('"', '')
        data_parents.append(data_parent)

#data_parents
#Create menu for copying and pasting
menu = {}
for primary_key in primary_keys:
    index = primary_keys.index(primary_key)
    value = values[index]
    
    if len(data_parents) == 0:
        menu_item = {primary_key: {'value': value}}
    else:
        data_parent = data_parents[index]
        menu_item = {primary_key: {'value': value, 'data-parent': data_parent}}

    menu.update(menu_item)

# %%
#'Product line'
#Updated 20250505

product_line_options = {'Credit': {'value': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Deposit Taking': {'value': '779de0b0-93c1-ed11-b597-00224892f893'},
 'General Insurance': {'value': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Investments': {'value': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Life Insurance': {'value': '7f9de0b0-93c1-ed11-b597-00224892f893'},
 'Non rules': {'value': '7b9de0b0-93c1-ed11-b597-00224892f893'},
 'Payment Systems': {'value': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Superannuation': {'value': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Traditional Trustee Services': {'value': '819de0b0-93c1-ed11-b597-00224892f893'}}


# %%
#'Product category'
#Updated 20250505

#Data parents are values of product lines
product_category_options = {'Annuity Policy': {'value': '78c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Approved Deposit Fund': {'value': '7ac2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Business Finance': {'value': '52c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Consumer Credit': {'value': '54c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Corporate Fund': {'value': '7cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Current Accounts': {'value': '6cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '779de0b0-93c1-ed11-b597-00224892f893'},
 'Derivatives/hedging': {'value': '64c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Direct Transfer': {'value': '70c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Domestic Insurance': {'value': '5ac2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Estate Management': {'value': '8ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '819de0b0-93c1-ed11-b597-00224892f893'},
 'Estate Planning': {'value': '90c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '819de0b0-93c1-ed11-b597-00224892f893'},
 'Extended Warranty': {'value': '5ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Guarantees': {'value': '50c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Income Stream Risk': {'value': '8cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7f9de0b0-93c1-ed11-b597-00224892f893'},
 'Industry Fund': {'value': '7ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Life Policy Fund': {'value': '80c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Managed Investments': {'value': '60c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Margin Loans': {'value': '56c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Non rules': {'value': '74c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Non-Cash': {'value': '72c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Non-Income Stream Risk': {'value': 'dd439989-cfc6-ed11-b597-00224811ec4e',
  'data-parent': '7f9de0b0-93c1-ed11-b597-00224892f893'},
 'Professional Indemnity Insurance': {'value': '5cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Public Sector Fund': {'value': '82c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Real Property': {'value': '68c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Retail Fund': {'value': '84c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Retirement Savings Account': {'value': '86c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Safe Custody': {'value': '6ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '779de0b0-93c1-ed11-b597-00224892f893'},
 'Savings Accounts': {'value': '6ac2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '779de0b0-93c1-ed11-b597-00224892f893'},
 'Securities': {'value': '62c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Small APRA Fund': {'value': '88c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Small Business/Farm Insurance': {'value': '58c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Superannuation - Non Trustee Related': {'value': '66c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Superannuation Fund': {'value': '76c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Trusts': {'value': '92c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '819de0b0-93c1-ed11-b597-00224892f893'}}

# %%
#'Product name'
#Updated 20250505

product_name_options = {'Annuities': {'value': '87139d98-3fc2-ed11-b597-00224892f51a'},
 'Annuity Policy': {'value': '89139d98-3fc2-ed11-b597-00224892f51a'},
 'Another type of credit': {'value': 'ba1adf72-fde3-ed11-8847-000d3a6ad49b'},
 'Another type of general insurance': {'value': 'e1957fbb-5ee6-ed11-8848-000d3a6a9642'},
 'Approved Deposit Fund': {'value': '8b139d98-3fc2-ed11-b597-00224892f51a'},
 'ATM': {'value': '8d139d98-3fc2-ed11-b597-00224892f51a'},
 'Australian Equity Funds': {'value': '8f139d98-3fc2-ed11-b597-00224892f51a'},
 'Bank Bills': {'value': '91139d98-3fc2-ed11-b597-00224892f51a'},
 'Bank Drafts': {'value': '93139d98-3fc2-ed11-b597-00224892f51a'},
 'Bank Guarantee': {'value': '95139d98-3fc2-ed11-b597-00224892f51a'},
 'Beneficiary': {'value': '97139d98-3fc2-ed11-b597-00224892f51a'},
 'Bills of Exchange': {'value': '99139d98-3fc2-ed11-b597-00224892f51a'},
 'Bonds': {'value': '9b139d98-3fc2-ed11-b597-00224892f51a'},
 'Brown Goods': {'value': '9d139d98-3fc2-ed11-b597-00224892f51a'},
 'Builder’s warranty': {'value': 'f45b7989-00e9-ed11-8848-000d3a6a9642'},
 'Business Credit Card': {'value': '9f139d98-3fc2-ed11-b597-00224892f51a'},
 'Business Guarantee': {'value': 'a1139d98-3fc2-ed11-b597-00224892f51a'},
 'Business Loans': {'value': 'a3139d98-3fc2-ed11-b597-00224892f51a'},
 'Business or farm': {'value': 'bd685caf-5ee6-ed11-8848-000d3a6a9642'},
 'Business Transaction Accounts': {'value': 'a5139d98-3fc2-ed11-b597-00224892f51a'},
 'Buy Now, Pay Later': {'value': 'a7139d98-3fc2-ed11-b597-00224892f51a'},
 'Cash Management Accounts': {'value': '5e897c0a-d053-ee11-be6f-000d3a6ad35b'},
 'Cash Management Accounts*': {'value': 'a9139d98-3fc2-ed11-b597-00224892f51a'},
 'Cash Management Accounts**': {'value': '8cfd2556-258e-ee11-be36-6045bde4aa06'},
 'Charitable/ Educational Schemes': {'value': 'ab139d98-3fc2-ed11-b597-00224892f51a'},
 'Cheques': {'value': 'ad139d98-3fc2-ed11-b597-00224892f51a'},
 'Commercial bills': {'value': 'af139d98-3fc2-ed11-b597-00224892f51a'},
 'Commercial Property': {'value': 'b1139d98-3fc2-ed11-b597-00224892f51a'},
 'Commercial Vehicles': {'value': 'b3139d98-3fc2-ed11-b597-00224892f51a'},
 'Computer & Electronic Breakdown': {'value': 'b5139d98-3fc2-ed11-b597-00224892f51a'},
 'Construction Loans': {'value': 'b7139d98-3fc2-ed11-b597-00224892f51a'},
 'Consumer Credit Insurance': {'value': 'b9139d98-3fc2-ed11-b597-00224892f51a'},
 'Consumer Credit Insurance*': {'value': '3218b47b-268e-ee11-be36-6045bde4aa06'},
 'Consumer Guarantee': {'value': 'bb139d98-3fc2-ed11-b597-00224892f51a'},
 'Contractors All Risk': {'value': 'bd139d98-3fc2-ed11-b597-00224892f51a'},
 'Contracts for Difference': {'value': 'bf139d98-3fc2-ed11-b597-00224892f51a'},
 'Counter Transactions': {'value': 'c3139d98-3fc2-ed11-b597-00224892f51a'},
 'Credit Cards': {'value': 'c5139d98-3fc2-ed11-b597-00224892f51a'},
 'Cryptocurrency': {'value': 'c7139d98-3fc2-ed11-b597-00224892f51a'},
 'Cyber': {'value': 'c9139d98-3fc2-ed11-b597-00224892f51a'},
 'Death Benefit': {'value': 'cb139d98-3fc2-ed11-b597-00224892f51a'},
 'Death Benefit*': {'value': '717416f2-278e-ee11-be36-6045bde4a41a'},
 'Death Benefit**': {'value': 'b38c09d9-2a8e-ee11-be36-6045bde4a41a'},
 'Death Benefit***': {'value': '7d68c7ec-2c8e-ee11-be36-6045bde4a41a'},
 'Death Benefit****': {'value': '322f228d-2d8e-ee11-be36-6045bde4a41a'},
 'Death Benefit*****': {'value': 'f5a921e1-cd9f-ee11-be37-6045bde6f4e7'},
 'Debentures': {'value': 'cd139d98-3fc2-ed11-b597-00224892f51a'},
 'Debt Agreement': {'value': 'cf139d98-3fc2-ed11-b597-00224892f51a'},
 'Debt management/credit repair': {'value': 'd1139d98-3fc2-ed11-b597-00224892f51a'},
 'Direct Debits': {'value': 'd3139d98-3fc2-ed11-b597-00224892f51a'},
 'EFTPOS': {'value': 'd5139d98-3fc2-ed11-b597-00224892f51a'},
 'Electronic Banking': {'value': 'd7139d98-3fc2-ed11-b597-00224892f51a'},
 'Endowments': {'value': 'd9139d98-3fc2-ed11-b597-00224892f51a'},
 'Enduring Powers of Attorney': {'value': 'db139d98-3fc2-ed11-b597-00224892f51a'},
 'Equity Release': {'value': 'dd139d98-3fc2-ed11-b597-00224892f51a'},
 'Estate Management': {'value': 'df139d98-3fc2-ed11-b597-00224892f51a'},
 'Exchange Traded Funds': {'value': 'e1139d98-3fc2-ed11-b597-00224892f51a'},
 'Film Schemes': {'value': 'e3139d98-3fc2-ed11-b597-00224892f51a'},
 'Fire or accidental damage': {'value': 'e5139d98-3fc2-ed11-b597-00224892f51a'},
 'First Home Buyer Accounts': {'value': 'e7139d98-3fc2-ed11-b597-00224892f51a'},
 'Foreign Currency Accounts': {'value': 'e9139d98-3fc2-ed11-b597-00224892f51a'},
 'Foreign Currency Transfers': {'value': 'eb139d98-3fc2-ed11-b597-00224892f51a'},
 'Foreign Exchange': {'value': 'ed139d98-3fc2-ed11-b597-00224892f51a'},
 'Forwards': {'value': 'ef139d98-3fc2-ed11-b597-00224892f51a'},
 'Funeral Plans': {'value': 'f1139d98-3fc2-ed11-b597-00224892f51a'},
 'Futures': {'value': 'f3139d98-3fc2-ed11-b597-00224892f51a'},
 'Glass': {'value': 'f5139d98-3fc2-ed11-b597-00224892f51a'},
 'Hire purchase/lease': {'value': 'f7139d98-3fc2-ed11-b597-00224892f51a'},
 'Hire purchase/lease*': {'value': 'e3abf1be-218e-ee11-be36-6045bde4aa06'},
 'Home Building': {'value': 'f9139d98-3fc2-ed11-b597-00224892f51a'},
 'Home Contents': {'value': 'fb139d98-3fc2-ed11-b597-00224892f51a'},
 'Home Loans': {'value': 'fd139d98-3fc2-ed11-b597-00224892f51a'},
 'Horse Schemes': {'value': 'ff139d98-3fc2-ed11-b597-00224892f51a'},
 'Income Protection': {'value': 'faf79a05-c953-ee11-be6f-000d3a6ad35b'},
 'Income Protection*': {'value': '01149d98-3fc2-ed11-b597-00224892f51a'},
 'Industrial Special Risk': {'value': '03149d98-3fc2-ed11-b597-00224892f51a'},
 'Interest free finance': {'value': '07149d98-3fc2-ed11-b597-00224892f51a'},
 'International Equity Funds': {'value': '09149d98-3fc2-ed11-b597-00224892f51a'},
 'Investment Property Loans': {'value': '0b149d98-3fc2-ed11-b597-00224892f51a'},
 'Investor Direct Portfolio Services': {'value': '0d149d98-3fc2-ed11-b597-00224892f51a'},
 'Land Transit': {'value': '0f149d98-3fc2-ed11-b597-00224892f51a'},
 'Landlords Insurance': {'value': '11149d98-3fc2-ed11-b597-00224892f51a'},
 'Letter of credit': {'value': '13149d98-3fc2-ed11-b597-00224892f51a'},
 'Life Policy Fund': {'value': '15149d98-3fc2-ed11-b597-00224892f51a'},
 'Line of credit/overdraft': {'value': '17149d98-3fc2-ed11-b597-00224892f51a'},
 'Line of credit/overdraft*': {'value': 'cbd06226-218e-ee11-be36-6045bde4aa06'},
 'Litigation Funding Scheme': {'value': '19149d98-3fc2-ed11-b597-00224892f51a'},
 'Livestock': {'value': '1b149d98-3fc2-ed11-b597-00224892f51a'},
 'Loss of Profits/ Business Interruption': {'value': '1d149d98-3fc2-ed11-b597-00224892f51a'},
 'Loyalty Programs': {'value': '1f149d98-3fc2-ed11-b597-00224892f51a'},
 'Machinery breakdowns': {'value': '21149d98-3fc2-ed11-b597-00224892f51a'},
 'Managed Discretionary Accounts': {'value': '23149d98-3fc2-ed11-b597-00224892f51a'},
 'Managed Strata Title Schemes': {'value': '25149d98-3fc2-ed11-b597-00224892f51a'},
 'Margin Loans': {'value': '27149d98-3fc2-ed11-b597-00224892f51a'},
 'Marine': {'value': 'a8b3cdd8-00e9-ed11-8848-000d3a6a9642'},
 'Medical Indemnity': {'value': '29149d98-3fc2-ed11-b597-00224892f51a'},
 'Merchant Facilities': {'value': '2b149d98-3fc2-ed11-b597-00224892f51a'},
 'Mixed Asset Fund/s': {'value': '2d149d98-3fc2-ed11-b597-00224892f51a'},
 'Money': {'value': '2f149d98-3fc2-ed11-b597-00224892f51a'},
 'Mortgage Offset Accounts': {'value': '31149d98-3fc2-ed11-b597-00224892f51a'},
 'Mortgage Schemes': {'value': '33149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle': {'value': '3d149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle*': {'value': 'dcd07e3f-356f-ef11-a670-002248979a53'},
 'Motor Vehicle- Comprehensive': {'value': '35149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle- Third Party': {'value': '37149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle- Third Party Fire and Theft': {'value': '39149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle- Uninsured Third Party': {'value': '3b149d98-3fc2-ed11-b597-00224892f51a'},
 'Non FF Debt': {'value': '3f149d98-3fc2-ed11-b597-00224892f51a'},
 'Non FF debt/Non-financial product deb': {'value': '41149d98-3fc2-ed11-b597-00224892f51a'},
 'Non rules': {'value': '43149d98-3fc2-ed11-b597-00224892f51a'},
 'Non-Cash Systems': {'value': '45149d98-3fc2-ed11-b597-00224892f51a'},
 'Online Accounts': {'value': '47149d98-3fc2-ed11-b597-00224892f51a'},
 'Options ': {'value': '49149d98-3fc2-ed11-b597-00224892f51a'},
 'Other Complaint': {'value': '9bd97ba8-c753-ee11-be6f-000d3a6ad35b'},
 'Other Complaint*': {'value': '3e17d79f-c853-ee11-be6f-000d3a6ad35b'},
 'Other Complaint**': {'value': 'bc92fcc5-ce53-ee11-be6f-000d3a6ad35b'},
 'Other Complaint***': {'value': 'f60b61a8-00e4-ed11-8847-000d3a6ad49b'},
 'Other Professional Indemnity': {'value': '4b149d98-3fc2-ed11-b597-00224892f51a'},
 'Other superannuation fund complaint': {'value': '2a187c25-6fe7-ed11-8848-000d3a6ad49b'},
 'Passbook Accounts': {'value': '4d149d98-3fc2-ed11-b597-00224892f51a'},
 'Pension': {'value': '4f149d98-3fc2-ed11-b597-00224892f51a'},
 'Pension*': {'value': 'b98e7d7c-278e-ee11-be36-6045bde4a41a'},
 'Pension**': {'value': '58dfd680-2d8e-ee11-be36-6045bde4a41a'},
 'Personal and Domestic Property- Caravan': {'value': '51149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Domestic Pet': {'value': '53149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Horse': {'value': '55149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Mobile Phone': {'value': '57149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Moveables': {'value': '59149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Pleasure Craft': {'value': '5b149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Trailer': {'value': '5d149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Valuables': {'value': '5f149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal Loans': {'value': '61149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal Transaction Accounts': {'value': '63149d98-3fc2-ed11-b597-00224892f51a'},
 'Pooled Superannuation Trust': {'value': '65149d98-3fc2-ed11-b597-00224892f51a'},
 'Primary Production Schemes': {'value': '67149d98-3fc2-ed11-b597-00224892f51a'},
 'Private health': {'value': 'd66672c0-00e9-ed11-8848-000d3a6a9642'},
 'Promissory Notes': {'value': '69149d98-3fc2-ed11-b597-00224892f51a'},
 'Property Funds': {'value': '6b149d98-3fc2-ed11-b597-00224892f51a'},
 'Public Liability': {'value': '6d149d98-3fc2-ed11-b597-00224892f51a'},
 'Real Property': {'value': '71149d98-3fc2-ed11-b597-00224892f51a'},
 'Residential Strata Title': {'value': '73149d98-3fc2-ed11-b597-00224892f51a'},
 'Retirement Savings Account': {'value': '77149d98-3fc2-ed11-b597-00224892f51a'},
 'Safe Custody': {'value': '79149d98-3fc2-ed11-b597-00224892f51a'},
 'Scholarship Funds': {'value': '7b149d98-3fc2-ed11-b597-00224892f51a'},
 'Self-managed Superannuation Fund': {'value': '7d149d98-3fc2-ed11-b597-00224892f51a'},
 'Shares': {'value': '7f149d98-3fc2-ed11-b597-00224892f51a'},
 'Short term finance': {'value': '81149d98-3fc2-ed11-b597-00224892f51a'},
 'Sickness and Accident Insurance': {'value': '83149d98-3fc2-ed11-b597-00224892f51a'},
 'Small APRA Fund': {'value': '85149d98-3fc2-ed11-b597-00224892f51a'},
 'Specific purpose': {'value': '87149d98-3fc2-ed11-b597-00224892f51a'},
 'Stored Value Cards': {'value': '89149d98-3fc2-ed11-b597-00224892f51a'},
 'Superannuation Account': {'value': '8b149d98-3fc2-ed11-b597-00224892f51a'},
 'Superannuation Account*': {'value': 'b0f7d146-2b8e-ee11-be36-6045bde4a41a'},
 'Superannuation Account**': {'value': '8928f16d-2d8e-ee11-be36-6045bde4a41a'},
 'Superannuation Account***': {'value': '4b542808-2e8e-ee11-be36-6045bde4a41a'},
 'Superannuation Account****': {'value': 'f87e4611-cf9f-ee11-be37-6045bde6f4e7'},
 'Superannuation Fund': {'value': '8d149d98-3fc2-ed11-b597-00224892f51a'},
 'Swaps': {'value': '8f149d98-3fc2-ed11-b597-00224892f51a'},
 'Telegraphic Transfers': {'value': '91149d98-3fc2-ed11-b597-00224892f51a'},
 'Term Deposits': {'value': '93149d98-3fc2-ed11-b597-00224892f51a'},
 'Term Life': {'value': '95149d98-3fc2-ed11-b597-00224892f51a'},
 'Terminal Illness': {'value': '97149d98-3fc2-ed11-b597-00224892f51a'},
 'Terminal Illness*': {'value': 'd1e580f1-2a8e-ee11-be36-6045bde4a41a'},
 'Terminal Illness**': {'value': '5ba3aaff-2c8e-ee11-be36-6045bde4a41a'},
 'Terminal Illness***': {'value': '065900b9-2d8e-ee11-be36-6045bde4a41a'},
 'Terminal Illness****': {'value': '38b92f12-ce9f-ee11-be37-6045bde6f4e7'},
 'Theft': {'value': '99149d98-3fc2-ed11-b597-00224892f51a'},
 'Ticket Insurance': {'value': '9b149d98-3fc2-ed11-b597-00224892f51a'},
 'Timeshare Schemes': {'value': '9d149d98-3fc2-ed11-b597-00224892f51a'},
 'Title Insurance': {'value': '9f149d98-3fc2-ed11-b597-00224892f51a'},
 'Total & Permanent Disability': {'value': '48c5503c-c953-ee11-be6f-000d3a6ad35b'},
 'Total & Permanent Disability*': {'value': 'a1149d98-3fc2-ed11-b597-00224892f51a'},
 'Total & Permanent Disability**': {'value': '3697d553-298e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability***': {'value': '4b393410-2b8e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability****': {'value': 'bb19b324-2d8e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability*****': {'value': '4ac09bdd-2d8e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability******': {'value': '3f986a59-ce9f-ee11-be37-6045bde6f4e7'},
 'Total & Temporary Disability': {'value': 'afc19083-288e-ee11-be36-6045bde4a41a'},
 'Total & Temporary Disability*': {'value': 'df854728-2b8e-ee11-be36-6045bde4a41a'},
 'Total & Temporary Disability**': {'value': '68d0dc61-2d8e-ee11-be36-6045bde4a41a'},
 'Total & Temporary Disability***': {'value': 'd545c8f5-2d8e-ee11-be36-6045bde4a41a'},
 'Trauma': {'value': 'a5149d98-3fc2-ed11-b597-00224892f51a'},
 'Travel': {'value': 'a7149d98-3fc2-ed11-b597-00224892f51a'},
 "Travellers' Cheques": {'value': 'a9149d98-3fc2-ed11-b597-00224892f51a'},
 'Trust Bond': {'value': 'ab149d98-3fc2-ed11-b597-00224892f51a'},
 'Trustee Common Funds': {'value': 'ad149d98-3fc2-ed11-b597-00224892f51a'},
 'Trusts': {'value': 'c66d7c30-6be7-ed11-8848-000d3a6ad5b3'},
 'Warrants': {'value': 'af149d98-3fc2-ed11-b597-00224892f51a'},
 'White Goods': {'value': 'b1149d98-3fc2-ed11-b597-00224892f51a'},
 'Whole of Life ': {'value': 'b3149d98-3fc2-ed11-b597-00224892f51a'},
 'Wills': {'value': 'b5149d98-3fc2-ed11-b597-00224892f51a'},
 'Worker’s compensation': {'value': 'd39e8da1-00e9-ed11-8848-000d3a6a9642'}}


# %%
#'Issue type'
#Updated 20250505

issue_type_options = {'Advice': {'value': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Charges': {'value': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Consumer Data Right': {'value': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Credit Reporting': {'value': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Disclosure': {'value': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'FF Decision': {'value': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Financial Difficulty': {'value': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Instructions': {'value': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Non rules': {'value': 'fe41fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Other Complaint': {'value': '4e60feb6-20e8-ed11-8848-000d3a6ad5b3'},
 'Privacy & Confidentiality': {'value': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Service': {'value': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Transactions': {'value': '9579125d-afc1-ed11-83fe-000d3a6ad49b'}}

# %%
#'Issue'
#Updated 20250505

#Data parents are values of issue types

issue_options = {'A fee or charge - eg premiums, excesses': {'value': '49170f1f-f805-ee11-8f6e-000d3a6ad5b3',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Account administration error': {'value': 'ef32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Account closure': {'value': '4d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Applicant rejects FSP decision': {'value': '4133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Application for early super release declined': {'value': '4f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Appropriate Lending': {'value': '5133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Break costs': {'value': '1b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Break costs disclosure': {'value': '2b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Cancellation of policy': {'value': '5333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Cancellation of refund': {'value': '5533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Chargebacks - declined (consumer)': {'value': '0b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Chargebacks - delayed (consumer)': {'value': '0d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Chargebacks - merchant': {'value': '0f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Claim amount': {'value': '5733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Commercial credit reporting': {'value': '5933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Credit Enquiry': {'value': '9533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Credit reporting': {'value': '0333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Credit Score': {'value': '9733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Death benefit distribution': {'value': '5b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Decline of Financial Difficulty Request': {'value': '4333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Deductible or excess': {'value': '1d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Default judgment obtained': {'value': '4533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Default Listing': {'value': '9933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Default Notice': {'value': '4733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Delay': {'value': 'e932d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Delay in claim handling': {'value': 'f132d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Delay in complaint handling': {'value': 'f332d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of application or variation request': {'value': '5d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim': {'value': '5f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-complainant non-disclosure': {'value': '6133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-DUI': {'value': '6333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-Exclusion/ condition': {'value': '6533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-Fraudulent claim': {'value': '6733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-No policy or contract': {'value': '6933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-No proof of loss': {'value': '6b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of variation request': {'value': '6d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Dishonoured transactions': {'value': '1133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Error in debt collection': {'value': '6f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 "Failure to act in client's best interests": {'value': '3533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to follow instructions/agreement': {'value': 'eb32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to prioritise clients interests': {'value': '3733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to provide advice': {'value': '3933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to provide special needs assistance': {'value': 'f532d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure/ refusal to provide access': {'value': '0533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Family law division of super benefit': {'value': '7133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Fee Disclosure': {'value': '2d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'FF failure to respond to request for assistance': {'value': '4933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Financial advice provided by my trustee': {'value': '222fb630-0fe8-ed11-8848-000d3a6ad5b3',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'I believe the fee has been incorrectly charged to me': {'value': 'c1bd198d-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'I believe the fee has been incorrectly charged to me*': {'value': 'c580a80a-1c01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'I cannot afford my repayments': {'value': 'ffec1c3b-f4e8-ed11-8848-000d3a6b1bd3',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'I was provided with incorrect fee information': {'value': 'cb01b180-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'I was provided with incorrect fee information*': {'value': '3087fefc-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'Inappropriate advice': {'value': '3b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Inappropriate debt collection action': {'value': '7333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Inappropriate margin call notice and/or investment': {'value': '7533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Inappropriate portfolio liquidation': {'value': 'f732d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect  payment': {'value': '3d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect advice': {'value': '1f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect commissions': {'value': '2133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect fees/ costs': {'value': 'f932d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect Fees/Charges': {'value': '03faa0de-67e9-ed11-8848-000d3a6b1bd3',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect financial information provided': {'value': '2333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect interest added': {'value': '1333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect premiums': {'value': '2533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect product/service information': {'value': '2f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect tax': {'value': '2733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate advice': {'value': '8733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data collection': {'value': '8933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data correction': {'value': '8b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data maintenance': {'value': '8d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data use or disclosure': {'value': '8f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrectly processed instructions': {'value': 'ed32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Insufficient product/service information': {'value': '3133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Interpretation of Policy Terms and Conditions': {'value': '7733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Interpretation of product terms and conditions': {'value': '7933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Liability Disputed': {'value': '7b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Loss of documents/ personal property': {'value': 'fb32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Management of complainant details': {'value': 'fd32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Misleading product/service information': {'value': '3333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Mistaken Internet Payment': {'value': '1533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Mortgagee sale': {'value': '7d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'My application for credit was declined': {'value': 'd189a235-f9e8-ed11-8848-000d3a6b1bd3',
  'data-parent': ''},
 'My complaint involves a scam': {'value': '70e6a978-f9e8-ed11-8848-000d3a6b1bd3',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'My complaint is with another driver’s insurer': {'value': '1f501d02-fff5-ed11-8849-000d3a6ad49b',
  'data-parent': ''},
 'No claim bonus': {'value': '2933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Non rules': {'value': '8533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'fe41fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Non ToR': {'value': '3f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Other': {'value': '9b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Other CDR issue': {'value': '9133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Other Complaint': {'value': '92365f86-0fe8-ed11-8848-000d3a6ad5b3',
  'data-parent': ''},
 'Other privacy breaches': {'value': '0733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Other reason / not sure': {'value': '41aee1c9-1609-ee11-8f6e-000d3a6ad49b',
  'data-parent': ''},
 'Other reason for disputing the fee / not sure': {'value': '9514719f-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'Other reason for disputing the fee / not sure*': {'value': '0c92d01c-1c01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'Other type of scam': {'value': '54b1e51a-42df-ed11-a7c7-000d3a6ad49b',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Repayment History Information': {'value': '9d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Request to Suspend Enforcement Proceedings': {'value': '4b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Responsible lending': {'value': '7f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Scam - phishing/ spoofing': {'value': '0fed3e7e-5cd8-ed11-a7c7-000d3a6ad5b3',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Scam - remote access': {'value': 'ab6930b4-5cd8-ed11-a7c7-000d3a6ad5b3',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Security and Destruction/De-identification': {'value': '9333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Service issue': {'value': 'b8dc2e5b-0fe8-ed11-8848-000d3a6ad5b3',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Service quality': {'value': 'ff32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Technical Problems': {'value': '0133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Unauthorised information disclosed': {'value': '0933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Unauthorised transactions': {'value': '1933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Unconscionable conduct': {'value': '8133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Unfair contract terms': {'value': '8333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'}}

# %% [markdown]
# ### Obtain search results

# %%
#For getting clean text
#Based on https://stackoverflow.com/questions/1936466/how-to-scrape-only-visible-webpage-text-with-beautifulsoup

from bs4.element import Comment
def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def text_from_html(body):
    soup = BeautifulSoup(body, 'lxml')
    texts = soup.find_all(text=True)
    visible_texts = filter(tag_visible, texts)  
    return u"\n".join(t.strip() for t in visible_texts)


# %%
#Define search boxes

#@st.cache_data(show_spinner = False)
def afca_search(keywordsearch_input, #= '', 
                ffsearch_input, #= '', 
                product_line_input, #= '', 
                product_category_input, #= '', 
                product_name_input, #= '', 
                issue_type_input, #= '', 
                issue_input, #= '', 
                date_from_input, #= 'DD/MM/YYYY', 
                date_to_input #= 'DD/MM/YYYY'
                ):

    #Open browser
    browser.get('https://my.afca.org.au/searchpublisheddecisions/')
    browser.delete_all_cookies()
    browser.refresh()

    #Obtain input elements
    
    #'Search for published decisions'
    keywordsearch = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'keywordsearch')))

    #'Search for a financial firm'
    ffsearch = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'ffsearch')))
    
    #'Product line'
    product_line = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'plsearch')))
    dropdown_product_line = Select(product_line)

    #'Product category'
    product_category = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'pcsearch')))
    dropdown_product_category = Select(product_category)

    #'Product name'
    product_name = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'pnsearch')))
    dropdown_product_name = Select(product_name)

    #'Issue type'
    issue_type = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'itsearch')))
    dropdown_issue_type = Select(issue_type)

    #'Issue'
    issue = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'issearch')))
    dropdown_issue = Select(issue)

    #'Date from'
    #date_from = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'date_from')))
    date_from = Wait(browser,  20).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='date_from']")))
    
    #data-date-format="DD/MM/YYYY"
    #eg date_input.send_keys("07/07/2023")
    
    #'Date to'
    #date_to = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'date_to')))
    date_to = Wait(browser,  20).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='date_to']")))
    
    #Buttons
    submit_button = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'submitsearch')))
    clear_button = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'clearsearch')))
    
    #Enter input
    #clear_button.click()

    if ((keywordsearch_input != None) and (keywordsearch_input != '')):
        keywordsearch.send_keys(keywordsearch_input)

    if ((ffsearch_input != None) and (ffsearch_input != '')):
        ffsearch.send_keys(ffsearch_input)

    if ((product_line_input != None) and (product_line_input != '')):
        product_line_value = product_line_options[product_line_input]["value"]
        dropdown_product_line.select_by_value(product_line_value)

    if ((product_category_input != None) and (product_category_input != '')):

        product_category_value = product_category_options[product_category_input]["value"]
        dropdown_product_category.select_by_value(product_category_value)

        #Pause for menu to update
        pause.seconds(5)
        
        #If parent value not automatically updated
        #for key in product_line_options:
            #if product_category_options[product_category_input]["data-parent"] == product_line_options[key]["value"]:
                #product_line_value = product_line_options[product_line_input]["value"]
                #product_line_value = product_line_options[product_line_input]["value"]
    
    if ((product_name_input != None) and (product_name_input != '')):

        product_name_value = product_name_options[product_name_input]["value"]
        dropdown_product_name.select_by_value(product_name_value)

        #Pause for menu to update
        pause.seconds(5)
    
    if ((issue_type_input != None) and (issue_type_input != '')):

        issue_type_value = issue_type_options[issue_type_input]["value"]
        dropdown_issue_type.select_by_value(issue_type_value)

        #Pause for menu to update
        pause.seconds(5)
        
    if ((issue_input != None) and (issue_input != '')):

        issue_value = issue_options[issue_input]["value"]
        dropdown_issue.select_by_value(issue_value)
        #If parent value not automatically updated

        #Pause for menu to update
        pause.seconds(5)

        #for key in issue_type_options:
            #if issue_options[issue_input]["data-parent"] == issue_type_options[key]["value"]:
                #issue_type_value = issue_type_options[issue_type_input]["value"]
                #issue_type_value = issue_type_options[issue_type_input]["value"]

    #if date_from_input != 'DD/MM/YYYY':
    if ((date_from_input != None) and (date_from_input != '')):
        date_from_converted = streamlit_cloud_date_format(date_from_input)
                
        date_from.send_keys(date_from_converted)
        
    #if date_to_input != 'DD/MM/YYYY':
    if ((date_to_input != None) and (date_to_input != '')):

        date_to_converted = streamlit_cloud_date_format(date_to_input)

        date_to.send_keys(date_to_converted)

    #Get search results
    submit_button.click()

    case_list = [] #For preview

    urls = [] #For actual scraping

    raw_cases = [] #Placeholder

    try:
        raw_cases = Wait(browser, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='kb_record panel panel-default container']")))
            
        for raw_case in raw_cases:
            case_name = raw_case.text.split('\n')[0]
            case_number = raw_case.text.split('\n')[1].replace('Case number: ', '').replace('Case Number: ', '')
            firm = raw_case.text.split('\n')[2].replace('Financial Firm: ', '').replace('Financial firm: ', '')
            date = raw_case.text.split('\n')[3].replace('Date: ', '')

            inner_html = raw_case.get_attribute('innerHTML')
            soup_case = BeautifulSoup(inner_html, "lxml")            
            url = 'https://my.afca.org.au' + soup_case.find_all('a', href=True)[0]['href']
            
            case_meta = {#'Case name': case_name, #Bijective function between case name and number
                'Case number': case_number, 'Financial firm': firm, 'Date': date, 'Hyperlink to AFCA Portal': url}
            case_list.append(case_meta)
            urls.append(url)
                    
    except Exception as e:
        print('Search terms returned no results.')
        print(e)

    #Alternative method of getting cases
    #try:
        #raw_cases= Wait(browser, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='kb_record panel panel-default container']")))
    
        #raw_links = Wait(browser, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//*[contains(@href, 'searchpublisheddecisions/kb-article/')]")))
        
        #The above gets twice as many raw links as cases, in an ordered way.
        #for raw_case in raw_cases:
            #raw_case_index = raw_cases.index(raw_case)
            #raw_link_index = int(raw_case_index)*2 #There are twice as many raw links as cases, in an ordered way.
            #case_name = raw_case.text.split('\n')[0]
            #case_number = raw_case.text.split('\n')[1].replace('Case number: ', '').replace('Case Number: ', '')
            #firm = raw_case.text.split('\n')[2].replace('Financial Firm: ', '').replace('Financial firm: ', '')
            #date = raw_case.text.split('\n')[3].replace('Date: ', '')
            #url = raw_links[raw_link_index].get_attribute("href")
            #case_meta = {#'Case name': case_name, #Bijective function between case name and number
                #'Case number': case_number, 'Financial firm': firm, 'Date': date, 'Hyperlink to AFCA Portal': url}
            #case_list.append(case_meta)
            #urls.append(url)
    #except Exception as e:
        #print('Search terms returned no results.')
        #print(e)

    #browser.close()
    
    return {'case_sum': len(case_list), 'case_list': case_list, 'urls': urls}



# %%
#@st.cache_data(show_spinner = False)
def afca_meta_judgment_dict(judgment_url):

    judgment_dict = {'Case name': '', 'Hyperlink to AFCA Portal': link(judgment_url), 'Case number': '', 'Financial firm': '', 'Date': '', 'judgment': ''}

    try:
        #headers = {'User-Agent': 'whatever'}
        #page = requests.get(judgment_url, headers=headers)
        #soup = BeautifulSoup(page.content, "lxml")

        page = browser.get(judgment_url)
        browser.delete_all_cookies()
        browser.refresh()
        html_source = browser.page_source
        soup = BeautifulSoup(html_source, "lxml")
        
        #The following gets judgment text but also a lot of html tags
        #judgment_html_text = soup.get_text(separator="\n", strip=True)
    
        #Get text from html   
        judgment_html_text = text_from_html(html_source)

        #Try to get judgment text from PDF first, get from html if that fails
        try:
            print_options = PrintOptions()
            browser.get(judgment_url)
            pdf_b64 = browser.print_page(print_options)
    
            buffer=base64.b64decode(pdf_b64)
            f=io.BytesIO(buffer)
            
            pdfdoc_remote = pypdf.PdfReader(f)
            
            text_list = []
            
            for page in pdfdoc_remote.pages:
                text_list.append(page.extract_text())
    
            judgment_pdf_text = str(text_list)
    
            judgment_dict['judgment'] = judgment_pdf_text
    
            #Save judgment pdf if not popping judgment
            if pop_judgment() == 0:
                
                file_id = judgment_url.split('id=')[1] + '.pdf'
                
                with open(f"{download_dir}/{file_id}", "wb") as f:
                    f.write(base64.b64decode(pdf_b64))

        except:

            if 'Download PDF' in judgment_html_text:
                judgment_html_text = judgment_html_text.split('Download PDF')[1]
    
            if 'Before you complain to us' in judgment_html_text:
                judgment_html_text = judgment_html_text.split('Before you complain to us')[0]
            
            judgment_dict['judgment'] = judgment_html_text
        
        #Get case name
        try:
        
            case_name = soup.find('title').get_text(separator="\n", strip=True)
            
            judgment_dict['Case name'] = case_name.split('\xa0')[0]
        
        except:
             print(f'{judgment_url}: case name not found.')

        #Get case number
        try:
            
            if 'Case number\n' in judgment_html_text:
                case_number = judgment_html_text.split('Case number\n')[1].split('\n')[0]
            elif 'Case numbers\n' in judgment_html_text:
                case_number = judgment_html_text.split('Case numbers\n')[1].split('\n')[0]
            elif 'Determination For Case ' in case_name:
                case_number = case_name.split('Determination For Case ')[1]
            else:
                case_number = ''
                
            judgment_dict['Case number'] = case_number
            
        except:
            print(f'{judgment_url}: case number not found.')

        #Get financial firm
        try:
            judgment_dict['Financial firm'] = judgment_html_text.split('Financial firm\n')[1].split('\n')[0]
        except:
            print(f'{judgment_url}: financial firm not found.')

        #Get date
        try:
            potential_dates = judgment_html_text.split('\n')

            date = ''
            
            for potential_date in potential_dates:
                if is_date(potential_date) == True:
                    date = potential_date
                    break
                    
            judgment_dict['Date'] = date
            
        except:
            print(f'{judgment_url}: date not found.')

    except Exception as e:
        print(f"{judgment_url}: judgment not scrapped")
        print(e)

    #browser.close()
    
    return judgment_dict


# %%
afca_meta_labels_droppable = ["Case number", "Financial firm", 'Date']

# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from functions.gpt_functions import basic_model, flagship_model#, role_content



# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction
#system_instruction = role_content

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %% [markdown]
# ## Pre June 2024

# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def afca_old_run(df_master):
    
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    search_results = afca_old_search(earlier_t_o_r_input = df_master.loc[0, 'Include decisions made under earlier Terms of Reference'], 
                                                    all_these_words_input = df_master.loc[0, 'All these words'], 
                                                    this_exact_wording_or_phrase_input = df_master.loc[0, 'This exact wording or phrase'], 
                                                    one_or_more_of_these_words_1_input = df_master.loc[0, 'One or more of these words - 1'], 
                                                    one_or_more_of_these_words_2_input = df_master.loc[0, 'One or more of these words - 2'], 
                                                    one_or_more_of_these_words_3_input = df_master.loc[0, 'One or more of these words - 3'], 
                                                    any_of_these_unwanted_words_input = df_master.loc[0, 'Any of these unwanted words'], 
                                                    case_number_input = df_master.loc[0, 'Case number'], 
                                                    date_from_input = df_master.loc[0, 'Date from'], 
                                                    date_to_input = df_master.loc[0, 'Date to'], 
                                                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                                                )

    #for link in judgments_links:
    for case in search_results['case_list']:

            judgment_dict = case.copy()

            judgment_text = afca_old_pdf_judgment(case)

            judgment_dict['judgment'] = judgment_text

            judgment_dict['Hyperlink to AFCA Portal'] = link(case['Hyperlink to AFCA Portal'])
    
            judgments_file.append(judgment_dict)
            
            pause.seconds(np.random.randint(20, 40))

            print(f"Scrapped {len(judgments_file)}/{judgment_counter_bound} judgments.")

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
    
    #Rename column titles
    
#    try:
#        df_individual['Hyperlink (double click)'] = df_individual['Hyperlink'].apply(link)
#        df_individual.pop('Hyperlink')
#    except:
#        pass
                    
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = flagship_model
    else:        
        gpt_model = basic_model
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in afca_old_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
                
    return df_updated


# %% [markdown]
# ## Post 14 June 2024

# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def afca_new_run(df_master):
    
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    search_results = afca_search(keywordsearch_input = df_master.loc[0, 'Search for published decisions'], 
                ffsearch_input = df_master.loc[0, 'Search for a financial firm'], 
                product_line_input = df_master.loc[0, 'Product line'], 
                product_category_input = df_master.loc[0, 'Product category'], 
                product_name_input = df_master.loc[0, 'Product name'], 
                issue_type_input = df_master.loc[0, 'Issue type'], 
                issue_input = df_master.loc[0, 'Issue'], 
                date_from_input = df_master.loc[0, 'Date from'], 
                date_to_input = df_master.loc[0, 'Date to'])

    pause.seconds(np.random.randint(15, 30))
    
    #Create list of judgment links
    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    #judgments_links = []

    counter = 0

    #for link in judgments_links:
    for link in search_results['urls']:
        
        if counter < judgment_counter_bound:

            judgment_dict = afca_meta_judgment_dict(link)
    
            judgments_file.append(judgment_dict)

            counter += 1
            
            pause.seconds(np.random.randint(15, 30))

            print(f"Scrapped {len(judgments_file)}/{judgment_counter_bound} judgments.")
            
        else:
            
            break
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
                    
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = flagship_model
    else:        
        gpt_model = basic_model
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in afca_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
                
    return df_updated
    


# %% [markdown]
# ## Run function to use

# %%
@st.cache_data(show_spinner = False, ttl=600)
def afca_run(df_master):
    if df_master.loc[0, 'Collection'] == 'Decisions published before 14 June 2024':
        df_updated = afca_old_run(df_master)
    else:
        df_updated = afca_new_run(df_master)

    return df_updated
    


