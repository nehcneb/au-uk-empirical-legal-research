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
from io import BytesIO
import ast

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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, list_range_check, au_date, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # UK Courts search engine

# %%
#Initialize default courts

uk_courts_default_list = ['United Kingdom Supreme Court',
 'Privy Council',
 'Court of Appeal Civil Division',
 'Court of Appeal Criminal Division',
 'High Court (England & Wales) Administrative Court',
 'High Court (England & Wales) Admiralty Court',
 'High Court (England & Wales) Chancery Division',
 'High Court (England & Wales) Commercial Court',
 'High Court (England & Wales) Family Division',
 'High Court (England & Wales) Intellectual Property Enterprise Court',
 "High Court (England & Wales) King's/Queen's Bench Division",
 'High Court (England & Wales) Mercantile Court',
 'High Court (England & Wales) Patents Court',
 'High Court (England & Wales) Senior Courts Costs Office',
 'High Court (England & Wales) Technology and Construction Court'
]


# %%
#Define format functions for courts choice, and GPT questions

#auxiliary lists and variables
uk_courts ={'United Kingdom Supreme Court': 'uksc',
'Privy Council': 'ukpc',  
'Court of Appeal Civil Division': 'ewca/civ', 
 'Court of Appeal Criminal Division':  'ewca/crim',  
'High Court (England & Wales) Administrative Court': 'ewhc/admin',
'High Court (England & Wales) Admiralty Court': 'ewhc/admlty',  
'High Court (England & Wales) Chancery Division': 'ewhc/ch',  
'High Court (England & Wales) Commercial Court': 'ewhc/comm',  
'High Court (England & Wales) Family Division': 'ewhc/fam',  
'High Court (England & Wales) Intellectual Property Enterprise Court': 'ewhc/ipec',  
"High Court (England & Wales) King's/Queen's Bench Division" : 'ewhc/kb',
'High Court (England & Wales) Mercantile Court': 'ewhc/mercantile',  
'High Court (England & Wales) Patents Court': 'ewhc/pat',  
'High Court (England & Wales) Senior Courts Costs Office': 'ewhc/scco',  
'High Court (England & Wales) Technology and Construction Court': 'ewhc/tcc',  
'Court of Protection': 'ewcop',  
'Family Court': 'ewfc',  
'Employment Appeal Tribunal': 'eat',  
'Administrative Appeals Chamber': 'ukut/aac',  
'Immigration and Asylum Chamber': 'ukut/iac',
'Lands Chamber': 'ukut/lc',  
'Tax and Chancery Chamber': 'ukut/tcc',  
'General Regulatory Chamber': 'ukftt/grc',  
'Tax Chamber' : 'ukftt/tc'
}

uk_courts_list = list(uk_courts.keys())

def uk_court_choice(chosen_list):

    chosen_indice = []

    if isinstance(chosen_list, str):
        chosen_list = ast.literal_eval(chosen_list)

    for i in chosen_list:
        chosen_indice.append(uk_courts[i])
    
    return chosen_indice

#Tidy up hyperlink
def uk_link(x):
    y =str(x).replace('.uk/id', '.uk')
    value = '=HYPERLINK("' + y + '")'
    return value



# %%
#Function turning search terms to search results url

@st.cache_data(show_spinner = False)
def uk_search(query= '', 
              from_day= '',
              from_month='', 
              from_year='', 
              to_day='', 
              to_month='', 
              to_year='', 
              court = [], 
              party = '', 
              judge = ''
             ):
    base_url = "https://caselaw.nationalarchives.gov.uk/judgments/search?per_page=50&order=relevance"
    params = {'query' : query, 
              'from_date_0' : from_day,
              'from_date_1' : from_month, 
              'from_date_2' : from_year, 
              'to_date_0' : to_day, 
              'to_date_1' : to_month, 
              'to_date_2' : to_year, 
              'court' : court, 
              'party' : party, 
              'judge' : judge}

    response = requests.get(base_url, params=params)
    response.raise_for_status()

    #Get results count

    results_count = 0

    try:
        soup = BeautifulSoup(response.content, "lxml")
        results_count_raw = soup.find('p', {'class': "results__results-intro"})
        results_count_cleaned = results_count_raw.get_text(strip = True)
        results_count = int(float(results_count_cleaned.split(' ')[0].replace(',', '')))
    except:
        print('No results found.')


    #Get soup
    soup = BeautifulSoup(response.content, "lxml")

    
    return {'results_url': response.url, 'results_count': results_count, 'soup': soup}
    


# %%
#Define function turning search results url to case_infos to judgments

@st.cache_data(show_spinner = False)
def uk_search_results_to_judgment_links(_soup, judgment_counter_bound):
    #Reponse is from scraping per uk_search
    
    hrefs = _soup.find_all('span', {'class': 'judgment-listing__judgment'})
    case_infos = []

    #Get total number of pages
    page_nums_raw = _soup.find_all('li', attrs={'class': 'pagination__list-item'})
    page_nums = []
    
    for page_num in page_nums_raw:
        try:
            if ('Previous' not in page_num.get_text()) and ('Next' not in page_num.get_text()):
                
                page_nums.append(page_num)
    
        except:
            print('No new page')
    
    if len(page_nums) > 1:
        
        page_total = int(page_nums[-1].get_text().split('Page')[1].split('\n')[0])
    
    else:
        page_total = 1
    
    #Start counter
    
    counter = 1
    
    for link in hrefs:
        if counter <= judgment_counter_bound:

            case_info = {
            'Case name': '',
             'Medium neutral citation': '',
            'Hyperlink to The National Archives' : '', 
            'Date' : '',
            'Court' : ''
            }
            try:
                raw_link = link.find('a', href=True)['href']
                
                if "?" in raw_link:
                    cleaned_link = raw_link.split('?')[0]
                else:
                    cleaned_link = raw_link
                
                link_direct = f'https://caselaw.nationalarchives.gov.uk{cleaned_link}/data.xml'
                case_info['Hyperlink to The National Archives'] = link_direct

                
                title_raw = link.find('span', {'class': "judgment-listing__title"})
                title = title_raw.get_text(strip = True)
                
                case_info['Case name'] = title

                
                court_raw = link.find('span', {'class': "judgment-listing__court"})
                court = court_raw.get_text(strip = True)

                case_info['Court'] = court

                mnc_raw = link.find('span', {'class': "judgment-listing__neutralcitation"})
                mnc = mnc_raw.get_text(strip = True)

                case_info['Medium neutral citation'] = mnc

                date_raw = link.find('time', {'class': "judgment-listing__date"})
                date = date_raw.get_text(strip = True)

                case_info['Date'] = date

            except Exception as e:
                print(f"{case_info['Case name']}: Can't get metadata")
                print(e)
            
            case_infos.append(case_info)
            
            counter = counter + 1

    if page_total > 1:  
    
        for page_ending in range(page_total):
            
            if counter <=judgment_counter_bound:

                pause.seconds(np.random.randint(10, 20))

                url_next_page = url_search_results + f"&page={page_ending + 1}"
                
                page_judgment_next_page = requests.get(url_next_page)
                soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
        
                #Check if stll more results
                if 'No results have been found' not in str(soup_judgment_next_page):
                    hrefs_next_page = soup_judgment_next_page.find_all('span', {'class': 'judgment-listing__judgment'})
                    for extra_link in hrefs_next_page:
                        if counter <= judgment_counter_bound:

                            case_info = {
                            'Case name': '',
                             'Medium neutral citation': '',
                            'Hyperlink to The National Archives' : '', 
                            'Date' : '',
                            'Court' : ''
                            }
                            
                            try:
                                raw_link = extra_link.find('a', href=True)['href']
                                
                                if "?" in raw_link:
                                    cleaned_link = raw_link.split('?')[0]
                                else:
                                    cleaned_link = raw_link
                                
                                link_direct = f'https://caselaw.nationalarchives.gov.uk{cleaned_link}/data.xml'
                                case_info['Hyperlink to The National Archives'] = link_direct
                
                                
                                title_raw = link.find('span', {'class': "judgment-listing__title"})
                                title = title_raw.get_text(strip = True)
                                
                                case_info['Case name'] = title
                
                                
                                court_raw = link.find('span', {'class': "judgment-listing__court"})
                                court = court_raw.get_text(strip = True)
                
                                case_info['Court'] = court
                
                                mnc_raw = link.find('span', {'class': "judgment-listing__neutralcitation"})
                                mnc = mnc_raw.get_text(strip = True)
                
                                case_info['Medium neutral citation'] = mnc
                
                                date_raw = link.find('time', {'class': "judgment-listing__date"})
                                date = date_raw.get_text(strip = True)
                
                                case_info['Date'] = date
                
                            except Exception as e:
                                print(f"{case_info['Case name']}: Can't get metadata")
                                print(e)

                            case_infos.append(case_info)
                            
                            counter = counter + 1
    
                else:
                    break

            else:
                break
                
    
    return case_infos

# %%
#Meta labels and judgment combined

uk_meta_labels_droppable = ['Date', 
                         'Court', 
                         'Case number', 
                         'Judge(s) (non-exhaustiveive)', 
                         'Parties', 
                         'Header'
                        ]

@st.cache_data(show_spinner = False)
def uk_meta_judgment_dict(judgment_url_xml):

    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to The National Archives' : '', 
                'Date' : '',
                'Court' : '', 
                'Case number': '',
                'Judge(s) (non-exhaustiveive)' : [], 
                'Parties' : [],
                'Header' : '',
                'judgment': ''
                }

    #Get metadata

    try:
        page = requests.get(judgment_url_xml)
        soup = BeautifulSoup(page.content, "lxml")
    
        judgment_dict['Case name'] = soup.find("frbrname")['value']
        judgment_dict['Medium neutral citation'] = soup.find("uk:cite").getText()
        judgment_dict['Hyperlink to The National Archives'] = uk_link(soup.find("frbruri")['value'])
        judgment_dict['Date'] = soup.find("frbrdate")['date']
        judgment_dict['Court'] = soup.find("uk:court").getText()
        judgment_dict['Header'] = soup.find('header').getText()
        
        if judgment_dict['Header'][0:1] == '\n':
            judgment_dict['Header'] = judgment_dict['Header'][1: ]
            
        judgment_dict['Case number'] = soup.find("docketnumber").getText()
    except:
        pass
    
    for person in soup.find_all("tlcperson"):
        if 'judge' in str(person):
            judgment_dict['Judge(s) (non-exhaustiveive)'].append(person["showas"])
        else:
            judgment_dict['Parties'].append(person["showas"])

    #Get judgment

    pause.seconds(np.random.randint(5, 10))

    try:
        html_link = judgment_url_xml.replace('/data.xml', '')
        page_html = requests.get(html_link)
        soup_html = BeautifulSoup(page_html.content, "lxml")
        
        judgment_text = soup_html.get_text(separator="\n", strip=True)
    
        try:
            before_end_of_doc = judgment_text.split('End of document')[0]
            after_skip_to_end = before_end_of_doc.split('Skip to end')[1]
            judgment_text = after_skip_to_end
            
        except:
            pass
    
        judgment_dict['judgment'] = judgment_text

    except Exception as e:
        print(f"judgment_dict['Case name']: can't scrape judgment")
        
    return judgment_dict


# %%
def uk_search_url(df_master):

    df_master = df_master.fillna('')

    df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)
    
    #Combining catchwords into new column
    
    #Conduct search
    
    results_url_count = uk_search(query= df_master.loc[0, 'Free text'], 
                                   from_day= df_master.loc[0, 'From day'],
                                   from_month=df_master.loc[0, 'From month'], 
                                   from_year=df_master.loc[0, 'From year'], 
                                   to_day=df_master.loc[0, 'To day'], 
                                   to_month=df_master.loc[0, 'To month'], 
                                   to_year=df_master.loc[0, 'To year'], 
                                   court= df_master.loc[0, 'Courts'], 
                                   party = df_master.loc[0, 'Party'], 
                                   judge = df_master.loc[0, 'Judge']
                                  )

    results_url = results_url_count['results_url']

    results_count = results_url_count['results_count']

    search_results_soup = results_url_count['soup']
    
    return {'results_url': results_url, 'results_count': results_count, 'soup': search_results_soup}



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from functions.gpt_functions import question_characters_bound, role_content#, intro_for_GPT


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
def uk_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    search_results_soup = uk_search(query= df_master.loc[0, 'Free text'], 
                                   from_day= df_master.loc[0, 'From day'],
                                   from_month=df_master.loc[0, 'From month'], 
                                   from_year=df_master.loc[0, 'From year'], 
                                   to_day=df_master.loc[0, 'To day'], 
                                   to_month=df_master.loc[0, 'To month'], 
                                   to_year=df_master.loc[0, 'To year'], 
                                   court= df_master.loc[0, 'Courts'], 
                                   party = df_master.loc[0, 'Party'], 
                                   judge = df_master.loc[0, 'Judge']
                                  )['soup']
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_infos = uk_search_results_to_judgment_links(search_results_soup, judgments_counter_bound)

    for case_info in case_infos:

        judgment_dict = uk_meta_judgment_dict(case_info['Hyperlink to The National Archives'])
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(10, 20))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #For UK, convert date to string so as to avoid Excel producing random numbers for dates
    if 'Date' in df_individual.columns:
        df_individual['Date'] = df_individual['Date'].astype(str)
    
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

    if 'judgment' in df_updated.columns:
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in uk_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated

