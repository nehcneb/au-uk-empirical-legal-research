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
import urllib
from urllib.request import urlretrieve
import os
import io
from io import BytesIO
from io import StringIO
import math

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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input, link, is_date, split_title_mnc, pdf_judgment, pdf_image_judgment
#Import variables
from functions.common_functions import huggingface, today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

# %% [markdown]
# # High Court of Australia search engine

# %%
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
from selenium.common.exceptions import ElementClickInterceptedException
from selenium_stealth import stealth

if 'Users/Ben' not in os.getcwd(): 

    from pyvirtualdisplay import Display
    
    display = Display(visible=0, size=(1200, 1600))  
    display.start()

#For downloading judgments
download_dir = os.getcwd() + '/HCA_PDFs'

#@st.cache_resource(show_spinner = False, ttl=600)
def get_driver():

    options = Options()
    
    #For automation
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    #For downloading judgments
    options.add_experimental_option('prefs', {
    "download.default_directory": download_dir, #Change default directory for downloads
    "download.prompt_for_download": False, #To auto download the file
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True #It will not show PDF directly in chrome
    })
    
    browser = webdriver.Chrome(options=options)

    browser.implicitly_wait(15)
    browser.set_page_load_timeout(30)

    stealth(browser,
    
            languages=["en-US", "en"],
    
            vendor="Google Inc.",
    
            platform="Win32",
    
            webgl_vendor="Intel Inc.",
    
            renderer="Intel Iris OpenGL Engine",
    
            webdriver=False,
    
            fix_hairline=True)
    
    if 'Users/Ben' in os.getcwd():
        browser.minimize_window()
    
    return browser



# %%
#Load hca_data

@st.cache_resource(show_spinner = False)
def hca_load_data(url):
    df = pd.read_csv(url)
    return df

hca_data_url = 'https://raw.githubusercontent.com/nehcneb/au-uk-empirical-legal-research/main/hca_data.csv'

#response = requests.get(hca_data_url)

#hca_df = pd.read_csv(StringIO(response.text))

hca_df = hca_load_data(hca_data_url)

# %% [markdown]
# ## Definitions

# %%
#Collections available
hca_collections_dict = {
'Judgments 2000-present': 'judgments-2000-current',
'Commonwealth Law Reports, volumes 1-100': '1-clr-100-clr',
'Single Justice Judgments': 'single-justice-judgments',
'Unreported Judgments': 'unreported-judgments'
}


hca_collections_years_dict = {
'Judgments 2000-present': [str(x) for x in range(datetime.now().year, 2000-1, -1)],
'Commonwealth Law Reports, volumes 1-100': [str(x) for x in range(1903, 1958 + 1)],
'Single Justice Judgments': [str(x) for x in range(datetime.now().year, 2024-1, -1)],
'Unreported Judgments': [str(x) for x in (list(range(1994, 1921-1, -1)) + ['1906'])],
}


# %%
hca_clr_volumns = [str(x) for x in range(1, 100+1)]

# %%
hca_collections = list(hca_collections_dict.keys())

# %%
#Meta labels and judgment combined
hca_meta_labels_droppable = ['Date', 'Case number', 'Before', 'Catchwords']

# %%
#Get judges and years dicts
#judges_dict = {}
#years_dict = {}

#search_url = 'https://www.hcourt.gov.au/cases-and-judgments/judgments/judgments-2000-current?'
#search_url = 'https://www.hcourt.gov.au/cases-and-judgments/judgments/single-justice-judgments?'#For single judges
#search_url = 'https://www.hcourt.gov.au/cases-and-judgments/judgments/unreported-judgments'#For unreported judgments
#search_page = requests.get(search_url)

#search_soup = BeautifulSoup(search_page.content, "lxml")
#judges = search_soup.find_all('li', class_ = 'facet-item')

#for judge in judges:
    #key = judge.get_text(strip = True)

    #code = judge.find('a', href = True)['href'].split('=')[-1]

    #if not re.search(r'\d', key):
    
        #judges_dict.update({key: code})

    #else:
        
        #years_dict.update({key: code})


# %%
unreported_judges_dict = {'Aickin': 'justices:Aickin',
 'Barwick': 'justices:Barwick',
 'Brennan': 'justices:Brennan',
 'Dawson': 'justices:Dawson',
 'Deane': 'justices:Deane',
 'Dixon': 'justices:Dixon',
 'Duffy': 'justices:Duffy',
 'Evatt': 'justices:Evatt',
 'Fullagar': 'justices:Fullagar',
 'Gaudron': 'justices:Gaudron',
 'Gavan Duffy': 'justices:Gavan%20Duffy',
 'Gibbs': 'justices:Gibbs',
 'Griffith': 'justices:Griffith',
 'Higgins': 'justices:Higgins',
 'Isaacs': 'justices:Isaacs',
 'Jacobs': 'justices:Jacobs',
 'Kitto': 'justices:Kitto',
 'Knox': 'justices:Knox',
 'Latham': 'justices:Latham',
 'Markell': 'justices:Markell',
 'Mason': 'justices:Mason',
 'McHugh': 'justices:McHugh',
 'McTiernan': 'justices:McTiernan',
 'Menzies': 'justices:Menzies',
 'Murphy': 'justices:Murphy',
 'Owen': 'justices:Owen',
 'Rich': 'justices:Rich',
 'Starke': 'justices:Starke',
 'Stephen': 'justices:Stephen',
 'Taylor': 'justices:Taylor',
 'Toohey': 'justices:Toohey',
 'Walsh': 'justices:Walsh',
 'Webb': 'justices:Webb',
 'Williams': 'justices:Williams',
 'Wilson': 'justices:Wilson',
 'Windeyer': 'justices:Windeyer'}


# %%
single_judges_dict = {'Beech-Jones': 'justices:BeechJones',
 'Edelman': 'justices:Edelman',
 'Gleeson': 'justices:Gleeson',
 'Gordon': 'justices:Gordon',
 'Jagot': 'justices:Jagot',
 'Steward': 'justices:Steward'}

# %%
judges_dict = {'Beech-Jones': 'justices:BeechJones',
 'Bell': 'justices:Bell',
 'Callinan': 'justices:Callinan',
 'Crennan': 'justices:Crennan',
 'Edelman': 'justices:Edelman',
 'French': 'justices:French',
 'Gageler': 'justices:Gageler',
 'Gaudron': 'justices:Gaudron',
 'Gleeson': 'justices:Gleeson',
 'Gordon': 'justices:Gordon',
 'Gummow': 'justices:Gummow',
 'Hayne': 'justices:Hayne',
 'Heydon': 'justices:Heydon',
 'Jagot': 'justices:Jagot',
 'Keane': 'justices:Keane',
 'Kiefel': 'justices:Kiefel',
 'Kirby': 'justices:Kirby',
 'McHugh': 'justices:McHugh',
 'Nettle': 'justices:Nettle',
 'Steward': 'justices:Steward'}

# %%
hca_judges = list(judges_dict.keys())

# %%
single_hca_judges = list(single_judges_dict.keys())

# %%
unreported_hca_judges = list(unreported_judges_dict.keys())

# %%
all_judges_dict = judges_dict | single_judges_dict | unreported_judges_dict

# %%
hca_collections_judges_dict = {
'Judgments 2000-present': hca_judges,
'Commonwealth Law Reports, volumes 1-100': None,
'Single Justice Judgments': single_hca_judges,
'Unreported Judgments': unreported_hca_judges,
}

# %%
hca_search_methods_dict = {
'Judgments 2000-present': ["Keywords, case number, Justices, year or Citation"], #["Keywords or case number", "Justices or year", "Citation"],
'Commonwealth Law Reports, volumes 1-100': ["Keywords, CLR volumn or year"], #["Keywords", "CLR volumn or year"],
'Single Justice Judgments': ["Keywords, case number, Justices, year or Citation"], #["Keywords or case number", "Justices or year", "Citation"],
'Unreported Judgments': ["Keywords, case number, Justices, year or Citation"], #["Keywords or case number", "Justices or year", "Citation"],    
}


# %% [markdown]
# ## Search engine

# %%
class hca_search_tool:

    def __init__(self, 
                 collection = hca_collections[0],
                 method = hca_search_methods_dict[hca_collections[0]][0],
                 keywords = '',
                 case_number = '', 
                 judge = None,
                 clr = None,                 
                 year = None,
                citation = '',
                judgment_counter_bound = default_judgment_counter_bound
                ):

        #Initialise parameters
        self.collection = collection
        self.method = method
        self.keywords = keywords
        self.case_number = case_number
        self.judge = judge
        self.clr = clr
        self.year = year
        self.citation = citation

        self.judgment_counter_bound = judgment_counter_bound
        
        self.page = 1
        
        self.results_count = 0

        self.total_pages = 1
        
        self.results_url = ''

        self.results_url_to_show = ''
        
        self.soup = None
        
        self.case_infos = []

        #For getting judgment directly from HCA database if can't get from OALC
        self.case_infos_direct = []

    #Function for getting search results
    def search(self):

        #Reset infos of cases found
        self.case_infos = []
        
        params_raw = []
        
        base_url = f'https://www.hcourt.gov.au/cases-and-judgments/judgments/{hca_collections_dict[self.collection]}?'

        #Url for selenium to start

        self.results_url = base_url
        
        #Before entering year, justice or CLR, must enter keywords or case number first, then load

        browser = get_driver()
        
        browser.get(self.results_url)

        if len(self.keywords) > 0:
            
            keywords_input = Wait(browser,  20).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="edit-keywords--2"]')))
            keywords_input.send_keys(self.keywords)

            params_raw.append(('keywords', self.keywords))

        if len(self.case_number) > 0:

            case_number_input = Wait(browser,  20).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="edit-case-number--2"]')))
            keywords_input.send_keys(self.case_number)

            params_raw.append(('case_number', self.case_number))
        
        elif (len(self.case_number) == 0) and (len(self.citation) > 0):

            print(f"Trying to infer case_number from self.citation == {self.citation}")
            
            hca_case_number = hca_df[hca_df['mnc'].isin([self.citation])]
            
            if len(hca_case_number) > 0:

                hca_case_number.reset_index(inplace = True)

                case_number = hca_case_number.loc[0, 'case_number']
                
                if isinstance(case_number, str):
    
                    if len(case_number) > 0:

                        for puncutation in [' ', ',', ';']:

                            if puncutation in case_number:

                                case_number = case_number.split(puncutation)[0]

                        print(f"Inferred case_number == {case_number} from self.citation == {self.citation}")

            case_number_input = Wait(browser,  20).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="edit-case-number--2"]')))
            keywords_input.send_keys(case_number)

            params_raw.append(('case_number', case_number))

        #Select 100 results per page
        items_per_page_menu = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'edit-items-per-page--2')))
        items_per_page_menu_input = Select(items_per_page_menu)
        
        items_per_page_menu_input.select_by_value('100')

        #Click apply button and load
        apply_button = Wait(browser, 20).until(EC.visibility_of_element_located((By.ID, 'edit-submit-judgments--2')))
        apply_button.click()

        #Wait until any search results present       
        loaded = Wait(browser, 15).until(EC.presence_of_element_located((By.XPATH, "//div[@class='views-element-container']")))
        
        #Update results_url
        params = urllib.parse.urlencode(params_raw, quote_via=urllib.parse.quote)
        self.results_url = base_url + '&' + params + '&items_per_page=100'
        
        #Enter year, justice or CLR if selected
        selection_counter = 0

        for selection in [self.judge, self.year, self.clr]:

            if (not pd.isna(selection)) and (not selection == None) and (not str(selection) == 'None'):

                if isinstance(selection, float) or isinstance(selection, int) or isinstance(selection, int):

                    selection = str(int(selection))

                if isinstance(selection, str):

                    if len(selection) > 0:

                        #If year
                        if re.search(r'\d{4}', selection):
        
                            selection = f"d:{selection}"

                        #If CLR volumn
                        elif re.search(r'\d+', selection):
        
                            selection = f"volume:{selection}"

                        #If judge
                        else:
                            selection = all_judges_dict[selection]
                            
                        params_raw.append((f'f[{selection_counter}]', selection))

                        selection_counter += 1

                        #Update self.results_url then reload selenium
                        params = urllib.parse.urlencode(params_raw, quote_via=urllib.parse.quote)
                
                        self.results_url = base_url + '&' + params + '&items_per_page=100'
        
                        #Pause to avoid getting kicked out
                        pause.seconds(np.random.randint(10, 15))

                        print(f"Given '{selection}' entered, loading {self.results_url} ")
                        
                        browser.get(self.results_url)

                        #Wait until any search results present
                        loaded = Wait(browser, 15).until(EC.presence_of_element_located((By.XPATH, "//div[@class='views-element-container']")))

        print(f"Loaded search results from self.results_url == {self.results_url}")
                
        self.soup = BeautifulSoup(browser.page_source, "lxml")

        #Get results count
        if 'displaying' in self.soup.text.lower():
            
            results_count_raw = self.soup.find('div', class_ = 'view-summary')
            
            if re.search(r'\d+', results_count_raw.text):
                
                self.results_count = int(re.findall(r'\d+', results_count_raw.text)[-1])
        
        else:
            
            self.results_count = 0

        #Get page count
        self.total_pages = math.ceil(self.results_count/100)

        print(f"Found {self.results_count} results on {self.total_pages} pages")
        
        if self.results_count > 0:

            for page in range(0, self.total_pages):

                if len(self.case_infos) < min(self.results_count, self.judgment_counter_bound):
                    #Update self.soup from new page if necessary
                    if page > 0:
    
                        #Pause to avoid getting kicked out
                        pause.seconds(np.random.randint(10, 15))

                        next_page_url = self.results_url + f"&page={page}"

                        browser = get_driver()
                        browser.get(self.next_page_url)
                        #browser.delete_all_cookies() #Don't
                        #browser.refresh() #Don't

                        #Wait until search results present, if any
                        loaded = Wait(browser, 15).until(EC.presence_of_element_located((By.XPATH, "//div[@class='views-element-container']")))

                        self.soup = BeautifulSoup(browser.page_source, "lxml")

                        browser.quit()
        
                    print(f"Getting results from page {page} (0 denotes first page)")
                    
                    results = self.soup.find_all('div', class_ = 'views-row')

                    for result in results:

                        if len(self.case_infos) < min(self.results_count, self.judgment_counter_bound):

                            case_info = {'Case name': '',
                                         'Hyperlink to High Court Judgments Database': '',
                                         'Medium neutral citation': '',
                                          'Reported': '',
                                          'Case number': '',
                                         'Before': '',
                                         'Date': '', 
                                        }

                            try:
                                link = 'https://www.hcourt.gov.au' + result.find('a', class_ = 'views-row-item views-row-item-judgement')['href']
                                case_info['Hyperlink to High Court Judgments Database'] = link
                            except:
                                print(f"Can't get link")

                            try:
                                case_name = result.find('div', class_ = 'field field--title text-bold').get_text(strip = True)
                                case_info['Case name'] = case_name
                            except:
                                print(f"{case_info['Hyperlink to High Court Judgments Database']}: can't get case_name")

                            try:

                                reported_list = []
                                
                                citations = result.find_all('div', class_ = 'field field--citation')

                                for citation in citations:

                                    citation = citation.get_text(strip = True)
                                    
                                    if ':' in citation:
                                    
                                        citation = citation.split(':')[-1]

                                    #print(citation)

                                    if re.search(r'\[\d{4}\]', citation):
                                        
                                        case_info['Medium neutral citation'] = citation

                                    else:

                                        reported_list.append(citation)

                                case_info['Reported'] = '; '.join(reported_list)
                            
                            except:
                                
                                print(f"{case_info['Case name']}: can't get citation")

                            try:

                                #before = ''
                                
                                if 'field field--name-field-hca-justices field--type-string field--label-above field__item' in str(result):
                                
                                    before = result.find('div', class_ = 'field field--name-field-hca-justices field--type-string field--label-above field__item').get_text(strip = True)
                                
                                elif 'field field--legacy-before' in str(result):

                                    before = result.find('div', class_ = 'field field--legacy-before').get_text(strip = True)

                                if ':' in before:
                                
                                    before = before.split(':')[-1]

                                case_info['Before'] = before
                                
                            except:
                                
                                print(f"{case_info['Case name']}: can't get before")

                            try:
                                
                                date = result.find('div', class_ = 'field field--hca-date-issued').get_text(strip = True)
                                
                                if ':' in date:
                                
                                    date = date.split(':')[-1]

                                case_info['Date'] = date

                            except:
                                
                                print(f"{case_info['Case name']}: can't get date")

                            try:
                                case_number = result.find('div', class_ = 'field field--hca-matter-number').get_text(strip = True)
                                
                                if ':' in case_number:
                                
                                    case_number = case_number.split(':')[-1]

                                case_info['Case number'] = case_number

                            except:
                                
                                print(f"{case_info['Case name']}: can't get case_number")

                            self.case_infos.append(case_info)

                        else:
                            #Got enough results, break results per page loop
                            break

                else:
                    #Got enough results, break out of page loop
                    break

        browser.quit()

    #Function for attaching judgment text to case_info dict
    def attach_judgment(self, case_info):

        catchwords = ''
        
        judgment_text = ''
        
        judgment_url = case_info['Hyperlink to High Court Judgments Database']

        browser = get_driver()
    
        browser.get(judgment_url)
        #browser.delete_all_cookies() #Don't
        #browser.refresh() #Don't
        
        #Wait until pdf link present
        pdf_link_present = Wait(browser, 15).until(EC.presence_of_element_located((By.XPATH, "//span[@class='file file--mime-application-pdf file--application-pdf']")))

        result_soup = BeautifulSoup(browser.page_source, "lxml")
        
        #Get catchwords

        if 'text-content clearfix field field--name-field-hca-catchwords field--type-text-long field--label-above' in str(result_soup):
            
            try:
                catchwords = result_soup.find('div', class_ = 'text-content clearfix field field--name-field-hca-catchwords field--type-text-long field--label-above')
                catchwords = catchwords.text
    
            except Exception as e:
                
                print(f"{case_info['Case name']}: Can't get catchwords due to error: {e}")

        #Get judgment text
        
        try:

            #Stat downloading judgment pdf
            pdf_link_present.click()
                
            #Get path to most recent downloaded file
            
            pdf_link = result_soup.find('span', class_ = 'file file--mime-application-pdf file--application-pdf')
        
            pdf_link = 'https://www.hcourt.gov.au' + pdf_link.find('a', href=True)['href']

            pdf_file = pdf_link.split('/')[-1]    

            pdf_file = urllib.parse.unquote(pdf_file)
            
            pdf_path = f"{download_dir}/{pdf_file}"

            #Limiting waiting time for downloading PDF to 1 min
            
            waiting_counter = 0
            
            while ((not os.path.exists(pdf_path)) and (waiting_counter < 10)):
                pause.seconds(5)
                waiting_counter += 1
                            
            print(f"{case_info['Case name']}: Trying to OCR pdf from pdf_path == {pdf_path}")

            if ('2000' in self.collection) or ('Single' in self.collection):

                judgment_text = pdf_judgment(url_or_path = pdf_path, url_given = False)
                                                                
            else:
                
                judgment_text = pdf_image_judgment(url_or_path = pdf_path, url_given = False)

            #MUST remove pdf from download folder automatically or manually
            os.remove(pdf_path)
            
        except Exception as e:
            
            print(f"{case_info['Case name']}: Can't get judgment_text due to error: {e}")

        case_info.update({'Catchwords': catchwords})
        case_info.update({'judgment': judgment_text})
        
        browser.quit()
        
        return case_info
    
    #Function for getting all requested judgments
    def get_judgments(self):

        self.case_infos_w_judgments = []

        #Search if not done yet
        if len(self.case_infos) == 0:

            self.search()

        #If huggingface enabled
        if huggingface == True:

            #Load oalc
            from functions.oalc_functions import load_corpus, get_judgment_from_oalc
    
            #Create a list of mncs for HuggingFace:
            mnc_list = []
    
            for case_info in self.case_infos:
    
                #Add mnc to list for HuggingFace
                mnc_list.append(case_info['Medium neutral citation'])
    
            #Get judgments from oalc first
            mnc_judgment_dict = get_judgment_from_oalc(mnc_list)
        
            #Append OALC judgment 
            for case_info in self.case_infos:
                
                #Append judgments from oalc first
                if case_info['Medium neutral citation'] in mnc_judgment_dict.keys():
                    
                    case_info.update({'judgment': mnc_judgment_dict[case_info['Medium neutral citation']]})

                    #Make link clickable
                    judgment_url = case_info['Hyperlink to High Court Judgments Database']
                    case_info.update({'Hyperlink to High Court Judgments Database': link(judgment_url)})

                    #Add case_info to self.case_infos_w_judgments
                    self.case_infos_w_judgments.append(case_info)
    
                    print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from OALC")
    
                else:
                    
                    #To get from HCA database directly if can't get from OALC
                    self.case_infos_direct.append(case_info)

            print(f"Scrapped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments from OALC")

        else:
            
            #If huggingface not enabled
            self.case_infos_direct = copy.deepcopy(self.case_infos)
        
        #Get judgments from HCA database directly
        for case_info in self.case_infos_direct:

            #Pause to avoid getting kicked out
            pause.seconds(np.random.randint(10, 15))

            case_info = self.attach_judgment(case_info)

            #Make link clickable
            judgment_url = case_info['Hyperlink to High Court Judgments Database']
            case_info.update({'Hyperlink to High Court Judgments Database': link(judgment_url)})

            #Add case_info to self.case_infos_w_judgments

            self.case_infos_w_judgments.append(case_info)
            
            print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from HCA directly")
            
            print(f"Scrapped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments")



# %%
def hca_search_preview(df_master):
    
    df_master = df_master.fillna('')

    #Conduct search

    hca_search = hca_search_tool(collection = df_master.loc[0, 'Collection'], 
                                 method = df_master.loc[0, 'Search method'], 
                   keywords = df_master.loc[0, 'Keyword search'],
                    case_number = df_master.loc[0, 'Case number'], 
                    judge = df_master.loc[0, 'Justices'],
                    clr = df_master.loc[0, 'Filter by CLR volume'],
                    year = df_master.loc[0, 'Year'],    
                    citation = df_master.loc[0, 'Medium neutral citation'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )

    hca_search.search()
    
    results_count = hca_search.results_count
    
    case_infos = hca_search.case_infos

    results_url = hca_search.results_url

    #st.write(results_url)
    
    return {'results_url': results_url, 'results_count': results_count, 'case_infos': case_infos}


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json, gpt_batch_input
#Import variables
from functions.gpt_functions import basic_model, flagship_model#, role_content


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction
#hca_role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from specific paragraphs, pages or sections, provide the paragraph or page numbers or section names as part of your answer. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". '

#system_instruction = role_content #hca_role_content

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#For getting judgments directly from the High Court if not available in OALC

@st.cache_data(show_spinner = False, ttl=600)
def hca_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    hca_search = hca_search_tool(collection = df_master.loc[0, 'Collection'], 
                                 method = df_master.loc[0, 'Search method'], 
                   keywords = df_master.loc[0, 'Keyword search'],
                    case_number = df_master.loc[0, 'Case number'], 
                    judge = df_master.loc[0, 'Justices'],
                    clr = df_master.loc[0, 'Filter by CLR volume'],
                    year = df_master.loc[0, 'Year'],    
                    citation = df_master.loc[0, 'Medium neutral citation'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )

    hca_search.get_judgments()
    
    for judgment_json in hca_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in hca_metalabels_droppable:
            try:
                df_individual.pop(meta_label)
            except Exception as e:
                print(f'{meta_label} not popped.')
                print(e)

    #Need to convert date column to string

    if 'Date' in df_individual.columns:

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


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def hca_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []

    #Conduct search
    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    hca_search = hca_search_tool(collection = df_master.loc[0, 'Collection'], 
                                 method = df_master.loc[0, 'Search method'], 
                   keywords = df_master.loc[0, 'Keyword search'],
                    case_number = df_master.loc[0, 'Case number'], 
                    judge = df_master.loc[0, 'Justices'],
                    clr = df_master.loc[0, 'Filter by CLR volume'],
                    year = df_master.loc[0, 'Year'],    
                    citation = df_master.loc[0, 'Medium neutral citation'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )

    hca_search.get_judgments()
    
    for judgment_json in hca_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in hca_metalabels_droppable:
            try:
                df_individual.pop(meta_label)
            except Exception as e:
                print(f'{meta_label} not popped.')
                print(e)

    #Need to convert date column to string

    if 'Date' in df_individual.columns:

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

    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)
    
    return batch_record_df_individual


# %%
