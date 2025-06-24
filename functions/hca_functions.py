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
#import pypdf
import io
from io import BytesIO
from io import StringIO

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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input, pdf_judgment, link, is_date, split_title_mnc
#Import variables
from functions.common_functions import huggingface, today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # High Court of Australia search engine

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
hca_collections = ['Judgments 2000-present', 'Judgments 1948-1999', '1 CLR - 100 CLR (judgments 1903-1958)']

# %%
#Parties include categories
parties_include_categories = {'include': 'contains', 
                             'do not include': 'notcontains'}

# %%
#Year is categories
year_is_categories = {'is': 'contains', 
                    'is not': 'notcontains'}

# %%
#Judges include categories
judge_includes_categories = {'includes': 'contains', 
                             'does not include': 'notcontains'}

# %% [markdown]
# ## Search engine

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
#Function to get judgment links with filters

#@st.cache_data(show_spinner = False, ttl=600)
def hca_soup_to_judgments(_soup, 
                          collection, 
                         judgment_counter_bound,
                        ):
        
    #Start counter
    
    counter = 1
    
    #Start links list
    case_infos = []
    
    if counter <= judgment_counter_bound:

        #Get raw links and names of cases
        raw_links = _soup.find_all(class_='case')

        #Get catchwords
        catchwords_list = _soup.find_all('div', class_='well')
        #The first element of catchwords_list is not catchwords
        
        for raw_link in raw_links:

            if counter <= judgment_counter_bound:

                index = raw_links.index(raw_link)
                #mnc = '[' + raw_link.text.split('[')[-1]
                case_name_mnc = split_title_mnc(raw_link.get_text().strip())
                case_name = case_name_mnc[0]
                mnc = case_name_mnc[1]

                catchwords = ''
                if collection != hca_collections[-1]:
                    try:
                        catchwords = catchwords_list[counter].get_text()
                    except Exception as e:
                        f"{mnc}: can't get catchwords due to error: {e}"

                case_info = {'Case name': case_name, #hca_df.loc[int(index), 'case'], 
                             'Medium neutral citation': mnc, #New
                             'Hyperlink to High Court Judgments Database': 'https://eresources.hcourt.gov.au' + raw_link['href'],
                             'Catchwords': catchwords
                            }

                #Try to get case info from hca_df
                try:
                    index_list = hca_df.index[hca_df['mnc'].str.contains(mnc, case=False, na=False, regex=False)].tolist()
                    index = index_list[0]

                    case_info.update({'Reported': hca_df.loc[int(index), 'reported']})

                    case_info.update({'Before': hca_df.loc[int(index), 'before']})

                    case_info.update({'Date': hca_df.loc[index, 'date']})
                                        
                except Exception as e:
                    print(f"{mnc}: can't get case info from hca_df.")
                    print(e)

                case_infos.append(case_info)
                
                counter += 1 
            
            else:
                break

    #pause.seconds(np.random.randint(5, 15))

    return case_infos


# %%
def hca_search(collection = hca_collections[0], 
               quick_search = '',
               citation = '', 
                full_text = '', 
                parties_include = list(parties_include_categories.keys())[0],
                parties = '',
                year_is = list(year_is_categories.keys())[0],
                year = '', 
                case_number = '', 
                judge_includes = list(judge_includes_categories.keys())[0],
                judge = '',
                judgment_counter_bound = default_judgment_counter_bound
                ):
    
    #Default base url is for judgments 2000-current
    #base_url = 'https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term='
    base_url = 'https://eresources.hcourt.gov.au/search?col=0'
    
    if collection == 'Judgments 2000-present':
    
        #base_url = 'https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term='
        base_url = 'https://eresources.hcourt.gov.au/search?col=0'

    if collection == 'Judgments 1948-1999':
        #base_url = 'https://eresources.hcourt.gov.au/search?col=1&facets=&srch-Term='

        base_url = 'https://eresources.hcourt.gov.au/search?col=1'
    
    if collection == '1 CLR - 100 CLR (judgments 1903-1958)':
        #base_url = 'https://eresources.hcourt.gov.au/search?col=2&facets=&srch-Term='

        base_url = 'https://eresources.hcourt.gov.au/search?col=2'

    #Get elements
    #base_url = 'https://eresources.hcourt.gov.au/search?col=0'
    browser.get(base_url)
    browser.refresh()

    #Clear button
    clear_button = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//button[@value='Clear']")))
    
    #Clear input
    clear_button.click()

    #Quick search
    #quick_search = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'qsrch-term')))
    quick_search_input = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='qsrch-term']")))
    
    #Search for citation
    #citation = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'id_filter_type_13')))
    citation_input = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='id_filter_type_13']")))

    #Parties include/not include
    parties_include_input = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'id_filter_relational_operator_2')))
    parties_include_category = Select(parties_include_input)
    
    #Parties
    parties_input = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='id_filter_2']")))
    
    #Year is/is not
    year_is_input = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'id_filter_relational_operator_4')))
    year_is_category = Select(year_is_input)
    
    #Year
    year_input = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='id_filter_4']")))

    if collection != hca_collections[-1]:

        #Full text search
        #full_text = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'srch-term')))
        full_text_input = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='srch-term']")))
        
        #case number
        case_number_input = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='id_filter_5']")))
        
        #Judge includes/does not include
        judge_includes_input = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'id_filter_relational_operator_6')))
        judge_includes_category = Select(judge_includes_input)
        
        #Judge
        judge_input = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='id_filter_6']")))

    #Search button
    search_button = Wait(browser, 30).until(EC.visibility_of_element_located((By.ID, 'apply_filter')))
    
    #Enter input
    #Quick search
    if ((quick_search != None) and (quick_search != '')):
        
        quick_search_input.send_keys(quick_search)

    #Citation
    if ((citation != None) and (citation != '')):
        
        citation_input.send_keys(citation)

    #Parties
    parties_include_category_value = parties_include_categories[parties_include]
    parties_include_category.select_by_value(parties_include_category_value)

    if ((parties != None) and (parties != '')):
        
        parties_input.send_keys(parties)

    #Year
    year_is_category_value = year_is_categories[year_is]
    year_is_category.select_by_value(year_is_category_value)

    if ((year != None) and (year != '')):
        
        year_input.send_keys(year)

    if collection != hca_collections[-1]:
    
        #Full text
        if ((full_text != None) and (full_text != '')):
            
            full_text_input.send_keys(full_text)
    
        #Case number
        if ((case_number != None) and (case_number != '')):
            
            case_number_input.send_keys(case_number)
    
        #Judge
        judge_includes_category_value = judge_includes_categories[judge_includes]
        judge_includes_category.select_by_value(judge_includes_category_value)
    
        if ((judge != None) and (judge != '')):
            
            judge_input.send_keys(judge)

    #Get search results
    search_button.click()

    #Results count
    results_count_text = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//div[@id='postsearch']")))
    results_count_raw = results_count_text.text.split('\n')[1]
    results_count = int(re.findall(r'\d+', results_count_raw)[0])

    #Page bound
    page_bound = int(re.findall(r'\d+', results_count_text.text)[-1])

    #Set page counter
    page_counter = 1
    
    #print(f'Searching page {page_counter}')

    #Report on search terms
    print(results_count_text.text.strip())

    #Get case_infos from first page
    soup = BeautifulSoup(browser.page_source, "lxml")
    case_infos = hca_soup_to_judgments(soup, collection, judgment_counter_bound)

    #Next page if available and needed
    while (page_counter < page_bound) and (len(case_infos) < min(judgment_counter_bound, results_count)):

        #Pause to avoid getting kicked out
        pause.seconds(np.random.randint(5, 10))
        
        #Increase page count
        page_counter += 1

        #print(f'Searching page {page_counter}')

        #Get and click button for next page
        #Top next button
        next_page_button = Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//a[@id='nextbutton1']")))

        #Bottom next button
        #next_page_button = Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:newPage(2)']")))
        
        browser.execute_script("arguments[0].click();",next_page_button)
        
        #Wait for next page to load
        pause.seconds(np.random.randint(5, 10))
        
        Wait(browser, 30).until(EC.text_to_be_present_in_element((By.XPATH, "//div[@id='postsearch']"), f'{str(page_counter)[-1]} (of'))

        #Report on search terms
        results_count_text = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//div[@id='postsearch']")))
        print(results_count_text.text.strip())

        #Get soup for next page
        soup_next_page = BeautifulSoup(browser.page_source, "lxml")

        #Get case_infos from next page
        case_infos_next_page = hca_soup_to_judgments(soup_next_page, collection, judgment_counter_bound)

        #Add case_infos from next page to all case_infos
        for case_info in case_infos_next_page:
            if len(case_infos) < min(judgment_counter_bound, results_count):
                case_infos.append(case_info)

    return {'results_count': results_count, 'case_infos': case_infos}


# %%
#Meta labels and judgment combined
hca_meta_labels_droppable = ['Reported', 'Date', 'Case number', 'Before', 'Catchwords', 'Order']


# %%
#If judgment link contains 'showCase'

#@st.cache_data(show_spinner = False)
def hca_meta_judgment_dict(judgment_url):
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to High Court Judgments Database' : '', 
                 'Catchwords' : '',                       
                 'Reported': '', 
                 'Date' : '',  
                 'Case number' : '',  
                 'Before' : '',  
                'Order': '', 
                'judgment' : ''
                }
    
    try:
        #Attach hyperlink
    
        judgment_dict['Hyperlink to High Court Judgments Database'] = link(judgment_url)
        
        page = requests.get(judgment_url)
        soup = BeautifulSoup(page.content, "lxml")
    
        #Case name
        judgment_dict['Case name'] = soup.find('title').text
    
        #Medium neutral citation
        year = judgment_url.split('showCase/')[1][0:4]
        num = judgment_url.split('HCA/')[1]
        
        judgment_dict['Medium neutral citation'] = f'[{year}] HCA {num}'
    
        #Reported, decision date, before
    
        h2_tags = soup.find_all('h2')
    
        if len(h2_tags) > 0:
            
            for h2 in soup.find_all('h2'):
                if 'clr' in h2.text.lower():
                    
                    judgment_dict['Reported'] = h2.text
        
                elif is_date(h2.text, fuzzy=False):
        
                    judgment_dict['Date'] = h2.text
        
                elif 'before' in h2.text.lower():
                    judgment_dict['Before'] = h2.text.replace('Before', '').replace('before', '').replace('Catchwords', '').replace('catchwords', '').replace('\n', '').replace('\t', '').replace('  ', '')
        
                else:
                    continue
        
        #Case number
    
        case_number_list = soup.find_all(string=re.compile('Case Number'))
    
        if len(case_number_list) > 0:
            
            judgment_dict['Case number'] = case_number_list[0].split('Case Number')[1].replace(': ', '')
    
        #Checking
    
        if len(str(judgment_dict['Reported'])) < 5:
    
            try:
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Reported'] = hca_df.loc[int(index), 'reported']
    
            except:
                print(f"Can't get reported for {judgment_dict['Medium neutral citation']}")
    
        if is_date(str(judgment_dict['Date']), fuzzy=False) == False:
    
            try:
                
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Date'] = hca_df.loc[index, 'date']
    
            except:
                print(f"Can't get date for {judgment_dict['Medium neutral citation']}")
    
        if len(str(judgment_dict['Before'])) < 3:
    
            try:
        
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Before'] = hca_df.loc[int(index), 'before']
    
        
            except:
                print(f"Can't get before for {judgment_dict['Medium neutral citation']}")
    
        if len(str(judgment_dict['Case number'])) < 3:
    
            try:
    
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Case number'] = hca_df.loc[int(index), 'case_number']
    
        
            except:
                print(f"Can't get case number for {judgment_dict['Medium neutral citation']}")
        
        #Catchwords
    
        catchwords_list = soup.find_all('div', class_='well')
    
        if len(catchwords_list) > 0:
            
            judgment_dict['Catchwords'] = catchwords_list[0].text
    
        #Judgment text
        judgment_url = judgment_url.replace('showCase', 'downloadPdf')
        judgment_dict['judgment'] = pdf_judgment(judgment_url)

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
        
    return judgment_dict


# %%
#If judgment link contains 'showbyHandle'

#@st.cache_data(show_spinner = False)
def hca_meta_judgment_dict_alt(judgment_url):
    
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to High Court Judgments Database' : '', 
                  'Catchwords' : '',
                 'Reported': '', 
                 'Date' : '',  
                 'Case number' : '',  
                 'Before' : '',  
                'Order': '',
                'judgment' : ''
                }

    try:
        #Attach hyperlink
    
        judgment_dict['Hyperlink to High Court Judgments Database'] = link(judgment_url)
        
        page = requests.get(judgment_url)
        soup = BeautifulSoup(page.content, "lxml")
    
        #Case name
        judgment_dict['Case name'] = soup.find('title').text
    
        #Judgment text
    
        judgment_list = soup.find_all("div", {"class": "opinion"})
        
        judgment_pdfs_list = soup.find_all('a', {'class': 'btn btn-success'})
        
        if len(judgment_list) > 0:
    
            judgment_dict['judgment'] = judgment_list[0].text
    
        elif len(judgment_pdfs_list) > 0:
            raw_link = judgment_pdfs_list[0]['href']
            pdf_link = 'https://eresources.hcourt.gov.au' + raw_link
            pdf_link = pdf_link.replace('showCase', 'downloadPdf')
            judgment_dict['judgment'] = pdf_judgment(pdf_link)
    
        else:
            judgment_dict['judgment'] = ''
                
        #Catchwords
    
        catchwords_list = soup.find_all("div", {"class": "Catchphrases"})
    
        if len(catchwords_list) > 0:
            judgment_dict['Catchwords'] = catchwords_list[0].text
        
        #Medium neutral citation meta tag
        mnc_list = soup.find_all("div", {"class": "MNC"})
    
        if len(mnc_list):
    
            judgment_dict['Medium neutral citation'] = mnc_list[0].text
    
        elif len(judgment_pdfs_list) > 0:
    
            mnc_raw = judgment_pdfs_list[0]['href'].replace('/downloadPdf/', '').replace('/', '')
    
            year = mnc_raw.lower().split('hca')[0]
    
            num = mnc_raw.lower().split('hca')[1]
    
            judgment_dict['Medium neutral citation'] = f"[{year}] HCA {num}"
    
        #Before
        judges_list = soup.find_all("div", {"class": "judges-title"})
    
        if len(judges_list) > 0:
    
            judgment_dict['Before'] = judges_list[0].text
    
    
        #Order
        order_list = soup.find_all("div", {"class": "order-text"})
    
        if len(order_list) > 0:
    
            order = order_list[0].text#.replace('\n            ', '')
    
            judgment_dict['Order'] = order
    
        #Reported, decision date, before
    
        h2_tags = soup.find_all('h2')
    
        if len(h2_tags) > 0:
            
            for h2 in soup.find_all('h2'):
                if 'clr' in h2.text.lower():
                    
                    judgment_dict['Reported'] = h2.text
        
                elif is_date(h2.text, fuzzy=False):
        
                    judgment_dict['Date'] = h2.text
        
                elif 'before' in h2.text.lower():
                    judgment_dict['Before'] = h2.text.replace('Before', '').replace('before', '').replace('Catchwords', '').replace('catchwords', '').replace('\n', '').replace('\t', '').replace('  ', '')
        
                else:
                    continue
    
        #Checking
    
        if len(str(judgment_dict['Reported'])) < 5:
    
            try:
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Reported'] = hca_df.loc[int(index), 'reported']
    
            except:
                print(f"Can't get reported for {judgment_dict['Medium neutral citation']}")
    
        if is_date(str(judgment_dict['Date']), fuzzy=False) == False:
    
            try:
                
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Date'] = hca_df.loc[index, 'date']
    
            except:
                print(f"Can't get date for {judgment_dict['Medium neutral citation']}")
    
        if len(str(judgment_dict['Before'])) < 3:
    
            try:
        
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Before'] = hca_df.loc[int(index), 'before']
    
        
            except:
                print(f"Can't get before for {judgment_dict['Medium neutral citation']}")
    
        if len(str(judgment_dict['Case number'])) < 3:
    
            try:
    
                index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
                index = index_list[0]
        
                judgment_dict['Case number'] = hca_df.loc[int(index), 'case_number']
    
        
            except:
                print(f"Can't get case number for {judgment_dict['Medium neutral citation']}")

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
    
    return judgment_dict

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

    case_infos = hca_search(collection = df_master.loc[0, 'Collection'], 
                   quick_search = df_master.loc[0, 'Quick search'],
                   citation = df_master.loc[0, 'Search for citation'], 
                    full_text = df_master.loc[0, 'Full text search'], 
                    parties_include = df_master.loc[0, 'Parties include/do not include'],
                    parties = df_master.loc[0, 'Parties'],
                    year_is = df_master.loc[0, 'Year is/is not'],
                    year = df_master.loc[0, 'Year'], 
                    case_number = df_master.loc[0, 'Case number'], 
                    judge_includes = df_master.loc[0, 'Judge includes/does not include'],
                    judge = df_master.loc[0, 'Judge'],
                    judgment_counter_bound = judgment_counter_bound
                    )['case_infos']
    
    if huggingface == False: #If not running on HuggingFace
        
        #Get judgments from HCA database
        for case in case_infos:
            judgment_link = case['Hyperlink to High Court Judgments Database']
            
            if 'showbyHandle' in judgment_link:
                
                judgment_dict = hca_meta_judgment_dict_alt(judgment_link)
    
            else: #If 'showCase' in judgment_link:
    
                judgment_dict = hca_meta_judgment_dict(judgment_link)
    
            for key in judgment_dict.keys():
                if key not in case.keys():
                    case.update({key: judgment_dict[key]}) 
            
            judgments_file.append(case)
            
            pause.seconds(np.random.randint(5, 15))
    
    else: #If running on HuggingFace
        
        #Load oalc
        from functions.oalc_functions import load_corpus, get_judgment_from_oalc

        #Create a list of mncs for HuggingFace:
        mnc_list = []

        for case in case_infos:

            #Add mnc to list for HuggingFace
            mnc_list.append(case['Medium neutral citation'])

        #Get judgments from oalc first
        mnc_judgment_dict = get_judgment_from_oalc(mnc_list)
    
        #Append OALC judgment to judgments_file 
        for case in case_infos:
            
            #Append judgments from oalc first
            if case['Medium neutral citation'] in mnc_judgment_dict.keys():
                
                case.update({'judgment': mnc_judgment_dict[case['Medium neutral citation']]})

                judgments_file.append(case)

                print(f"{case['Case name']} {case['Medium neutral citation']}: got judgment from OALC")

            else:
            #Get remaining judgments from HCA database
    
                judgment_link = case['Hyperlink to High Court Judgments Database']
                
                if 'showbyHandle' in judgment_link:
                    
                    judgment_dict = hca_meta_judgment_dict_alt(judgment_link)
        
                else: #If 'showCase' in judgment_link:
        
                    judgment_dict = hca_meta_judgment_dict(judgment_link)
        
                for key in judgment_dict.keys():
                    if key not in case.keys():
                        case.update({key: judgment_dict[key]}) 
                
                judgments_file.append(case)

                print(f"{case['Case name']} {case['Medium neutral citation']}: got judgment from HCA directly.")
                
                pause.seconds(np.random.randint(5, 15))
    
    #Make judgment_link clickable
    for decision in judgments_file:
        if '=HYPERLINK' not in decision['Hyperlink to High Court Judgments Database']:
            clickable_link =  link(decision['Hyperlink to High Court Judgments Database'])
            decision.update({'Hyperlink to High Court Judgments Database': clickable_link})
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in hca_metalabels_droppable:
            try:
                df_updated.pop(meta_label)
            except Exception as e:
                print(f'{meta_label} not popped.')
                print(e)
    
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
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in hca_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
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

    case_infos = hca_search(collection = df_master.loc[0, 'Collection'], 
                   quick_search = df_master.loc[0, 'Quick search'],
                   citation = df_master.loc[0, 'Search for citation'], 
                    full_text = df_master.loc[0, 'Full text search'], 
                    parties_include = df_master.loc[0, 'Parties include/do not include'],
                    parties = df_master.loc[0, 'Parties'],
                    year_is = df_master.loc[0, 'Year is/is not'],
                    year = df_master.loc[0, 'Year'], 
                    case_number = df_master.loc[0, 'Case number'], 
                    judge_includes = df_master.loc[0, 'Judge includes/does not include'],
                    judge = df_master.loc[0, 'Judge'],
                    judgment_counter_bound = judgment_counter_bound
                    )['case_infos']
    
    if huggingface == False: #If not running on HuggingFace
        
        #Get judgments from HCA database
        for case in case_infos:
            judgment_link = case['Hyperlink to High Court Judgments Database']
            
            if 'showbyHandle' in judgment_link:
                
                judgment_dict = hca_meta_judgment_dict_alt(judgment_link)
    
            else: #If 'showCase' in judgment_link:
    
                judgment_dict = hca_meta_judgment_dict(judgment_link)
    
            for key in judgment_dict.keys():
                if key not in case.keys():
                    case.update({key: judgment_dict[key]}) 
            
            judgments_file.append(case)
            
            pause.seconds(np.random.randint(5, 15))
    
    else: #If running on HuggingFace
        
        #Load oalc
        from functions.oalc_functions import load_corpus, get_judgment_from_oalc

        #Create a list of mncs for HuggingFace:
        mnc_list = []

        for case in case_infos:

            #add search results to json
            #judgments_file.append(case)

            #Add mnc to list for HuggingFace
            mnc_list.append(case['Medium neutral citation'])

        #Get judgments from oalc first
        mnc_judgment_dict = get_judgment_from_oalc(mnc_list)
    
        #Append judgment to judgments_file 
        for case in case_infos: #judgments_file:
            
            #Append judgment from oalc first
            if case['Medium neutral citation'] in mnc_judgment_dict.keys():
                
                case.update({'judgment': mnc_judgment_dict[case['Medium neutral citation']]})

                judgments_file.append(case)
                
                print(f"{case['Case name']} {case['Medium neutral citation']}: got judgment from OALC")

            else:
            #Get remaining judgment from HCA database
        
                judgment_link = case['Hyperlink to High Court Judgments Database']
                
                if 'showbyHandle' in judgment_link:
                    
                    judgment_dict = hca_meta_judgment_dict_alt(judgment_link)
        
                else: #If 'showCase' in judgment_link:
        
                    judgment_dict = hca_meta_judgment_dict(judgment_link)
        
                for key in judgment_dict.keys():
                    if key not in case.keys():
                        case.update({key: judgment_dict[key]}) 
                
                judgments_file.append(case)

                print(f"{case['Case name']} {case['Medium neutral citation']}: got judgment from HCA directly.")
                
                pause.seconds(np.random.randint(5, 15))
    
    #Make judgment_link clickable
    for decision in judgments_file:
        if '=HYPERLINK' not in decision['Hyperlink to High Court Judgments Database']:
            clickable_link =  link(decision['Hyperlink to High Court Judgments Database'])
            decision.update({'Hyperlink to High Court Judgments Database': clickable_link})
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in hca_metalabels_droppable:
            try:
                df_updated.pop(meta_label)
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
