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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, au_date, save_input, search_error_display, display_df, download_buttons
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # UK Courts search engine

# %%
from functions.uk_functions import uk_courts_default_list, uk_courts, uk_courts_list, uk_court_choice, uk_link, uk_search, uk_search_results_to_judgment_links, uk_meta_labels_droppable, uk_meta_judgment_dict, uk_search_url


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
            'Courts' : courts_list, 
            'Party' : party,
            'Judge' : judge, 
            'Metadata inclusion' : meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status, 
          'Use own account': own_account,
            'Use flagship version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame([new_row])

#    df_master_new.to_json(current_dir + '/df_master.json', orient = 'split', compression = 'infer')
#    df_master_new.to_excel(current_dir + '/df_master.xlsx', index=False)

#    if len(df_master_new) > 0:
        
    return df_master_new

#    else:
#        return 'Error: spreadsheet of reponses NOT generated.' 

# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from functions.gpt_functions import question_characters_bound, default_msg, default_caption


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction



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
from functions.common_functions import open_page, clear_cache_except_validation_df_master, tips


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])
    
#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

if 'df_master' not in st.session_state:

    #Generally applicable
    df_master_dict = {'Your name' : '', 
    'Your email address' : '', 
    'Your GPT API key' : '', 
    'Metadata inclusion' : True, 
    'Maximum number of judgments' : default_judgment_counter_bound, 
    'Enter your questions for GPT' : '', 
    'Use GPT' : False, 
    'Use own account' : False, 
    'Use flagship version of GPT' : False,
    'Example' : ''
    }

    #Jurisdiction specific
    jurisdiction_specific_dict = {'Free text' : None,
    'From day' : None,
    'From month' : None,
    'From year' : None,
    'To day' : None,
    'To month' : None,
    'To year' : None,
    'Courts' : [],
    'Party' : None,
    'Judge' : None
    }

    #Make into  df
    df_master_dict.update(jurisdiction_specific_dict)
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])


# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
#if st.session_state.page_from != "pages/UK.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form for court selection

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the United Kingdom courts and tribunals]")

st.success(default_msg)

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Courts and tribunals to cover")

default_on = st.button('ADD the Supreme Court, the Privy Council, the Court of Appeal, and the High Court of England & Wales', help = 'You may need to press :red[RESET] to add these courts.')

if default_on:
    st.session_state['df_master']['Courts'] = st.session_state['df_master']['Courts'].astype('object')
    st.session_state['df_master'].at[0, 'Courts'] = uk_courts_default_list

courts_entry = st.multiselect(label = 'Select or type in the courts and tribunals to search', options = uk_courts_list, default = st.session_state['df_master'].loc[0, 'Courts'])

#st.caption("All courts and tribunals listed in this menu will be covered if left blank.")

#Search terms

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [The National Archives](https://caselaw.nationalarchives.gov.uk/structured_search). This section mimics their search function.
""")

query_entry = st.text_input(label = 'Free text', value = st.session_state.df_master.loc[0, 'Free text'])

from_date_entry = st.date_input('From day', value = au_date(f"{st.session_state.df_master.loc[0, 'From day']}/{st.session_state.df_master.loc[0, 'From month']}/{st.session_state.df_master.loc[0, 'From year']}"), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

to_date_entry = st.date_input('To day', value = au_date(f"{st.session_state.df_master.loc[0, 'To day']}/{st.session_state.df_master.loc[0, 'To month']}/{st.session_state.df_master.loc[0, 'To year']}"), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

st.caption('[Relatively earlier](https://caselaw.nationalarchives.gov.uk/structured_search) judgments are not available.')

judge_entry = st.text_input(label = 'Judge name', value = st.session_state.df_master.loc[0, 'Judge'])

party_entry = st.text_input(label = 'Party name', value = st.session_state.df_master.loc[0, 'Party'])

st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the judge(s), the parties and so on. 

You will always obtain case names and medium neutral citations.
""")

meta_data_entry = st.checkbox('Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])

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

# %% jp-MarkdownHeadingCollapsed=true
if preview_button:
    
    with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):
        
        df_master = uk_create_df()
    
        results_url_num = uk_search_url(df_master)
            
        results_count = results_url_num['results_count']
    
        results_url = results_url_num['results_url']
    
        search_results_soup = results_url_num['soup']
    
        if results_count > 0:
        
            #Get relevant cases
            
            judgments_file = []
            
            judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
            
            case_infos = uk_search_results_to_judgment_links(search_results_soup, judgments_counter_bound) 
            
            for case in case_infos:
            
                #add search results to json
                judgments_file.append(case)
    
            #Clean df
            
            df_preview = pd.DataFrame(judgments_file)
    
            #Clean df
            df_preview['Hyperlink to The National Archives'] = df_preview['Hyperlink to The National Archives'].apply(lambda link: link.replace('/data.xml', ''))
            
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

    all_search_terms = str(query_entry) + str(from_date_entry) + str(to_date_entry) + str(judge_entry) + str(party_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif len(courts_entry) == 0:
        
        st.warning('Please select at least one court to cover.')
            
    else:
                            
        df_master = uk_create_df()
        
        save_input(df_master)
    
        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = uk_create_df()
    
    save_input(df_master)

    st.session_state["page_from"] = 'pages/UK.py'

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
        
        st.warning('Please select at least one court to cover.')
    
    else:

        df_master = uk_create_df()
        
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):
            
            try:

                results_url_num = uk_search_url(df_master)
        
                results_count = results_url_num['results_count']
    
                if results_count == 0:
                    st.error(no_results_msg)
    
                else:
    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/UK.py'
                    
                    st.switch_page('pages/GPT.py')

            except Exception as e:
                print(search_error_display)
                print(e)
                st.error(search_error_display)
                st.error(e)
