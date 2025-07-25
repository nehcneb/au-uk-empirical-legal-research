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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_range_check, date_parser, save_input, display_df, download_buttons, report_error
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # Federal Courts search engine

# %%
from functions.fca_functions import fca_courts, fca_courts_list, npa_dict, npa_list, fca_search, fca_search_url, fca_search_results_to_judgment_links, fca_metalabels, fca_metalabels_droppable, fca_meta_judgment_dict, fca_pdf_name_mnc_list, fca_pdf_name
#fca_link_to_doc


# %%
from functions.common_functions import link


# %%
#function to create dataframe
def fca_create_df():

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
        
    #Courts
    #courts_list = courts_entry
    #court_string = ', '.join(courts_list)
    #court = court_string

    court = courts_entry
    
    #dates
    
    on_this_date = ''

    if on_this_date_entry != 'None':

        try:

            #on_this_date = on_this_date_entry.strftime('%d/%m/%Y') + on_this_date_entry.strftime('%d') + on_this_date_entry.strftime('%B').lower()[:3] + on_this_date_entry.strftime('Y')

            on_this_date = str(on_this_date_entry.strftime('%d')) + str(on_this_date_entry.strftime('%B')).lower()[:3] + str(on_this_date_entry.strftime('%Y'))

        except:
            pass
        
    
    before_date = ''

    if before_date_entry != 'None':

        try:

            before_date = str(before_date_entry.strftime('%d')) + str(before_date_entry.strftime('%B')).lower()[:3] + str(before_date_entry.strftime('%Y'))

        except:
            pass

    
    after_date = ''

    if after_date_entry != 'None':
        
        try:
            after_date = str(after_date_entry.strftime('%d')) + str(after_date_entry.strftime('%B')).lower()[:3] + str(after_date_entry.strftime('%Y'))
            
        except:
            pass
    
    #Other entries
    case_name_mnc = case_name_mnc_entry
    judge =  judge_entry
    reported_citation = reported_citation_entry
    file_number = file_number_entry
    npa = npa_entry
    with_all_the_words = with_all_the_words_entry
    with_at_least_one_of_the_words = with_at_least_one_of_the_words_entry
    without_the_words = without_the_words_entry
    phrase = phrase_entry
    proximity = proximity_entry
    legislation = legislation_entry
    cases_cited = cases_cited_entry
    catchwords = catchwords_entry 
    
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
           'Courts' : court, 
           'Case name or medium neutral citation': case_name_mnc, 
           'Judge' : judge, 
            'Reported citation' : reported_citation, 
            'File number': file_number,
            'National practice area': npa,
            'With all the words': with_all_the_words,
            'With at least one of the words': with_at_least_one_of_the_words,
            'Without the words': without_the_words,
            'Phrase': phrase,
            'Proximity': proximity,
            'On this date': on_this_date,
            'Decision date is after': after_date,
            'Decision date is before': before_date,
            'Legislation': legislation,
            'Cases cited': cases_cited,
            'Catchwords' : catchwords, 
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
from functions.common_functions import open_page, clear_cache_except_validation_df_master, tips


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
    st.session_state['df_master'].loc[0, 'Example'] = ''

    #Jurisdiction specific
    st.session_state['df_master'].loc[0, 'Courts'] = 'Federal Court'
    st.session_state['df_master'].loc[0, 'Case name or medium neutral citation'] = None
    st.session_state['df_master'].loc[0, 'Judge'] = None
    st.session_state['df_master'].loc[0, 'Reported citation'] = None
    st.session_state['df_master'].loc[0, 'File number'] = None
    st.session_state['df_master'].loc[0, 'National practice area'] = 'All'
    st.session_state['df_master'].loc[0, 'With all the words'] = None
    st.session_state['df_master'].loc[0, 'With at least one of the words'] = None
    st.session_state['df_master'].loc[0, 'Without the words'] = None
    st.session_state['df_master'].loc[0, 'Phrase'] = None
    st.session_state['df_master'].loc[0, 'Proximity'] = None
    st.session_state['df_master'].loc[0, 'On this date'] = None
    st.session_state['df_master'].loc[0, 'Decision date is after'] = None
    st.session_state['df_master'].loc[0, 'Decision date is before'] = None
    st.session_state['df_master'].loc[0, 'Legislation'] = None
    st.session_state['df_master'].loc[0, 'Cases cited'] = None
    st.session_state['df_master'].loc[0, 'Catchwords']  = None

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})
    
if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#Initialise jurisdiction_page
if 'jurisdiction_page' not in st.session_state:
    st.session_state['jurisdiction_page'] = 'pages/FCA.py'

#Initialise error reporting status
if 'error_msg' not in st.session_state:
    st.session_state['error_msg'] = ''

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'HOME.py'

# %% [markdown]
# ## Form before AI

# %%
#if st.session_state.page_from != "pages/FCA.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the Federal Court of Australia]")

st.success(default_msg)

st.write(f'This app sources cases from the [Federal Court Digital Law Library](https://www.fedcourt.gov.au/digital-law-library/judgments/search)  and the [Open Australian Legal Corpus](https://huggingface.co/datasets/umarbutler/open-australian-legal-corpus) compiled by Umar Butler.')

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Court or tribunal to cover")

courts_entry = st.selectbox(label = 'Select one to search', options = fca_courts_list, index = fca_courts_list.index(st.session_state.df_master.loc[0, 'Courts']))

st.write('You may select the Federal Court, tribunals administered by the Court, the Supreme Court of Norfolk Island and the Industrial Relations Court of Australia.')

st.subheader("Your search terms")

st.markdown("""For search tips, please visit the [Federal Court Digital Law Library](https://www.fedcourt.gov.au/digital-law-library/judgments/search). This section mimics their judgments search function.
""")

catchwords_entry = st.text_input(label = 'Catchwords', value = st.session_state.df_master.loc[0, 'Catchwords'] )

legislation_entry = st.text_input(label = 'Legislation', value = st.session_state.df_master.loc[0, 'Legislation'])

cases_cited_entry = st.text_input(label = 'Cases cited', value = st.session_state.df_master.loc[0, 'Cases cited'])

case_name_mnc_entry = st.text_input(label = "Case name or medium neutral citation", value = st.session_state.df_master.loc[0, 'Case name or medium neutral citation'])

judge_entry = st.text_input(label = 'Judge', value = st.session_state.df_master.loc[0, 'Judge'])

reported_citation_entry = st.text_input(label = 'Reported citation', value = st.session_state.df_master.loc[0, 'Reported citation'])

file_number_entry = st.text_input(label = 'File number', value = st.session_state.df_master.loc[0, 'File number'])

npa_entry = st.selectbox(label = 'National practice area (FCA2016-)', options = npa_list, index = npa_list.index(st.session_state.df_master.loc[0, 'National practice area']), help = 'NPAs (National Practice Areas) are searchable only for judgments from 2016 onwards.')

with_all_the_words_entry = st.text_input(label = 'With ALL the words', value = st.session_state.df_master.loc[0, 'With all the words'] )

with_at_least_one_of_the_words_entry = st.text_input(label = 'With at least one of the words', value = st.session_state.df_master.loc[0, 'With at least one of the words'])

without_the_words_entry = st.text_input(label = 'Without the words', value = st.session_state.df_master.loc[0, 'Without the words'])

phrase_entry = st.text_input(label = 'Phrase', value = st.session_state.df_master.loc[0, 'Phrase'])

proximity_entry  = st.text_input(label = 'Proximity', value = st.session_state.df_master.loc[0, 'Proximity'])

on_this_date_entry = st.date_input(label = 'On this date', value = date_parser(st.session_state.df_master.loc[0, 'On this date']), format="DD/MM/YYYY", min_value = date(1976, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

date_col1, date_col2 = st.columns(2)

with date_col1:

    after_date_entry = st.date_input(label = 'Decision date is after', value = date_parser(st.session_state.df_master.loc[0, 'Decision date is after']), format="DD/MM/YYYY", min_value = date(1976, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")


with date_col2:

    before_date_entry = st.date_input(label = 'Decision date is before', value = date_parser(st.session_state.df_master.loc[0, 'Decision date is before'] ), format="DD/MM/YYYY", min_value = date(1976, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")


st.caption('This app will not collect catchwords or other metadata from judgments published before 1995 (given their [PDF](https://www.fedcourt.gov.au/digital-law-library/judgments/judgments-faq) format).')

#st.subheader("Judgment metadata collection")

#st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 

#Case name and medium neutral citation are always included with your results.
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
    
    with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):

        try:
            
            df_master = fca_create_df()
            
            results_url_num = fca_search_url(df_master)
                
            results_count = results_url_num['results_count']
        
            results_url = results_url_num['results_url']
        
            search_results_soup = results_url_num['soup']
        
            if results_count > 0:
            
                #Get relevant cases
                
                judgments_file = []
                
                judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                
                case_infos = fca_search_results_to_judgment_links(search_results_soup, results_url, judgments_counter_bound)
                
                for case in case_infos:
                
                    #add search results to json
                    judgments_file.append(case)
        
                df_preview = pd.DataFrame(judgments_file)
        
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

    all_search_terms = str(catchwords_entry) + str(legislation_entry) + str(cases_cited_entry) + str(case_name_mnc_entry) + str(judge_entry) + str(reported_citation_entry) + str(file_number_entry) + str(npa_entry) + str(with_all_the_words_entry) + str(with_at_least_one_of_the_words_entry) + str(without_the_words_entry) + str(phrase_entry) + str(proximity_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
                
    else:
            
        df_master = fca_create_df()

        save_input(df_master)
        
        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:
    
    df_master = fca_create_df()

    save_input(df_master)

    st.session_state["page_from"] = 'pages/FCA.py'
    
    st.switch_page("Home.py")


# %%
#if remove_button:
    
    #st.session_state.pop('df_master')

    #st.rerun()

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    all_search_terms = str(catchwords_entry) + str(legislation_entry) + str(cases_cited_entry) + str(case_name_mnc_entry) + str(judge_entry) + str(reported_citation_entry) + str(file_number_entry) + str(npa_entry) + str(with_all_the_words_entry) + str(with_at_least_one_of_the_words_entry) + str(without_the_words_entry) + str(phrase_entry) + str(proximity_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
    
        df_master = fca_create_df()

        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:
                
                results_url_num = fca_search_url(df_master)
                    
                results_count = results_url_num['results_count']

                if results_count == 0:
                    
                    st.error(no_results_msg)

                else:
    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/FCA.py'
                    
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

