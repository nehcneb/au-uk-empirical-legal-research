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
#import pypdf
import io
from io import BytesIO
import ast
import math
import mammoth

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

#Conversion to text
#import fitz
#from io import StringIO
#from io import BytesIO
#import mammoth
#from doc2docx import convert

# %%
#Import functions
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input, date_parser, pdf_judgment, docx_judgment, str_to_int
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # HK search engine

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

# %% [markdown]
# ## Definitions

# %%
#Number of times to click away alerts
alert_bound = 5

# %%
hk_sortby_dict = {'Relevance': '1', 'Date': '0', 'Title': '2'}

# %%
hk_sortby_keys = [*hk_sortby_dict.keys()]
hk_sortby_values = [*hk_sortby_dict.values()]

# %%
#1 means True, 0 means False
#hk_stemming_dict = {1: '1', 0: ''}
#hk_stemming_keys = [*hk_stemming_dict.keys()]
#hk_stemming_values = [*hk_stemming_dict.values()]

# %%
hk_courts_dict = {'Court of Final Appeal': 'FA',
 'Court of Appeal': 'CA',
 'Court of First Instance': 'HC',
 'Competition Tribunal': 'CT',
 'District Court': 'DC',
 'Family Court': 'FC',
 'Lands Tribunal': 'LD',
 'Other Court Levels': 'OT'}

# %%
hk_courts_keys = [*hk_courts_dict.keys()]
hk_courts_values = [*hk_courts_dict.values()]

# %%
hk_appeals_from_ca = {'Application for Review': 'AR',
"Attorney General's Reference": 'AG',
'Civil Appeal': 'CV',
'Criminal Appeal': 'CC',
'Miscellaneous Proceedings': 'MP',
'Reservation of Question of Law': 'QL',
"Secretary for Justice's Reference": 'SJ'
}

# %%
hk_appeals_from_hc = {'Admiralty Action': 'AJ',
'Adoption Application': 'AD',
'Application for Grant': 'AG',
'Application to set aside a Statutory Demand (under Bankruptcy Ordinance)': 'SD',
'Applications under the Mental Health Ordinance': 'MH',
'Bankruptcy Proceedings': 'B',
'Bill of Sale Registration': 'BS',
'Bookdebt Registration': 'BD',
'Caveat': 'CA',
'Citation Application': 'CI',
'Civil Action': 'A',
'Commercial Action': 'CL',
'Companies Winding-up Proceedings': 'CW',
'Confidential Miscellaneous Proceedings': 'CM',
'Constitutional and Administrative Law Proceedings': 'AL',
'Construction and Arbitration Proceedings': 'CT',
'Criminal Case': 'CC',
'Estate Duty Appeal': 'ED',
'Ex-parte Application': 'EA',
'High Court Bankruptcy Interim Order': 'BI',
'Inland Revenue Appeal': 'IA',
'Intellectual Property Case': 'IP',
'Intended Action': 'ZZ',
'Labour Tribunal Appeal': 'LA',
'Legal Aid Appeal': 'AA',
'Magistracy Appeal': 'MA',
'Matrimonial Causes': 'MC',
'Minor Employment Claims Appeal': 'ME',
'Miscellaneous Proceedings': 'MP',
'Miscellaneous Proceedings (Criminal)': 'CP',
'Obscene Articles Tribunal Appeal': 'OA',
'Personal Injuries Action': 'PI',
'Probate Action': 'AP',
'Reciprocal Enforcement Case': 'RE',
'Referral Case': 'RC',
'Small Claims Tribunal Appeal': 'SA',
'Stop Notice': 'SN',
'Trade Unions Appeal': 'UA'
}

# %%
hk_appeals_from_dc = {'Civil Action': 'CJ',
'Criminal Case': 'CC',
'Distraint Case': 'DT',
'District Court Tax Claim': 'TC',
"Employee's Compensation Case": 'EC',
'Equal Opportunities Action': 'EO',
'Intended Action': 'ZZ',
'Miscellaneous Appeals': 'MA',
'Miscellaneous Proceedings': 'MP',
'Occupational Deafness (Compensation) Appeal': 'OA',
'Personal Injuries Action': 'PI',
'Pneumoconiosis (Compensation) Appeal': 'PA',
'Stamp Duty Appeal': 'SA',
'Stop Notice': 'SN'
}

# %%
hk_appeals_from_fc = {'Joint application': 'JA',
'Matrimonial Causes': 'MC',
'Miscellaneous Proceedings': 'MP',
'Reciprocal Enforcement Proceedings': 'RE'
}

# %%
hk_databases_dict = {'Judgments': 'JU',
'Reasons for Verdict': 'RV',
'Reasons for Sentence': 'RS',
'Practice Directions': 'PD'
}

# %%
hk_databases_keys = [*hk_databases_dict.keys()]
hk_databases_values = [*hk_databases_dict.values()]

# %%
hc_appeal_dict = {'Court of Appeal': hk_appeals_from_ca,
'Court of First Instance': hk_appeals_from_hc,
'District Court': hk_appeals_from_dc,
'Family Court': hk_appeals_from_fc
}


# %%
#Function for changing selection menu for type on Streamlit

def dict_value_or_none(some_dict, some_key):

    if (some_key in [None, '']) or (not isinstance(some_dict, dict)):

        return None
    
    elif some_key not in some_dict.keys():
        
        return None
    
    else:

        return_value = some_dict[some_key]

        if isinstance(return_value, dict):
            
            return_value = [*return_value.keys()]
        
        return return_value
    


# %%
#Function for turning month or year choice to number or empty string

def month_year_to_str(x):

    if not re.search(r'\d+', str(x)):

        return ''

    else:
        
        return re.findall(r'\d+', str(x))[0]



# %% [markdown]
# ## Search engine

# %%
from functions.common_functions import link


# %%
class hk_search_tool:

    def __init__(self, 
                any_of_these_words = '', 
                these_words_in_any_order = '', 
                this_phrase = '', 
                stemming = True, 
                date_of_judgment = None,
                coram = '',
                parties = '', 
                representation = '', 
                offence = '',
                court_levels_filter = hk_courts_keys, 
                on_appeal_from_court = '',
                on_appeal_from_type = '', 
                medium_neutral_citation = '', 
                case_number = '', 
                reported_citation = '', 
                databases = hk_databases_keys, 
                sortby = hk_sortby_keys[0],
                judgment_counter_bound = default_judgment_counter_bound
                ):

        #Initialise parameters
        self.any_of_these_words = any_of_these_words 
        self.these_words_in_any_order = these_words_in_any_order
        self.this_phrase = this_phrase 
        self.stemming = stemming 
        self.date_of_judgment = date_of_judgment 
        self.coram = coram
        self.parties = parties 
        self.representation = representation 
        self.offence = offence
        self.court_levels_filter = court_levels_filter
        self.on_appeal_from_court = on_appeal_from_court
        self.on_appeal_from_type = on_appeal_from_type 
        self.medium_neutral_citation = medium_neutral_citation 
        self.case_number = case_number 
        self.reported_citation = reported_citation 
        self.databases = databases
        self.sortby = sortby
        
        self.judgment_counter_bound = judgment_counter_bound

        self.params = []
        
        self.page = 1
        
        self.results_count = 0

        self.total_pages = 1
        
        self.results_url = ''
        
        self.soup = None
        
        self.case_infos = []
    
    #Function for getting search results
    def search(self):

        #Reset infos of cases found
        self.case_infos = []
        
        params_raw = []

        params_raw.append(('txtselectopt', '1'))

        params_raw.append(('txtSearch', self.any_of_these_words))

        params_raw.append(('txtselectopt1', '2'))

        params_raw.append(('txtSearch1', self.these_words_in_any_order))

        params_raw.append(('txtselectopt2', '3'))
        
        params_raw.append(('txtSearch2', self.this_phrase))

        #stemming_param = int(float(self.stemming))

        stemming_param = str_to_int(self.stemming)

        if stemming_param == 1:

            params_raw.append(('stem', stemming_param))

        params_raw.append(('txtselectopt3', '5'))

        #st.write(f"self.date_of_judgment == {self.date_of_judgment}")

        date_entered = None

        if isinstance(self.date_of_judgment, datetime):

            date_entered = self.date_of_judgment
        
        elif self.date_of_judgment != [None, '']:
            
            date_entered = date_parser(self.date_of_judgment)

        #st.write(f"date_entered == {date_entered}")

        if isinstance(date_entered, datetime):

            day = date_entered.day
            month = date_entered.month
            year = date_entered.year
                            
            params_raw.append(('txtSearch3', f'{day}/{month}/{year}'))

        else:

            day = '0'
            month = '0'
            year = '0' 

            #Enter incomplete date if given
            date_list = self.date_of_judgment.split('/')

            if len(date_list) == 3:
            
                if len(date_list[0]) > 0:
                    day = date_list[0]
            
                if len(date_list[1]) > 0:
                    month = date_list[1]
            
                if len(date_list[2]) > 0:
                    year = date_list[2]

            txtSearch3_param = ''

            for info in [day, month, year]:

                if info != '0':

                    txtSearch3_param += f'{info}/'

                else:
                    
                    txtSearch3_param += f'/'

            
            if txtSearch3_param == '///':

                txtSearch3_param = ''
            
            params_raw.append(('txtSearch3', f'{txtSearch3_param}'))

        #st.write(f"day == {day}, month = {month}, year = {year}")
        
        params_raw.append(('day1', day))

        params_raw.append(('month', month))

        params_raw.append(('year', year))

        params_raw.append(('txtselectopt4', '6'))

        params_raw.append(('txtSearch4', self.coram))

        params_raw.append(('txtselectopt5', '7'))

        params_raw.append(('txtSearch5', self.parties))

        params_raw.append(('txtselectopt6', '8'))
        
        params_raw.append(('txtSearch6', self.representation))

        params_raw.append(('txtselectopt7', '9'))
        
        params_raw.append(('txtSearch7', self.offence))

        if self.court_levels_filter != [None, '']:
            
            if isinstance(self.court_levels_filter, str):
                
                self.court_levels_filter = ast.literal_eval(self.court_levels_filter)
    
            if len(self.court_levels_filter) == 0:
    
                params_raw.append(('selSchct', hk_courts_values[0]))
    
            else:
    
                if len(self.court_levels_filter) == len(hk_courts_keys):
    
                    params_raw.append(('selallct', '1'))
                
                for court in self.court_levels_filter:
                    
                    params_raw.append(('selSchct', hk_courts_dict[court]))
        
        else:
            params_raw.append(('selSchct', hk_courts_values[0]))

        try:# self.on_appeal_from_court != [None, '']:
        
            params_raw.append(('selcourtname', hk_courts_dict[self.on_appeal_from_court]))

        except Exception as e:

            print("on_appeal_from_court not entered.")
            
            params_raw.append(('selcourtname', ''))

        #st.write(f"self.on_appeal_from_court == {self.on_appeal_from_court}")

        #st.write(f"self.on_appeal_from_type == {self.on_appeal_from_type}")
        
        #if (self.on_appeal_from_type != [None, '']) and (self.on_appeal_from_court != [None, '']):
        try:
            
            params_raw.append(('selcourtype', hc_appeal_dict[self.on_appeal_from_court][self.on_appeal_from_type]))
        
        except Exception as e:

            print("on_appeal_from_type not entered.")
            
            params_raw.append(('selcourtype', ''))
    
        params_raw.append(('txtselectopt8', '10'))

        params_raw.append(('txtSearch8', self.medium_neutral_citation))

        params_raw.append(('txtselectopt9', '4'))

        params_raw.append(('txtSearch9', self.case_number))

        params_raw.append(('txtselectopt10', '12'))
        
        params_raw.append(('txtSearch10', self.reported_citation))

        if self.databases != [None, '']:

            if isinstance(self.databases, str):
                
                self.databases = ast.literal_eval(self.databases)
    
            if len(self.databases) == 0:
    
                params_raw.append(('selDatabase2', hk_databases_values[0]))
    
            else:
    
                if len(self.databases) == len(hk_databases_keys):
    
                    params_raw.append(('selall2', '1'))
                
                for database in self.databases:
                    
                    params_raw.append(('selDatabase2', hk_databases_dict[database]))
        
        else:
            params_raw.append(('selDatabase2', hk_databases_values[0]))

        params_raw.append(('order', hk_sortby_dict[self.sortby]))        

        params_raw.append(('SHC', ''))        

        params_raw.append(('page', self.page))        
        
        #Save params
        params = urllib.parse.urlencode(params_raw, quote_via=urllib.parse.quote)
        
        self.params = params

        #API url
        search_form = 'https://legalref.judiciary.hk/lrs/common/search/search_result_form.jsp?isadvsearch=1'

        #Get results page
        response = requests.get(search_form, params=self.params, headers= {'User-Agent': 'whatever'}, allow_redirects=True)

        #Update return values
        self.results_url = response.url

        #self.results_url = search_form + urllib.parse.urlencode(params)
        
        #Try to get search results a few times

        try_counter = 0
        try_success = False

        while (try_counter < 3) and (not try_success):

            try_counter += 1
            
            try:
                
                browser.get(self.results_url)
                #browser.delete_all_cookies()
                browser.refresh()
        
                #self.soup = BeautifulSoup(browser.page_source, "lxml")
                
                results_count_list = Wait(browser, 10).until(EC.presence_of_all_elements_located((By.ID, "searchresult-total")))
                
                self.results_count = int(results_count_list[0].text)
        
                page_count_list = Wait(browser, 10).until(EC.presence_of_all_elements_located((By.ID, "searchresult-totalpages")))
        
                self.total_pages = int(page_count_list[0].text)
                                
                self.soup = BeautifulSoup(browser.page_source, "lxml")
        
                #Get case infos from search results page
                
                case_numbers_list_raw = self.soup.find_all('a', {'class': 'searchfont result-caseno'})
                
                link_mnc_list_raw = self.soup.find_all('div', {'class': 'col-md-6 pl-1'}) #Every second item in this list is redundant

                #st.write(f"link_mnc_list_raw == {link_mnc_list_raw}")
                
                date_list_raw = self.soup.find_all('div', {'class': 'col-md-4 pl-1'})
                
                case_names_list_raw = self.soup.find_all('div', {'class': 'col-md-12 pl-1'})
                
                case_numbers_list = []

                reported_list = []
                
                mnc_list = []
                
                judgment_urls_list = []
                
                date_list = []
                
                case_names_list = []
                
                for case_number_raw in case_numbers_list_raw:
                    case_number = case_number_raw.get_text(strip = True)
                    case_numbers_list.append(case_number)
                
                mnc_counter = 0
                
                for link_mnc_raw in link_mnc_list_raw:

                    if mnc_counter % 2 == 0:
                        
                        #link_mnc_raw = link_mnc_raw.get_text(strip = True) #This doesn't work on Streamlit Cloud
                        
                        link_mnc_raw = str(link_mnc_raw)
                        
                        #st.write(f"link_mnc_raw == {link_mnc_raw}")

                        if re.search(r'\[\d{4}\].+\d+', link_mnc_raw):
                            
                            mnc = re.findall(r'\[\d{4}\].+\d+', link_mnc_raw)[0]
                        
                        else:
                            
                            mnc = ''
                
                        if re.search(r"\'DIS.+\'", link_mnc_raw):
                        
                            judgment_url = re.findall(r"\'DIS.+\'", link_mnc_raw)[0]
                        
                        else:
                            
                            judgment_url = ''
                        
                        judgment_url =  "https://legalref.judiciary.hk/lrs/common/search/search_result_detail_frame.jsp?" + judgment_url.replace("'", "")
                            
                        mnc_list.append(mnc)
                
                        judgment_urls_list.append(judgment_url)
                    
                    mnc_counter += 1
                
                for date_raw in date_list_raw:
                    
                    date = date_raw.get_text(strip = True)
                
                    if ':' in date:
                        date = date.split(':')[-1]
                
                    date = date.replace(' ', '')
                        
                    date_list.append(date)
                
                for case_name_raw in case_names_list_raw:
                    
                    case_name = case_name_raw.get_text(strip = True)

                    reported = ''

                    if 'Reported in' in case_name:
                        
                        case_name_reported = case_name.split('Reported in')

                        case_name = case_name_reported[0]
                        
                        while case_name[-1] in [';', ' ']:
                            case_name = case_name[:-1]

                        reported = case_name_reported[1]

                        while reported[0] in [':', ' ']:
                            reported = reported[1:]
                    
                    case_names_list.append(case_name)

                    reported_list.append(reported)
                    
                for case_name in case_names_list:
        
                    if len(self.case_infos) < self.judgment_counter_bound:
        
                        counter = len(self.case_infos)
        
                        judgment_url = judgment_urls_list[counter]
        
                        mnc = mnc_list[counter]

                        reported = reported_list[counter]
                        
                        case_number = case_numbers_list[counter]
        
                        date = date_list[counter]
                        
                        case_info = {'Case name': case_name,
                                    'Hyperlink to the Hong Kong Legal Reference System': judgment_url, 
                                     'Medium neutral citation': mnc,
                                     'Reported': reported,
                                    'Case number': case_number,
                                    'Date': date
                                    }
        
                        self.case_infos.append(case_info)
        
                #browser.delete_all_cookies()
                #browser.close()

                try_success = True

                #print(f"Got {self.results_count} search results based on page {self.page}.")
                
            except Exception as e:

                print(f"Failed to get search results due to error: {e}")
    
    #Function for attaching judgment text to case_info dict
    def attach_judgment_text_and_urls(self, case_info):

        #Initialise urls for docx, pdf, and Chinese translation and English original, and for judgment text
        docx_url = ''
        pdf_url = ''
        chinese_url = ''
        english_url = ''        
        judgment_text = ''
        alert = ''

        case_number = case_info['Case number']
        
        #Try to get judgment from html first
        try:

            judgment_url = case_info['Hyperlink to the Hong Kong Legal Reference System']

            browser.get(judgment_url)
            
            #Click away potentially multiple alerts
            alert_counter = 1
            while alert_counter <= alert_bound:
                try:
                    Wait(browser, 10).until(EC.alert_is_present())
                    alert += f"{browser.switch_to.alert.text}\n\n"
                    
                    try:
                        browser.switch_to.alert.accept()
                    except:
                        browser.switch_to.alert.dismiss()
                        
                    print(f'{case_number}: clicked away alert {alert_counter}.')

                except TimeoutException:
                    print(f'{case_number}: no more alert.')
                    alert_counter += alert_bound

                except Exception as e:
                    print(f'{case_number}: failed to click away alert {alert_counter} due to error {e}.')

                alert_counter += 1
            
            #Get urls for docx, pdf, and Chinese translation/English original if available
            browser.switch_to.frame("topFrame")
            
            hrefs = browser.find_elements(By.XPATH, "//a[@href]")
            
            top_buttons_dict = {}
            
            for elem in hrefs:
                button_name = elem.text
                button_link = elem.get_attribute('href')
                
                top_buttons_dict.update({button_name.lower(): button_link})
            
            for key in top_buttons_dict.keys():
            
                if 'word' in key:
                    docx_url = top_buttons_dict[key]
            
                if 'pdf' in key:
                    pdf_url = top_buttons_dict[key]

                    pdf_url = re.sub(r'lan\=\w{1,2}\&', '', pdf_url.replace('gotoPdf', 'loadPdf')) + '&mobile=N'
                
                if 'chinese' in key:
                    chinese_url = top_buttons_dict[key]
                    
                if 'english' in key:
                    english_url = top_buttons_dict[key]

            #Redirect to English original if available
            if len(english_url) > 0:
            
                judgment_url = english_url
                
                print(f"{case_number}: redirecting to Englsh original")

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))
                
                browser.get(judgment_url)

                #Click away potentially multiple alerts
                alert_counter = 1
                while alert_counter <= alert_bound:
                    try:
                        Wait(browser, 10).until(EC.alert_is_present())
                        alert += f"{browser.switch_to.alert.text}\n\n"
                        
                        try:
                            browser.switch_to.alert.accept()
                        except:
                            browser.switch_to.alert.dismiss()
                            
                        print(f'{case_number}: clicked away alert {alert_counter}.')

                    except TimeoutException:
                        print(f'{case_number}: no more alert.')
                        alert_counter += alert_bound

                    except Exception as e:
                        print(f'{case_number}: failed to click away alert {alert_counter} due to error {e}.')

                    alert_counter += 1

                #Get urls for docx, pdf, and Chinese translation for the English original
                browser.switch_to.frame("topFrame")
                
                hrefs = browser.find_elements(By.XPATH, "//a[@href]")
                
                english_top_buttons_dict = {}
                
                for elem in hrefs:
                    button_name = elem.text
                    button_link = elem.get_attribute('href')
                    
                    english_top_buttons_dict.update({button_name.lower(): button_link})
                
                for key in top_buttons_dict.keys():
                
                    if 'word' in key:
                        docx_url = english_top_buttons_dict[key]
                
                    if 'pdf' in key:
                        pdf_url = english_top_buttons_dict[key]

                        pdf_url = re.sub(r'lan\=\w{1,2}\&', '', pdf_url.replace('gotoPdf', 'loadPdf')) + '&mobile=N'
                    
                    if 'chinese' in key:
                        chinese_url = english_top_buttons_dict[key]

                browser.switch_to.default_content()
            
            else:
                
                browser.switch_to.default_content()
            
            browser.switch_to.frame("mainFrame")

            judgment_text = BeautifulSoup(browser.page_source, "lxml").get_text()

            print(f"{case_number}: Got judgment from html.")
        
        except Exception as e:
            
            print(f"{case_number}: Failed to get judgment from html.")
        
        #Get judgment text from pdf if necessary
        if len(judgment_text) == 0:
        
            try:
                
                judgment_text = pdf_judgment(pdf_url)
                
                print(f"{case_number}: Got judgment from pdf.")
            
            except Exception as e:

                print(f"{case_number}: Can't get judgment from pdf.")

        #Get judgment text from docx if necessary
        if len(judgment_text) == 0:
        
            try:
                
                judgment_text = docx_judgment(docx_url)
                
                print(f"{case_number}: Got judgment from docx.")
            
            except Exception as e:

                print(f"{case_number}: Can't get judgment from docx.")
        
        #Older method for getting judgment text from pdf or docx by inference from case number

        #if len(judgment_text) == 0:

            #case_number_ds = re.findall(r'\d+', case_number)
            #case_number_numbers = case_number_ds[0]
            #case_number_alphabets = case_number.split(case_number_numbers)[0]
            #case_number_year = case_number_ds[1]
            #case_number_numbers_6_digis = case_number_numbers
            #while len(case_number_numbers_6_digis) < 6:
                #case_number_numbers_6_digis = '0' + case_number_numbers_6_digis
                
            #for language in ['en', 'ch']:

                #for doc_type in ['docx', 'doc']:

                    #pdf_url = f'https://legalref.judiciary.hk/lrs/common/ju/loadPdf.jsp?url=https://legalref.judiciary.hk/doc/judg/word/vetted/other/{language}/{case_number_year}/{case_number_alphabets}{case_number_numbers_6_digis}_{case_number_year}.{doc_type}&mobile=N'

                    #if len(judgment_text) == 0:

                        #pdf_url = f'https://legalref.judiciary.hk/lrs/common/ju/loadPdf.jsp?url=https://legalref.judiciary.hk/doc/judg/word/vetted/other/{language}/{case_number_year}/{case_number_alphabets}{case_number_numbers_6_digis}_{case_number_year}.{doc_type}&mobile=N'
                    
                        #try:
                            
                            #judgment_text = pdf_judgment(pdf_url)
                            
                            #print(f"{case_number}: Got judgment in language == {language} from pdf based on doc_type == {doc_type}.")
                        
                        #except Exception as e:

                            #print(f"{case_number}: Can't get judgment in language == {language} from pdf based on doc_type == {doc_type}.")

            #if len(judgment_text) == 0:
            
                #try:

                    #docx_url = f'https://legalref.judiciary.hk/doc/judg/word/vetted/other/{language}/{case_number_year}/{case_number_alphabets}{case_number_numbers_6_digis}_{case_number_year}.docx'
                    
                    #judgment_text = docx_judgment(docx_url)
                    
                    #print(f"{case_number}: Got judgment in language == {language} from docx.")

                #except Exception as e:
                    
                    #print(f"{case_number}: Can't get judgment from pdf or docx.")

        #Create updated case_info dict with judgment text and links to Chinese translation, English original
        case_info_w_judgment = {'Case name': case_info['Case name'],
                                'Hyperlink to the Hong Kong Legal Reference System': case_info['Hyperlink to the Hong Kong Legal Reference System'],
                                'Hyperlink to Chinese translation (if any)': chinese_url,
                                'Hyperlink to English original (if any)': english_url, 
                                 'Medium neutral citation': case_info['Medium neutral citation'],
                                 'Reported': case_info['Reported'],
                                'Case number': case_info['Case number'],
                                'Date': case_info['Date'], 
                                'Alert': alert,
                                'judgment': judgment_text
                                }

        #Get appendices (eg corrigendum) if any
        
        browser.switch_to.default_content()
        
        browser.switch_to.frame("bottomFrame")
        
        hrefs = browser.find_elements(By.XPATH, "//a[@href]")
        
        appendices_dict = {}
        
        bottom_buttons_dict = {}
        
        for elem in hrefs:
            button_name = elem.text
            button_link = elem.get_attribute('href')
        
            if 'javascript' not in button_link:
            
                bottom_buttons_dict.update({button_name.lower(): button_link})
        
        for key in bottom_buttons_dict.keys():
        
            try:
                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))
                
                app_url = bottom_buttons_dict[key]
                browser.get(app_url)
                
                browser.switch_to.frame("mainFrame")

                app_text = str(BeautifulSoup(browser.page_source, "lxml"))
                
                #Enable to get text instead of all html
                #app_text = BeautifulSoup(browser.page_source, "lxml").get_text()
                
                print(f"{case_number}: Got appendix {key} from html.")
        
                appendices_dict.update({f'{key}': app_text})
            except:
                print(f"{case_number}: Can't get appendix {key} from html.")

        #Append any appendices to case_info_w_judgment
        if len(appendices_dict) > 0:
            for app_key in appendices_dict.keys():
                app_text = appendices_dict[app_key]
                case_info_w_judgment.update({f'appendix to judgment: {app_key}': app_text})

        #Make links clickable
        for key in case_info_w_judgment:
            if 'Hyperlink' in key:
                case_info_w_judgment[key] = link(case_info_w_judgment[key])
                break

        #case_info_w_judgment['Hyperlink to the Hong Kong Legal Reference System'] = link(case_info['Hyperlink to the Hong Kong Legal Reference System'])
        
        return case_info_w_judgment
        
    #Function for getting all requested judgments
    def get_judgments(self):

        self.case_infos_w_judgments = []

        #Search if not done yet
        if len(self.case_infos) == 0:

            self.search()
        
        #Get judgments from cases shown on the initial page (page 1)
        for case_info in self.case_infos:
            
            if len(self.case_infos_w_judgments) < self.judgment_counter_bound:

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))

                #Attach judgment text and urls to case_info dict
                case_info_w_judgment = self.attach_judgment_text_and_urls(case_info)
        
                self.case_infos_w_judgments.append(case_info_w_judgment)
                
                print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments.")

        #Scrape the next page if necessary and available
        while (len(self.case_infos_w_judgments) < min(self.results_count, self.judgment_counter_bound)) and (self.page < self.total_pages):
            
            self.page += 1

            #Pause to avoid getting kicked out
            pause.seconds(np.random.randint(5, 10))
        
            #Get cases on subsequent page
            self.search()

            #Get judgments from cases shown on the initial page (page 1)
            for case_info in self.case_infos:
                
                if len(self.case_infos_w_judgments) < self.judgment_counter_bound:
    
                    #Pause to avoid getting kicked out
                    pause.seconds(np.random.randint(5, 10))

                    #Attach judgment text and urls to case_info dict
                    case_info_w_judgment = self.attach_judgment_text_and_urls(case_info)

                    self.case_infos_w_judgments.append(case_info_w_judgment)
                    
                    print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments.")
    
        #browser.delete_all_cookies()
        #browser.close()


# %%
#@st.cache_data(show_spinner = False, ttl=600)
def hk_search_function(
                    any_of_these_words, 
                    these_words_in_any_order, 
                    this_phrase, 
                    stemming, 
                    date_of_judgment,
                    coram,
                    parties, 
                    representation, 
                    offence,
                    court_levels_filter, 
                    on_appeal_from_court,
                    on_appeal_from_type, 
                    medium_neutral_citation, 
                    case_number, 
                    reported_citation, 
                    databases, 
                    sortby,
                    judgment_counter_bound,
                ):

    #Conduct search

    hk_search = hk_search_tool(
                    any_of_these_words = any_of_these_words, 
                    these_words_in_any_order = these_words_in_any_order, 
                    this_phrase = this_phrase, 
                    stemming = stemming, 
                    date_of_judgment = date_of_judgment,
                    coram = coram,
                    parties = parties, 
                    representation = representation, 
                    offence = offence,
                    court_levels_filter = court_levels_filter, 
                    on_appeal_from_court = on_appeal_from_court,
                    on_appeal_from_type = on_appeal_from_type, 
                    medium_neutral_citation = medium_neutral_citation, 
                    case_number = case_number, 
                    reported_citation = reported_citation, 
                    databases = databases, 
                    sortby = sortby,
                    judgment_counter_bound = judgment_counter_bound,
                )
        
    hk_search.search()
    
    return hk_search
    


# %%
def hk_search_preview(df_master):
    
    df_master = df_master.fillna('')
            
    #Conduct search

    hk_search = hk_search_tool(
                    any_of_these_words = df_master.loc[0, 'Any of these words'], 
                    these_words_in_any_order = df_master.loc[0, 'These words in any order'], 
                    this_phrase = df_master.loc[0, 'This phrase'], 
                    stemming = df_master.loc[0, 'Stemming'], 
                    date_of_judgment = df_master.loc[0, 'Date of judgment'],
                    coram = df_master.loc[0, 'Coram'],
                    parties = df_master.loc[0, 'Parties'], 
                    representation = df_master.loc[0, 'Representation'], 
                    offence = df_master.loc[0, 'Offence'],
                    court_levels_filter = df_master.loc[0, 'Court level(s) filter'], 
                    on_appeal_from_court = df_master.loc[0, 'On appeal from (court)'],
                    on_appeal_from_type = df_master.loc[0, 'On appeal from (type)'], 
                    medium_neutral_citation = df_master.loc[0, 'Medium neutral citation'], 
                    case_number = df_master.loc[0, 'Case number'], 
                    reported_citation = df_master.loc[0, 'Reported citation'], 
                    databases = df_master.loc[0, 'Database(s)'], 
                    sortby = df_master.loc[0, 'Sort by'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']),
                )


    hk_search.search()
    
    results_count = hk_search.results_count
    case_infos = hk_search.case_infos

    results_url = hk_search.results_url

    #st.write(results_url)
    
    return {'results_url': results_url, 'results_count': results_count, 'case_infos': case_infos}

# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import basic_model, flagship_model
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction

role_content_hk = """You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. 
Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a part of the judgment or metadata, include a page or paragraph reference to that part of the judgment or metadata. 
If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". 
The "judgment" field of the JSON given to you is in English or Chinese or both. Please answer questions based on either or both languages. 
"""

#Respond in JSON form. In your response, produce as many keys as you need. 

#system_instruction = role_content_hk

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def hk_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
        
    hk_search = hk_search_function(
                    any_of_these_words = df_master.loc[0, 'Any of these words'], 
                    these_words_in_any_order = df_master.loc[0, 'These words in any order'], 
                    this_phrase = df_master.loc[0, 'This phrase'], 
                    stemming = df_master.loc[0, 'Stemming'], 
                    date_of_judgment = df_master.loc[0, 'Date of judgment'],
                    coram = df_master.loc[0, 'Coram'],
                    parties = df_master.loc[0, 'Parties'], 
                    representation = df_master.loc[0, 'Representation'], 
                    offence = df_master.loc[0, 'Offence'],
                    court_levels_filter = df_master.loc[0, 'Court level(s) filter'], 
                    on_appeal_from_court = df_master.loc[0, 'On appeal from (court)'],
                    on_appeal_from_type = df_master.loc[0, 'On appeal from (type)'], 
                    medium_neutral_citation = df_master.loc[0, 'Medium neutral citation'], 
                    case_number = df_master.loc[0, 'Case number'], 
                    reported_citation = df_master.loc[0, 'Reported citation'], 
                    databases = df_master.loc[0, 'Database(s)'], 
                    sortby = df_master.loc[0, 'Sort by'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']),
                )

    hk_search.get_judgments()
    
    for judgment_json in hk_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

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

    #Pop judgment and appendices
    if pop_judgment() > 0:
        for col in df_updated.columns:
            if (col == 'judgment') or (re.search(r'^(appendix\sto\sjudgment)', col)):
                df_updated.pop(col)

    #Pop empty columns (eg columns of Chinese original, English translation)
    df_updated.replace("", np.nan, inplace=True)
    df_updated.dropna(how='all', axis=1, inplace=True)
    df_updated.replace(np.nan, '', inplace=True)
    
    return df_updated
    


# %% editable=true slideshow={"slide_type": ""}
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def hk_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
        
    hk_search = hk_search_function(
                    any_of_these_words = df_master.loc[0, 'Any of these words'], 
                    these_words_in_any_order = df_master.loc[0, 'These words in any order'], 
                    this_phrase = df_master.loc[0, 'This phrase'], 
                    stemming = df_master.loc[0, 'Stemming'], 
                    date_of_judgment = df_master.loc[0, 'Date of judgment'],
                    coram = df_master.loc[0, 'Coram'],
                    parties = df_master.loc[0, 'Parties'], 
                    representation = df_master.loc[0, 'Representation'], 
                    offence = df_master.loc[0, 'Offence'],
                    court_levels_filter = df_master.loc[0, 'Court level(s) filter'], 
                    on_appeal_from_court = df_master.loc[0, 'On appeal from (court)'],
                    on_appeal_from_type = df_master.loc[0, 'On appeal from (type)'], 
                    medium_neutral_citation = df_master.loc[0, 'Medium neutral citation'], 
                    case_number = df_master.loc[0, 'Case number'], 
                    reported_citation = df_master.loc[0, 'Reported citation'], 
                    databases = df_master.loc[0, 'Database(s)'], 
                    sortby = df_master.loc[0, 'Sort by'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']),
                )

    hk_search.get_judgments()
    
    for judgment_json in hk_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

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

    #Need to convert date column to string
    if 'Date' in df_individual.columns:

        df_individual['Date'] = df_individual['Date'].astype(str)
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)
    
    return batch_record_df_individual


# %%
