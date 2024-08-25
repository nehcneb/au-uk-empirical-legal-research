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
from common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_range_check, au_date, save_input, pdf_judgment
#Import variables
from common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # Federal Courts search engine

# %%
from common_functions import link


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


# %%
#Define format functions for courts choice, and GPT questions

#auxiliary lists and variables

fca_courts = {'Federal Court': 'fca', 
              'Industrial Relations Court of Australia': 'irc', 
              'Australian Competition Tribunal': 'tribunals%2Facompt', 
              'Copyright Tribunal': 'tribunals%2Facopyt', 
              'Defence Force Discipline Appeal Tribunal': 'tribunals%2Fadfdat', 
              'Federal Police Discipline Tribunal': 'tribunals%2Ffpdt', 
              'Trade Practices Tribunal': 'tribunals%2Fatpt', 
              'Supreme Court of Norfolk Island': 'nfsc',
             'All': ''}

fca_courts_list = list(fca_courts.keys())


# %%
#Function turning search terms to search results url
def fca_search(court = '', 
               case_name_mnc= '', 
               judge ='', 
               reported_citation ='', 
               file_number ='', 
               npa = '', 
               with_all_the_words = '', 
               with_at_least_one_of_the_words = '', 
               without_the_words = '', 
               phrase = '', 
               proximity = '', 
               on_this_date = '', 
               after_date = '', 
               before_date = '', 
               legislation = '', 
               cases_cited = '', 
               catchwords = ''):

    #If only searching FCA
    #base_url = "https://search2.fedcourt.gov.au/s/search.html?collection=judgments&sort=date&meta_v_phrase_orsand=judgments%2FJudgments%2Ffca"

    #If allowing users to search which court
    base_url = "https://search2.fedcourt.gov.au/s/search.html?collection=judgments&sort=date&meta_v_phrase_orsand=judgments%2FJudgments%2F" + fca_courts[court]
    
    params = {'meta_2' : case_name_mnc, 
              'meta_A' : judge, 
              'meta_z' : reported_citation, 
              'meta_3' : file_number, 
              'meta_n_phrase_orsand' : npa, 
              'query_sand' : with_all_the_words, 
              'query_or' : with_at_least_one_of_the_words, 
              'query_not' : without_the_words, 
              'query_phrase' : phrase, 
              'query_prox' : proximity, 
              'meta_d' : on_this_date, 
              'meta_d1' : after_date, 
              'meta_d2' : before_date, 
              'meta_7' : legislation, 
              'meta_4' : cases_cited, 
              'meta_B' : catchwords}

    response = requests.get(base_url, params=params)
    response.raise_for_status()
    # Process the response (e.g., extract relevant information)
    # Your code here...
    return response.url


# %%
#Define function turning search results url to links to judgments

@st.cache_data
def fca_search_results_to_judgment_links(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")

    #Start counter

    counter = 1
    
    # Get links of first 20 results
    #links_raw = soup.find_all("a", href=re.compile("fca")) #If want to search FCA only
    
    links_raw = soup.find_all("a", href=re.compile("judgments"))
    links = []
    
    for i in links_raw:
        if (('title=' in str(i)) and (counter <=judgment_counter_bound)):
            remove_title = str(i).split('" title=')[0]
            remove_leading_words = remove_title.replace('<a href="', '')
            if 'a class=' not in remove_leading_words:
                links.append(remove_leading_words)
                counter = counter + 1

    #Go beyond first 20 results

    #Auxiliary list for getting more pages of search results
    further_page_ending_list = []
    for i in range(100):
        further_page_ending = 20 + i
        if ((str(further_page_ending)[-1] =='1') & (str(further_page_ending)[0] not in ['3', '5', '7', '9', '11'])):
            further_page_ending_list.append(str(further_page_ending))
    
    for ending in further_page_ending_list:
        if counter <=judgment_counter_bound:
            url_next_page = url_search_results + '&start_rank=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            #links_next_page_raw = soup_judgment_next_page.find_all("a", href=re.compile("fca"))  #If want to search FCA only
            links_next_page_raw = soup_judgment_next_page.find_all("a", href=re.compile("judgments"))

            #Check if stll more results
            if len(links_next_page_raw) > 0:
                for i in links_next_page_raw:
                    if (('title=' in str(i)) and (counter <=judgment_counter_bound)):
                        remove_title = str(i).split('" title=')[0]
                        remove_leading_words = remove_title.replace('<a href="', '')
                        if 'a class=' not in remove_leading_words:
                            links.append(remove_leading_words)
                            counter = counter + 1

            else:
                break

    return links


# %%
#judgment url to word document
#NOT in use
def fca_link_to_doc(url_judgment):
    page_judgment = requests.get(url_judgment)
    soup_judgment = BeautifulSoup(page_judgment.content, "lxml")
    link_word_raw = soup_judgment.find_all('a', string=re.compile('Word'))
    if len(link_word_raw)> 0:
        link_to_word = str(link_word_raw).split('>')[0].replace('[<a href="', '')
        return link_to_word
    else:
        return url_judgment


# %%
#Meta labels and judgment combined
#IN USE
fca_metalabels = ['MNC', 'Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to']
fca_metalabels_droppable = ['Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to', 'Order']

@st.cache_data
def fca_meta_judgment_dict(judgment_url):
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to Federal Court Digital Law Library' : '', 
                'MNC' : '',  
                 'Year' : '',  
                 'Appeal' : '',  
                 'File_Number' : '',  
                 'Judge' : '',  
                 'Judgment_Dated' : '',  
                 'Catchwords' : '',  
                 'Subject' : '',  
                 'Words_Phrases' : '',  
                 'Legislation' : '',  
                 'Cases_Cited' : '',  
                 'Division' : '',  
                 'NPA' : '',  
                'Sub_NPA' : '', 
                 'Pages' : '',  
                 'All_Parties' : '',  
                 'Jurisdiction' : '',  
                 'Reported' : '',  
                 'Summary' : '',  
                 'Corrigenda' : '',  
                 'Parties' : '',  'FileName' : '',  
                 'Asset_ID' : '',  
                 'Date.published' : '', 
                'Appeal_to' : '', 
                'Order': '',
                'judgment' : ''
                }

    #Attach hyperlink

    judgment_dict['Hyperlink to Federal Court Digital Law Library'] = link(judgment_url)
    
    page = requests.get(judgment_url)
    soup = BeautifulSoup(page.content, "lxml")
    meta_tags = soup.find_all("meta")

    #Attach meta tags
    if len(meta_tags)>0:
        for tag_index in range(len(meta_tags)):
            meta_name = meta_tags[tag_index].get("name")
            if meta_name in fca_metalabels:
                meta_content = meta_tags[tag_index].get("content")
                judgment_dict[meta_name] = meta_content

    #Check if not gets taken to a PDF

    if '.pdf' not in judgment_url.lower():
    
        try:
            judgment_dict['Case name'] = judgment_dict['MNC'].split('[')[0]
            judgment_dict['Medium neutral citation'] = '[' + judgment_dict['MNC'].split('[')[1]
            del judgment_dict['MNC']
    
        except:
            pass

        #Attach order_text and judgment
    
        judgment_text = ''
        order_text = ''
    
        try:
            judgment_raw = ''
            judgment_raw = soup.find("div", {"class": "judgment_content"}).get_text(separator="\n", strip=True)
    
            above_reasons_for_judgment = str(re.split("REASONS FOR JUDGMENT", judgment_raw, flags=re.IGNORECASE)[0])
    
            below_reasons_for_judgment = str(re.split("REASONS FOR JUDGMENT", judgment_raw, flags=re.IGNORECASE)[1:])
    
            order_text = "BETWEEEN:" + str(re.split("BETWEEN:", above_reasons_for_judgment, flags=re.IGNORECASE)[1:])[2:][:-2]
    
            judgment_text = below_reasons_for_judgment
    
        except:
            try:
                judgment_text = soup.find("div", {"class": "judgment_content"}).get_text(separator="\n", strip=True)
            except:
                judgment_text = soup.get_text(separator="\n", strip=True)
        
        judgment_dict['judgment'] = judgment_text
        judgment_dict['Order'] = order_text

    #Check if gets taken to a PDF

    else:
        #Attach case name
        judgment_dict['Case name'] = 'Not working properly because judgment in PDF. References to paragraphs likely to pages or wrong.'

        #Attach judgment pdf text
        try:
            judgment_pdf_raw = pdf_judgment(judgment_url)
            judgment_dict['judgment'] = judgment_pdf_raw
            
        except:
            pass
    
        #Attach medium neutral citation
        try:
            mnc_raw = judgment_url.split('/')[-1].replace('.pdf', '')

            #for court_i in ['fca', 'fcafc']: #If want to search FCA only
            for court_i in ['fca', 'fcafc', 'irc', 'acompt', 'acopyt', 'adfdat', 'fpdt', 'atpt', 'nfsc']:
                if court_i in mnc_raw.lower():
                    mnc_list = mnc_raw.lower().split(court_i)
                    judgment_dict['Medium neutral citation'] = '[' + mnc_list[0] + '] ' + court_i.upper()  + ' ' +  mnc_list[1]
                    judgment_dict['Medium neutral citation']=judgment_dict['Medium neutral citation']

                    while ' 0' in judgment_dict['Medium neutral citation']:
                        judgment_dict['Medium neutral citation'] = judgment_dict['Medium neutral citation'].replace(' 0', ' ')
            
            del judgment_dict['MNC']
    
        except:
            pass        
            
    return judgment_dict


# %%
#Preliminary function for changing names for any PDF judgments

@st.cache_data
def fca_pdf_name_mnc_list(url_search_results, judgment_counter_bound):
                      
    #Scrape webpage of search results
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")
    
    #Placeholder
    name_mnc_list = []

    #Start counter
    counter = 1
    # Get links of first 20 results
    #links_raw = soup.find_all("a", href=re.compile("fca")) #If want to search FCA only
    links_raw = soup.find_all("a", href=re.compile("judgments"))
    
    for i in links_raw:
        if (('title=' in str(i)) and (counter <=judgment_counter_bound)):
            name_mnc_list.append(i['title'])
            counter = counter + 1
    
    #Go beyond first 20 results

    #Auxiliary list for getting more pages of search results
    further_page_ending_list = []
    for i in range(100):
        further_page_ending = 20 + i
        if ((str(further_page_ending)[-1] =='1') & (str(further_page_ending)[0] not in ['3', '5', '7', '9', '11'])):
            further_page_ending_list.append(str(further_page_ending))

    for ending in further_page_ending_list:
        if counter <=judgment_counter_bound:
            url_next_page = url_search_results + '&start_rank=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            #links_next_page_raw = soup_judgment_next_page.find_all("a", href=re.compile("fca")) #If want to search FCA only
            links_next_page_raw = soup_judgment_next_page.find_all("a", href=re.compile("judgments"))
    
            #Check if stll more results
            if len(links_next_page_raw) > 0:
                for i in links_next_page_raw:
                    if (('title=' in str(i)) and (counter <=judgment_counter_bound)):
                        name_mnc_list.append(i['title'])
                        counter = counter + 1
            else:
                break
        
    return name_mnc_list


# %%
#Function for changing names for any PDF judgments

def fca_pdf_name(name_mnc_list, mnc):
    #Placeholder
    name = 'Not working properly because judgment in PDF. References to paragraphs likely to pages or wrong.' 
    
    for i in name_mnc_list:
        if mnc in i:
            name_raw = i.split(' ' + mnc)[0]
            name = name_raw.replace('Cached: ', '')
            
    return name



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from gpt_functions import question_characters_bound, role_content#, intro_for_GPT


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


# %%
#Obtain parameters

@st.cache_data
def fca_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    url_search_results = fca_search(court = df_master.loc[0, 'Courts'], 
                     case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
                     judge = df_master.loc[0, 'Judge'], 
                     reported_citation = df_master.loc[0, 'Reported citation'],
                     file_number  = df_master.loc[0, 'File number'],
                     npa = df_master.loc[0, 'National practice area'], 
                     with_all_the_words  = df_master.loc[0, 'With all the words'], 
                     with_at_least_one_of_the_words = df_master.loc[0, 'With at least one of the words'],
                     without_the_words = df_master.loc[0, 'Without the words'],
                     phrase  = df_master.loc[0, 'Phrase'], 
                     proximity = df_master.loc[0, 'Proximity'], 
                     on_this_date = df_master.loc[0, 'On this date'], 
                     after_date = df_master.loc[0, 'Decision date is after'], 
                     before_date = df_master.loc[0, 'Decision date is before'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'] 
                    )
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    judgments_links = fca_search_results_to_judgment_links(url_search_results, judgments_counter_bound)

    for link in judgments_links:

        judgment_dict = fca_meta_judgment_dict(link)

#        meta_data = meta_dict(link)  
#        doc_link = fca_link_to_doc(link)
#        judgment_dict = doc_link_to_dict(doc_link)
#        judgment_dict = link_to_dict(link)
#        judgments_all_info = { **meta_data, **judgment_dict}
#        judgments_file.append(judgments_all_info)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(5, 15))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
    
    #Rename column titles
    
#    try:
#        df_individual['Hyperlink (double click)'] = df_individual['Hyperlink'].apply(link)
#        df_individual.pop('Hyperlink')
#    except:
#        pass

    #Correct case names for any PDFs

    name_mnc_list = fca_pdf_name_mnc_list(url_search_results, judgments_counter_bound)

    for judgment_index in df_individual.index:
        
        if (('pdf' in df_individual.loc[judgment_index, 'Case name'].lower()) or ('.pdf' in str(df_individual.loc[judgment_index, 'Hyperlink to Federal Court Digital Law Library']).lower())):
            try:
                df_individual.loc[judgment_index, 'Case name'] = fca_pdf_name(name_mnc_list, df_individual.loc[judgment_index, 'Medium neutral citation'])
            except Exception as e:
                print(f"{df_individual.loc[judgment_index, 'Medium neutral citation']}: cannot change case name for PDF.")
                print(e)
                    
    #Instruct GPT
    
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
        for meta_label in fca_metalabels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
def fca_search_url(df_master):
    df_master = df_master.fillna('')
    
    #Combining catchwords into new column
    
    #Conduct search
    
    url = fca_search(court = df_master.loc[0, 'Courts'], 
                     case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
                     judge = df_master.loc[0, 'Judge'], 
                     reported_citation = df_master.loc[0, 'Reported citation'],
                     file_number  = df_master.loc[0, 'File number'],
                     npa = df_master.loc[0, 'National practice area'], 
                     with_all_the_words  = df_master.loc[0, 'With all the words'], 
                     with_at_least_one_of_the_words = df_master.loc[0, 'With at least one of the words'],
                     without_the_words = df_master.loc[0, 'Without the words'],
                     phrase  = df_master.loc[0, 'Phrase'], 
                     proximity = df_master.loc[0, 'Proximity'], 
                     on_this_date = df_master.loc[0, 'On this date'], 
                     after_date = df_master.loc[0, 'Decision date is after'], 
                     before_date = df_master.loc[0, 'Decision date is before'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'] 
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
    st.session_state['df_master'].loc[0, 'Courts'] = 'Federal Court'
    st.session_state['df_master'].loc[0, 'Case name or medium neutral citation'] = None
    st.session_state['df_master'].loc[0, 'Judge'] = None
    st.session_state['df_master'].loc[0, 'Reported citation'] = None
    st.session_state['df_master'].loc[0, 'File number'] = None
    st.session_state['df_master'].loc[0, 'National practice area'] = None
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

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
if st.session_state.page_from != "pages/FCA.py": #Need to add in order to avoid GPT page from showing form of previous page

    #Create form
    
    return_button = st.button('RETURN to first page')
    
    st.header(f"You have selected to study :blue[judgments of the Federal Court of Australia].")
    
    #    st.header("Judgment Search Criteria")
    
    st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.
""")
    
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')

    reset_button = st.button(label='RESET', type = 'primary')
    
    st.subheader("Court or tribunal to cover")
    
    courts_entry = st.selectbox(label = 'Select or type in the court or tribunal to cover', options = fca_courts_list, index = fca_courts_list.index(st.session_state.df_master.loc[0, 'Courts']))
    
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
    
    npa_entry = st.text_input(label = 'National practice area', value = st.session_state.df_master.loc[0, 'National practice area'] )
    
    with_all_the_words_entry = st.text_input(label = 'With ALL the words', value = st.session_state.df_master.loc[0, 'With all the words'] )
    
    with_at_least_one_of_the_words_entry = st.text_input(label = 'With at least one of the words', value = st.session_state.df_master.loc[0, 'With at least one of the words'])
    
    without_the_words_entry = st.text_input(label = 'Without the words', value = st.session_state.df_master.loc[0, 'Without the words'])
    
    phrase_entry = st.text_input(label = 'Phrase', value = st.session_state.df_master.loc[0, 'Phrase'])
    
    proximity_entry  = st.text_input(label = 'Proximity', value = st.session_state.df_master.loc[0, 'Proximity'])
    
    on_this_date_entry = st.date_input(label = 'On this date', value = au_date(st.session_state.df_master.loc[0, 'On this date']), format="DD/MM/YYYY", min_value = date(1976, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
    after_date_entry = st.date_input(label = 'Decision date is after', value = au_date(st.session_state.df_master.loc[0, 'Decision date is after']), format="DD/MM/YYYY", min_value = date(1976, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
    before_date_entry = st.date_input(label = 'Decision date is before', value = au_date(st.session_state.df_master.loc[0, 'Decision date is before'] ), format="DD/MM/YYYY", min_value = date(1976, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
    st.caption('[Relatively earlier](https://www.fedcourt.gov.au/digital-law-library/judgments/judgments-faq) judgments will not be collected.')
    
    st.markdown("""You can preview the judgments returned by your search terms after you have entered some search terms.
    
You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")
    
    preview_button = st.button(label = 'PREVIEW on the Federal Court Digital Law Library (in a popped up window)', type = 'primary')
    
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
        
        df_master = fca_create_df()
        
        judgments_url = fca_search_url(df_master)
        
        open_page(judgments_url)

    # %%
    if keep_button:
    
        #Check whether search terms entered
    
        all_search_terms = str(catchwords_entry) + str(legislation_entry) + str(cases_cited_entry) + str(case_name_mnc_entry) + str(judge_entry) + str(reported_citation_entry) + str(file_number_entry) + str(npa_entry) + str(with_all_the_words_entry) + str(with_at_least_one_of_the_words_entry) + str(without_the_words_entry) + str(phrase_entry) + str(proximity_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry)
        
        if all_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
                    
        else:
                
            df_master = fca_create_df()

            save_input(df_master)
            
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

            save_input(df_master)

            #Check search results
            fca_url_to_check = fca_search_url(df_master)
            fca_html = requests.get(fca_url_to_check)
            fca_soup = BeautifulSoup(fca_html.content, "lxml")
            if 'Display' not in str(fca_soup):
                st.error(no_results_msg)

            else:
                        
                st.session_state["page_from"] = 'pages/FCA.py'
                
                st.switch_page('pages/GPT.py')

