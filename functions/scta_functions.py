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
from dateutil.relativedelta import *
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

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # SCTA search engine

# %%
from functions.common_functions import link

# %%
#list of search methods

scta_methods_list = ['Full text', 'Titles only', 'This Boolean query', 'Any of these words', 'All of these words']
scta_method_types = ['auto', 'title', 'boolean', 'any', 'all']


# %%
#Function turning search terms to search results url

def scta_search(query= '', 
              method = ''
             ):
    base_url = "https://www.austlii.edu.au/cgi-bin/sinosrch.cgi?"

    method_index = scta_methods_list.index(method)
    method_type = scta_method_types[method_index]

    query_text = query

    params = {#'meta' : ';',
              'mask_path' : 'au/cases/cth/SCTA', 
              'method' : method_type,
              'query' : query_text
             }

    response = requests.get(base_url, params=params)
    
    return response.url


# %%
#Define function turning search results url to case_link_pairs to judgments

@st.cache_data(show_spinner = False)
def scta_search_results_to_case_link_pairs(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    headers = {'User-Agent': 'whatever'}
    page = requests.get(url_search_results, headers=headers)
    soup = BeautifulSoup(page.content, "lxml")
    hrefs = soup.find_all('a', href=True)
    case_link_pairs = []

    #number of search results
    docs_found_string = str(soup.find('title')).split('AustLII:')[1].split('documents')[0].replace(' ', '')
    docs_found = int(docs_found_string)

    #Start counter
    counter = 1
    
    for link in hrefs:
        if ((counter <= judgment_counter_bound) and (' SCTA ' in str(link)) and ('LawCite' not in str(link))):
            case = link.get_text()
            link_direct = link.get('href')
            link = 'https://www.austlii.edu.au' + link_direct.split('?context')[0]
            dict_object = { 'case': case, 'link_direct': link}
            case_link_pairs.append(dict_object)
            counter = counter + 1
        
    for ending in range(10, docs_found, 10):
        if counter <= min(judgment_counter_bound, docs_found):
            url_next_page = url_search_results + ';offset=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page, headers=headers)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            
            hrefs_next_page = soup_judgment_next_page.find_all('a', href=True)
            for extra_link in hrefs_next_page:
                if ((counter <= judgment_counter_bound) and (' SCTA ' in str(extra_link)) and ('LawCite' not in str(extra_link))):
                    case = extra_link.get_text()
                    extra_link_direct = extra_link.get('href')
                    extra_link = 'https://www.austlii.edu.au' + extra_link_direct.split('?context')[0]
                    dict_object = { 'case': case, 'link_direct': extra_link}
                    case_link_pairs.append(dict_object)
                    counter = counter + 1

            pause.seconds(np.random.randint(5, 15))
            
        else:
            break

    #Get rid of repetitions
    case_link_pairs_no_repeats = []

    for case_link_pair in case_link_pairs:
        if  case_link_pair not in case_link_pairs_no_repeats:
            case_link_pairs_no_repeats.append(case_link_pair)
            
    return case_link_pairs_no_repeats


# %%
#Convert case-link pairs to judgment text

@st.cache_data(show_spinner = False)
def scta_judgment_text(case_link_pair):
    url = case_link_pair['link_direct']
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

def scta_meta_judgment_dict(case_link_pair):
    
    judgment_dict = {'Case name': '',
                     'Medium neutral citation' : '', 
                     'Other reports': '', 
                     'Hyperlink to AustLII': '', 
                     'Date' : '', 
                     'judgment': ''
                    }

    case_name = case_link_pair['case']
    date = case_link_pair['case'].split('(')[-1].replace(')', '')
    year = case_link_pair['case'].split('[')[1][0:4]
    case_number_raw = case_link_pair['case'].split('SCTA ')[1].split(' (')[0]
    
    if ";" in case_number_raw:
        case_number = case_number_raw.split(';')[0]
    else:
        case_number = case_number_raw
    
    mnc = '[' + year +']' + ' SCTA ' + case_number
    nr_cite = ''
        
    try:
        case_name = case_link_pair['case'].split('[')[0][:-1]
        nr_cite = case_link_pair['case'].split('; ')[1].replace(' (' + date + ')', '')
    except:
        pass
                
    judgment_dict['Case name'] = case_name
    judgment_dict['Medium neutral citation'] = mnc
    judgment_dict['Other reports'] = nr_cite
    judgment_dict['Date'] = date
    judgment_dict['Hyperlink to AustLII'] = link(case_link_pair['link_direct'])
    judgment_dict['judgment'] = scta_judgment_text(case_link_pair)

        
    return judgment_dict


# %%
def scta_search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    url = scta_search(query= df_master.loc[0, 'Enter search query'],
                    method= df_master.loc[0, 'Find (method)']
                   )
    return url


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from functions.gpt_functions import question_characters_bound, role_content


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction

if check_questions_answers() > 0:
    print(f'By default, questions and answers are checked for potential privacy violation.')
else:
    print(f'By default, questions and answers are NOT checked for potential privacy violation.')


# %%
#Jurisdiction specific instruction
system_instruction = role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#Obtain parameters

@st.cache_data(show_spinner = False)
def scta_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    url_search_results = scta_search(query= df_master.loc[0, 'Enter search query'], 
                                   method = df_master.loc[0, 'Find (method)']
                                  )
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_link_pairs = scta_search_results_to_case_link_pairs(url_search_results, judgments_counter_bound)

    for case_link_pair in case_link_pairs:

        judgment_dict = scta_meta_judgment_dict(case_link_pair)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(5, 15))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    df_individual = pd.read_json(json_individual)

    #For SCTA, convert date to string so as to avoid Excel producing random numbers for dates
    df_individual['Date'] = df_individual['Date'].astype(str)

    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o-2024-08-06"
    else:        
        gpt_model = "gpt-4o-mini"
            
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    df_updated.pop('judgment')
    
    return df_updated

# %%
