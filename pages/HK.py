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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input, display_df, download_buttons, date_parser, list_value_check
#Import variables
from functions.common_functions import today_in_nums, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # HK search engine

# %%
from functions.hk_functions import hk_search_tool, hk_search_function, hk_search_preview, hk_sortby_dict, hk_sortby_keys, hk_sortby_values, hk_courts_dict, hk_courts_keys, hk_courts_values, hk_appeals_from_ca, hk_appeals_from_hc, hk_appeals_from_dc, hk_appeals_from_fc, hk_databases_dict, hk_databases_keys, hk_databases_values, hc_appeal_dict, dict_value_or_none, month_year_to_str

#hk_stemming_dict, hk_stemming_keys, hk_stemming_values, 


# %%
from functions.common_functions import link, reverse_link


# %%
#function to create dataframe
def hk_create_df():

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

    any_of_these_words = ''
    
    if any_of_these_words_entry:
        
        any_of_these_words = any_of_these_words_entry

    these_words_in_any_order = ''
    
    if these_words_in_any_order_entry:
        
        these_words_in_any_order = these_words_in_any_order_entry

    this_phrase = ''
    
    if this_phrase_entry:
        
        this_phrase = this_phrase_entry


    try:
    
        stemming = stemming_entry

    except:

        print('Stemming not entered')

        stemming = True

    #st.write(f"stemming == {stemming}")
    
    date_of_judgment = None

    if date_of_judgment_entry:

        date_of_judgment = date_of_judgment_entry

    coram = ''
    
    if coram_entry:
        
        coram = coram_entry

    parties = ''
    
    if parties_entry:
        
        parties = parties_entry

    representation = ''
    
    if representation_entry:
        
        representation = representation_entry

    offence = ''
    
    if offence_entry:
        
        offence = offence_entry
   
    court_levels_filter = hk_courts_keys
    
    if court_levels_filter_entry:
    
        court_levels_filter = court_levels_filter_entry
    
        #if len(court_levels_filter) == 0:
    
            #court_levels_filter = [hk_courts_keys[0]]
        
    on_appeal_from_court = None
    
    if on_appeal_from_court_entry:
        
        on_appeal_from_court = on_appeal_from_court_entry

    on_appeal_from_type = None
    
    if on_appeal_from_type_entry:
        
        on_appeal_from_type = on_appeal_from_type_entry

    medium_neutral_citation = ''
    
    if medium_neutral_citation_entry:
        
        medium_neutral_citation = medium_neutral_citation_entry
    
    case_number = ''
    
    if case_number_entry:
        
        case_number = case_number_entry

    reported_citation = ''
    
    if reported_citation_entry:
        
        reported_citation = reported_citation_entry

    databases = hk_databases_keys
    
    if databases_entry:
        
        databases = databases_entry

        #if len(databases) == 0:
    
            #databases = [hk_databases_keys[0]]

    sortby = hk_sortby_keys[0]
    
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
        'Any of these words': any_of_these_words, 
        'These words in any order': these_words_in_any_order,
        'This phrase': this_phrase,
        'Stemming': stemming,
        'Date of judgment': date_of_judgment,
        'Coram': coram,
        'Parties': parties,
        'Representation': representation,
        'Offence': offence,
        'Court level(s) filter': court_levels_filter,
        'On appeal from (court)': on_appeal_from_court,
        'On appeal from (type)': on_appeal_from_type,
        'Medium neutral citation': medium_neutral_citation,
        'Case number': case_number,
        'Reported citation': reported_citation,
        'Database(s)': databases,
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
    df_master_dict = {'Your name': '', 
    'Your email address': '', 
    'Your GPT API key': '', 
    'Metadata inclusion': True, 
    'Maximum number of judgments': default_judgment_counter_bound, 
    'Enter your questions for GPT': '', 
    'Use GPT': False, 
    'Use own account': False, 
    'Use flagship version of GPT': False,
    'Example': ''
    }

    #Jurisdiction specific
    jurisdiction_specific_dict = {
    'Any of these words': '',
    'These words in any order': '',
    'This phrase': '',
    'Stemming': True,
    'Date of judgment': None,
    'Coram': '',
    'Parties': '',
    'Representation': '',
    'Offence': '',
    'Court level(s) filter': hk_courts_keys,
    'On appeal from (court)': None,
    'On appeal from (type)': None,
    'Medium neutral citation': '',
    'Case number': '',
    'Reported citation': '',
    'Database(s)': hk_databases_keys,
    'Sort by': hk_sortby_keys[0],
    }

    #Make into  df
    df_master_dict.update(jurisdiction_specific_dict)
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#Specific to HK: enter month and year of judgment if available

if 'month_of_judgment' not in st.session_state:

    st.session_state['month_of_judgment'] = None

if 'year_of_judgment' not in st.session_state:
    
    st.session_state['year_of_judgment'] = None

#st.write(f"st.session_state['df_master'].loc[0, 'Date of judgment'] == {st.session_state['df_master'].loc[0, 'Date of judgment']}")

if date_parser(st.session_state['df_master'].loc[0, 'Date of judgment']) == None:

    date_list = str(st.session_state['df_master'].loc[0, 'Date of judgment']).split('/')

    #st.write(f"date_list == {date_list}")
    
    if len(date_list) == 3:

        st.session_state['month_of_judgment'] = int(date_list[1])
        
        st.session_state['year_of_judgment'] = int(date_list[2])

#st.write(f"st.session_state['month_of_judgment'] == {st.session_state['month_of_judgment']}")
#st.write(f"st.session_state['year_of_judgment'] == {st.session_state['year_of_judgment']}")


# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %% editable=true slideshow={"slide_type": ""}
#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the Hong Kong courts and tribunals]")

st.success(default_msg)

st.write(f'This app sources cases from [the Hong Kong Legal Reference System](https://legalref.judiciary.hk/lrs/common/search/search.jsp).')

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [the Hong Kong Legal Reference System](https://legalref.judiciary.hk/lrs/common/search/search.jsp). This section mimics their search function.
""")

any_of_these_words_entry = st.text_input(label = 'Any of these words', value = st.session_state['df_master'].loc[0, 'Any of these words'])

these_words_in_any_order_entry = st.text_input(label = 'These words in any order', value = st.session_state['df_master'].loc[0, 'These words in any order'])

this_phrase_entry = st.text_input(label = 'This phrase', value = st.session_state['df_master'].loc[0, 'This phrase'])

stemming_entry = st.checkbox(label = 'Stemming', value = st.session_state['df_master'].loc[0, "Stemming"], help = 'Example: find "taxes" if your search word is "tax".')

#st.write(f"stemming_entry == {stemming_entry}")

month_year_only = st.toggle(label = 'Slide to enter month and year of judgment only', value = bool((st.session_state['month_of_judgment'] != None) or (st.session_state['year_of_judgment'] != None)))

if not month_year_only:

    date_of_judgment_entry = st.date_input(label = "Date of judgment", value = date_parser(st.session_state['df_master'].loc[0, 'Date of judgment']),  format="DD/MM/YYYY", min_value = date(1945, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

else:

    #st.session_state['df_master'].loc[0, 'Date of judgment'] = None

    month_entry = st.selectbox(label = 'Month of judgment', 
                               options = list(range(1, 13)), 
                              index = list_value_check(list(range(1, 13)), st.session_state['month_of_judgment']), 
                              )

    year_entry = st.selectbox(label = 'Year of judgment', 
                              options = list(reversed(range(1945, datetime.now().year + 1))), 
                            index = list_value_check(list(reversed(range(1945, datetime.now().year + 1))), st.session_state['year_of_judgment']), 
                             )

    date_of_judgment_entry = f"/{month_year_to_str(month_entry)}/{month_year_to_str(year_entry)}"
    
#st.write(f"date_of_judgment_entry == {date_of_judgment_entry}, type(date_of_judgment_entry) == {type(date_of_judgment_entry)}")

coram_entry = st.text_input(label = 'Coram', value = st.session_state['df_master'].loc[0, 'Coram'])

parties_entry = st.text_input(label = 'Parties', value = st.session_state['df_master'].loc[0, 'Parties'])

representation_entry = st.text_input(label = 'Representation', value = st.session_state['df_master'].loc[0, 'Representation'])

offence_entry = st.text_input(label = 'Offence', value = st.session_state['df_master'].loc[0, 'Offence'])

default_on_courts = st.checkbox(label = 'Select all courts', help = 'You may need to press :red[RESET] to select all courts.', value = bool(st.session_state['df_master'].loc[0, "Court level(s) filter"] == hk_courts_keys))

if default_on_courts == True:

    if not isinstance(st.session_state['df_master'].loc[0, "Court level(s) filter"], list):
        
        st.session_state['df_master']["Court level(s) filter"] = st.session_state['df_master']["Court level(s) filter"].astype('object')

    st.session_state['df_master'].at[0, "Court level(s) filter"] = hk_courts_keys

else:
    
    st.session_state['df_master'].at[0, "Court level(s) filter"] = [hk_courts_keys[0]]

court_levels_filter_entry = st.multiselect(label = 'Court level(s) filter', 
                                      options = hk_courts_keys, 
                                      default = st.session_state['df_master'].loc[0, "Court level(s) filter"], 
                                    disabled = bool(default_on_courts == False)
                                    )

on_appeal_from_court_entry = st.selectbox(label = 'On appeal from (court)', 
                                      options = [*hc_appeal_dict.keys()], 
                                    index = list_value_check([*hc_appeal_dict.keys()], st.session_state['df_master'].loc[0, "On appeal from (court)"]), 
                                    help = 'You may need to press :red[RESET] to select or remove a court.'
                                    )

if on_appeal_from_court_entry:
    
    st.session_state['df_master'].loc[0, "On appeal from (court)"] = on_appeal_from_court_entry

on_appeal_from_type_entry = st.selectbox(label = 'On appeal from (type)', 
                                      options = dict_value_or_none(hc_appeal_dict, st.session_state['df_master'].loc[0, "On appeal from (court)"]), 
                                    index = list_value_check(dict_value_or_none(hc_appeal_dict, st.session_state['df_master'].loc[0, "On appeal from (court)"]), st.session_state['df_master'].loc[0, "On appeal from (type)"]), 
                                     help = 'You may need to press :red[RESET] to select or remove a type.'
                                    )

medium_neutral_citation_entry = st.text_input(label = 'Medium neutral citation', value = st.session_state['df_master'].loc[0, 'Medium neutral citation'], help = 'Example: [2018] HKCA 14')

case_number_entry = st.text_input(label = 'Case number', value = st.session_state['df_master'].loc[0, 'Case number'], help = 'Example: FACV 18/2000')

reported_citation_entry = st.text_input(label = 'Reported citation', value = st.session_state['df_master'].loc[0, 'Reported citation'], help = 'Example: (2021) 24 HKCFAR 116')

default_on_databases = st.checkbox(label = 'Select all databases', help = 'You may need to press :red[RESET] to select all databases.', value = bool(st.session_state['df_master'].loc[0, "Database(s)"] == hk_databases_keys))

if default_on_databases == True:

    if not isinstance(st.session_state['df_master'].loc[0, "Database(s)"], list):
        
        st.session_state['df_master']["Database(s)"] = st.session_state['df_master']["Database(s)"].astype('object')

    st.session_state['df_master'].at[0, "Database(s)"] = hk_databases_keys

else:
    
    st.session_state['df_master'].at[0, "Database(s)"] = [hk_databases_keys[0]]

databases_entry = st.multiselect(label = 'Database(s)', 
                                      options = hk_databases_keys, 
                                      default = st.session_state['df_master'].loc[0, "Database(s)"],
                                 disabled = bool(default_on_databases == False)
                                    )

sortby_entry = st.selectbox(label = "Sort by", options = hk_sortby_keys, index = hk_sortby_keys.index(st.session_state['df_master'].loc[0, 'Sort by']))

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
    
    hk_search_terms = str(any_of_these_words_entry) + str(these_words_in_any_order_entry) + str(this_phrase_entry) + str(date_of_judgment_entry).replace('/', '') + str(coram_entry) + str(parties_entry) + str(representation_entry) + str(offence_entry) + str(on_appeal_from_court_entry) + str(medium_neutral_citation_entry) + str(case_number_entry) + str(reported_citation_entry) 
    
    if hk_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):
            
            df_master = hk_create_df()
    
            search_results_w_count = hk_search_preview(df_master)
            
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

    hk_search_terms = str(any_of_these_words_entry) + str(these_words_in_any_order_entry) + str(this_phrase_entry) + str(date_of_judgment_entry).replace('/', '') + str(coram_entry) + str(parties_entry) + str(representation_entry) + str(offence_entry) + str(on_appeal_from_court_entry) + str(medium_neutral_citation_entry) + str(case_number_entry) + str(reported_citation_entry)
    
    if hk_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = hk_create_df()

        save_input(df_master)

        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = hk_create_df()

    save_input(df_master)
    
    st.session_state["page_from"] = 'pages/HK.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    hk_search_terms = str(any_of_these_words_entry) + str(these_words_in_any_order_entry) + str(this_phrase_entry) + str(date_of_judgment_entry).replace('/', '') + str(coram_entry) + str(parties_entry) + str(representation_entry) + str(offence_entry) + str(on_appeal_from_court_entry) + str(medium_neutral_citation_entry) + str(case_number_entry) + str(reported_citation_entry) 
    
    if hk_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = hk_create_df()
    
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:

                search_results_w_count = hk_search_preview(df_master)
                
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    
                    st.error(no_results_msg)
    
                else:
                    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/HK.py'
                    
                    st.switch_page('pages/GPT.py')

            except Exception as e:
                print(search_error_display)
                print(e)
                st.error(search_error_display)
                st.error(e)

