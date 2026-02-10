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

# %% [markdown] editable=true slideshow={"slide_type": ""}
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
import traceback

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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input, display_df, download_buttons, date_parser, list_value_check, dict_value_or_none, month_year_to_str, report_error

#Import variables
from functions.common_functions import today_in_nums, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # HKLII search engine

# %%
from functions.hklii_functions import hklii_search_tool, hklii_search_preview, hklii_sortby_dict, hklii_sortby_keys, hklii_sortby_values, hklii_dbs_dict, hklii_en_cases_list, hklii_en_legis_list, hklii_en_other_list, hklii_c_cases_list, hklii_c_legis_list, hklii_c_other_list

#hklii_stemming_dict, hklii_stemming_keys, hklii_stemming_values, 


# %%
from functions.common_functions import link, reverse_link


# %%
#function to create dataframe
def hklii_create_df():

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

    #Entries

    citation = None

    if citation_entry:

        citation = citation_entry

    title = None

    if title_entry:

        title = title_entry

    captitle = None

    if captitle_entry:

        captitle = captitle_entry    
    
    parties = None
    
    if parties_entry:
        
        parties = parties_entry

    coram = None
    
    if coram_entry:
        
        coram = coram_entry
    
    representation = None
    
    if representation_entry:
        
        representation = representation_entry

    charge = None
    
    if charge_entry:
        
        charge = charge_entry
    
    text = None
    
    if text_entry:
        
        text = text_entry

    anyword = None
    
    if anyword_entry:
        
        anyword = anyword_entry

    phrase = None
    
    if phrase_entry:
        
        phrase = phrase_entry

    min_date = None

    if min_date_entry:

        min_date = min_date_entry

    max_date = None

    if max_date_entry:
        
        max_date = max_date_entry

    dbs_en_cases = []

    if dbs_en_cases_entry:

        dbs_en_cases = dbs_en_cases_entry

    dbs_en_legis = []

    if dbs_en_legis_entry:

        dbs_en_legis = dbs_en_legis_entry

    dbs_en_other = []

    if dbs_en_other_entry:

        dbs_en_other = dbs_en_other_entry

    dbs_c_cases = []

    if dbs_c_cases_entry:

        dbs_c_cases = dbs_c_cases_entry

    dbs_c_legis = []

    if dbs_c_legis_entry:

        dbs_c_legis = dbs_c_legis_entry

    dbs_c_other = []

    if dbs_c_other_entry:

        dbs_c_other = dbs_c_other_entry
    
    sortby = hklii_sortby_keys[0]
    
    if sortby_entry:
        
        sortby = sortby_entry

    #Entries common to all jurisdictions
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
    meta_data_choice = True
        
    new_row = {
        'Processed': '',
        'Timestamp': timestamp,
        'Your name': name, 
        'Your email address': email, 
        'Your GPT API key': gpt_api_key, 
        'Citation': citation,
        'Case name': title,
        'Legislation name': captitle, 
        'Parties of judgment': parties,
        'Coram of judgment': coram,
        'Parties representation': representation,
        'Charge': charge,
        'All of these words': text,
        'Any of these words': anyword, 
        'Exact phrase': phrase,
        'Start date': min_date,
        'End date': max_date,
        'English case databases': dbs_en_cases,
        'English legislation databases': dbs_en_legis,
        'English other databases': dbs_en_other,
        '中文判案書資料庫': dbs_c_cases,
        '中文法例資料庫': dbs_c_legis,
        '其他中文資料庫': dbs_c_other,
        'Sort by': sortby,
        'Maximum number of judgments': judgments_counter_bound, 
        'Enter your questions for GPT': gpt_questions, 
        'Use GPT': gpt_activation_status,
        'Use own account': own_account,
        'Use flagship version of GPT': gpt_enhancement
        }

    df_master_new = pd.DataFrame([new_row])#, index = [0])
    
    return df_master_new


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from functions.gpt_functions import question_characters_bound, default_msg, default_caption, basic_model, flagship_model


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = basic_model
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    from functions.common_functions import API_key

    st.session_state['gpt_api_key'] = API_key


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
    df_master_dict = {'Your name': '', 
    'Your email address': '', 
    'Your GPT API key': '', 
    'Metadata inclusion': True, 
    'Maximum number of judgments': default_judgment_counter_bound, 
    'Enter your questions for GPT': '', 
    'Use GPT': True, 
    'Use own account': False, 
    'Use flagship version of GPT': False,
    'Example': ''
    }

    #Jurisdiction specific
    jurisdiction_specific_dict = {
    'Citation': None,
    'Case name': None,
    'Legislation name': None,
    'Parties of judgment': None,
    'Coram of judgment': None,
    'Parties representation': None,
    'Charge': None,
    'All of these words': None,
    'Any of these words': None,
    'Exact phrase': None,
    'Start date': None,
    'End date': None,
    'English case databases': [],
    'English legislation databases': [],
    'English other databases': [],
    '中文判案書資料庫': [],
    '中文法例資料庫': [],
    '其他中文資料庫': [],        
    'Sort by': hklii_sortby_keys[0],
    }

    #Make into  df
    df_master_dict.update(jurisdiction_specific_dict)
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#Initialise jurisdiction_page
if 'jurisdiction_page' not in st.session_state:
    st.session_state['jurisdiction_page'] = 'pages/HKLII.py'

#Initialise error reporting status
if 'error_msg' not in st.session_state:
    st.session_state['error_msg'] = ''

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %% editable=true slideshow={"slide_type": ""}
#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases, legislation and other legal materials from Hong Kong]")

st.success(default_msg)

st.write(f'This app sources cases, legislation and other legal materials from [HKLII](https://www.hklii.hk).')

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Databases to cover")

#st.markdown("""**Select scope of search**""")

filtered_by_dbs_toggle = st.toggle(label = 'Select/unselect databases', 
                                   value = bool((len(st.session_state['df_master'].loc[0, "English case databases"] + st.session_state['df_master'].loc[0, "English legislation databases"] + st.session_state['df_master'].loc[0, "English other databases"] + st.session_state['df_master'].loc[0, "中文判案書資料庫"] + st.session_state['df_master'].loc[0, "中文法例資料庫"] + st.session_state['df_master'].loc[0, "其他中文資料庫"])) > 0)
                                  )

if not filtered_by_dbs_toggle:

    st.info("All databases will be covered if you don't make a selection.")

    dbs_en_cases_entry = []

    dbs_en_legis_entry = []

    dbs_en_other_entry = []

    dbs_c_cases_entry = []

    dbs_c_legis_entry = []

    dbs_c_other_entry = []

else:

    st.warning("Please select the databases to cover.")


    
    default_dbs_en_cases = st.button(label = 'Select all English case databases', help = 'You may need to press :red[RESET] to select all.', 
                                     #value = bool(st.session_state['df_master'].loc[0, "English case databases"] == hklii_en_cases_list)
                                    )
    
    if default_dbs_en_cases == True:
    
        if not isinstance(st.session_state['df_master'].loc[0, "English case databases"], list):
            
            st.session_state['df_master']["English case databases"] = st.session_state['df_master']["English case databases"].astype('object')
    
        st.session_state['df_master'].at[0, "English case databases"] = hklii_en_cases_list
    
    #else:
        
        #if not isinstance(st.session_state['df_master'].loc[0, "English case databases"], list):
            
            #st.session_state['df_master']["English case databases"] = st.session_state['df_master']["English case databases"].astype('object')
    
        #st.session_state['df_master'].at[0, "English case databases"] = []
    
    dbs_en_cases_entry = st.multiselect(label = 'English case databases', 
                                          options = hklii_en_cases_list, 
                                          default = st.session_state['df_master'].loc[0, "English case databases"], 
                                        #disabled = bool(default_dbs_en_cases == False)
                                        )
    
    


    
    default_dbs_en_legis = st.button(label = 'Select all English legislation databases', help = 'You may need to press :red[RESET] to select all.', 
                                     #value = bool(st.session_state['df_master'].loc[0, "English legislation databases"] == hklii_en_legis_list)
                                    )
    
    if default_dbs_en_legis == True:
    
        if not isinstance(st.session_state['df_master'].loc[0, "English legislation databases"], list):
            
            st.session_state['df_master']["English legislation databases"] = st.session_state['df_master']["English legislation databases"].astype('object')
    
        st.session_state['df_master'].at[0, "English legislation databases"] = hklii_en_legis_list
    
    #else:
        
        #if not isinstance(st.session_state['df_master'].loc[0, "English legislation databases"], list):
            
            #st.session_state['df_master']["English legislation databases"] = st.session_state['df_master']["English legislation databases"].astype('object')
    
        #st.session_state['df_master'].at[0, "English legislation databases"] = []

    dbs_en_legis_entry = st.multiselect(label = 'English legislation databases', 
                                          options = hklii_en_legis_list, 
                                          default = st.session_state['df_master'].loc[0, "English legislation databases"], 
                                        #disabled = bool(default_dbs_en_legis == False
                                        )
    


    
    default_dbs_en_other = st.button(label = 'Select all English other databases', help = 'You may need to press :red[RESET] to select all.', 
                                     #value = bool(st.session_state['df_master'].loc[0, "English other databases"] == hklii_en_other_list)
                                    )
    
    if default_dbs_en_other == True:
    
        if not isinstance(st.session_state['df_master'].loc[0, "English other databases"], list):
            
            st.session_state['df_master']["English other databases"] = st.session_state['df_master']["English other databases"].astype('object')
    
        st.session_state['df_master'].at[0, "English other databases"] = hklii_en_other_list
    
    #else:
        
        #if not isinstance(st.session_state['df_master'].loc[0, "English other databases"], list):
            
            #st.session_state['df_master']["English other databases"] = st.session_state['df_master']["English other databases"].astype('object')
    
        #st.session_state['df_master'].at[0, "English other databases"] = []

    dbs_en_other_entry = st.multiselect(label = 'English other databases', 
                                          options = hklii_en_other_list, 
                                          default = st.session_state['df_master'].loc[0, "English other databases"], 
                                        #disabled = bool(default_dbs_en_other == False
                                        )
    


    
    default_dbs_c_cases = st.button(label = '選擇所有中文判案書資料庫', help = 'You may need to press :red[RESET] to select all.', 
                                    #value = bool(st.session_state['df_master'].loc[0, "中文判案書資料庫"] == hklii_c_cases_list)
                                   )
    
    if default_dbs_c_cases == True:
    
        if not isinstance(st.session_state['df_master'].loc[0, "中文判案書資料庫"], list):
            
            st.session_state['df_master']["中文判案書資料庫"] = st.session_state['df_master']["中文判案書資料庫"].astype('object')
    
        st.session_state['df_master'].at[0, "中文判案書資料庫"] = hklii_c_cases_list
    
    #else:
        
        #if not isinstance(st.session_state['df_master'].loc[0, "中文判案書資料庫"], list):
            
            #st.session_state['df_master']["中文判案書資料庫"] = st.session_state['df_master']["中文判案書資料庫"].astype('object')
    
        #st.session_state['df_master'].at[0, "中文判案書資料庫"] = []
    
    dbs_c_cases_entry = st.multiselect(label = '中文判案書資料庫', 
                                          options = hklii_c_cases_list, 
                                          default = st.session_state['df_master'].loc[0, "中文判案書資料庫"], 
                                        #disabled = bool(default_dbs_c_cases == False
                                        )


    
    default_dbs_c_legis = st.button(label = '選擇所有中文法例資料庫', help = 'You may need to press :red[RESET] to select all.', 
                                    #value = bool(st.session_state['df_master'].loc[0, "中文法例資料庫"] == hklii_c_legis_list)
                                   )
    
    if default_dbs_c_legis == True:
    
        if not isinstance(st.session_state['df_master'].loc[0, "中文法例資料庫"], list):
            
            st.session_state['df_master']["中文法例資料庫"] = st.session_state['df_master']["中文法例資料庫"].astype('object')
    
        st.session_state['df_master'].at[0, "中文法例資料庫"] = hklii_c_legis_list
    
    #else:
        
        #if not isinstance(st.session_state['df_master'].loc[0, "中文法例資料庫"], list):
            
            #st.session_state['df_master']["中文法例資料庫"] = st.session_state['df_master']["中文法例資料庫"].astype('object')
    
        #st.session_state['df_master'].at[0, "中文法例資料庫"] = []
    
    dbs_c_legis_entry = st.multiselect(label = '中文法例資料庫', 
                                          options = hklii_c_legis_list, 
                                          default = st.session_state['df_master'].loc[0, "中文法例資料庫"], 
                                        #disabled = bool(default_dbs_c_legis == False
                                        )


    
    default_dbs_c_other = st.button(label = '選擇所有其他中文資料庫', help = 'You may need to press :red[RESET] to select all.', 
                                    #value = bool(st.session_state['df_master'].loc[0, "其他中文資料庫"] == hklii_c_other_list)
                                   )
    
    if default_dbs_c_other == True:
    
        if not isinstance(st.session_state['df_master'].loc[0, "其他中文資料庫"], list):
            
            st.session_state['df_master']["其他中文資料庫"] = st.session_state['df_master']["其他中文資料庫"].astype('object')
    
        st.session_state['df_master'].at[0, "其他中文資料庫"] = hklii_c_other_list
    
    #else:
        
        #if not isinstance(st.session_state['df_master'].loc[0, "其他中文資料庫"], list):
            
            #st.session_state['df_master']["其他中文資料庫"] = st.session_state['df_master']["其他中文資料庫"].astype('object')
    
        #st.session_state['df_master'].at[0, "其他中文資料庫"] = []
    
    dbs_c_other_entry = st.multiselect(label = '其他中文資料庫', 
                                          options = hklii_c_other_list, 
                                          default = st.session_state['df_master'].loc[0, "其他中文資料庫"], 
                                        #disabled = bool(default_dbs_c_other == False
                                        )


    
st.subheader("Your search terms")

st.markdown("""For search tips, please visit [HKLII](https://www.hklii.hk/advancedsearch). This section mimics their advanced search function.
""")

#st.markdown("""**Search in specific fields**""")

citation_entry = st.text_input(label = 'Citation', value = st.session_state['df_master'].loc[0, 'Citation'], help = 'e.g.1: [2002] HKCFI 1234; e.g.2: CACV 154/1984')

title_entry = st.text_input(label = 'Case name', value = st.session_state['df_master'].loc[0, 'Case name'], help = 'e.g.1: HKSAR v. CHAN KAM WAH; e.g.2: 香港特別行政區 訴 富士達香港有限公司')

captitle_entry = st.text_input(label = 'Legislation name', value = st.session_state['df_master'].loc[0, 'Legislation name'], help = 'e.g.1: JUSTICES OF THE PEACE ORDINANCE; e.g.2: 建築物能源效益')

parties_entry = st.text_input(label = 'Parties of judgment', value = st.session_state['df_master'].loc[0, 'Parties of judgment'], help = 'e.g.: B & Q PLC')

coram_entry = st.text_input(label = 'Coram of judgment', value = st.session_state['df_master'].loc[0, 'Coram of judgment'], help = 'e.g.1: E.C. Barnes, D.J.; e.g.2: 張慧玲')

representation_entry = st.text_input(label = 'Parties representation', value = st.session_state['df_master'].loc[0, 'Parties representation'], help = 'e.g.1: G. Alderdice; e.g.2: 資深大律師')

charge_entry = st.text_input(label = 'Charge', value = st.session_state['df_master'].loc[0, 'Charge'], help = 'e.g.1: Dangerous driving; e.g.2: 危險駕駛')

#st.markdown("""**Search in all fields**""")

text_entry = st.text_input(label = 'All of these words', value = st.session_state['df_master'].loc[0, 'All of these words'], help = 'e.g. breach fiduciary duty')

anyword_entry = st.text_input(label = 'Any of these words', value = st.session_state['df_master'].loc[0, 'Any of these words'], help = 'e.g. waste pollution radiation')

phrase_entry = st.text_input(label = 'Exact phrase', value = st.session_state['df_master'].loc[0, 'Exact phrase'], help = 'e.g. parliamentary sovereignty')

#st.markdown("""**Filter by date**""")

col1, col2 = st.columns(2, gap = 'small')

with col1:

    min_date_entry = st.date_input(label = "Start date", value = date_parser(st.session_state['df_master'].loc[0, 'Start date']),  format="DD/MM/YYYY", min_value = date(1800, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

with col2:
    
    max_date_entry = st.date_input(label = "End date", value = date_parser(st.session_state['df_master'].loc[0, 'End date']),  format="DD/MM/YYYY", min_value = date(1800, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

sortby_entry = st.selectbox(label = "Sort by", options = hklii_sortby_keys, index = hklii_sortby_keys.index(st.session_state['df_master'].loc[0, 'Sort by']))

#st.subheader("Case metadata collection")

#st.markdown("""Would you like to obtain case metadata? Such data include the judge(s), the filing date and so on. 

#You will always obtain case names and citations.
#""")

#meta_data_entry = st.checkbox(label = 'Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])

meta_data_entry = True

st.info("""You can preview the results returned by your search terms.""")

with stylable_container(
    "purple",
    css_styles="""
    button {
        background-color: purple;
        color: white;
    }""",
):
    preview_button = st.button(label = 'PREVIEW')


# %% [markdown]
# ## Preview

# %%
if preview_button:
    
    hklii_search_terms = str(citation_entry) + str(title_entry) + str(anyword_entry) + str(text_entry) + str(phrase_entry) + str(min_date_entry).replace('/', '') + str(max_date_entry).replace('/', '') + str(coram_entry) + str(parties_entry) + str(representation_entry) + str(charge_entry)  
    
    if hklii_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
        
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):

            try:
            
                df_master = hklii_create_df()
        
                search_results_w_count = hklii_search_preview(df_master)
                
                results_count = search_results_w_count['results_count']
        
                case_infos = search_results_w_count['case_infos']
        
                results_url = search_results_w_count['results_url']
        
                if results_count > 0:
        
                    df_preview = pd.DataFrame(case_infos)
        
                    #Get display settings
                    display_df_dict = display_df(df_preview)
        
                    df_preview = display_df_dict['df']
        
                    link_heading_config = display_df_dict['link_heading_config']
        
                    #Display search results
                    st.success(f'Your search terms returned {results_count} result(s). Please see below for the top {min(results_count, default_judgment_counter_bound)} result(s).')
                                
                    st.dataframe(df_preview.head(default_judgment_counter_bound),  column_config=link_heading_config)
        
                    st.page_link(results_url, label=f"SEE all search results (in a popped up window)", icon = "🌎")
            
                else:
                    st.error(no_results_msg)

            except Exception as e:

                st.error(search_error_display)
                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()



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
if keep_button:

    #Check whether search terms entered

    hklii_search_terms = str(citation_entry) + str(title_entry) + str(anyword_entry) + str(text_entry) + str(phrase_entry) + str(min_date_entry).replace('/', '') + str(max_date_entry).replace('/', '') + str(coram_entry) + str(parties_entry) + str(representation_entry) + str(charge_entry) 
    
    if hklii_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = hklii_create_df()

        save_input(df_master)

        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = hklii_create_df()

    save_input(df_master)
    
    st.session_state["page_from"] = 'pages/HKLII.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    hklii_search_terms = str(citation_entry) + str(title_entry) + str(anyword_entry) + str(text_entry) + str(phrase_entry) + str(min_date_entry).replace('/', '') + str(max_date_entry).replace('/', '') + str(coram_entry) + str(parties_entry) + str(representation_entry) + str(charge_entry)  
    
    if hklii_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = hklii_create_df()
    
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:

                search_results_w_count = hklii_search_preview(df_master)
                
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    
                    st.error(no_results_msg)
    
                else:
                    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/HKLII.py'
                    
                    st.switch_page('pages/GPT.py')

            except Exception as e:

                st.error(search_error_display)
                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()



# %% [markdown]
# # Report error

# %%
if len(st.session_state.error_msg) > 0:

    report_error_button = st.button(label = 'REPORT the error', type = 'primary', help = 'Send your entries and a report of the error to the developer.')

    if report_error_button:

        st.session_state.error_msg = report_error(error_msg = st.session_state.error_msg, jurisdiction_page = st.session_state.jurisdiction_page, df_master = st.session_state.df_master)

