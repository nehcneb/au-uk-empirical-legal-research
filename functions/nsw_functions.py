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
#import re
#import datetime
#from datetime import date
#from dateutil import parser
#from dateutil.relativedelta import *
#from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
#import httplib2
#from urllib.request import urlretrieve
import os
#import pypdf
import io
from io import BytesIO
import ast
import copy

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
#import streamlit_ext as ste
#from streamlit_extras.stylable_container import stylable_container

#NSWCaseLaw
from nswcaselaw.search import Search

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb


# %%
#Import functions
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, date_parser, save_input, split_title_mnc, pdf_image_judgment
#Import variables
from functions.common_functions import huggingface, today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound

#Load oalc
from functions.oalc_functions import get_judgment_from_oalc



# %% [markdown]
# # CaseLaw NSW functions and parameters

# %% [markdown]
# ### Definitions

# %%
#Auxiliary lists
#search_criteria = ['Free text', 'Case name', 'Before', 'Catchwords', 'Party names', 'Medium neutral citation', 'Decision date from', 'Decision date to', 'File number', 'Legislation cited', 'Cases cited']
nsw_meta_labels_droppable = ["Catchwords", "Before", "Decision date(s)", "Hearing date(s)", "Date(s) of order",  "Jurisdiction", "Decision", "Legislation cited", "Cases cited", "Texts cited", "Category", "Parties", "File number", "Representation", "Decision under appeal"]


# %%
#List of nsw courts

#For showing as menu
nsw_courts =["Court of Appeal", 
             "Court of Criminal Appeal", 
             "Supreme Court", 
             'Land and Environment Court (Judges)', 
             'Land and Environment Court (Commissioners)', 
             'District Court', 
             'Local Court',
             "Children's Court", 
             'Compensation Court', 
             'Drug Court', 
             'Industrial Court',
             'Industrial Relations Commission (Judges)', 
             'Industrial Relations Commission (Commissioners)'
            ] #, "All of the above Courts"]


# %%
#Default courts
nsw_default_courts = ["Court of Appeal", "Court of Criminal Appeal", "Supreme Court"]

# %%
#List of NSW tribunals

nsw_tribunals = ['Administrative Decisions Tribunal (Appeal Panel)',
 'Administrative Decisions Tribunal (Divisions)',
 'Civil and Administrative Tribunal (Administrative and Equal Opportunity Division)',
 'Civil and Administrative Tribunal (Appeal Panel)',
 'Civil and Administrative Tribunal (Consumer and Commercial Division)',
 'Civil and Administrative Tribunal (Enforcement)',
 'Civil and Administrative Tribunal (Guardianship Division)',
 'Civil and Administrative Tribunal (Occupational Division)',
 'Dust Diseases Tribunal',
 'Equal Opportunity Tribunal',
 'Fair Trading Tribunal',
 'Legal Services Tribunal',
 'Medical Tribunal',
 'Transport Appeal Boards']


# %%
#Create function to convert the list of chosen courts to a list; 13 = NSWSC, 3 = NSWCA, 4 = NSWCCA
#For more, see https://github.com/Sydney-Informatics-Hub/nswcaselaw/blob/main/src/nswcaselaw/constants.py

nsw_courts_positioning = ["Placeholder", "Children's Court",
 'Compensation Court',
 'Court of Appeal',
 'Court of Criminal Appeal',
 'District Court',
 'Drug Court',
 'Industrial Court',
 'Industrial Relations Commission (Commissioners)',
 'Industrial Relations Commission (Judges)',
 'Land and Environment Court (Commissioners)',
 'Land and Environment Court (Judges)',
 'Local Court',
 'Supreme Court']

def nsw_court_choice(chosen_list):
    
    chosen_indice = []

    if isinstance(chosen_list, str):
        chosen_list = ast.literal_eval(chosen_list)

    for i in chosen_list:
        chosen_indice.append(nsw_courts_positioning.index(i))       
        
    return chosen_indice

nsw_tribunals_positioning = ['Placeholder',
 'Administrative Decisions Tribunal (Appeal Panel)',
 'Administrative Decisions Tribunal (Divisions)',
 'Civil and Administrative Tribunal (Administrative and Equal Opportunity Division)',
 'Civil and Administrative Tribunal (Appeal Panel)',
 'Civil and Administrative Tribunal (Consumer and Commercial Division)',
 'Civil and Administrative Tribunal (Enforcement)',
 'Civil and Administrative Tribunal (Guardianship Division)',
 'Civil and Administrative Tribunal (Occupational Division)',
 'Dust Diseases Tribunal',
 'Equal Opportunity Tribunal',
 'Fair Trading Tribunal',
 'Legal Services Tribunal',
 'Medical Tribunal',
 'Transport Appeal Boards']

def nsw_tribunal_choice(chosen_list):
    
    chosen_indice = []

    if isinstance(chosen_list, str):
        chosen_list = ast.literal_eval(chosen_list)

    for i in chosen_list:
        chosen_indice.append(nsw_tribunals_positioning.index(i))            

    return chosen_indice



# %%
#Functions for tidying up

#Tidy up dates
def nsw_date(x):
    if len(str(x)) > 0:
        return str(x).split()[0]
    else:
        return str(x)

# Headnotes fields
headnotes_fields = ["Free text", "Case name", "Before", "Decision date(s)", "Catchwords", "Hearing date(s)", "Date(s) of order",  "Jurisdiction", "Decision", "Legislation cited", "Cases cited", "Texts cited", "Category", "Parties", "Medium neutral citation", "Decision date from", "Decision date to", "File number", "Representation", "Decision under appeal"]
headnotes_keys = ["body", "title", "before", "decisionDate", "catchwords", "hearingDates", "dateOfOrders", "jurisdiction", "decision", "legislationCited", "casesCited", "textsCited", "category", "parties", "mnc", "startDate", "endDate", "fileNumber", "representation", "decisionUnderAppeal"]

#Functions for tidying up headings of columns

#Tidy up hyperlink
def nsw_link(x):
    link='https://www.caselaw.nsw.gov.au'+ str(x)
    value = '=HYPERLINK("' + link + '")'
    return value



# %% [markdown]
# ### Search function

# %%
#Define function for short judgments, which checks if judgment is in PDF
#returns a list of judgment type and judgment text

#@st.cache_data(show_spinner = False, ttl=600)
def nsw_short_judgment(uri):
    
    html_link = 'https://www.caselaw.nsw.gov.au'+ uri
    
    page_html = requests.get(html_link, headers = {'User-Agent': 'whatever'})
    
    soup_html = BeautifulSoup(page_html.content, "lxml")

    judgment_type = ''

    #Check if judgment contains PDF link
    PDF_raw_link = soup_html.find('a', string='See Attachment (PDF)')
    
    if str(PDF_raw_link).lower() != 'none':
        PDF_link = 'https://www.caselaw.nsw.gov.au' + PDF_raw_link.get('href')    
        judgment_text = pdf_image_judgment(url_or_path = PDF_link, url_given = True)
        judgment_type = 'pdf'
        
    #Return html text if no PDF
    else:
        judgment_text = soup_html.get_text(separator="\n", strip=True)
        judgment_type = 'html'

    return [judgment_type, judgment_text]


# %%
class nsw_search_tool:

    def __init__(self,
                courts = [],
                tribunals = [],
                body = '',
                title = '',
                before = '',
                catchwords = '',
                party = '',
                mnc = '',
                startDate = '',
                endDate = '',
                fileNumber = '',
                legislationCited = '',
                casesCited = '',
                pause = int(0),
                 judgment_counter_bound = default_judgment_counter_bound
                ):

        #Initialise parameters
        self.courts = courts
        self.tribunals = tribunals
        self.body = body
        self.title = title
        self.before = before
        self.catchwords = catchwords
        self.party = party
        self.mnc = mnc
        self.startDate = startDate
        self.endDate = endDate
        self.fileNumber = fileNumber
        self.legislationCited = legislationCited
        self.casesCited = casesCited
        self.pause = pause

        #Initialise scraper object
        self.query = None

        #Initialise other objects to update
        self.judgment_counter_bound = judgment_counter_bound
        
        #self.page = 1
                
        self.results_count = 0

        #self.total_pages = 1
        
        self.results_url = ''

        #self.results_url_to_show = ''
        
        self.soup = None
        
        self.case_infos = []

        self.case_infos_w_judgments = []
        
        #For getting judgment directly from NSW Caselaw database if can't get from OALC
        self.case_infos_direct = []

    def search(self):

        #Reset infos of cases found
        self.case_infos = []

        #Conduct search
        self.query = Search(courts = nsw_court_choice(self.courts),
                tribunals = nsw_tribunal_choice(self.tribunals), 
                body = self.body, 
                title = self.title, 
                before = self.before, 
                catchwords = self.catchwords, 
                party = self.party, 
                mnc = self.mnc, 
                startDate = nsw_date(self.startDate), 
                endDate = nsw_date(self.endDate),
                fileNumber = self.fileNumber, 
                legislationCited  = self.legislationCited, 
                casesCited = self.casesCited,
                pause = self.pause
                )

        #Get url to NSW Caselaw search page
        self.results_url = self.query.url

        #Check for positive result
        positive_result = False
        
        for decision in self.query.results():

            positive_result = True
            
            break
        
        #If positive result
        if positive_result:
            
            pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))

            #Get number of results
            page_html = requests.get(self.query.url)
            self.soup = BeautifulSoup(page_html.content, "lxml")
            results_count_raw = self.soup.find('div', {'id': 'paginationcontainer'})
            results_count_text = results_count_raw.get_text(strip = True)
            results_count_text = results_count_text.replace(',', '').replace('.', '')
            self.results_count = int(float(results_count_text.split(' ')[-2]))

            pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))            
            
            #Get case infos
            for decision in self.query.results():
                
                if len(self.case_infos) < min(self.judgment_counter_bound, self.results_count):
        
                    decision_w_meta = copy.deepcopy(decision.values)
        
                    self.case_infos.append(decision_w_meta)
                            
                else:
                    
                    break

    #Function for getting all requested judgments
    def get_judgments(self):

        self.case_infos_w_judgments = []

        #Search if not done yet
        if len(self.case_infos) == 0:

            self.search()
    
        #Create a list of mncs
        mnc_list = []
    
        for case_info in self.case_infos:

            if len(self.case_infos_w_judgments) < self.judgment_counter_bound:
                
                mnc = split_title_mnc(case_info['title'])[1]
                
                #Add mnc to list for HuggingFace
                mnc_list.append(mnc)
    
        if huggingface == False: #If not running on HuggingFace
    
            mnc_judgment_dict = {}
        
        else: #If running on HuggingFace    
        
            #Get judgments from oalc first
            mnc_judgment_dict = get_judgment_from_oalc(mnc_list)
    
        #Append judgment to self.case_infos_w_judgments 
        
        for case_info in self.case_infos:
            
            mnc = split_title_mnc(case_info['title'])[1]
            
            if mnc in mnc_judgment_dict.keys():
                
                case_info.update({'judgment': mnc_judgment_dict[mnc]})
                
                print(f"{case_info['title']} got judgment from OALC.")

                #Add case_info to self.case_infos_w_judgments
                self.case_infos_w_judgments.append(case_info)

            else: #Get case from Caselaw NSW if can't get from oalc
                
                for case in self.query.results():
    
                    case_meta = copy.deepcopy(case.values)
                    
                    if mnc == split_title_mnc(case_meta['title'])[1]:
                        
                        try:

                            case_info.update({'judgment': ''})
                            
                            case.fetch()
                                                        
                            for key in case.values.keys():
    
                                if key not in case_info.keys():
    
                                    case_info.update({key: case.values[key]})
                                
                            case_info.update({'judgment': str(case.values)})
    
                            print(f"{case_info['title']} got judgment from NSW Caselaw directly.")
                            
                        except:
                            
                            case_info.update({'judgment': ''})
                            
                            print(f'{case_info["title"]}: judgment text scraping error.')

                        #Add case_info to self.case_infos_w_judgments
                        self.case_infos_w_judgments.append(case_info)
                        
                        #Pause only if need to get judgment from Caselaw NSW
                        pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))
                
            print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.judgment_counter_bound, self.results_count)} judgments.")
    
        #Check length of judgment text, replace with text scraped from raw html if smaller than lower boound
        judgment_dicts_to_remove = []
        judgment_dicts_to_append = []
        for judgment_dict in self.case_infos_w_judgments:
    
            #Checking if judgment text is too short                
            judgment_raw_text = str(judgment_dict["judgment"])
                    
            if num_tokens_from_string(judgment_raw_text, "cl100k_base") < judgment_text_lower_bound:

                judgment_dicts_to_remove.append(judgment_dict)

                judgment_dict_updated = copy.deepcopy(judgment_dict)
                
                try:

                    pause.seconds(np.random.randint(scraper_pause_mean - 5, scraper_pause_mean + 5))
                    
                    judgment_type_text = nsw_short_judgment(judgment_dict["uri"])
        
                    #attach judgment text, judgment_type_text[0] has judgment type, eg 'pdf', while judgment_type_text[1] the text
                    judgment_dict_updated["judgment"] = judgment_type_text[1]
    
                    print(f'{judgment_dict["title"]}: given judgment tokens < {judgment_text_lower_bound}, scraped whole judgment from raw html.')                        
                    
                except Exception as e:
                    
                    judgment_dict_updated["judgment"] = ''
                    print(f'{judgment_dict["title"]}: while judgment tokens < {judgment_text_lower_bound}, cannot scrape whole judgment from raw html due to error: {e}')

                judgment_dicts_to_append.append(judgment_dict_updated)

            for judgment_dict in judgment_dicts_to_remove:

                if judgment_dict in self.case_infos_w_judgments:

                    #print(f'Removing judgment_dict["title"] == {judgment_dict["title"]} of length {len(str(judgment_dict))}')

                    self.case_infos_w_judgments.remove(judgment_dict)

            for judgment_dict_updated in judgment_dicts_to_append:

                if judgment_dict_updated not in self.case_infos_w_judgments:

                    #print(f'Appending judgment_dict_updated["title"] == {judgment_dict_updated["title"]} of length {len(str(judgment_dict_updated))}')
                    
                    self.case_infos_w_judgments.append(judgment_dict_updated)



# %%
#@st.cache_data(show_spinner = False)
def nsw_search_preview(df_master):
    
    df_master = df_master.fillna('')

    #Conduct search
    nsw_search = nsw_search_tool(courts = df_master.loc[0, 'Courts'], 
                   tribunals = df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, 'Free text'], 
                   title = df_master.loc[0, 'Case name'], 
                   before = df_master.loc[0, 'Before'], 
                   catchwords = df_master.loc[0, 'Catchwords'], 
                   party = df_master.loc[0, 'Party names'],
                   mnc = df_master.loc[0, 'Medium neutral citation'], 
                   startDate = df_master.loc[0, 'Decision date from'], 
                   endDate = df_master.loc[0, 'Decision date to'],
                   fileNumber = df_master.loc[0, 'File number'], 
                   legislationCited = df_master.loc[0, 'Legislation cited'], 
                   casesCited = df_master.loc[0, 'Cases cited'],
                #pause = 0,
                 judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                  )

    nsw_search.search()
    
    results_count = nsw_search.results_count
    
    case_infos = nsw_search.case_infos

    results_url = nsw_search.results_url

    #st.write(results_url)
    
    return {'results_url': results_url, 'results_count': results_count, 'case_infos': case_infos}



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import basic_model#, flagship_model#, role_content
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction
#system_instruction = role_content

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#function to tidy up after GPT output is produced

def nsw_tidying_up(df_master, df_individual):

    #Rename column titles
    try:
        df_individual['Hyperlink to NSW Caselaw'] = df_individual['uri'].apply(nsw_link)
        df_individual.pop('uri')
    except:
        pass

    #Replace abbreviated column names with full names
    for col_name in headnotes_keys:
        if col_name in df_individual.columns:
            col_index = headnotes_keys.index(col_name)
            new_col_name = headnotes_fields[col_index]
            df_individual.rename(columns={col_name: new_col_name}, inplace=True)
            #df_individual[new_col_name] = df_individual[col_name]
            #df_individual.pop(col_name)

    #Reorganise columns
    df_individual = df_individual.loc[:,~df_individual.columns.duplicated()].copy()

    old_columns = df_individual.columns.to_list()
    
    for i in ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw']:
        if i in old_columns:
            old_columns.remove(i)
    
    new_columns = ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw'] + old_columns
    
    df_individual = df_individual.reindex(columns=new_columns)

    #Drop metadata if not wanted 
    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in nsw_meta_labels_droppable:
            if meta_label in df_individual.columns:
                df_individual.pop(meta_label)

    #Remove judgment column
    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    if (pop_judgment() > 0) and ('judgment' in df_individual.columns):
        df_individual.pop("judgment")
        
    #Check case name, medium neutral citation 

    for k in df_individual.index:
        
        most_informative_key = ''

        if len(str(df_individual.loc[k, "Case name"])) > len(str(df_individual.loc[k, "Medium neutral citation"])):
            most_informative_key = "Case name"
        else:
            most_informative_key = "Medium neutral citation"
        
        case_name_mnc = split_title_mnc(df_individual.loc[k, most_informative_key])
        case_name = case_name_mnc[0]
        mnc = case_name_mnc[1]
        
        df_individual.loc[k, "Case name"] = case_name
        df_individual.loc[k, "Medium neutral citation"] = mnc

    return df_individual
    


# %%
#function to tidy up before GPT output is produced

def nsw_tidying_up_pre_gpt(df_master, df_individual):

    #Rename column titles
    try:
        df_individual['Hyperlink to NSW Caselaw'] = df_individual['uri'].apply(nsw_link)
        df_individual.pop('uri')
    except:
        pass

    #Replace abbreviated column names with full names
    for col_name in headnotes_keys:
        if col_name in df_individual.columns:
            col_index = headnotes_keys.index(col_name)
            new_col_name = headnotes_fields[col_index]
            df_individual.rename(columns={col_name: new_col_name}, inplace=True)

    #Reorganise columns
    old_columns = list(df_individual.columns)
    
    for i in ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw']:
        if i in old_columns:
            old_columns.remove(i)
    
    new_columns = ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw'] + old_columns
    
    df_individual = df_individual.reindex(columns=new_columns)

    #Drop metadata if not wanted
    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in nsw_meta_labels_droppable:
            if meta_label in df_individual.columns:
                df_individual.pop(meta_label)
        
    #Check case name, medium neutral citation 
    for k in df_individual.index:

        most_informative_key = ''

        if len(str(df_individual.loc[k, "Case name"])) > len(str(df_individual.loc[k, "Medium neutral citation"])):
            most_informative_key = "Case name"
        else:
            most_informative_key = "Medium neutral citation"
        
        case_name_mnc = split_title_mnc(df_individual.loc[k, most_informative_key])
        case_name = case_name_mnc[0]
        mnc = case_name_mnc[1]
        
        df_individual.loc[k, "Case name"] = case_name
        df_individual.loc[k, "Medium neutral citation"] = mnc

    return df_individual
    


# %%
#Download from Caselaw NSW if can't find judgment in OALC

@st.cache_data(show_spinner = False, ttl=600)
def nsw_run(df_master):
    
    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []

    #Conduct search
    nsw_search = nsw_search_tool(courts = df_master.loc[0, 'Courts'], 
                   tribunals = df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, 'Free text'], 
                   title = df_master.loc[0, 'Case name'], 
                   before = df_master.loc[0, 'Before'], 
                   catchwords = df_master.loc[0, 'Catchwords'], 
                   party = df_master.loc[0, 'Party names'],
                   mnc = df_master.loc[0, 'Medium neutral citation'], 
                   startDate = df_master.loc[0, 'Decision date from'], 
                   endDate = df_master.loc[0, 'Decision date to'],
                   fileNumber = df_master.loc[0, 'File number'], 
                   legislationCited = df_master.loc[0, 'Legislation cited'], 
                   casesCited = df_master.loc[0, 'Cases cited'],
                #pause = 0,
                 judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                  )

    nsw_search.get_judgments()
    
    for judgment_json in nsw_search.case_infos_w_judgments:

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

    #tidy up
    df_updated = nsw_tidying_up(df_master, df_updated)

    return df_updated


# %%
#For batch mode

@st.cache_data(show_spinner = False, ttl=600)
def nsw_batch(df_master):

    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []

    #Conduct search
    
    nsw_search = nsw_search_tool(courts = df_master.loc[0, 'Courts'], 
                   tribunals = df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, 'Free text'], 
                   title = df_master.loc[0, 'Case name'], 
                   before = df_master.loc[0, 'Before'], 
                   catchwords = df_master.loc[0, 'Catchwords'], 
                   party = df_master.loc[0, 'Party names'],
                   mnc = df_master.loc[0, 'Medium neutral citation'], 
                   startDate = df_master.loc[0, 'Decision date from'], 
                   endDate = df_master.loc[0, 'Decision date to'],
                   fileNumber = df_master.loc[0, 'File number'], 
                   legislationCited = df_master.loc[0, 'Legislation cited'], 
                   casesCited = df_master.loc[0, 'Cases cited'],
                #pause = 0,
                 judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                  )

    nsw_search.get_judgments()
    
    for judgment_json in nsw_search.case_infos_w_judgments:

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
    
    #Tidu up then send batch input to gpt
    df_individual = nsw_tidying_up_pre_gpt(df_master, df_individual)

    #Engage GPT
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)
    
    return batch_record_df_individual

