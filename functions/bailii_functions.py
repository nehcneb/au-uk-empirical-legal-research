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
import pypdf
import io
from io import BytesIO
import pdf2image
#from PIL import Image
import math
from math import ceil
import copy

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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input, date_parser
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, default_judgment_counter_bound, no_results_msg, search_error_note


# %% [markdown]
# # BAILII search engine

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

options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--headless")
options.add_argument('--no-sandbox')  
options.add_argument('--disable-dev-shm-usage')  

#@st.cache_resource(show_spinner = False, ttl=600)
def get_driver():
    return webdriver.Chrome(options=options)

try:
    browser = get_driver()
    
    #browser.implicitly_wait(5)
    #browser.set_page_load_timeout(15)

    #browser.quit()
    
except Exception as e:
    st.error('Sorry, your internet connection is not stable enough for this app. Please check or change your internet connection and try again.')
    print(e)
    quit()

# %%
#Definitions for search function
bailii_methods_list = ['using autosearch', 'this Boolean query', 'any of these words', 'all of these words', 'this phrase', 'this case name']

bailii_method_types = ['auto', 'boolean', 'any', 'all', 'phrase', 'title']

bailii_sort_dict = {'Relevance': 'rank',
                    'Title': 'desc',
                    'Jurisdiction': 'juris',
                    'Date': 'date', 
                    'Date (oldest first)': 'fdate', 
                   }

bailii_highlight_dict = {'Yes': '1', 'No': '0'}

# %%
#Initialise default courts
bailii_courts_default_list = ['House of Lords', 
'Supreme Court',
 'Privy Council',
 'Court of Appeal (Civil Division)',
 'Court of Appeal (Criminal Division)',
 'High Court Administrative Court',
 'High Court Admiralty Court',
 'High Court Chancery Division',
 'High Court Commercial Court',
 'High Court Family Division',
 'High Court Intellectual Property Enterprise Court',
 "High Court King's/Queen's Bench Division",
 'High Court Mercantile Court',
 'High Court Patents Court',
 'High Court Senior Courts Costs Office',
 'High Court Technology and Construction Court'
]

# %%
#auxiliary lists and variables
bailii_courts = {'House of Lords': 'uk/cases/UKHL',
 'Supreme Court': 'uk/cases/UKSC',
 'Privy Council': 'uk/cases/UKPC',
 'Court of Appeal (Civil Division)': 'ew/cases/EWCA/CIV',
 'Court of Appeal (Criminal Division)': 'ew/cases/EWCA/CRIM',
 'High Court Administrative Court': 'ew/cases/EWHC/ADMIN',
 'High Court Admiralty Court': 'ew/cases/EWHC/ADMLTY',
 'High Court Chancery Division': 'ew/cases/EWHC/CH',
 'High Court Commercial Court': 'ew/cases/EWHC/COMM',
 'High Court Family Division': 'ew/cases/EWHC/FAM',
 'High Court Intellectual Property Enterprise Court': 'ew/cases/EWHC/IPEC',
 "High Court King's/Queen's Bench Division": 'ew/cases/EWHC/KB',
 'High Court Mercantile Court': 'ew/cases/EWHC/MERCANTILE',
 'High Court Patents Court': 'ew/cases/EWHC/PAT',
 'High Court Senior Courts Costs Office': 'ew/cases/EWHC/SCCO',
 'High Court Technology and Construction Court': 'ew/cases/EWHC/TCC',
 'Court of Protection': 'ew/cases/EWCOP',
 'Family Court (High Court Judges)': 'ew/cases/EWFC/HCJ',
 'Family Court (Other Judges)': 'ew/cases/EWFC/OJ',
 "Magistrates' Court (Family)": 'ew/cases/EWMC/FPC',
 'County Court (Family)': 'ew/cases/EWCC/FAM'}

bailii_courts_list = list(bailii_courts.keys())


# %%
def bailii_court_choice(chosen_list):

    chosen_indice = []

    if isinstance(chosen_list, str):
        chosen_list = ast.literal_eval(chosen_list)

    for i in chosen_list:
        
        chosen_indice.append(bailii_courts[i])
    
    return chosen_indice



# %%
#Function turning search terms to search results url
class bailii_search_tool:

    def __init__(self,
                 citation= '',
                case_name = '',
                all_of_these_words = '',
                exact_phrase = '',
                any_of_these_words = '',
                advanced_query = '',
                datelow = None,
                datehigh = None,
                sort = list(bailii_sort_dict.keys())[0],
                highlight = True,
                courts = [],
                 judgment_counter_bound = default_judgment_counter_bound
             ):

        #Initialise parameters
        self.citation= citation
        self.case_name = case_name
        self.all_of_these_words = all_of_these_words
        self.exact_phrase = exact_phrase
        self.any_of_these_words = any_of_these_words
        self.advanced_query = advanced_query
        self.datelow = datelow
        self.datehigh = datehigh
        self.sort = sort
        self.highlight = highlight
        self.courts = courts
        self.judgment_counter_bound = judgment_counter_bound
        
        self.results_count = 0

        self.total_pages = 0
        
        self.results_url = ''
        
        self.soup = None
        
        self.case_infos = []
        
    #Function for getting url for search results and the soup of first page
    def get_url(self):
    
        #If citation is given, then all other search paras are ignored
        if len(self.citation) > 0:
    
            findby = 'find_by_citation.cgi?'
    
            base_url = "https://www.bailii.org/cgi-bin/" + findby
            
            params = {'citation': self.citation}
    
    
        else:
            
            findby = 'lucy_search_1.cgi?'
    
            base_url = "https://www.bailii.org/cgi-bin/" + findby
    
            #Initialise list of search terms
            query_list = []
    
            if len(self.case_name) > 0:
                
                case_name_query = f'(title:( {self.case_name} ))'
    
                query_list.append(case_name_query)
    
            if len(self.all_of_these_words) > 0:
    
                all_of_these_words_query_raw_list = self.all_of_these_words.split(' ')
    
                all_of_these_words_query_list = []
    
                for word in all_of_these_words_query_raw_list:
    
                    all_of_these_words_query_list.append(f" ({word}) ")
    
                all_of_these_words_query = ' AND '.join(all_of_these_words_query_list)
    
                query_list.append(all_of_these_words_query)
    
            if len(self.exact_phrase) > 0:
    
                exact_phrase_query = f'("{self.exact_phrase}")'
    
                query_list.append(exact_phrase_query)
    
            if len(self.any_of_these_words) > 0:
    
                any_of_these_words_query_raw_list = self.any_of_these_words.split(' ')
    
                any_of_these_words_query_raw = ' OR '.join(any_of_these_words_query_raw_list)
    
                any_of_these_words_query = f"({any_of_these_words_query_raw})"
    
                query_list.append(any_of_these_words_query)
    
            if len(self.advanced_query) > 0:
    
                advanced_query_query = f'({self.advanced_query})'
    
                query_list.append(advanced_query_query)
                
            query = ' AND '.join(query_list)
    
            #print(f"Search terms are as follows: {query}")
    
            #Datelow param
            if self.datelow not in [None, '']:
                
                self.datelow = date_parser(self.datelow)
                
                if isinstance(self.datelow, datetime):
        
                    self.datelow = self.datelow.strftime('%Y%m%d')
        
                else:
                    
                    print("Can't get datelow param.")
            
            #Datehigh param
            if self.datehigh not in [None, '']:
        
                self.datehigh = date_parser(self.datehigh)
                
                if isinstance(self.datehigh, datetime):
        
                    self.datehigh = self.datehigh.strftime('%Y%m%d')
    
                else:
                    
                    print("Can't get datehigh param.")
    
            #Sort param
            try:
                
                self.sort = bailii_sort_dict[self.sort]
                
            except:
                
                self.sort = bailii_sort_dict[list(bailii_sort_dict.keys())[0]]
                
                print(f"Can't get sort param. Kept default {self.sort}.")
    
            #Highlight param            
            try:
                
                self.highlight = int(bool(self.highlight))
                
            except:
                
                self.highlight = True
                
                print(f"Can't get highlight param. Kept default {self.highlight}.")
    
            #Choice of courts
            courts_indices = ' '.join(bailii_court_choice(self.courts))
    
            #Limiting to EW cases
            mask_path = 'ew/cases uk/cases/UKHL uk/cases/UKPC uk/cases/UKSC ' 
            
            mask_path += courts_indices
    
            params = {'method': 'boolean',
                      'query': query,
                      'datelow': self.datelow,
                      'datehigh': self.datehigh,
                      'sort': self.sort,
                      'highlight': self.highlight,
                      'mask_path': mask_path
                      }
    
        #print(f"params == {params}")
    
        #params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        
        headers = {'User-Agent': 'whatever'}
        #response = requests.get(base_url, params=params, headers=headers)
    
        #soup = BeautifulSoup(response.content, "lxml")
    
        self.results_url = base_url + urllib.parse.urlencode(params)
    
        print(f"self.results_url == {self.results_url}")
    
        #return {'results_url': self.results_url, 'soup': self.soup}

        
    def search(self):

        if len(self.results_url) == 0:

            self.get_url()
            
        #If citation for a case directly give, then return only that case
        if 'lucy_search' not in self.results_url:
    
            case_info = {'Case name': '',
             'Medium neutral citation' : self.citation, 
            'Date': '',
             'Reports': '', 
             'Hyperlink to BAILII': self.results_url, 
             'judgment': ''
            }
    
            self.case_infos.append(case_info)
    
        else:

            browser.get(self.results_url)

            self.soup = BeautifulSoup(browser.page_source, "lxml")
            
            results_pattern = re.compile(r"Total\sresults.+")
            results_num_list = self.soup.find_all("td", text= results_pattern)
            
            if len(results_num_list) > 0:
            
                results_count_raw = results_num_list[0].text.split(' ')[-1].replace(',', '')
                self.results_count = int(float(results_count_raw))
                self.total_pages = math.ceil(self.results_count/10)

            print(f"Found {self.results_count} results or {self.total_pages} pages")
            
            if self.results_count > 0:
                
                #Start counter
                counter = 0
    
                for page in range(1, self.total_pages + 1):
    
                    if counter < min(self.results_count, self.judgment_counter_bound):

                        #For subsequent pages, need to press next
                        if page > 1:
                            
                            pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))
                            
                            submit_buttons = Wait(browser, 30).until(EC.presence_of_all_elements_located((By.XPATH, "//input[@type='submit']")))
                            next_button = submit_buttons[-1]
                            next_button.click()
                            self.soup = BeautifulSoup(browser.page_source, "lxml")
    
                    else:
    
                        break

                    print(f"Processing page {page} of {self.total_pages}")
                    
                    cases_raw = self.soup.find_all("li")
                    
                    for case_raw in cases_raw:
                
                        if counter < min(self.results_count, self.judgment_counter_bound):
                
                            #Initialise default values
                            case_name = ''
                            mnc = ''
                            date = ''
                            reports = ''
                            link = ''
                
                            try:           
                                
                                link = 'https://www.bailii.org' + case_raw.find("a", href = True).get('href')
                            
                            except Exception as e:
                                
                                print(f"Can't get link from case_raw == {case_raw}.")
                
                            #Get all other metas
                            meta_list = case_raw.get_text().split('\n')
                
                            if len(meta_list) > 0:
                
                                try:
                        
                                    for meta in meta_list:
                                    
                                        if len(meta) > 0:
                                    
                                            case_name = meta
                                    
                                            break
                                    
                                    date_list = re.findall(r'\(\d.+\d\)', case_name)
                                    
                                    if len(date_list) > 0:
                                        
                                        date = date_list[-1]
                                    
                                        if isinstance(date, tuple):
                                    
                                            date = date[0]
                                        
                                        case_name = case_name.replace(date, '')
                                        
                                        date =  date.replace('(', '').replace(')', '')
                                    
                                    mnc_list = re.findall(r'(\[\d{4}\].+\w+\d+\s?(\(\w+\))?)', case_name)
                                    
                                    if len(mnc_list) > 0:
                                    
                                        mnc = mnc_list[0]
                                    
                                        if isinstance(mnc, tuple):
                                    
                                            mnc = mnc[0]

                                        if len(mnc) > 0:

                                            while mnc[-1] == ' ':

                                                mnc = mnc[:-1]
                                        
                                        case_name = case_name.replace(mnc, '')
                                    
                                    while case_name[-1] == ' ':
                                        
                                        case_name = case_name[:-1]
                                    
                                    reports = meta_list[-2]
                
                                    while reports[0] in ['(', ',', ' ']:
                                        reports = reports[1:]
                                    
                                    while reports[-1] == ';':
                                        reports = reports[:-1]

                                except Exception as e:

                                    print(f"Can't get some metadata for {link}")
            
                            case_info = {'Case name': case_name,
                                     'Medium neutral citation' : mnc, 
                                    'Date': date,
                                     'Reports': reports, 
                                     'Hyperlink to BAILII': link, 
                                     'judgment': ''
                                    }
                
                            self.case_infos.append(case_info)

                            counter += 1
                            #print(f"counter == {counter}")

    #Function for getting all requested judgments
    def get_judgments(self):

        self.case_infos_w_judgments = []

        for case_info in self.case_infos:

            if len(self.case_infos_w_judgments) < min(self.results_count, self.judgment_counter_bound):

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))

                #Initialise default return value
                case_info_w_judgment = copy.deepcopy(case_info)
                
                #Initialise default text
                text = ''
                
                judgment_url = case_info['Hyperlink to BAILII']
                headers = {'User-Agent': 'whatever'}
                
                page = requests.get(judgment_url, headers=headers)
                soup = BeautifulSoup(page.content, "lxml")
                text = soup.get_text()
            
                if '[Help]' in text:
                    try:
                        text = text.split('[Help]')[-1]
                    except:
                        print(f"Can't get rid of layout type content")
                
                #Attach judgment text and urls to case_info dict
                case_info_w_judgment['judgment'] = text

                #Make links clickable
                for key in case_info_w_judgment:
                    
                    if 'Hyperlink' in key:
                        
                        direct_link = case_info_w_judgment[key]

                        if '&query' in direct_link:
                            
                            direct_link = direct_link.split('&query')[0]
                        
                        case_info_w_judgment[key] = link(direct_link)

                        break
                
                self.case_infos_w_judgments.append(case_info_w_judgment)
                    
                print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments.")


# %%
#@st.cache_data(show_spinner = False)
def bailii_search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    bailii_search = bailii_search_tool(
                citation= df_master.loc[0, 'Citation'],
                case_name = df_master.loc[0, 'Case name'],
                all_of_these_words = df_master.loc[0, 'All of these words'],
                exact_phrase = df_master.loc[0, 'Exact phrase'],
                any_of_these_words = df_master.loc[0, 'Any of these words'],
                advanced_query = df_master.loc[0, 'Advanced query'],
                datelow = df_master.loc[0, 'From date'],
                datehigh = df_master.loc[0, 'To date'],
                sort = df_master.loc[0, 'Sort results by'],
                highlight = df_master.loc[0, 'Highlight search terms in result'],
                courts = df_master.loc[0, 'Courts'],
                judgment_counter_bound = df_master.loc[0, 'Maximum number of judgments']
             )

    bailii_search.search()
    
    return {'results_url': bailii_search.results_url, 'results_count': bailii_search.results_count, 'case_infos': bailii_search.case_infos}



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import basic_model, flagship_model


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, GPT_answers_check, unanswered_questions, checked_questions_json, answers_check_system_instruction


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def bailii_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    bailii_search = bailii_search_tool(
                    citation= df_master.loc[0, 'Citation'],
                    case_name = df_master.loc[0, 'Case name'],
                    all_of_these_words = df_master.loc[0, 'All of these words'],
                    exact_phrase = df_master.loc[0, 'Exact phrase'],
                    any_of_these_words = df_master.loc[0, 'Any of these words'],
                    advanced_query = df_master.loc[0, 'Advanced query'],
                    datelow = df_master.loc[0, 'From date'],
                    datehigh = df_master.loc[0, 'To date'],
                    sort = df_master.loc[0, 'Sort results by'],
                    highlight = df_master.loc[0, 'Highlight search terms in result'],
                    courts = df_master.loc[0, 'Courts'],
                    judgment_counter_bound = df_master.loc[0, 'Maximum number of judgments']
                 )
    
    bailii_search.search()

    bailii_search.get_judgments()

    for case_info in bailii_search.case_infos_w_judgments:
        
        judgments_file.append(case_info)
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
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
    
    return df_updated

# %%
