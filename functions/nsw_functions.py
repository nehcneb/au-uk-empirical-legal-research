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
import pypdf
import io
from io import BytesIO

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste
from streamlit_extras.stylable_container import stylable_container

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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_range_check, au_date, save_input, split_title_mnc
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # CaseLaw NSW functions and parameters

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

#For positioning
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


# %%
#Create function to convert the string of chosen courts to a list; 13 = NSWSC, 3 = NSWCA, 4 = NSWCCA
#For more, see https://github.com/Sydney-Informatics-Hub/nswcaselaw/blob/main/src/nswcaselaw/constants.py

def nsw_court_choice(x):
    individual_choice = []

    if len(x) < 5:
        pass #If want to select no court absent any choice
        #individual_choice = [3, 4, 13] #If want to select NSWSC, CA and CCA absent any choice
        #for j in range(1, len(nsw_courts_positioning)):
            #individual_choice.append(j) #If want to select all courts absent any choice
    else:
        y = x.split(', ')
        for i in y:
            individual_choice.append(nsw_courts_positioning.index(i))            
    
    return individual_choice

def nsw_tribunal_choice(x):
    individual_choice = []

    if len(x) < 5:
        pass #If want to select no tribunal absent any choice
        #for j in range(1, len(nsw_tribunals_positioning)):
            #individual_choice.append(j) #If want to select all tribunals absent any choice
    else:
        y = x.split(', ')
        for i in y:
            individual_choice.append(nsw_tribunals_positioning.index(i))            
    
    return individual_choice

#Functions for tidying up

#Tidy up dates
def nsw_date(x):
    if len(str(x)) >0:
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



# %%
#Define function for short judgments, which checks if judgment is in PDF
#returns a list of judgment type and judgment text

@st.cache_data(show_spinner = False)
def nsw_short_judgment(uri):
    
    html_link = 'https://www.caselaw.nsw.gov.au'+ uri
    page_html = requests.get(html_link)
    soup_html = BeautifulSoup(page_html.content, "lxml")

    judgment_type = ''

    #Check if judgment contains PDF link
    PDF_raw_link = soup_html.find('a', string='See Attachment (PDF)')
    
    if str(PDF_raw_link).lower() != 'none':
        PDF_link = 'https://www.caselaw.nsw.gov.au' + PDF_raw_link.get('href')    
        headers = {'User-Agent': 'whatever'}
        r = requests.get(PDF_link, headers=headers)
        remote_file_bytes = io.BytesIO(r.content)
        pdfdoc_remote = pypdf.PdfReader(remote_file_bytes)
        text_list = []
        
        for page in pdfdoc_remote.pages:
            text_list.append(page.extract_text())

        judgment_type = 'pdf'
        
        return [judgment_type, str(text_list)]

    #Return html text if no PDF
    else:
        judgment_text = soup_html.get_text(separator="\n", strip=True)
        judgment_type = 'html'

        return [judgment_type, judgment_text]


# %%
def nsw_search_url(df_master):
    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Courts'] = df_master['Courts'].apply(nsw_court_choice)
    df_master['Tribunals'] = df_master['Tribunals'].apply(nsw_tribunal_choice)

    #df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    #df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Combining catchwords into new column
    
    search_dict = {'body': df_master.loc[0, 'Free text']}
    search_dict.update({'title': df_master.loc[0, 'Case name']})
    search_dict.update({'before': df_master.loc[0, 'Before']})
    search_dict.update({'catchwords': df_master.loc[0, 'Catchwords']})
    search_dict.update({'party': df_master.loc[0, 'Party names']})
    search_dict.update({'mnc': df_master.loc[0, 'Medium neutral citation']})
    search_dict.update({'startDate': df_master.loc[0, 'Decision date from']})
    search_dict.update({'endDate': df_master.loc[0, 'Decision date to']})
    search_dict.update({'fileNumber': df_master.loc[0, 'File number']})
    search_dict.update({'legislationCited': df_master.loc[0, 'Legislation cited']})
    search_dict.update({'casesCited': df_master.loc[0, 'Cases cited']})
    df_master.loc[0, 'SearchCriteria']=[search_dict]

    #Conduct search
    
    query = Search(courts=df_master.loc[0, 'Courts'], 
                   tribunals=df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, "SearchCriteria"]['body'], 
                   title = df_master.loc[0, "SearchCriteria"]['title'], 
                   before = df_master.loc[0, "SearchCriteria"]['before'], 
                   catchwords = df_master.loc[0, "SearchCriteria"]['catchwords'], 
                   party = df_master.loc[0, "SearchCriteria"]['party'], 
                   mnc = df_master.loc[0, "SearchCriteria"]['mnc'], 
                   startDate = nsw_date(df_master.loc[0, "SearchCriteria"]['startDate']), 
                   endDate = nsw_date(df_master.loc[0, "SearchCriteria"]['endDate']),
                   fileNumber = df_master.loc[0, "SearchCriteria"]['fileNumber'], 
                   legislationCited  = df_master.loc[0, "SearchCriteria"]['legislationCited'], 
                   casesCited = df_master.loc[0, "SearchCriteria"]['legislationCited'],
                   pause = 0
                  )
    
    return query.url


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import question_characters_bound, role_content#, intro_for_GPT
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input


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
#function to tidy up output

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

    old_columns = list(df_individual.columns)
    
    for i in ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw']:
        if i in old_columns:
            old_columns.remove(i)
    
    new_columns = ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw'] + old_columns
    
    df_individual = df_individual.reindex(columns=new_columns)

    #Drop metadata if not wanted
    
    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in nsw_meta_labels_droppable:
            try:
                df_individual.pop(meta_label)
            except:
                pass
    
    #Remove judgment column
    if 'judgment' in df_individual.columns:
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
#function to tidy up output

def nsw_tidying_up_prebatch(df_master, df_individual):

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

    old_columns = list(df_individual.columns)
    
    for i in ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw']:
        if i in old_columns:
            old_columns.remove(i)
    
    new_columns = ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw'] + old_columns
    
    df_individual = df_individual.reindex(columns=new_columns)

    #Drop metadata if not wanted
    
    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in nsw_meta_labels_droppable:
            try:
                df_individual.pop(meta_label)
            except:
                pass
        
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
#Obtain parameters

@st.cache_data(show_spinner = False)
def nsw_run(df_master):
    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Courts'] = df_master['Courts'].apply(nsw_court_choice)
    df_master['Tribunals'] = df_master['Tribunals'].apply(nsw_tribunal_choice)
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Do search

    search_dict = {'body': df_master.loc[0, 'Free text']}
    search_dict.update({'title': df_master.loc[0, 'Case name']})
    search_dict.update({'before': df_master.loc[0, 'Before']})
    search_dict.update({'catchwords': df_master.loc[0, 'Catchwords']})
    search_dict.update({'party': df_master.loc[0, 'Party names']})
    search_dict.update({'mnc': df_master.loc[0, 'Medium neutral citation']})
    search_dict.update({'startDate': df_master.loc[0, 'Decision date from']})
    search_dict.update({'endDate': df_master.loc[0, 'Decision date to']})
    search_dict.update({'fileNumber': df_master.loc[0, 'File number']})
    search_dict.update({'legislationCited': df_master.loc[0, 'Legislation cited']})
    search_dict.update({'casesCited': df_master.loc[0, 'Cases cited']})
    df_master.loc[0, 'SearchCriteria']=[search_dict]

    #Conduct search
    
    query = Search(courts=df_master.loc[0, 'Courts'], 
                   tribunals=df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, "SearchCriteria"]['body'], 
                   title = df_master.loc[0, "SearchCriteria"]['title'], 
                   before = df_master.loc[0, "SearchCriteria"]['before'], 
                   catchwords = df_master.loc[0, "SearchCriteria"]['catchwords'], 
                   party = df_master.loc[0, "SearchCriteria"]['party'], 
                   mnc = df_master.loc[0, "SearchCriteria"]['mnc'], 
                   startDate = nsw_date(df_master.loc[0, "SearchCriteria"]['startDate']), 
                   endDate = nsw_date(df_master.loc[0, "SearchCriteria"]['endDate']),
                   fileNumber = df_master.loc[0, "SearchCriteria"]['fileNumber'], 
                   legislationCited  = df_master.loc[0, "SearchCriteria"]['legislationCited'], 
                   casesCited = df_master.loc[0, "SearchCriteria"]['legislationCited'],
                   pause = 0
                  )

    #Create judgments file
    judgments_file = []

    #Counter to limit search results to append
    counter = 0

    #Go through search results
    
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
    
    for decision in query.results():
        if counter < judgments_counter_bound:
            #Get case info from results page
            decision_v = decision.values

            #Get case info from individual case page
            decision.fetch()

            #Attach new info
            decision_v_new = decision.values
            for key in decision_v_new.keys():
                if key not in decision_v.keys():
                    decision_v.update({key: decision_v_new[key]})
                                    
            #add search results to json
            judgments_file.append(decision_v)
            counter +=1
    
            pause.seconds(np.random.randint(5, 15))
            
        else:
            
            break

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Check length of judgment text, replace with raw html if smaller than lower boound

    for judgment_index in df_individual.index:

        #Checking if judgment text has been scrapped or too short
        try:
            judgment_raw_text = str(df_individual.loc[judgment_index, "judgment"])
                    
            if num_tokens_from_string(judgment_raw_text, "cl100k_base") < judgment_text_lower_bound:

                judgment_type_text = nsw_short_judgment(df_individual.loc[judgment_index, "uri"])
    
                #attach judgment text
                df_individual.loc[judgment_index, "judgment"] = judgment_type_text[1]

                #judgment_type_text[0] has judgment type, eg 'pdf'
                
                pause.seconds(np.random.randint(5, 15))
            
        except Exception as e:
            
            df_individual.loc[judgment_index, "judgment"] = ['Error. Judgment text not scrapped.']
            print(f'{df_individual.loc[judgment_index, "title"]}: judgment text scraping error.')
            print(e)
    
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

    #tidy up
    df_updated = nsw_tidying_up(df_master, df_updated)

    if 'judgment' in df_updated.columns:
        df_updated.pop('judgment')
    
    return df_updated
    


# %%
#Obtain parameters

@st.cache_data(show_spinner = False)
def nsw_batch(df_master):

    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Courts'] = df_master['Courts'].apply(nsw_court_choice)
    df_master['Tribunals'] = df_master['Tribunals'].apply(nsw_tribunal_choice)
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Do search

    search_dict = {'body': df_master.loc[0, 'Free text']}
    search_dict.update({'title': df_master.loc[0, 'Case name']})
    search_dict.update({'before': df_master.loc[0, 'Before']})
    search_dict.update({'catchwords': df_master.loc[0, 'Catchwords']})
    search_dict.update({'party': df_master.loc[0, 'Party names']})
    search_dict.update({'mnc': df_master.loc[0, 'Medium neutral citation']})
    search_dict.update({'startDate': df_master.loc[0, 'Decision date from']})
    search_dict.update({'endDate': df_master.loc[0, 'Decision date to']})
    search_dict.update({'fileNumber': df_master.loc[0, 'File number']})
    search_dict.update({'legislationCited': df_master.loc[0, 'Legislation cited']})
    search_dict.update({'casesCited': df_master.loc[0, 'Cases cited']})
    df_master.loc[0, 'SearchCriteria']=[search_dict]

    #Conduct search
    
    query = Search(courts=df_master.loc[0, 'Courts'], 
                   tribunals=df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, "SearchCriteria"]['body'], 
                   title = df_master.loc[0, "SearchCriteria"]['title'], 
                   before = df_master.loc[0, "SearchCriteria"]['before'], 
                   catchwords = df_master.loc[0, "SearchCriteria"]['catchwords'], 
                   party = df_master.loc[0, "SearchCriteria"]['party'], 
                   mnc = df_master.loc[0, "SearchCriteria"]['mnc'], 
                   startDate = nsw_date(df_master.loc[0, "SearchCriteria"]['startDate']), 
                   endDate = nsw_date(df_master.loc[0, "SearchCriteria"]['endDate']),
                   fileNumber = df_master.loc[0, "SearchCriteria"]['fileNumber'], 
                   legislationCited  = df_master.loc[0, "SearchCriteria"]['legislationCited'], 
                   casesCited = df_master.loc[0, "SearchCriteria"]['legislationCited'],
                   pause = 0
                  )

    #Create judgments file
    judgments_file = []

    #Counter to limit search results to append
    counter = 0

    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    #Check if running on HuggingFace
    from functions.oalc_functions import huggingface
    
    if huggingface == False: #If not running on HuggingFace

        for decision in query.results():
            if counter < judgments_counter_bound:
                #Get case info from results page
                decision_v = decision.values
    
                #Get case info from individual case  page
                decision.fetch()
    
                #Attach new info
                decision_v_new = decision.values
                for key in decision_v_new.keys():
                    if key not in decision_v.keys():
                        decision_v.update({key: decision_v_new[key]})
                                        
                #add search results to json
                judgments_file.append(decision_v)
                counter +=1
        
                pause.seconds(np.random.randint(5, 15))
                
            else:
                break

    else: #If running on HuggingFace
        
        #Load oalc
        from functions.oalc_functions import load_corpus, get_judgment_from_oalc

        #Create a list of mncs for HuggingFace:
        mnc_list = []

        #Create list of relevant cases
        for decision in query.results():
            
            if counter < judgments_counter_bound:
    
                #Append to judgments_file to create df_individual
                decision_v = decision.values
    
                #Create and mnc
                mnc = split_title_mnc(decision_v['title'])[1]
                decision_v.update({'mnc': mnc})
                
                #add search results to json
                judgments_file.append(decision_v)

                #Add mnc to list for HuggingFace
                mnc_list.append(mnc)
                
                counter +=1            
                
            else:
                break

        #Get judgments from oalc first
        mnc_judgment_dict = get_judgment_from_oalc(mnc_list)
    
        #Append judgment to judgments_file 
        for decision in judgments_file:
            
            #Append judgments from oalc first
            if decision['mnc'] in mnc_judgment_dict.keys():
                decision.update({'judgment': mnc_judgment_dict[decision['mnc']]})
                
            else: #Get the first case from Caselaw NSW if can't get from oalc
                
                case_query = Search(mnc = decision['mnc'])
                
                for case in query.results():
                    case.fetch()
                    case_v = decision.values

                    #Append judgment and other keys
                    for key in case_v:
                        if key not in decision.keys():
                            decision.update({key: case_v[key]})
                    
                    break

                pause.seconds(np.random.randint(5, 15))

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Check length of judgment text, replace with raw html if smaller than lower boound

    for judgment_index in df_individual.index:

        #Checking if judgment text has been scrapped or too short
        try:
            
            judgment_raw_text = str(df_individual.loc[judgment_index, "judgment"])
                    
            if num_tokens_from_string(judgment_raw_text, "cl100k_base") < judgment_text_lower_bound:

                judgment_type_text = nsw_short_judgment(df_individual.loc[judgment_index, "uri"])
    
                #attach judgment text
                df_individual.loc[judgment_index, "judgment"] = judgment_type_text[1]

                #judgment_type_text[0] has judgment type, eg 'pdf'
                
                pause.seconds(np.random.randint(5, 15))
            
        except Exception as e:
            
            df_individual.loc[judgment_index, "judgment"] = ['Error. Judgment text not scrapped.']
            print(f'{df_individual.loc[judgment_index, "title"]}: judgment text scraping error.')
            print(e)

    #tidy up
    df_individual = nsw_tidying_up_prebatch(df_master, df_individual)
    
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o-2024-08-06"
    else:        
        gpt_model = "gpt-4o-mini"
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    questions_json = df_master.loc[0, 'questions_json']
            
    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)
    
    return batch_record_df_individual

