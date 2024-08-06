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

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
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
from common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner, list_range_check, au_date
#Import variables
from common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")


# %% [markdown]
# # UK Courts search engine

# %%
#function to create dataframe
def uk_create_df():

    #submission time
    timestamp = datetime.now()

    
    #Personal info entries

    name = ''
    
    email = ''

    gpt_api_key = ''

    try:
        name = name_entry
    except:
        print('Name not entered')
    
    try:
        email = email_entry
    except:
        print('Email not entered')

    try:
        gpt_api_key = gpt_api_key_entry
    except:
        print('API key not entered')
        
    #Own account status
    own_account = st.session_state.own_account
    
    #Judgment counter bound
    judgments_counter_bound = st.session_state.judgments_counter_bound

    #GPT enhancement
    gpt_enhancement = st.session_state.gpt_enhancement_entry
    
    #Free text

    query = query_entry
    
    #dates        
    
    from_day= '',
    from_month='', 
    from_year='', 

    if from_date_entry != 'None':

        try:
            from_day = str(from_date_entry.strftime('%d'))
            from_month = str(from_date_entry.strftime('%m'))
            from_year = str(from_date_entry.strftime('%Y'))

        except:
            pass

    
    to_day= '',
    to_month='', 
    to_year='', 

    if to_date_entry != 'None':

        try:
            to_day = str(to_date_entry.strftime('%d'))
            to_month = str(to_date_entry.strftime('%m'))
            to_year = str(to_date_entry.strftime('%Y'))

        except:
            pass
    
    #Courts
    courts_list = courts_entry
    court_string = ', '.join(courts_list)
    court = court_string
    
    #Other entries
    party = party_entry
    judge =  judge_entry

    #GPT choice and entry
    try:
        gpt_activation_status = gpt_activation_entry
    except:
        gpt_activation_status = False
    
    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry[0: question_characters_bound]
    
    except:
        print('GPT questions not entered.')
        
    #metadata choice

    meta_data_choice = meta_data_entry
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Free text': query,
           'From day': from_day, 
            'From month': from_month,
            'From year': from_year,
            'To day': to_day,
            'To month': to_month,
            'To year' : to_year,
            'Courts' : court, 
            'Party' : party,
            'Judge' : judge, 
            'Metadata inclusion' : meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status, 
          'Use own account': own_account,
            'Use flagship version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
    
#    df_master_new.to_json(current_dir + '/df_master.json', orient = 'split', compression = 'infer')
#    df_master_new.to_excel(current_dir + '/df_master.xlsx', index=False)

#    if len(df_master_new) > 0:
        
    return df_master_new

#    else:
#        return 'Error: spreadsheet of reponses NOT generated.' 

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
'Court of Appeal Civil Division': 'ewca%2Fciv', 
 'Court of Appeal Criminal Division':  'ewca%2Fcrim',  
'High Court (England & Wales) Administrative Court': 'ewhc%2Fadmin',
'High Court (England & Wales) Admiralty Court': 'ewhc%2Fadmlty',  
'High Court (England & Wales) Chancery Division': 'ewhc%2Fch',  
'High Court (England & Wales) Commercial Court': 'ewhc%2Fcomm',  
'High Court (England & Wales) Family Division': 'ewhc%2Ffam',  
'High Court (England & Wales) Intellectual Property Enterprise Court': 'ewhc%2Fipec',  
"High Court (England & Wales) King's/Queen's Bench Division" : 'ewhc%2Fkb',
'High Court (England & Wales) Mercantile Court': 'ewhc%2Fmercantile',  
'High Court (England & Wales) Patents Court': 'ewhc%2Fpat',  
'High Court (England & Wales) Senior Courts Costs Office': 'ewhc%2Fscco',  
'High Court (England & Wales) Technology and Construction Court': 'ewhc%2Ftcc',  
'Court of Protection': 'ewcop',  
'Family Court': 'ewfc',  
'Employment Appeal Tribunal': 'eat',  
'Administrative Appeals Chamber': 'ukut%2Faac',  
'Immigration and Asylum Chamber': 'ukut%2Fiac',
'Lands Chamber': 'ukut%2Flc',  
'Tax and Chancery Chamber': 'ukut%2Ftcc',  
'General Regulatory Chamber': 'ukftt%2Fgrc',  
'Tax Chamber' : 'ukftt%2Ftc'
}

uk_courts_list = list(uk_courts.keys())

def uk_court_choice(x):
    individual_choice = []
    if len(x) < 5:
        pass #If want no court to be covered absent choice
        #for i in uk_courts.keys():
            #individual_choice.append(uk_courts[i])
    else:
        y = x.split(', ')
        for j in y:
            individual_choice.append(uk_courts[j])
    
    return individual_choice


#Tidy up hyperlink
def uk_link(x):
    y =str(x).replace('.uk/id', '.uk')
    value = '=HYPERLINK("' + y + '")'
    return value



# %%
#Function turning search terms to search results url
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

    proper_url = str(response.url).replace('%25', '%')
    
    return proper_url


# %%
url_search_results = 'https://caselaw.nationalarchives.gov.uk/judgments/search?per_page=50&order=relevance&query=constitution&from_day=&from_month=&from_year=&to_day=&to_month=&to_year=&court=uksc&court=ukpc&court=ewca%2Fciv&court=ewca%2Fcrim&court=ewhc%2Fadmin&court=ewhc%2Fadmlty&court=ewhc%2Fch&court=ewhc%2Fcomm&court=ewhc%2Ffam&court=ewhc%2Fipec&court=ewhc%2Fkb&court=ewhc%2Fmercantile&court=ewhc%2Fpat&court=ewhc%2Fscco&court=ewhc%2Ftcc&party=&judge='


# %%
#Define function turning search results url to links to judgments
def uk_search_results_to_judgment_links(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")
    hrefs = soup.find_all('a', href=True)
    links = []

    #Get total number of pages
    page_nums_raw = soup.find_all('li', attrs={'class': 'pagination__list-item'})
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
        if ((counter <= judgment_counter_bound) and ('a href="/' in str(link)) and '">' in str(link) and '?' in str(link)):
            link_direct = 'https://caselaw.nationalarchives.gov.uk' + str(link).split('?')[0][9:] + '/data.xml'
            links.append(link_direct.replace('.uk/id', '.uk'))
            counter = counter + 1

    if page_total > 1:  
    
        for page_ending in range(page_total):
            
            if counter <=judgment_counter_bound:
                
                url_next_page = url_search_results + f"&page={page_ending + 1}"
                
                page_judgment_next_page = requests.get(url_next_page)
                soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
        
                #Check if stll more results
                if 'No results have been found' not in str(soup_judgment_next_page):
                    hrefs_next_page = soup_judgment_next_page.find_all('a', href=True)
                    for extra_link in hrefs_next_page:
                        if ((counter <= judgment_counter_bound) and ('a href="/' in str(extra_link)) and '">' in str(extra_link) and '?' in str(extra_link)):
                            extra_link_direct = 'https://caselaw.nationalarchives.gov.uk' + str(extra_link).split('?')[0][9:] + '/data.xml'
                            links.append(extra_link_direct.replace('.uk/id', '.uk'))
                            counter = counter + 1
    
                else:
                    break
                
                pause.seconds(np.random.randint(10, 20))

    return links


# %%
#Meta labels and judgment combined

uk_meta_labels_droppable = ['Date', 
                         'Court', 
                         'Case number', 
                         'Judge(s) (non-exhaustiveive)', 
                         'Parties', 
                         'Header'
                        ]

    
def uk_meta_judgment_dict(judgment_url_xml):
    page = requests.get(judgment_url_xml)
    soup = BeautifulSoup(page.content, "lxml")
    
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
    try:
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
    
    #Get judgment content as a list of headings and paras, but not enumeration/paragraph number
    #for text in soup.find_all('content'):
    #    judgment_dict['judgment'].append(text.getText())

    #Get judgment

    pause.seconds(np.random.randint(5, 10))

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
    
    #try:
     #   judgment_text = str(soup.find_all('content'))
    #except:
      #  judgment_text= soup.get_text(strip=True)
        
    return judgment_dict


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from gpt_functions import question_characters_bound, default_judgment_counter_bound, role_content#, intro_for_GPT


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

# %%
#For checking questions and answers
from common_functions import check_questions_answers

from gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction

if check_questions_answers() > 0:
    print(f'By default, questions and answers are checked for potential privacy violation.')
else:
    print(f'By default, questions and answers are NOT checked for potential privacy violation.')


# %%
#Jurisdiction specific instruction
system_instruction = role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-4o-mini"
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#Upperbound on number of judgments to scrape
if 'judgments_counter_bound' not in st.session_state:
    st.session_state['judgments_counter_bound'] = default_judgment_counter_bound


# %%
#Obtain parameters

def uk_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    url_search_results = uk_search(query= df_master.loc[0, 'Free text'], 
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
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    judgments_links = uk_search_results_to_judgment_links(url_search_results, judgments_counter_bound)

    for link in judgments_links:

        judgment_dict = uk_meta_judgment_dict(link)

#        meta_data = meta_dict(link)  
#        doc_link = link_to_doc(link)
#        judgment_dict = doc_link_to_dict(doc_link)
#        judgment_dict = link_to_dict(link)
#        judgments_all_info = { **meta_data, **judgment_dict}
#        judgments_file.append(judgments_all_info)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(10, 20))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #For UK, convert date to string so as to avoid Excel producing random numbers for dates
    df_individual['Date'] = df_individual['Date'].astype(str)
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-4o-mini"
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in uk_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
def uk_search_url(df_master):

    df_master = df_master.fillna('')

    df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)
    
    #Combining catchwords into new column
    
    #Conduct search
    
    url = uk_search(query= df_master.loc[0, 'Free text'], 
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
    return url


# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from common_functions import open_page, clear_cache_except_validation_df_master, tips


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default_courts

if 'default_courts' not in st.session_state:
    st.session_state['default_courts'] = []

# %%
#Initialize default values

if 'gpt_enhancement_entry' not in st.session_state:
    st.session_state['gpt_enhancement_entry'] = False

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_master' not in st.session_state:

    #Generally applicable
    st.session_state['df_master'] = pd.DataFrame([])
    st.session_state['df_master'].loc[0, 'Your name'] = ''
    st.session_state['df_master'].loc[0, 'Your email address'] = ''
    st.session_state['df_master'].loc[0, 'Your GPT API key'] = ''
    st.session_state['df_master'].loc[0, 'Metadata inclusion'] = True
    st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound
    st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = ''
    st.session_state['df_master'].loc[0, 'Use GPT'] = False
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False

    #Jurisdiction specific
    st.session_state.df_master.loc[0, 'Free text'] = None 
    st.session_state.df_master.loc[0, 'From day'] = None
    st.session_state.df_master.loc[0, 'From month'] = None 
    st.session_state.df_master.loc[0, 'From year'] = None 
    st.session_state.df_master.loc[0, 'To day'] = None 
    st.session_state.df_master.loc[0, 'To month'] = None 
    st.session_state.df_master.loc[0, 'To year'] = None 
    st.session_state.df_master.loc[0, 'Courts'] = '' 
    st.session_state.df_master.loc[0, 'Party'] = None 
    st.session_state.df_master.loc[0, 'Judge'] = None

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])
    
#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
if st.session_state.page_from != "pages/UK.py": #Need to add in order to avoid GPT page from showing form of previous page

    #Create form for court selection
    
    return_button = st.button('RETURN to first page')
    
    st.header(f"You have selected to study :blue[judgments of select United Kingdom courts and tribunals].")
    
    #st.header("Judgment Search Criteria")
    
    st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.
""")
    
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments.')
    
    reset_button = st.button(label='RESET', type = 'primary')

    st.subheader("Courts and tribunals to cover")
    
    default_on = st.checkbox('Prefill the Supreme Court, the Privy Council, the Court of Appeal, the High Court of England & Wales')
    
    if default_on:
    
        st.session_state.default_courts = uk_courts_default_list
    
    else:
        st.session_state.default_courts = list_range_check(uk_courts, st.session_state['df_master'].loc[0, 'Courts'])
    
    courts_entry = st.multiselect(label = 'Select or type in the courts and tribunals to cover', options = uk_courts_list, default = st.session_state.default_courts)
        
    #st.caption("All courts and tribunals listed in this menu will be covered if left blank.")
    
    #Search terms
    
    st.subheader("Your search terms")
    
    st.markdown("""For search tips, please visit [The National Archives](https://caselaw.nationalarchives.gov.uk/structured_search). This section mimics their search function.
""")
    
    query_entry = st.text_input(label = 'Free text', value = st.session_state.df_master.loc[0, 'Free text'])
    
    from_date_entry = st.date_input('From day', value = au_date(f"{st.session_state.df_master.loc[0, 'From day']}/{st.session_state.df_master.loc[0, 'From month']}/{st.session_state.df_master.loc[0, 'From year']}"), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now())
    
    to_date_entry = st.date_input('To day', value = au_date(f"{st.session_state.df_master.loc[0, 'To day']}/{st.session_state.df_master.loc[0, 'To month']}/{st.session_state.df_master.loc[0, 'To year']}"), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now())
    
    st.caption('[Relatively earlier](https://caselaw.nationalarchives.gov.uk/structured_search) judgments are not available.')
    
    judge_entry = st.text_input(label = 'Judge name', value = st.session_state.df_master.loc[0, 'Judge'])
    
    party_entry = st.text_input(label = 'Party name', value = st.session_state.df_master.loc[0, 'Party'])
    
    st.markdown("""You can preview the judgments returned by your search terms on The National Archives after you have entered some search terms.
    
You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")
    
    preview_button = st.button(label = 'PREVIEW on The National Archives (in a popped up window)', type = 'primary')
    
    st.subheader("Judgment metadata collection")
    
    st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the names of the parties and so on. 
    
Case name and medium neutral citation are always included with your results.
""")

    meta_data_entry = st.checkbox('Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])


# %% [markdown]
# ## Buttons

    # %%
    #Buttons
    
    #col1, col2, col3, col4 = st.columns(4, gap = 'small')
    
    #with col1:
    
        #reset_button = st.button(label='RESET', type = 'primary')
    
    #with col4:
    with stylable_container(
        "green",
        css_styles="""
        button {
            background-color: #00FF00;
            color: black;
        }""",
    ):
        next_button = st.button(label='NEXT')
    
    keep_button = st.button('SAVE')


# %% [markdown]
# # Save and run

    # %%
    if preview_button:
    
        df_master = uk_create_df()
    
        judgments_url = uk_search_url(df_master)
    
        open_page(judgments_url)


    # %%
    if keep_button:
    
        all_search_terms = str(query_entry) + str(from_date_entry) + str(to_date_entry) + str(judge_entry) + str(party_entry)
            
        if all_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
    
        elif len(courts_entry) == 0:
            st.write('Please select at least one court to cover.')
                
        else:
                                
            df_master = uk_create_df()

            st.session_state['df_master'] = df_master
        
            df_master.pop("Your GPT API key")
        
            df_master.pop("Processed")
        
            responses_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'
        
            #Produce a file to download
        
            csv = convert_df_to_csv(df_master)
            
            ste.download_button(
                label="Download as a CSV (for use in Excel etc)", 
                data = csv,
                file_name=responses_output_name + '.csv', 
                mime= "text/csv", 
        #            key='download-csv'
            )
    
            xlsx = convert_df_to_excel(df_master)
            
            ste.download_button(label='Download as an Excel spreadsheet (XLSX)',
                                data=xlsx,
                                file_name=responses_output_name + '.xlsx', 
                                mime='application/vnd.ms-excel',
                               )
        
            json = convert_df_to_json(df_master)
            
            ste.download_button(
                label="Download as a JSON", 
                data = json,
                file_name= responses_output_name + '.json', 
                mime= "application/json", 
            )


    # %%
    if return_button:
    
        st.switch_page("Home.py")

    # %%
    if reset_button:
        st.session_state.pop('df_master')

        #clear_cache()
        st.rerun()

    # %%
    if next_button:
    
        all_search_terms = str(query_entry) + str(from_date_entry) + str(to_date_entry) + str(judge_entry) + str(party_entry)
            
        if all_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
    
        elif len(courts_entry) == 0:
            st.write('Please select at least one court to cover.')
        
        else:
    
            df_master = uk_create_df()
            
            st.session_state['df_master'] = df_master
            
            st.session_state["page_from"] = 'pages/UK.py'
            
            st.switch_page('pages/GPT.py')
