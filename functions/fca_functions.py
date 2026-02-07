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
import httplib2
import urllib
from urllib.request import urlretrieve
from bs4 import BeautifulSoup, SoupStrainer
import os
#import pypdf
import io
from io import BytesIO
import copy
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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_range_check, date_parser, save_input, pdf_judgment
#Import variables
from functions.common_functions import huggingface, today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

#Load oalc
from functions.oalc_functions import get_judgment_from_oalc



# %% [markdown]
# # Federal Courts search engine

# %% [markdown]
# ### Definitions

# %%
#Define format functions for courts choice, and GPT questions

#auxiliary lists and variables

fca_courts = {'All': 'FCA+FCAFC+IRCA+ACOMPT+ACOPYT+ADFDAT+FPDT+ATPT+NFSC',
              'Federal Court': 'FCA+FCAFC', 
              'Industrial Relations Court of Australia': 'IRCA', 
              'Australian Competition Tribunal': 'ACOMPT', 
              'Copyright Tribunal': 'ACOPYT', 
              'Defence Force Discipline Appeal Tribunal': 'ADFDAT', 
              'Federal Police Discipline Tribunal': 'FPDT', 
              'Trade Practices Tribunal': 'ATPT', 
              'Supreme Court of Norfolk Island': 'NFSC',
             }

fca_courts_list = list(fca_courts.keys())

# %%
npa_dict = {'All': '', 
    'Admin., Constitutional, Human Rights': 'administrative', 
  'Admiralty and Maritime': 'admiralty', 
  'Commercial and Corporations': 'commercial', 
  'Employment and Industrial Relations': 'employment', 
  'Federal Crime and Related Proceedings': 'crime', 
  'Intellectual Property': 'intellectual', 
  'Native Title': 'native', 
  'Taxation': 'taxation',
      'Other Federal Jurisdiction': 'other',
    }

npa_list = list(npa_dict.keys())

# %%
sort_dict = {"Relevance": "",
    "Most Recent": "date",
    "Least Recent": "adate",
    "Title Ascending": "metaMNC",
    "Title Descending": "dmetaMNC",
    }


# %%
#Meta labels and judgment combined
#IN USE
fca_metalabels = ['Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'Date.published', 'Appeal_to']
#'MNC', 'FileName', 'Asset_ID', 
fca_metalabels_droppable = ['Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'Date.published', 'Appeal_to', 'Order']
#'FileName', 'Asset_ID', 


# %% [markdown]
# ### Search function

# %%
from functions.common_functions import running_locally_dir, get_uc_driver

#For downloading judgments
download_dir = f"{os.getcwd()}/FCA_PDFs"

#Headless mode?
if running_locally_dir in os.getcwd(): 

    headless = False

else:

    headless = False
    
    from pyvirtualdisplay import Display
    
    display = Display(visible=0, size=(1200, 1600))  
    display.start()


# %%
#Get uc modules
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


# %%
from functions.common_functions import link, split_title_mnc


# %%
class fca_search_tool:

    def __init__(self,
                court = list(fca_courts.keys())[0], 
                case_name_mnc= None, 
                judge =None, 
                reported_citation =None, 
                file_number =None, 
                npa = list(npa_dict.keys())[0], 
                with_all_the_words = None, 
                with_at_least_one_of_the_words = None, 
                without_the_words = None, 
                phrase = None, 
                proximity = None, 
                on_this_date = None, 
                after_date = None, 
                before_date = None, 
                legislation = None, 
                cases_cited = None, 
                catchwords = None,
                 sort = list(sort_dict.keys())[0], 
                judgment_counter_bound = default_judgment_counter_bound
                ):

        #Initialise parameters
        self.court = court
        self.case_name_mnc= case_name_mnc
        self.judge =judge
        self.reported_citation =reported_citation
        self.file_number =file_number
        self.npa = npa
        self.with_all_the_words = with_all_the_words
        self.with_at_least_one_of_the_words = with_at_least_one_of_the_words
        self.without_the_words = without_the_words
        self.phrase = phrase
        self.proximity = proximity
        self.on_this_date = on_this_date
        self.after_date = after_date
        self.before_date = before_date
        self.legislation = legislation
        self.cases_cited = cases_cited
        self.catchwords = catchwords
        self.sort = sort

        self.judgment_counter_bound = judgment_counter_bound
        
        self.page = 1
                
        self.results_count = 0

        self.total_pages = 1
        
        self.results_url = ''

        self.results_url_to_show = ''
        
        self.soup = None
        
        self.case_infos = []

        self.case_infos_w_judgments = []
        
        #For getting judgment directly from FCA database if can't get from OALC
        self.case_infos_direct = []

    #Function for getting case infos from search results page
    def get_case_infos(self):
        
        results_list = self.soup.find_all('div', attrs={'class' : 'result'})
            
        for result in results_list:
            
            if len(self.case_infos) < min(self.judgment_counter_bound, self.results_count):
    
                #Initialise default values
                title = ''
                case_name = ''
                mnc = ''
                link_to_case = ''
                date = ''
                judge = ''
                catchwords = ''
                subject = ''
                
                #Get full title
                
                title = result.h3.get_text(strip = True)
    
                #Get PDF status
                pdf_status = False
                
                if '(pdf' in title.lower():
                    
                    pdf_status = True
                
                #Get case name and mnc
                case_name_mnc = split_title_mnc(title)
                
                case_name = case_name_mnc[0]
                
                mnc = case_name_mnc[1]
                
                if '(PDF' in mnc:
                    mnc = mnc.replace('(PDF', '')
                
                #Get link to case
                link_to_case = result.h3.find('a').get('href')
    
                #Get decision date, subject area, judge
                date_area_court_str = str(result.find('p', attrs={'class' : 'meta'}))
                date_area_court_raw = str(date_area_court_str).split('<span class="divide"></span>')
    
                date = date_area_court_raw[0].replace('<p class="meta">', '')
                
                if len(date) > 0:
                    if date[-1] == ' ':
                        date = date[: -1]
                
                judge = date_area_court_raw[-1].replace('</p>', '')
                
                subject = result.find('p', attrs={'class' : 'meta'}).text.replace(date, '').replace(judge, '')
                
                if len(subject) > 0:
                    if subject[0] == ' ':
                        subject = subject[1:]
    
                #Get catchwords
                catchwords = ''
                try:
                    catchwords = result.find('p', attrs={'class' : 'summary'}).get_text(strip = True)
                except:
                    print(f"{case_name}: can't get catchwords")
                
                case_info = {'Case name': case_name,
                     'Medium neutral citation': mnc,
                    'Hyperlink to Federal Court Digital Law Library' : link_to_case,
                    'Judge': judge,
                     'Judgment_Dated' : date,  
                     'Catchwords' : catchwords,  
                     'Subject' : subject,
                    'Judgment in PDF': pdf_status
                            }
                self.case_infos.append(case_info)
    
    #Function for getting search results
    def search(self):

        #Reset infos of cases found
        self.case_infos = []
        
        params_raw = []
        
        base_url = 'https://www.fedcourt.gov.au/digital-law-library/judgments/search'

        #Url for selenium to start

        self.results_url = base_url
        
        #Before entering year, justice or CLR, must enter keywords or case number first, then load

        browser = get_uc_driver(download_dir = download_dir, headless = headless)
        
        browser.get(self.results_url)

        #Clear form first
        clear_form = Wait(browser, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.clear-form")))
        clear_form.click()
        
        # Wait for the Court dropdown
        court_select_el = Wait(browser, 15).until(EC.presence_of_element_located((By.ID, "scope")))
        court_select = Select(court_select_el)
        
        if self.court != list(fca_courts.keys())[0]:
            
            court_select.select_by_value(fca_courts[self.court])
        
        # Wait for the NPA dropdown
        npa_select_el = Wait(browser, 15).until(EC.presence_of_element_located((By.ID, "NPA")))
        npa_select = Select(npa_select_el)
        
        if self.npa != list(npa_dict.keys())[0]:
            npa_select.select_by_visible_text(npa_dict[self.npa])
        
        # Case Name / MNC
        case_name = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "caseName")))
        
        if (not pd.isna(self.case_name_mnc)) and (not self.case_name_mnc == None) and (not str(self.case_name_mnc) == 'None'):
            
            case_name.send_keys(self.case_name_mnc)
        
        # Judge
        judge = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "searchJudge")))
        
        if (not pd.isna(self.judge)) and (not self.judge == None) and (not str(self.judge) == 'None'):
        
            judge.send_keys(self.judge)
        
        # Reported Citation
        reported = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "searchReportedCitation")))
        
        if (not pd.isna(self.reported_citation)) and (not self.reported_citation == None) and (not str(self.reported_citation) == 'None'):
            
            reported.send_keys(self.reported_citation)
        
        # File number
        file_no = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "searchFileNumber")))
        
        if (not pd.isna(self.file_number)) and (not self.file_number == None) and (not str(self.file_number) == 'None'):
            
            file_no.send_keys(self.file_number)
            
        #Click the "Full Text & Proximity" accordion full_text_tab
        full_text_tab = Wait(browser, 15).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'h2.accordion a[href="#fulltext"]')
        ))
        full_text_tab.click()
        
        # Wait for a field inside the section to be visible (means it's "opened")
        Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "allWords")))
        
        #With ALL the words, With at least one of the words, Without the words, Phrase, and Proximity
        all_words = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "allWords")))
        
        if (not pd.isna(self.with_all_the_words)) and (not self.with_all_the_words == None) and (not str(self.with_all_the_words) == 'None'):
        
            all_words.send_keys(self.with_all_the_words)
        
        one_word = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "oneWord")))
        
        if (not pd.isna(self.with_at_least_one_of_the_words)) and (not self.with_at_least_one_of_the_words == None) and (not str(self.with_at_least_one_of_the_words) == 'None'):
            
            one_word.send_keys(self.with_at_least_one_of_the_words)
        
        without_words = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "withoutWords")))
        
        if (not pd.isna(self.without_the_words)) and (not self.without_the_words == None) and (not str(self.without_the_words) == 'None'):
            
            without_words.clear()
            without_words.send_keys(self.without_the_words)
        
        phrase = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "phrase")))
        
        if (not pd.isna(self.phrase)) and (not self.phrase == None) and (not str(self.phrase) == 'None'):
            
            phrase.send_keys(self.phrase)
        
        proximity = Wait(browser, 15).until(EC.element_to_be_clickable((By.ID, "proximity")))
        
        if (not pd.isna(self.proximity)) and (not self.proximity == None) and (not str(self.proximity) == 'None'):
            
            proximity.send_keys(self.proximity)
        
        
        #Click the Date tab
        date_tab = Wait(browser, 15).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'h2.accordion a[href="#date"]')
        ))
        date_tab.click()
        
        # Wait until a field inside the Date section is visible
        Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "date-specific")))
        
        #On this date, After and Before
        on_this_date = Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "date-specific")))
        
        if (not pd.isna(self.on_this_date)) and (not self.on_this_date == None) and (not str(self.on_this_date) == 'None'):
            
            on_this_date.send_keys(self.on_this_date)
        
        date_from = Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "date-from")))
        
        if (not pd.isna(self.after_date)) and (not self.after_date == None) and (not str(self.after_date) == 'None'):
            
            date_from.send_keys(self.after_date)
        
        date_to = Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "date-to")))
        
        if (not pd.isna(self.before_date)) and (not self.before_date == None) and (not str(self.before_date) == 'None'):

            date_to.send_keys(self.before_date)
        
        # Click the Legislation accordion tab
        leg_tab = Wait(browser, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'h2.accordion a[href="#legislation"]')))
        leg_tab.click()
        
        #Legislation, Cases Cited, and Catchwords?
        
        legislation = Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "searchLegislation")))
        
        if (not pd.isna(self.legislation)) and (not self.legislation == None) and (not str(self.legislation) == 'None'):
            
            legislation.send_keys(self.legislation)
        
        cases_cited = Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "searchCasesCited")))
        
        if (not pd.isna(self.cases_cited)) and (not self.cases_cited == None) and (not str(self.cases_cited) == 'None'):
            
            cases_cited.send_keys(self.cases_cited)
        
        catchwords = Wait(browser, 15).until(EC.visibility_of_element_located((By.ID, "searchCatchwords")))
        
        if (not pd.isna(self.catchwords)) and (not self.catchwords == None) and (not str(self.catchwords) == 'None'):
                        
            catchwords.send_keys(self.catchwords)

        #Submit
        search_button = Wait(browser, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'fieldset.actions input[type="submit"][value="Search"]')))
        search_button.click()

        #Wait until number of search results present
        RESULT_CARD    = (By.CSS_SELECTOR, "#fb-results .result")
        NO_RESULTS_BOX = (By.ID, "fb-no-results")
        
        Wait(browser, 15).until(EC.any_of(
            EC.presence_of_element_located(RESULT_CARD),
            EC.presence_of_element_located(NO_RESULTS_BOX),
        ))
    
        #If positive results found
        if browser.find_elements(*RESULT_CARD):
    
            summary = Wait(browser, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".tools p.txarial")))
            m = re.search(r"\bof\s+([\d,]+)\b", summary.text)
            results_count = int(m.group(1).replace(",", "")) if m else 0
    
            #Update self.results_count
            self.results_count = results_count

        #Update self.results_url
        self.results_url = browser.current_url

        print(f"There are {self.results_count} search results from self.results_url == {self.results_url}")
        
        #If at least 1 result
        if self.results_count > 0:

            #Get page count
            #20 results per page. Each page url ends with 20*(page number - 1) + 1
            self.total_pages = math.ceil(self.results_count/20)

            #Sort results
            # Wait until the select exists
            sort_select_el = Wait(browser, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form.updateSort select[name='sort']")))
            sort_select = Select(sort_select_el)
            
            if self.sort != list(sort_dict.keys())[0]:
    
                sort_select.select_by_value(sort_dict[self.sort])
                
                # Click Sort button
                sort_button = Wait(browser, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form.updateSort input[type='submit']")))
                sort_button.click()
                
                # Wait for navigation to complete (URL contains sort=adate)
                Wait(browser, 15).until(lambda d: f"sort={sort_dict[self.sort]}" in d.current_url)

            #Wait search results present
            loaded = Wait(browser, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#fb-results .result h3 a")))
            
            #Update self.soup
            self.soup = BeautifulSoup(browser.page_source, "lxml")

            for page in range(0, self.total_pages):

                if len(self.case_infos) < min(self.results_count, self.judgment_counter_bound):
                    
                    #Update self.soup from new page if necessary
                    if page > 0:
    
                        #Pause to avoid getting kicked out
                        pause.seconds(np.random.randint(10, 15))

                        next20 = Wait(browser, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[rel="next"].fb-next-result-page')))
                        next20.click()
                        
                        #Wait until search results present, if any
                        loaded = Wait(browser, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#fb-results .result h3 a")))

                        #Update self.soup
                        self.soup = BeautifulSoup(browser.page_source, "lxml")

                    print(f"Getting results from page {page} (0 denotes first page)")
    
                #Get search results from current page
                self.get_case_infos()

        browser.quit()

    #Function for attaching judgment text to case_info dict
    def attach_judgment(self, case_info):

        judgment_dict = copy.deepcopy(case_info)
        
        judgment_url = case_info['Hyperlink to Federal Court Digital Law Library']
    
        #Get judgment text
        judgment_text = ''
    
        #Check if getting taken to a PDF
        if 'Judgment in PDF' not in judgment_dict.keys():
    
            judgment_dict.update({'Judgment in PDF': False})
        
        #Check if not taken to a PDF
        if not bool(judgment_dict['Judgment in PDF']):
        
            try:
    
                browser = get_uc_driver(download_dir = download_dir, headless = headless)
                browser.get(judgment_url)
        
                #Wait until judgment present
                loaded = Wait(browser, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.judgment_content")))

                #Wait until end of judgment
                top_link = Wait(browser, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.top-link-wrapper a.top-link")))

                #pause.seconds(10)
                
                soup = BeautifulSoup(browser.page_source, "lxml")
                
                browser.quit()
                
                #Attach judgment
                try:
                    
                    judgment_text = soup.find("div", {"class": "judgment_content"}).get_text(separator="\n", strip=True)
                                    
                except:
                    
                    judgment_text = soup.get_text(separator="\n", strip=True)
    
                #Attach meta tags
                meta_tags = soup.find_all("meta")
            
                #Attach meta tags
                if len(meta_tags)>0:
                    for tag_index in range(len(meta_tags)):
                        meta_name = meta_tags[tag_index].get("name")
                        if meta_name in fca_metalabels:
                            meta_content = meta_tags[tag_index].get("content")
                            judgment_dict.update({meta_name: meta_content})
                            
            except Exception as e:
                
                print(f"{judgment_dict['Case name']}: can't get html judgment or meta due to error {e}.")
                
        #Check if gets taken to a PDF
        else:
            
            print(f"{judgment_dict['Case name']}: trying to get pdf judgment")
            
            #Get judgment pdf text
            try:
                
                #judgment_text = pdf_judgment(url_or_path = judgment_url, url_given = True)

                browser = get_uc_driver(download_dir = download_dir, headless = headless)
                browser.get(judgment_url)
                
                pdf_file = judgment_url.split('/')[-1]    
    
                pdf_file = urllib.parse.unquote(pdf_file)
                
                pdf_path = f"{download_dir}/{pdf_file.upper()}.pdf"
    
                #Limiting waiting time for downloading PDF to 1 min
                
                waiting_counter = 0
                
                while ((not os.path.exists(pdf_path)) and (waiting_counter < 10)):
                    pause.seconds(10)
                    waiting_counter += 1
                                
                print(f"{case_info['Case name']}: Trying to OCR pdf from pdf_path == {pdf_path}")
    
                judgment_text = pdf_judgment(url_or_path = pdf_path, url_given = False)
                                                                    
                #MUST remove pdf from download folder automatically or manually
                os.remove(pdf_path)
    
                browser.quit()
                
            except Exception as e:
                
                print(f"{judgment_dict['Case name']}: can't get pdf judgment due to error {e}.")
    
        judgment_dict['judgment'] = judgment_text
        
        return judgment_dict

    #Function for getting all requested judgments
    def get_judgments(self):

        self.case_infos_w_judgments = []

        #Search if not done yet
        if len(self.case_infos) == 0:

            self.search()

        #If huggingface enabled
        if huggingface == True:

            #Create a list of mncs for HuggingFace:
            mnc_list = []
    
            for case_info in self.case_infos:

                if len(self.case_infos_w_judgments) < self.judgment_counter_bound:
                    
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
                    judgment_url = case_info['Hyperlink to Federal Court Digital Law Library']
                    case_info.update({'Hyperlink to Federal Court Digital Law Library': link(judgment_url)})

                    #Add case_info to self.case_infos_w_judgments
                    self.case_infos_w_judgments.append(case_info)
    
                    print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from OALC")
    
                else:
                    
                    #To get from FCA database directly if can't get from OALC
                    self.case_infos_direct.append(case_info)

            print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments from OALC")

        else:
            
            #If huggingface not enabled
            self.case_infos_direct = copy.deepcopy(self.case_infos)
        
        #Get judgments from FCA database directly
        for case_info in self.case_infos_direct:

            if len(self.case_infos_w_judgments) < self.judgment_counter_bound:

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(10, 15))
    
                case_info = self.attach_judgment(case_info)
    
                #Make link clickable
                judgment_url = case_info['Hyperlink to Federal Court Digital Law Library']
                case_info.update({'Hyperlink to Federal Court Digital Law Library': link(judgment_url)})
    
                #Add case_info to self.case_infos_w_judgments
    
                self.case_infos_w_judgments.append(case_info)
                
                print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from FCA directly")
                
                print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments")


# %%
def fca_search_preview(df_master):
    
    df_master = df_master.fillna('')
        
    fca_search = fca_search_tool(court = df_master.loc[0, 'Courts'], 
                     case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
                     judge = df_master.loc[0, 'Judge'], 
                     reported_citation = df_master.loc[0, 'Reported citation'],
                     file_number  = df_master.loc[0, 'File number'],
                     npa = df_master.loc[0, 'National practice area'], 
                     with_all_the_words  = df_master.loc[0, 'With all the words'], 
                     with_at_least_one_of_the_words = df_master.loc[0, 'With at least one of the words'],
                     without_the_words = df_master.loc[0, 'Without the words'],
                     phrase  = df_master.loc[0, 'Phrase'], 
                     proximity = df_master.loc[0, 'Proximity'], 
                     on_this_date = df_master.loc[0, 'On this date'], 
                     after_date = df_master.loc[0, 'Decision date is after'], 
                     before_date = df_master.loc[0, 'Decision date is before'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'],
                    sort = df_master.loc[0, 'Sort'],
                    )

    fca_search.search()
    
    results_count = fca_search.results_count
    
    case_infos = fca_search.case_infos

    results_url = fca_search.results_url

    #st.write(results_url)
    
    return {'results_url': results_url, 'results_count': results_count, 'case_infos': case_infos}



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json, gpt_batch_input
#Import variables
from functions.gpt_functions import basic_model#, flagship_model#, role_content


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction
#system_instruction = role_content

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#For getting judgments from the Federal Court if unavailable in OALC

@st.cache_data(show_spinner = False, ttl=600)
def fca_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)

    #Create judgments file
    judgments_file = []
    
    #Conduct search    
    fca_search = fca_search_tool(court = df_master.loc[0, 'Courts'], 
                     case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
                     judge = df_master.loc[0, 'Judge'], 
                     reported_citation = df_master.loc[0, 'Reported citation'],
                     file_number  = df_master.loc[0, 'File number'],
                     npa = df_master.loc[0, 'National practice area'], 
                     with_all_the_words  = df_master.loc[0, 'With all the words'], 
                     with_at_least_one_of_the_words = df_master.loc[0, 'With at least one of the words'],
                     without_the_words = df_master.loc[0, 'Without the words'],
                     phrase  = df_master.loc[0, 'Phrase'], 
                     proximity = df_master.loc[0, 'Proximity'], 
                     on_this_date = df_master.loc[0, 'On this date'], 
                     after_date = df_master.loc[0, 'Decision date is after'], 
                     before_date = df_master.loc[0, 'Decision date is before'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'],
                     sort = df_master.loc[0, 'Sort'],
                     judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )
    
    fca_search.get_judgments()
    
    for judgment_json in fca_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT
    
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)

    #Pop jugdment
    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in fca_metalabels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def fca_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []

    #Conduct search    
    fca_search = fca_search_tool(court = df_master.loc[0, 'Courts'], 
                     case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
                     judge = df_master.loc[0, 'Judge'], 
                     reported_citation = df_master.loc[0, 'Reported citation'],
                     file_number  = df_master.loc[0, 'File number'],
                     npa = df_master.loc[0, 'National practice area'], 
                     with_all_the_words  = df_master.loc[0, 'With all the words'], 
                     with_at_least_one_of_the_words = df_master.loc[0, 'With at least one of the words'],
                     without_the_words = df_master.loc[0, 'Without the words'],
                     phrase  = df_master.loc[0, 'Phrase'], 
                     proximity = df_master.loc[0, 'Proximity'], 
                     on_this_date = df_master.loc[0, 'On this date'], 
                     after_date = df_master.loc[0, 'Decision date is after'], 
                     before_date = df_master.loc[0, 'Decision date is before'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'],
                     sort = df_master.loc[0, 'Sort'],
                     judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )
    
    fca_search.get_judgments()
    
    for judgment_json in fca_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
                        
    #Drop metadata if not wanted
    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in fca_metalabels_droppable:
            if meta_label in df_individual.columns:
                df_individual.pop(meta_label)
    
    #Instruct GPT
    
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)
    
    return batch_record_df_individual

# %%
