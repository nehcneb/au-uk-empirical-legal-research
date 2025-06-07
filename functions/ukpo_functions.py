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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input, pdf_judgment
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # UK Pensions Ombudsman search engine

# %% [markdown]
# ## Definitions

# %%
ukpo_outcomes_dict = {'Not upheld': '14', 
                           'Partly upheld': '13', 
                            'Upheld': '12',
                           }


# %%
ukpo_topics_dict = {'Abatement': '282',
 'Administration': '228',
 'Automatic enrolment': '279',
 'Benefits: incorrect calculation': '221',
 'Benefits: missing': '231',
 'Benefits: overpayment (recovery of)': '232',
 'Benefits: refusal/failure to pay or late payment': '229',
 'Breach of trust': '278',
 'Charges/fees': '235',
 'Compensation': '285',
 'Contributions: failure to pay into scheme': '230',
 'Contributions: incorrect calculation': '233',
 'Contributions: refunds': '238',
 'CPI: switch to': '239',
 'Death benefits': '225',
 'Divorce': '236',
 'Equal treatment': '280',
 'Equalisation of retirement age': '283',
 'Failure to provide information/act on instructions': '224',
 'Fund switches': '271',
 'Guaranteed annuity rate': '234',
 'Ill Health': '223',
 'Injury benefit': '240',
 'Interpretation of scheme rules/policy terms': '227',
 'Membership': '226',
 'Misquote/misinformation': '222',
 'Other': '277',
 'Pension liberation': '237',
 'Post retirement increases (escalation): general': '270',
 'Post retirement increases (escalation): RPI/CPI': '269',
 'Pre retirement increases (revaluation)': '274',
 'Transfers: club transfers': '272',
 'Transfers: general': '220',
 'Unsecured pension/drawdown': '289',
 'Winding up': '273',
 'With-profits issues': '288'}

# %%
ukpo_types_dict = {'Financial Assistance Scheme appeal': '15',
 'Pension complaint or dispute': '16',
 'Pensions Protection Fund complaint': '17',
 'Pensions Protection Fund referral': '18'}

# %%
ukpo_sortby_dict = {'Sort A – Z': 'title_ASC', 
                  'Sort Z – A': 'title_DESC', 
                  'Decision Date Asc': 'field_decision_date_value_ASC', 
                  'Decision Date Desc': 'field_decision_date_value_DESC'    
}

# %% [markdown]
# ## Search engine

# %%
from functions.common_functions import link


# %%
class ukpo_search_tool:

    def __init__(self, 
                 keyword = '', 
                 outcomes_list = [], 
                 topics_list = [], 
                 types_list = [], 
                 sortby = list(ukpo_sortby_dict.keys())[-1], 
                 judgment_counter_bound = default_judgment_counter_bound
                ):

        #Initialise parameters
        self.keyword = keyword
        self.outcomes_list = outcomes_list
        self.topics_list = topics_list
        self.types_list = types_list
        self.sortby = sortby
        self.page = 0
        
        self.judgment_counter_bound = judgment_counter_bound

        self.results_count = 0
        self.results_url = ''
        self.soup = None
        self.case_infos = []

    #Function for getting search results
    #def search(self, keyword = '', outcomes_list = [], topics_list = [], types_list = [], sortby = list(ukpo_sortby_dict.keys())[-1], page = 0):
    def search(self):

        #st.write('Running search()')

        ukpo_url = 'https://www.pensions-ombudsman.org.uk/decisions'
    
        #Add search params
        params = {}
    
        #Add keyword
        if len(self.keyword) > 0:
            params.update({'keys': self.keyword})
        
        #Add outcomes
        for outcome in self.outcomes_list:
            outcome_value = ukpo_outcomes_dict[outcome]
            outcome_param = {f'outcome[{outcome_value}]': outcome_value}
            params.update(outcome_param)
    
        #Add topics
        for topic in self.topics_list:
            topic_value = ukpo_topics_dict[topic]
            topic_param = {f'topic[{topic_value}]': topic_value}
            params.update(topic_param)
    
        #Add types
        for type_chosen in self.types_list:
            type_value = ukpo_types_dict[type_chosen]
            type_param = {f'type[{type_value}]': type_value}
            params.update(type_param)
    
        #Add sortby
        sortby_value = ukpo_sortby_dict[self.sortby]
        params.update({'sort_bef_combine': sortby_value})
    
        #Add page number to search parameter if page > 0:
        if self.page > 0:
            params.update({'page': self.page})
        
        #Conduct search
        response = requests.get(ukpo_url, params = params, headers= {'User-Agent': 'whatever'})
        soup = BeautifulSoup(response.content, "lxml")
        
        #Get number of results    
        results_text = soup.find('div', {'role': 'status'}).text
        results_text = results_text.replace(',', '').replace('.', '')
        results_count_list = re.findall(r'\d+', results_text)
    
        if len(results_count_list) > 0:
            results_count = int(results_count_list[0])
    
        else:
            results_count = 0
    
        print(results_text)

        #Update return values
        self.results_url = response.url
        self.results_count = results_count
        self.soup = soup
        
        #return {'results_url': response.url, 'results_count': results_count, 'soup': soup}

    #Function for getting case infos from search results page
    def get_case_infos(self):

        #Get case infos

        #st.write(f'judgment_counter_bound == {self.judgment_counter_bound}')
        
        #Initialise results obtained
        #result_counter = 0

        #There are 12 cases per page, where the page number parameter starts at 0/none
        page_max = math.ceil(self.results_count/12-1)
    
        for page_to_check in range(0, page_max + 1):

            #st.write(f'result_counter == {result_counter}')

            #st.write(f'Checking page {page_to_check}')
            
            #st.write(f'len(self.case_infos) == {len(self.case_infos)}')
            
            #if result_counter < self.judgment_counter_bound:
            if len(self.case_infos) < self.judgment_counter_bound:

                #For all pages except the initial page, need to pause and update search results page
                if page_to_check > 0:
                    
                    #Pause to avoid getting kicked out
                    pause.seconds(np.random.randint(15, 20))
                    
                    self.page = page_to_check

                    self.search()

                #Get case infos
                search_results = self.soup.find_all('div', {'class': 'card-item teal'})
            
                for search_result in search_results:
                    
                    #if result_counter < self.judgment_counter_bound:
                    if len(self.case_infos) < self.judgment_counter_bound:

                        #Get case name
                        case_name = search_result.find('a', {'class': 'h3'}).text
                        #case_name
                        
                        #Link to case
                        link = search_result.find('a', {'class': 'h3'})['href']
                        #link
                        
                        #Get metadata
                        meta_text =  search_result.find('div', {'class': 'teal_font'}).get_text()
                        meta_list = meta_text.splitlines()
                        #meta_list
                        
                        #Initialise meta labels
                        complainant = ''
                        respondent = ''
                        outcome = ''
                        topic = ''
                        ref = ''
                        date = ''
                        
                        case_info = {'Case name': case_name,
                                    'Hyperlink to the Pensions Ombudsman': link, 
                                    'Complainant': complainant,
                                    'Respondent': respondent,
                                    'Outcome': outcome,
                                    'Complaint Topic': topic,
                                    'Ref': ref,
                                    'Date': date
                        }
                        
                        #Last added status to capture any lines with no commencing label
                        last_added = None
                        
                        for meta in meta_list:
                            
                            if 'complainant' in meta.lower():
                                case_info['Complainant'] += meta.split(': ')[1]
                                last_added = 'Complainant'
                                
                            elif 'respondent' in meta.lower():
                                case_info['Respondent'] += meta.split(': ')[1]
                                last_added = 'Respondent'
                                
                            elif 'outcome'  in meta.lower():
                                case_info['Outcome'] += meta.split(': ')[1]
                                last_added = 'Outcome'

                            elif 'topic' in meta.lower():
                                case_info['Complaint Topic'] += meta.split(': ')[1]
                                last_added = 'Complaint Topic'

                            elif 'ref' in meta.lower():
                                case_info['Ref'] += meta.split(': ')[1]
                                last_added = 'Ref'

                            elif 'date' in meta.lower():
                                case_info['Date'] += meta.split(': ')[1]
                                last_added = 'Date'

                            else:
                                if last_added in case_info.keys():
                                    case_info[last_added] += meta
                                
                        #Append case to return list and increase counter
                        self.case_infos.append(case_info)
            
                        #result_counter += 1
                    
                    else:
                        #stop if reached the maximum number of results wanted
                        break

            else:
                #stop if reached the maximum number of results wanted
                break     

        #st.write(self.case_infos)
            
    #Function for getting judgment text
    def get_judgments(self):

        #st.write('Running get_judgments()')

        #Initialise list of case_infos with judgment text
        
        self.case_infos_w_judgments = []

        judgment_counter = 0
        
        for case_info in self.case_infos:

            case_info_w_judgment = case_info.copy()

            if judgment_counter < self.judgment_counter_bound:

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(15, 20))

                result_url = case_info['Hyperlink to the Pensions Ombudsman']
                result_response = requests.get(result_url, headers = {'User-Agent': 'whatever'})
                result_soup = BeautifulSoup(result_response.content, "lxml")

                #Get appeal status

                appeal = ''

                try:
                    result_meta_text = result_soup.find('div', {'class': 'bg__teal decision-details'}).get_text()
                    result_meta_list = result_meta_text.splitlines()
                    
                    for line in result_meta_list:
                        if 'appeal' in line.lower():
                            appeal = line.split(': ')[-1]
                            break

                except:
                    
                    print(f"{case_info['Case name']}: can't get appeal status.")

                case_info_w_judgment.update({'Appeal': appeal}) 
                
                #Get summary

                summary = ''

                try:
                    summary = result_soup.find('div', {'class': 'article--body'}).get_text()

                    if 'View determination' in summary:
                        summary = summary.split('View determination')[0]
                    
                except:
                    print(f"{case_info['Case name']}: can't get summary.")

                case_info_w_judgment.update({'Summary': summary}) 

                #get judgment text or save .doc file locally
                judgment_link_raw = result_soup.find('a', {'class': 'btn btn_teal download_btn'})['href']
                judgment_link = 'https://www.pensions-ombudsman.org.uk' + judgment_link_raw
                judgment_text = ''

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(15, 20))

                try:
                    
                    if '.pdf' in judgment_link:
    
                        judgment_text = pdf_judgment(judgment_link)
                    
                        print(f"{case_info['Case name']}: got judgment.")
                    
                    if '.doc' in judgment_link:
                    
                        #If the judgment is in .doc, can only save the judgment to a local folder
                        doc_folder = 'UKPO_FILES'
                        
                        try:
                            os.mkdir(doc_folder)
                            print(f"Directory '{doc_folder}' created successfully.")
                        except:
                            print(f"Directory '{doc_folder}' already exists.")
                        
                        #Convert .doc to .docx
                        r = requests.get(judgment_link)
                    
                        doc_file_name = f"{doc_folder}/{judgment_link.split('/')[-1]}"
                        
                        with open(doc_file_name, 'wb') as f:
                            f.write(r.content)

                        print(f"{case_info['Case name']}: saved file.")

                except:
                    
                    print(f"{case_info['Case name']}: can't get judgment or save file.")
                    
                #Add judgment to dict of case_info_w_judgment
                case_info_w_judgment.update({'judgment': judgment_text}) 

                #Make link clickable
                clickable_link = link(case_info['Hyperlink to the Pensions Ombudsman'])
                case_info_w_judgment.update({'Hyperlink to the Pensions Ombudsman': clickable_link}) 
    
                #Keep case_info_w_judgment
                self.case_infos_w_judgments.append(case_info_w_judgment)

                judgment_counter += 1

                print(f"Scrapped {len(judgment_counter)}/{self.judgment_counter_bound} judgments.")
            
            else:
                #stop if reached the maximum number of results wanted
                break


# %%
#@st.cache_data(show_spinner = False, ttl=600)
def ukpo_search_function(keyword, 
                         outcomes_list, 
                         topics_list, 
                         types_list, 
                         sortby, 
                         judgment_counter_bound
                        ):

    #Conduct search
    ukpo_search = ukpo_search_tool(keyword = keyword, 
                         outcomes_list = outcomes_list, 
                         topics_list = topics_list, 
                         types_list = types_list, 
                         sortby = sortby, 
                         judgment_counter_bound = judgment_counter_bound
                )
    
    ukpo_search.search()

    ukpo_search.get_case_infos()
    
    return ukpo_search


# %%
def ukpo_search_preview(df_master):
    
    df_master = df_master.fillna('')
            
    #Conduct search
    
    ukpo_search = ukpo_search_function(
                keyword = df_master.loc[0, 'Keyword search'],
                outcomes_list = df_master.loc[0, 'Select outcome'],
                topics_list = df_master.loc[0, 'Select complaint topic'], 
                types_list = df_master.loc[0, 'Select type'], 
                sortby = df_master.loc[0, 'Sort by'],
                judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']), 
                )
    
    results_count = ukpo_search.results_count
    results_url = ukpo_search.results_url
    results_to_show = ukpo_search.case_infos

    #st.write(results_to_show)
    
    return {'results_url': results_url, 'results_count': results_count, 'results_to_show': results_to_show}
    


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import question_characters_bound, basic_model, flagship_model#, role_content
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction and functions

#system_instruction = role_content

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def ukpo_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
    
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
                
    ukpo_search = ukpo_search_function(
                keyword = df_master.loc[0, 'Keyword search'],
                outcomes_list = df_master.loc[0, 'Select outcome'],
                topics_list = df_master.loc[0, 'Select complaint topic'], 
                types_list = df_master.loc[0, 'Select type'], 
                sortby = df_master.loc[0, 'Sort by'],
                judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']), 
                )

    #Get judgments
    ukpo_search.get_judgments()

    for judgment_json in ukpo_search.case_infos_w_judgments:

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

    #Remove 'judgment' column
    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')
    
    return df_updated
