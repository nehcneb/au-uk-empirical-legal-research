# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
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
import urllib.request
import io
from io import BytesIO
import math
from math import ceil


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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input
#Import variables
from functions.common_functions import today_in_nums, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound


# %% [markdown]
# # Kercher Reports search engine

# %%
from functions.common_functions import link

# %%
#Scrape javascript

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys


options = Options()
options.add_argument("--disable-gpu")
#options.add_argument("--headless")
options.add_argument('--no-sandbox')  
options.add_argument('--disable-dev-shm-usage')  

if 'Users/Ben' not in os.getcwd(): 

    from pyvirtualdisplay import Display
    
    display = Display(visible=0, size=(1200, 1600))  
    display.start()

    options.add_argument("window-size=1200x600")

#@st.cache_resource(show_spinner = False, ttl=600)
def get_driver():

    browser = webdriver.Chrome(options=options)

    browser.implicitly_wait(15)
    browser.set_page_load_timeout(30)

    if 'Users/Ben' in os.getcwd():
        browser.minimize_window()
    
    return browser



# %%
def kr_selenium_judgment_text(case_info):
    url = case_info['Hyperlink to AustLII']

    browser = get_driver()
        
    #Get search results
    browser.get(url)

    soup = BeautifulSoup(browser.page_source, "lxml")

    text = soup.get_text()
    try:
        text = soup.get_text().split('Print (pretty)')[0].split('\n Any \n')[-1]
    except:
        pass

    browser.quit()
    
    return text

#Meta labels and judgment combined

#@st.cache_data(show_spinner = False)
def kr_selenium_meta_judgment_dict(case_info):
    
    try:
        
        judgment_dict = {'Case name': '',
                         'Medium neutral citation' : '', 
                         'Other reports': '', 
                         'Hyperlink to AustLII': '', 
                         'Date' : '', 
                         'judgment': ''
                        }
    
        case_name = case_info['Case name']
        date = case_info['Case name'].split('(')[-1].replace(')', '')
        year = case_info['Case name'].split('[')[1][0:4]
        case_number_raw = case_info['Case name'].split('NSWSupC ')[1].split(' (')[0]
        
        if ";" in case_number_raw:
            case_number = case_number_raw.split(';')[0]
        else:
            case_number = case_number_raw
        
        mnc = '[' + year +']' + ' NSWSupC ' + case_number
        nr_cite = ''
            
        try:
            case_name = case_info['Case name'].split('[')[0][:-1]
            nr_cite = case_info['Case name'].split('; ')[1].replace(' (' + date + ')', '')
        except:
            pass
                    
        judgment_dict['Case name'] = case_name
        judgment_dict['Medium neutral citation'] = mnc
        judgment_dict['Other reports'] = nr_cite
        judgment_dict['Date'] = date
        judgment_dict['Hyperlink to AustLII'] = link(case_info['Hyperlink to AustLII'])
        judgment_dict['judgment'] = kr_selenium_judgment_text(case_info)

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
        
    return judgment_dict


# %%
class kr_search_tool:

    def __init__(self,
             query= '',
            year = '',
            letter = '',
            judgment_counter_bound = default_judgment_counter_bound
         ):
    
        #Initialise parameters
        self.query = query
        self.year = str(year).replace('.', '')
        self.letter = letter
        self.judgment_counter_bound = judgment_counter_bound
        
        self.results_count = 0
        
        self.total_pages = 0
        
        self.results_url = ''
        
        self.base_url = 'https://www.austlii.edu.au/cgi-bin/viewdb/au/cases/nsw/NSWSupC/'
        
        self.soup = None
        
        self.case_infos = []

    def get_url(self):
    
        if len(self.year) > 0:
    
            self.results_url = f'https://www.austlii.edu.au/cgi-bin/viewtoc/au/cases/nsw/NSWSupC/{self.year}/'
    
        elif len(self.letter) > 0:
    
            self.results_url = f'https://www.austlii.edu.au/cgi-bin/viewtoc/au/cases/nsw/NSWSupC/toc-{self.letter.upper()}.html'
    
        else:
            
            params = {'meta' : '',
                      'mask_path' : 'au/cases/nsw/NSWSupC', 
                      'method' : 'auto',
                      'query' : self.query
                     }
    
            self.results_url = self.base_url + urllib.parse.urlencode(params)
        
        #return {'results_url': self.results_url, 'self.soup': self.soup}

    def search(self):

        if len(self.results_url) == 0:

            self.get_url()

        browser = get_driver()

        #If year or letter given, then search self.results_url
        if (len(self.year) > 0) or (len(self.letter) > 0):

            browser.get(self.results_url)

            pause.seconds(np.random.randint(10, 15))
            
            self.soup = BeautifulSoup(browser.page_source, "lxml")
            
            #number of search results

            #Get self.case_infos
            #hrefs = self.soup.find_all('a', href=re.compile('/cgi-bin/viewdoc/au/cases/nsw/NSWSupC'))
                        
            #for link in hrefs:
                
                #if (' NSWSupC ' in str(link)) and ('LawCite' not in str(link)):
            
                    #self.results_count += 1

            hrefs = self.soup.find_all('a', href=re.compile('/cgi-bin/viewdoc/au/cases/nsw/NSWSupC'))

            self.results_count = len(hrefs)
            
            self.total_pages = 1

        #If year or letter not given but query given, enter query in search box and enter
        else:

            browser.get(self.base_url)
            
            search_box = Wait(browser, 30).until(EC.visibility_of_element_located((By.ID, 'search-box')))

            search_box.send_keys(self.query)

            search_box.send_keys(Keys.ENTER)

            pause.seconds(np.random.randint(10, 15))
            
            self.soup = BeautifulSoup(browser.page_source, "lxml")
    
            #print(self.soup)
            
            #number of search results
            #docs_found_string = re.findall(r'\d+', str(self.soup.find('li', class_='number-docs').text).replace(',', ''))[0]
            docs_found_string = re.findall(r'\d+', str(self.soup.find('title')).replace(',', ''))[0]
            
            self.results_count = int(float(docs_found_string))
            self.total_pages = math.ceil(self.results_count/10) #10 results per page

        if self.results_count > 0:

            #Start counter
            counter = 0

            for page in range(1, self.total_pages + 1):

                if counter < min(self.results_count, self.judgment_counter_bound):

                    if page > 1:
                        
                        pause.seconds(np.random.randint(10, 15))

                        #Get next page buttons from current page
                        page_buttons = Wait(browser, 30).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@id='pagination-sort']//a[contains(@href, '/cgi-bin/sinosrch.cgi?')]")))

                        #Decide whether there is a need to click 'next' to get the next 10 pages
                        need_to_click_next = True
                        
                        for page_button in page_buttons:

                            if page_button.text == str(page):

                                need_to_click_next = False

                                page_button.click()

                                break

                        #If there is a need to click 'next' to get the next 10 pages 
                        if need_to_click_next == True:

                            #Get the next 10 pages
                            next_button = page_buttons[-1]

                            next_button.click()

                            page_buttons = Wait(browser, 30).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@id='pagination-sort']//a[contains(@href, '/cgi-bin/sinosrch.cgi?')]")))

                            for page_button in page_buttons:
    
                                if page_button.text == str(page):
    
                                    need_to_click_next = False
    
                                    page_button.click()
    
                                    break

                        #Update self.soup
                        self.soup = BeautifulSoup(browser.page_source, "lxml")

                else:

                    break

                print(f"Processing page {page} of {self.total_pages}")
        
                #Get self.case_infos
                #hrefs = self.soup.find_all('a', href=True)

                hrefs = self.soup.find_all('a', href=re.compile('/cgi-bin/viewdoc/au/cases/nsw/NSWSupC'))
                
                for link in hrefs:

                    if counter < self.judgment_counter_bound:
                    
                    #if ((counter < self.judgment_counter_bound) and (' NSWSupC ' in str(link)) and ('LawCite' not in str(link))):
                        case = link.get_text()
                        link_direct = link.get('href')
                        link = 'https://www.austlii.edu.au' + link_direct.split('?context')[0]
                        
                        dict_object = {'Case name': case, 
                                       'Hyperlink to AustLII': link}
                        
                        self.case_infos.append(dict_object)
                        
                        counter = counter + 1


        browser.quit()
        
        #return self.case_infos

    def get_judgments(self):

        self.case_infos_w_judgments = []
        
        for case_info in self.case_infos:

            if len(self.case_infos_w_judgments) < min(self.results_count, self.judgment_counter_bound):

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))

                case_info_w_judgment = kr_selenium_meta_judgment_dict(case_info)
                        
                self.case_infos_w_judgments.append(case_info_w_judgment)
                    
                print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments.")

# %%
#kr_search = kr_search_tool(query= 'Forbes', year = '', letter = '', judgment_counter_bound = 5)


# %%
#kr_search.search()

# %%
#kr_search.results_count

# %%
#kr_search.get_judgments()

# %%
#case_infos_w_judgments = kr_search.case_infos_w_judgments

# %%
#case_infos_w_judgments[0]

# %%
#list of search methods
#NOT IN USE

kr_methods_list = ['Full text', 'Titles only', 'This Boolean query', 'Any of these words', 'All of these words']
kr_method_types = ['auto', 'title', 'boolean', 'any', 'all']


# %%
#Function turning search terms to search results url
#NOT IN USE

#@st.cache_data(show_spinner = False)
def kr_search(query= '', 
              method = ''
             ):
    base_url = "https://www.austlii.edu.au/cgi-bin/sinosrch.cgi?"

    method_index = kr_methods_list.index(method)
    method_type = kr_method_types[method_index]

    query_text = query

    params = {'meta' : '',
              'mask_path' : 'au/cases/nsw/NSWSupC', 
              'method' : method_type,
              'query' : query_text
             }

    headers = {'User-Agent': 'whatever'}
    response = requests.get(base_url, params=params, headers=headers)

    soup = BeautifulSoup(response.content, "lxml")
    
    return {'results_url': response.url, 'soup': soup}


# %%
#Define function turning search results url to case_link_pairs to judgments

#NOT IN USE

#@st.cache_data(show_spinner = False)
def kr_search_results_to_case_link_pairs(_soup, url_search_results, judgment_counter_bound):
    #_soup, url_search_results are from kr_search

    hrefs = _soup.find_all('a', href=True)
    case_link_pairs = []

    #number of search results
    docs_found_string = re.findall(r'\d+', str(soup.find('title')).replace(',', ''))[0]
    docs_found = int(float(docs_found_string))

    #Start counter
    counter = 1
    
    for link in hrefs:
        if ((counter <= judgment_counter_bound) and (' NSWSupC ' in str(link)) and ('LawCite' not in str(link))):
#        if ((counter <= judgment_counter_bound) and ('AustLII' in str(link)) and ('cases/EngR' in str(link)) and ('LawCite' not in str(link))):
            case = link.get_text()
            link_direct = link.get('href')
            link = 'https://www.austlii.edu.au' + link_direct.split('?context')[0]
            dict_object = { 'Case name': case, 'Hyperlink to AustLII': link}
            case_link_pairs.append(dict_object)
            counter = counter + 1
        
    for ending in range(10, docs_found, 10):
        if counter <= min(judgment_counter_bound, docs_found):
            url_next_page = url_search_results + ';offset=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page, headers=headers)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            
            hrefs_next_page = soup_judgment_next_page.find_all('a', href=True)
            for extra_link in hrefs_next_page:
                if ((counter <= judgment_counter_bound) and (' NSWSupC ' in str(extra_link)) and ('LawCite' not in str(extra_link))):
#                if ((counter <= judgment_counter_bound) and ('AustLII' in str(extra_link)) and ('cases/EngR' in str(extra_link)) and ('LawCite' not in str(extra_link))):
                    case = extra_link.get_text()
                    extra_link_direct = extra_link.get('href')
                    extra_link = 'https://www.austlii.edu.au' + extra_link_direct.split('?context')[0]
                    dict_object = { 'Case name': case, 'Hyperlink to AustLII': extra_link}
                    case_link_pairs.append(dict_object)
                    counter = counter + 1

            pause.seconds(np.random.randint(5, 15))
            
        else:
            break
    
    #If no need to get rid of repetitions
    #return case_link_pairs
    
    #Get rid of repetitions
    case_link_pairs_no_repeats = []

    for case_link_pair in case_link_pairs:
        if  case_link_pair not in case_link_pairs_no_repeats:
            case_link_pairs_no_repeats.append(case_link_pair)
            
    return case_link_pairs_no_repeats
    


# %%
#Convert case-link pairs to judgment text

#NOT IN USE

#@st.cache_data(show_spinner = False)
def kr_judgment_text(case_link_pair):
    url = case_link_pair['Hyperlink to AustLII']
    headers = {'User-Agent': 'whatever'}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, "lxml")
    text = soup.get_text()
    try:
        text = soup.get_text().split('Print (pretty)')[0].split('\n Any \n')[-1]
    except:
        pass
    
    return text
        


# %%
#Meta labels and judgment combined

#NOT IN USE

#@st.cache_data(show_spinner = False)
def kr_meta_judgment_dict(case_link_pair):
    try:
        judgment_dict = {'Case name': '',
                         'Medium neutral citation' : '', 
                         'Other reports': '', 
                         'Hyperlink to AustLII': '', 
                         'Date' : '', 
                         'judgment': ''
                        }
    
        case_name = case_link_pair['Case name']
        date = case_link_pair['Case name'].split('(')[-1].replace(')', '')
        year = case_link_pair['Case name'].split('[')[1][0:4]
        case_number_raw = case_link_pair['Case name'].split('NSWSupC ')[1].split(' (')[0]
        
        if ";" in case_number_raw:
            case_number = case_number_raw.split(';')[0]
        else:
            case_number = case_number_raw
        
        mnc = '[' + year +']' + ' NSWSupC ' + case_number
        nr_cite = ''
            
        try:
            case_name = case_link_pair['Case name'].split('[')[0][:-1]
            nr_cite = case_link_pair['Case name'].split('; ')[1].replace(' (' + date + ')', '')
        except:
            pass
                    
        judgment_dict['Case name'] = case_name
        judgment_dict['Medium neutral citation'] = mnc
        judgment_dict['Other reports'] = nr_cite
        judgment_dict['Date'] = date
        judgment_dict['Hyperlink to AustLII'] = link(case_link_pair['Hyperlink to AustLII'])
        judgment_dict['judgment'] = kr_judgment_text(case_link_pair)

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
        
    return judgment_dict


# %%
#@st.cache_data(show_spinner = False)
def kr_search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    kr_search = kr_search_tool(query= df_master.loc[0, 'Search query'],
                    year = df_master.loc[0, 'Specific year'], 
                    letter = df_master.loc[0, 'Decision begins with'],
                    judgment_counter_bound = df_master.loc[0, 'Maximum number of judgments']
                   )

    kr_search.search()
    
    return {'results_url': kr_search.results_url, 'results_count': kr_search.results_count, 'case_infos': kr_search.case_infos}



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
#role_content_kr = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a part of the judgment or metadata, include a reference to that part of the judgment or metadata. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". '

#system_instruction = role_content#_kr

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def kr_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    kr_search = kr_search_tool(query= df_master.loc[0, 'Search query'],
                    year = df_master.loc[0, 'Specific year'], 
                    letter = df_master.loc[0, 'Decision begins with'],
                    judgment_counter_bound = df_master.loc[0, 'Maximum number of judgments']
                   )
    
    kr_search.search()

    kr_search.get_judgments()

    for case_info in kr_search.case_infos_w_judgments:
        
        judgments_file.append(case_info)
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    df_individual = pd.read_json(json_individual)

    #For KR, convert date to string so as to avoid Excel producing random numbers for dates
    df_individual['Date'] = df_individual['Date'].astype(str)

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
    
    return df_updated

