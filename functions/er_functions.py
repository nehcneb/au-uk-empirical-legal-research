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
import pypdf
import io
from io import BytesIO
import pdf2image
#from PIL import Image
#import math
#from math import ceil

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
test = 'A Copiholders Case [1657] EngR 1; (1657) Het 138; 124 E.R. 405 (B) (1 January 1657)'
re.findall(r'(\d+\sE\.?R\.?\s\d+((\s\(\w+\))?))', test)[0]

# %%
#Import functions
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, default_judgment_counter_bound, no_results_msg, search_error_note


# %% [markdown]
# # English Reports search engine

# %%
from functions.common_functions import link

# %%
#list of search methods

er_methods_list = ['using autosearch', 'this Boolean query', 'any of these words', 'all of these words', 'this phrase', 'this case name']
er_method_types = ['auto', 'boolean', 'any', 'all', 'phrase', 'title']


# %%
#Function turning search terms to search results url
#@st.cache_data(show_spinner = False)
def er_search(query= '', 
              method = ''
             ):
    base_url = "http://www.commonlii.org/cgi-bin/sinosrch.cgi?" #+ method

    method_index = er_methods_list.index(method)
    method_type = er_method_types[method_index]

    query_text = query

    params = {'meta' : '/commonlii', 
              'mask_path' : '+uk/cases/EngR+', 
              'method' : method_type,
              'query' : query_text
             }

    headers = {'User-Agent': 'whatever'}
    response = requests.get(base_url, params=params, headers=headers)

    soup = BeautifulSoup(response.content, "lxml")
    
    return {'results_url': response.url, 'soup': soup}


# %%
#Define function turning search results url to case_link_pairs to judgments

@st.cache_data(show_spinner = False, ttl=600)
def er_search_results_to_case_link_pairs(_soup, url_search_results, judgment_counter_bound):
    #_soup, url_search_results are from er_search

    hrefs = _soup.find_all('a', href=True)
    case_link_pairs = []

    #number of search results
    docs_found_string = str(_soup.find_all('span', {'class' : 'ndocs'})).split('Documents found:')[1].split('<')[0].replace(' ', '').replace(',', '')
    docs_found = int(float(docs_found_string))
    
    #Start counter
    counter = 1
    
    for link in hrefs:
        if ((counter <= judgment_counter_bound) and (' ER ' in str(link)) and ('cases' in str(link))):
#        if ((counter <= judgment_counter_bound) and ('commonlii' in str(link)) and ('cases/EngR' in str(link)) and ('LawCite' not in str(link))):
            case = link.get_text()
            link_direct = link.get('href')
            sub_link = link_direct.replace('.html', '.pdf').split('cases')[1].split('.pdf')[0]
            pdf_link = 'http://www.commonlii.org/uk/cases' + sub_link + '.pdf'
            dict_object = {'case':case, 'link_direct': pdf_link}
            case_link_pairs.append(dict_object)
            counter = counter + 1
        
    for ending in range(20, docs_found, 20):
        if counter <= min(judgment_counter_bound, docs_found):
            url_next_page = url_search_results + ';offset=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            
            hrefs_next_page = soup_judgment_next_page.find_all('a', href=True)
            for extra_link in hrefs_next_page:
                if ((counter <= judgment_counter_bound) and (' ER ' in str(extra_link)) and ('cases' in str(extra_link))):
#                if ((counter <= judgment_counter_bound) and ('commonlii' in str(extra_link)) and ('cases/EngR' in str(extra_link)) and ('LawCite' not in str(extra_link))):
                    case = extra_link.get_text()
                    extra_link_direct = extra_link.get('href')
                    sub_extra_link = extra_link_direct.replace('.html', '.pdf').split('cases')[1].split('.pdf')[0]
                    pdf_extra_link = 'http://www.commonlii.org/uk/cases' + sub_extra_link + '.pdf'
                    dict_object = {'case':case, 'link_direct': pdf_extra_link}
                    case_link_pairs.append(dict_object)
                    counter = counter + 1

            pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))
            
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

@st.cache_data(show_spinner = False, ttl=600)
def er_judgment_text(case_link_pair):
    url = case_link_pair['link_direct']
    headers = {'User-Agent': 'whatever'}
    r = requests.get(url, headers=headers)
    remote_file_bytes = io.BytesIO(r.content)
    pdfdoc_remote = pypdf.PdfReader(remote_file_bytes)
    
    text_list = []
    
    for page in pdfdoc_remote.pages:
        text_list.append(page.extract_text())
    
    return str(text_list)
    


# %%
#Meta labels and judgment combined
#@st.cache_data(show_spinner = False)
def er_meta_judgment_dict(case_link_pair):
    
    judgment_dict = {'Case name': '',
                     'Medium neutral citation' : '', 
                     'English Reports': '', 
                     'Nominate Reports': '', 
                     'Hyperlink to CommonLII': '', 
                     'Year' : '', 
                     'judgment': ''
                    }

    try:
        case_name = case_link_pair['case']
        year = case_link_pair['link_direct'].split('EngR/')[-1][0:4]
        case_num = case_link_pair['link_direct'].split('/')[-1].replace('.pdf', '')
        mnc = '[' + year + ']' + ' EngR ' + case_num
    
        er_cite = ''
        nr_cite = ''
            
        try:
            case_name = case_link_pair['case'].split('[')[0][:-1]
            nr_cite = case_link_pair['case'].split(';')[-2][1:]
            er_cite = case_link_pair['case'].split(';')[-1][1:]

            if ('ER' not in er_cite) and ('E.R.' not in er_cite):

                try:
                    
                    er_cite_raw = re.findall(r'(\d+\sE\.?R\.?\s\d+((\s\(\w+\))?))', case_link_pair['case'])[0]
    
                    if isinstance(er_cite_raw, tuple):
                        er_cite = er_cite_raw[0]
                    else:
                        er_cite = str(er_cite_raw)

                except:
                    print(f"{mnc}: can't get ER cite.")
            
        except:
            pass
        
        judgment_dict['Case name'] = case_name
        judgment_dict['Medium neutral citation'] = mnc
        judgment_dict['English Reports'] = er_cite
        judgment_dict['Nominate Reports'] = nr_cite
        judgment_dict['Year'] = year
        judgment_dict['Hyperlink to CommonLII'] = link(case_link_pair['link_direct'])
        judgment_dict['judgment'] = er_judgment_text(case_link_pair)

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
                
    return judgment_dict


# %%
#@st.cache_data(show_spinner = False)
def er_search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    url_soup = er_search(query= df_master.loc[0, 'Enter search query'],
                    method= df_master.loc[0, 'Find (method)']
                   )

    return {'results_url': url_soup['results_url'], 'soup': url_soup['soup']}



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import question_characters_bound


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, GPT_answers_check, unanswered_questions, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction

role_content_er = """You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. 
Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a part of the judgment or metadata, include a reference to that part of the judgment or metadata. 
If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". 
The "judgment" field of the JSON given to you sometimes contains judgments for multiple cases. If you detect multiple judgments in the "judgment" field, please provide answers only for the specific case identified in the "Case name" field of the JSON given to you. 
Respond in JSON form. In your response, produce as many keys as you need. 
"""

system_instruction = role_content_er

intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def er_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    results_url_soup = er_search(query= df_master.loc[0, 'Enter search query'], 
                                   method = df_master.loc[0, 'Find (method)']
                                  )     
    url_search_results = results_url_soup['results_url']

    soup = results_url_soup['soup']

    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_link_pairs = er_search_results_to_case_link_pairs(soup, url_search_results, judgments_counter_bound)

    for case_link_pair in case_link_pairs:

        judgment_dict = er_meta_judgment_dict(case_link_pair)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT

    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    df_updated.pop('judgment')
    
    return df_updated

# %% [markdown]
# # For vision

# %%
#Import functions
from functions.gpt_functions import get_image_dims, calculate_image_token_cost, GPT_b64_json, engage_GPT_b64_json


# %%
#Convert case-link pairs to judgment_b64 text

#@st.cache_data(show_spinner = False)
def er_judgment_tokens_b64(case_link_pair):

    output_b64 = {'judgment_b64':[], 'tokens_raw': 0}
    
    url = case_link_pair['link_direct']
    headers = {'User-Agent': 'whatever'}
    r = requests.get(url, headers=headers)
    bytes_data = io.BytesIO(r.content)
    
    images = pdf2image.convert_from_bytes(bytes_data.read(), timeout=30, fmt="jpeg")
    
    for image in images[ : len(images)]:

        output = BytesIO()
        image.save(output, format='JPEG')
        im_data = output.getvalue()
        
        image_data = base64.b64encode(im_data)
        if not isinstance(image_data, str):
            # Python 3, decode from bytes to string
            image_data = image_data.decode()
        data_url = 'data:image/jpg;base64,' + image_data

        #b64 = base64.b64encode(image_raw).decode('utf-8')

        b64_to_attach = data_url
        #b64_to_attach = f"data:image/png;base64,{b64}"

        output_b64['judgment_b64'].append(b64_to_attach)
    
    for image_b64 in output_b64['judgment_b64']:

        output_b64['tokens_raw'] = output_b64['tokens_raw'] + calculate_image_token_cost(image_b64, detail="auto")
    
    return output_b64
    


# %%
#Meta labels and judgment_b64 combined

def er_meta_judgment_dict_b64(case_link_pair):

    try:
        judgment_dict = {'Case name': '',
                         'Medium neutral citation' : '', 
                         'English Reports': '', 
                         'Nominate Reports': '', 
                         'Hyperlink to CommonLII': '', 
                         'Year' : '', 
                         'judgment_b64': '', 
                         'tokens_raw': 0
                        }
    
        case_name = case_link_pair['case']
        year = case_link_pair['link_direct'].split('EngR/')[-1][0:4]
        case_num = case_link_pair['link_direct'].split('/')[-1].replace('.pdf', '')
        mnc = '[' + year + ']' + ' EngR ' + case_num
    
        er_cite = ''
        nr_cite = ''
            
        try:
            case_name = case_link_pair['case'].split('[')[0][:-1]
            nr_cite = case_link_pair['case'].split(';')[1][1:]
            er_cite = case_link_pair['case'].split(';')[2][1:]
        except:
            pass
                    
        judgment_dict['Case name'] = case_name
        judgment_dict['Medium neutral citation'] = mnc
        judgment_dict['English Reports'] = er_cite
        judgment_dict['Nominate Reports'] = nr_cite
        judgment_dict['Year'] = year
        judgment_dict['Hyperlink to CommonLII'] = link(case_link_pair['link_direct'])
        judgment_dict['judgment_b64'] = er_judgment_tokens_b64(case_link_pair)['judgment_b64']
        judgment_dict['tokens_raw'] = er_judgment_tokens_b64(case_link_pair)['tokens_raw']

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment_b64 not scrapped")
        print(e)
    
    return judgment_dict
    


# %%
#For gpt-4o vision

@st.cache_data(show_spinner = False, ttl=600)
def er_run_b64(df_master):

    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    results_url_soup = er_search(query= df_master.loc[0, 'Enter search query'], 
                                   method = df_master.loc[0, 'Find (method)']
                                  )     
    url_search_results = results_url_soup['results_url']

    soup = results_url_soup['soup']

    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_link_pairs = er_search_results_to_case_link_pairs(soup, url_search_results, judgments_counter_bound)

    for case_link_pair in case_link_pairs:

        judgment_dict = er_meta_judgment_dict_b64(case_link_pair)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT

    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment_b64 spreadsheet
    
    questions_json = df_master.loc[0, 'questions_json']
            
    #apply GPT_individual to each respondent's judgment_b64 spreadsheet

    df_updated = engage_GPT_b64_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    #Remove redundant columns

    for column in ['tokens_raw', 'judgment_b64']:
        try:
            df_updated.pop(column)
        except:
            print(f"No {column} column.")

    return df_updated
