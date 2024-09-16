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
import PyPDF2
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # Canada search engine

# %%
from functions.ca_functions import all_ca_jurisdictions, ca_courts, bc_courts, ab_courts, sk_courts, mb_courts, on_courts, qc_courts, nb_courts, ns_courts, pe_courts, nl_courts, yk_courts, nt_courts, nu_courts, all_ca_jurisdiction_court_pairs, ca_court_tribunal_types, all_subjects, ca_search, ca_search_url, ca_search_results_to_judgment_links, ca_meta_labels_droppable, ca_meta_dict, ca_date, ca_meta_judgment_dict


# %%
#Scrape javascript

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By

options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--headless")
options.add_argument('--no-sandbox')  
options.add_argument('--disable-dev-shm-usage')  

@st.cache_resource
def get_driver():
    return webdriver.Chrome(
        #service=Service(
            #ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        #),
        options=options,
    )

browser = get_driver()

browser.implicitly_wait(10)
browser.set_page_load_timeout(10)



# %%
from functions.common_functions import link


# %%
#function to create dataframe
def ca_create_df():

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
    try:
        judgments_counter_bound = judgments_counter_bound_entry
    except:
        print('judgments_counter_bound not entered')
        judgments_counter_bound = default_judgment_counter_bound

    #GPT enhancement
    try:
        gpt_enhancement = gpt_enhancement_entry
    except:
        print('GPT enhancement not entered')
        gpt_enhancement = False
        
    #Juridiction
    jurisdiction = jurisdiction_entry
    
    #Court
    court = st.session_state.court

    #Year entry
    #year = st.session_state.year

    #Can't get noteup/discussion to work given dynamic
    #Noteup entry

    #cite = cited_entry
        
    #Other entries
    case_name_mnc = case_name_mnc_entry
    phrase = phrase_entry

    #Court/tribunal types
    if court_tribunal_type_entry == None:
        
        court_tribunal_type = 'All courts and tribunals'
    else:
        court_tribunal_type = court_tribunal_type_entry
    
    #dates
    
    on_this_date = ''

    if on_this_date_entry != 'None':

        try:

            on_this_date = on_this_date_entry.strftime("%Y-%m-%d")

        except:
            pass
        
    
    before_date = ''

    if before_date_entry != 'None':

        try:

            before_date = before_date_entry.strftime("%Y-%m-%d")
            
        except:
            pass

    
    after_date = ''

    if after_date_entry != 'None':
        
        try:
            after_date = after_date_entry.strftime("%Y-%m-%d")
            
        except:
            pass

    #Subjects

    subjects = ''

    try:
        
        subjects = ",".join(subjects_entry)
        
    except:
        
        pass
    
    #GPT choice and entry
    try:
        gpt_activation_status = gpt_activation_entry
    except:
        gpt_activation_status = False
    
    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry[0: 1000]
    
    except:
        print('GPT questions not entered.')

    #metadata choice

    meta_data_choice = meta_data_entry
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Jurisdiction': jurisdiction, 
           'Courts': court, 
           'Case name, citation or docket': case_name_mnc, 
            'Document text': phrase,
               'Court or tribunal type': court_tribunal_type, 
           'Decision date is': on_this_date,
            'Decision date is after': after_date,
            'Decision date is before': before_date,
               'Subjects': subjects, 
            #'Noteup/Discussion': cited, 
            #'Year': year,
            'Metadata inclusion' : meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status,
           'Use own account': own_account,
            'Use flagship version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
            
    return df_master_new


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
#Jurisdiction specific instruction and functions

system_instruction = role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-4o-mini"
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from functions.common_functions import open_page, tips, clear_cache, list_value_check


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

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
    st.session_state['df_master'].loc[0, 'Jurisdiction'] = 'All'
    st.session_state['df_master'].loc[0, 'Courts'] = 'All' 
    st.session_state['df_master'].loc[0, 'Document text'] = None 
    st.session_state['df_master'].loc[0, 'Case name, citation or docket'] = None
    st.session_state['df_master'].loc[0, 'Subjects'] = ''
    st.session_state['df_master'].loc[0, 'Court or tribunal type'] = None 
    st.session_state['df_master'].loc[0, 'Decision date is'] = None
    st.session_state['df_master'].loc[0, 'Decision date is after'] = None
    st.session_state['df_master'].loc[0, 'Decision date is before'] = None

    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})
    
if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

# %%
#Canada specific session states

#Disable toggles
if 'all_jurisdiction' not in st.session_state:
    st.session_state["all_jurisdiction"] = 'All'

#Disable toggles
if 'court' not in st.session_state:
    st.session_state["court"] = 'All'

if 'year' not in st.session_state:
    st.session_state["year"] = ''


# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
#if st.session_state.page_from != "pages/CA.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form

return_button = st.button('RETURN to first page')

st.header(f"You have selected to study :blue[judgments of the Canadian courts, boards and tribunals].")

#    st.header("Judgment Search Criteria")

st.markdown("""**:green[Please enter your search terms.]** This app will collect (ie scrape) the first 10 judgments returned by your search terms.
""")

st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Court, board or tribunal to cover")

jurisdiction_entry  = st.selectbox(label = 'Select or type in the jurisdiction to cover', options = list(list(all_ca_jurisdictions.keys())), index = list_value_check(list(all_ca_jurisdictions.keys()), st.session_state['df_master'].loc[0, 'Jurisdiction']))

st.session_state["all_jurisdiction"] = jurisdiction_entry

if st.session_state.all_jurisdiction != 'All':
    
    courts_entry = st.selectbox(label = 'Select or type in the court, board or tribunal to cover', options = list(all_ca_jurisdiction_court_pairs[st.session_state.all_jurisdiction].keys()), index = list_value_check(list(all_ca_jurisdiction_court_pairs[st.session_state.all_jurisdiction].keys()), st.session_state['df_master'].loc[0, 'Courts']))
    
    st.session_state["court"] = courts_entry

else:
    st.session_state["court"] = 'All'

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [CanLII](https://www.canlii.org/en/). This section largely mimics their judgments search function except the noteup/discussion function.
""")

phrase_entry = st.text_input(label = 'Document text', value = st.session_state['df_master'].loc[0, 'Document text'])

case_name_mnc_entry = st.text_input(label = "Case name, citation or docket", value = st.session_state['df_master'].loc[0, 'Case name, citation or docket'])

court_tribunal_type_entry = st.selectbox(label = "Court or tribunal type", options = list(ca_court_tribunal_types.keys()), index = list_value_check(list(ca_court_tribunal_types.keys()), st.session_state['df_master'].loc[0, 'Court or tribunal type']))

on_this_date_entry = st.date_input(label = 'Decision date is', value = ca_date(st.session_state['df_master'].loc[0, 'Decision date is']), format="YYYY-MM-DD", min_value = date(1800, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

after_date_entry = st.date_input(label = 'Decision date is after', value = ca_date(st.session_state['df_master'].loc[0, 'Decision date is after']), format="YYYY-MM-DD", min_value = date(1800, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

before_date_entry = st.date_input(label = 'Decision date is before', value = ca_date(st.session_state['df_master'].loc[0, 'Decision date is before']), format="YYYY-MM-DD", min_value = date(1800, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

subjects_entry = st.multiselect(label = 'Subjects', options = all_subjects, default = list_range_check(all_subjects, st.session_state['df_master'].loc[0, 'Subjects']))
st.caption('If left blank, all subjects will be covered.')

#Can't get Noteup/Discussion to work given dynamic
#cited_entry = st.text_input('Noteup/Discussion: cited case names, legislation titles, citations or dockets')

#Year and month are browse functions, need a separate url getter

#if st.session_state.court != 'All':

    #year_entry = st.text_input(label = 'Choose a year')

    #link_to_canlii = f"https://www.canlii.org/en/{all_ca_jurisdictions[st.session_state.all_jurisdiction]}/{all_ca_jurisdiction_court_pairs[st.session_state.all_jurisdiction][st.session_state.court]}/"

    #st.caption(f'[Relatively earlier]({link_to_canlii}) judgments will not be collected.')
    
    #if year_entry:
        
        #wrong_number_warning = f'You have not entered a valid year. The app will not filter any search results by year.'
    
        #try:
    
            #year_int = int(year_entry)

            #if ((year_int >= 1800) and (year_int <= datetime.now().year)):
    
                #st.session_state["year"] = year_entry
            
            #else:
                
                #st.warning(wrong_number_warning)
                
                #st.session_state["year"] = ''
        
        #except:
            #st.warning(wrong_number_warning)
            #st.session_state["year"] = ''
#else:
    #st.session_state["year"] = '' 
 
st.markdown("""You can preview the judgments returned by your search terms after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")
with stylable_container(
    "purple",
    css_styles="""
    button {
        background-color: purple;
        color: white;
    }""",
):
    preview_button = st.button(label = 'PREVIEW on the CanLII (in a popped up window)')

st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 

Case name and medium neutral citation are always included with your results.
""")

meta_data_entry = st.checkbox(label = 'Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])


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
    
    df_master = ca_create_df()
    
    judgments_url = ca_search_url(df_master)
    
    open_page(judgments_url)

# %%
if keep_button:

    #Check whether search terms entered

    ca_search_terms = str(case_name_mnc_entry)  + str(phrase_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry) + str(subjects_entry)
    
    if ca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = ca_create_df()

        save_input(df_master)

        st.write('**You can download a copy of your entries.**')
    
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

    df_master = ca_create_df()

    save_input(df_master)
    
    st.session_state["page_from"] = 'pages/CA.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    ca_search_terms = str(case_name_mnc_entry)  + str(phrase_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry) + str(subjects_entry)
    
    if ca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = ca_create_df()
    
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            ca_url_to_check = ca_search_url(df_master)
            browser.get(ca_url_to_check)
            #browser.delete_all_cookies()
            browser.refresh()
            ca_elements = browser.find_elements(By.CLASS_NAME, "result ")
            ca_case_num = len(ca_elements)
            if int(ca_case_num) == 0:
                
                st.error(no_results_msg)
            
            else:
                
                save_input(df_master)

                st.session_state["page_from"] = 'pages/CA.py'
                
                st.switch_page('pages/GPT.py')

