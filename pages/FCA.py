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
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb

# %%
#Import functions
from common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner 
#Import variables
from common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %% [markdown]
# # Federal Courts search engine

# %%
from common_functions import link


# %%
#function to create dataframe
def create_df():

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
    gpt_activation_status = gpt_activation_entry
    
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
#Auxiliary list for getting more pages of search results
further_page_ending_list = []
for i in range(100):
    further_page_ending = 20 + i
    if ((str(further_page_ending)[-1] =='1') & (str(further_page_ending)[0] not in ['3', '5', '7', '9', '11'])):
        further_page_ending_list.append(str(further_page_ending))


# %%
#Define function turning search results url to links to judgments
def search_results_to_judgment_links(url_search_results, judgment_counter_bound):
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
def link_to_doc(url_judgment):
    page_judgment = requests.get(url_judgment)
    soup_judgment = BeautifulSoup(page_judgment.content, "lxml")
    link_word_raw = soup_judgment.find_all('a', string=re.compile('Word'))
    if len(link_word_raw)> 0:
        link_to_word = str(link_word_raw).split('>')[0].replace('[<a href="', '')
        return link_to_word
    else:
        return url_judgment


# %%
#Define function for judgment link containing PDF
def pdf_judgment(url):
    headers = {'User-Agent': 'whatever'}
    r = requests.get(url, headers=headers)
    remote_file_bytes = io.BytesIO(r.content)
    pdfdoc_remote = PyPDF2.PdfReader(remote_file_bytes)
    text_list = []

    for page in pdfdoc_remote.pages:
        text_list.append(page.extract_text())
    
    return str(text_list)



# %%
#Meta labels and judgment combined
#IN USE
meta_labels = ['MNC', 'Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to']
meta_labels_droppable = ['Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to', 'Order']

def meta_judgment_dict(judgment_url):
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
            if meta_name in meta_labels:
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
def pdf_name_mnc_list(url_search_results, judgment_counter_bound):
                      
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

def pdf_name(name_mnc_list, mnc):
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
from gpt_functions import question_characters_bound, default_judgment_counter_bound, role_content#, intro_for_GPT


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

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

def run(df_master):
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

    judgments_links = search_results_to_judgment_links(url_search_results, judgments_counter_bound)

    for link in judgments_links:

        judgment_dict = meta_judgment_dict(link)

#        meta_data = meta_dict(link)  
#        doc_link = link_to_doc(link)
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

    name_mnc_list = pdf_name_mnc_list(url_search_results, judgments_counter_bound)

    for judgment_index in df_individual.index:
        
        if (('pdf' in df_individual.loc[judgment_index, 'Case name'].lower()) or ('.pdf' in str(df_individual.loc[judgment_index, 'Hyperlink to Federal Court Digital Law Library']).lower())):
            try:
                df_individual.loc[judgment_index, 'Case name'] = pdf_name(name_mnc_list, df_individual.loc[judgment_index, 'Medium neutral citation'])
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
        for meta_label in meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
def search_url(df_master):
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

if 'gpt_enhancement_entry' not in st.session_state:
    st.session_state['gpt_enhancement_entry'] = False

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_master' not in st.session_state:

    st.session_state['df_master'] = pd.DataFrame([])

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

# %%
#Try to carry over previously entered personal details    
try:
    st.session_state['gpt_api_key_entry'] = st.session_state.df_master.loc[0, 'Your GPT API key']
except:
    st.session_state['gpt_api_key_entry'] = ''

try:
    st.session_state['name_entry'] = st.session_state.df_master.loc[0, 'Your name']
except:
    st.session_state['name_entry'] = ''

try:
    st.session_state['email_entry'] = st.session_state.df_master.loc[0, 'Your email address']
    
except:
    st.session_state['email_entry'] = ''

# %% [markdown]
# ## Form before AI

# %%
#Create form

return_button = st.button('RETURN to first page')

st.header(f"You have selected to study :blue[judgments of the Federal Court of Australia].")

#    st.header("Judgment Search Criteria")

st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.
""")

st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')

st.subheader("Court or tribunal to cover")

courts_entry = st.selectbox(label = 'Select or type in the court or tribunal to cover', options = fca_courts_list, index = fca_courts_list.index('Federal Court'))

st.write('You may select the Federal Court, tribunals administered by the Court, the Supreme Court of Norfolk Island and the Industrial Relations Court of Australia.')

st.subheader("Your search terms")

st.markdown("""For search tips, please visit the [Federal Court Digital Law Library](https://www.fedcourt.gov.au/digital-law-library/judgments/search). This section mimics their judgments search function.
""")

catchwords_entry = st.text_input('Catchwords')

legislation_entry = st.text_input('Legislation')

cases_cited_entry = st.text_input('Cases cited')

case_name_mnc_entry = st.text_input("Case name or medium neutral citation")

judge_entry = st.text_input('Judge')

reported_citation_entry = st.text_input('Reported citation')

file_number_entry = st.text_input('File number')

npa_entry = st.text_input('National practice area')

with_all_the_words_entry = st.text_input('With ALL the words')

with_at_least_one_of_the_words_entry = st.text_input('With at least one of the words')

without_the_words_entry = st.text_input('Without the words')

phrase_entry = st.text_input('Phrase')

proximity_entry  = st.text_input('Proximity')

on_this_date_entry = st.date_input('On this date', value = None, format="DD/MM/YYYY")

after_date_entry = st.date_input('Decision date is after', value = None, format="DD/MM/YYYY")

before_date_entry = st.date_input('Decision date is before', value = None, format="DD/MM/YYYY")

st.caption('[Relatively earlier](https://www.fedcourt.gov.au/digital-law-library/judgments/judgments-faq) judgments will not be collected.')

st.markdown("""You can preview the judgments returned by your search terms on the Federal Court Digital Law Library after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")

preview_button = st.button('PREVIEW on the Federal Court Digital Law Library (in a popped up window)')

st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 

Case name and medium neutral citation are always included with your results.
""")

meta_data_entry = st.checkbox('Include metadata', value = False)



# %% [markdown]
# ## Form for AI and account

# %%
st.header("Use GPT as your research assistant")

#    st.markdown("**You have three (3) opportunities to engage with GPT through the Empirical Legal Research Kickstarter. Would you like to use one (1) of these opportunities now?**")

st.markdown("**:green[Would you like GPT to answer questions about the judgments returned by your search terms?]**")

st.markdown("""Please consider trying this program without asking GPT any questions first. You can, for instance, obtain the judgments satisfying your search criteria and extract the judgment metadata without using GPT.
""")

gpt_activation_entry = st.checkbox('Use GPT', value = False)

st.caption("Use of GPT is costly and funded by a grant. For the model used by default (gpt-4o-mini), Ben's own experience suggests that it costs approximately USD \$0.05 (excl GST) per judgment. The [exact cost](https://openai.com/pricing) for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced. You will be given ex-post cost estimates.")

st.subheader("Enter your questions for each judgment")

st.markdown("""Please enter one question **per line or per paragraph**. GPT will answer your questions for **each** judgment based only on information from **that** judgment. """)

st.markdown("""GPT is instructed to avoid giving answers which cannot be obtained from the relevant judgment itself. This is to minimise the risk of giving incorrect information (ie hallucination).""")

if st.toggle('See the instruction given to GPT'):
    st.write(f"{intro_for_GPT[0]['content']}")

if st.toggle('Tips for using GPT'):
    tips()

gpt_questions_entry = st.text_area(f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound) 

#Disable toggles while prompt is not entered or the same as the last processed prompt
if gpt_activation_entry:
    
    if gpt_questions_entry:
        st.session_state['disable_input'] = False
        
    else:
        st.session_state['disable_input'] = True
else:
    st.session_state['disable_input'] = False
    
st.caption(f"By default, answers to your questions will be generated by model gpt-4o-mini. Due to a technical limitation, this model will read up to approximately {round(tokens_cap('gpt-4o-mini')*3/4)} words from each judgment.")

if own_account_allowed() > 0:
    
    st.subheader(':orange[Enhance program capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum nunber of judgments to process? You can do so with your own GPT account.
    """)
    
    own_account_entry = st.toggle('Use my own GPT account',  disabled = st.session_state.disable_input)
    
    if own_account_entry:
    
        st.session_state["own_account"] = True
    
        st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage [here](https://platform.openai.com/signup). You can then create and find your API key [here](https://platform.openai.com/api-keys).
    """)
            
        name_entry = st.text_input(label = "Your name", value = st.session_state.name_entry)
    
        email_entry = st.text_input(label = "Your email address", value = st.session_state.email_entry)
        
        gpt_api_key_entry = st.text_input(label = "Your GPT API key (mandatory)", value = st.session_state.gpt_api_key_entry)
        
        valdity_check = st.button('VALIDATE your API key')
    
        if valdity_check:
            
            api_key_valid = is_api_key_valid(gpt_api_key_entry)
                    
            if api_key_valid == False:
                st.session_state['gpt_api_key_validity'] = False
                st.error('Your API key is not valid.')
                
            else:
                st.session_state['gpt_api_key_validity'] = True
                st.success('Your API key is valid.')
    
        st.markdown("""**:green[You can use the flagship version of GPT model (gpt-4o),]** which is :red[about 30 times more expensive, per character] than the default model (gpt-4o-mini) which you can use for free.""")  
        
        gpt_enhancement_entry = st.checkbox('Use the flagship GPT model', value = False)
        st.caption('Click [here](https://openai.com/api/pricing) for pricing information on different GPT models.')
        
        if gpt_enhancement_entry == True:
        
            st.session_state.gpt_model = "gpt-4o"
            st.session_state.gpt_enhancement_entry = True

        else:
            
            st.session_state.gpt_model = "gpt-4o-mini"
            st.session_state.gpt_enhancement_entry = False
        
        st.write(f'**:green[You can increase the maximum number of judgments to process.]** The default maximum is {default_judgment_counter_bound}.')
        
        #judgments_counter_bound_entry = round(st.number_input(label = 'Enter a whole number between 1 and 100', min_value=1, max_value=100, value=default_judgment_counter_bound))

        #st.session_state.judgments_counter_bound = judgments_counter_bound_entry

        judgments_counter_bound_entry = st.text_input(label = 'Enter a whole number between 1 and 100', value=str(default_judgment_counter_bound))

        if judgments_counter_bound_entry:
            wrong_number_warning = f'You have not entered a whole number between 1 and 100. The program will process up to {default_judgment_counter_bound} judgments instead.'
            try:
                st.session_state.judgments_counter_bound = int(judgments_counter_bound_entry)
            except:
                st.warning(wrong_number_warning)
                st.session_state.judgments_counter_bound = default_judgment_counter_bound

            if ((st.session_state.judgments_counter_bound <= 0) or (st.session_state.judgments_counter_bound > 100)):
                st.warning(wrong_number_warning)
                st.session_state.judgments_counter_bound = default_judgment_counter_bound
    
        st.write(f'*GPT model {st.session_state.gpt_model} will answer any questions based on up to approximately {round(tokens_cap(st.session_state.gpt_model)*3/4)} words from each judgment, for up to {st.session_state.judgments_counter_bound} judgments.*')
    
    else:
        
        st.session_state["own_account"] = False
    
        st.session_state.gpt_model = "gpt-4o-mini"

        st.session_state.gpt_enhancement_entry = False
    
        st.session_state.judgments_counter_bound = default_judgment_counter_bound

# %% [markdown]
# ## Consent and next steps

# %%
st.header("Consent")

st.markdown("""By running this program, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False, disabled = st.session_state.disable_input)

st.markdown("""If you do not agree, then please feel free to close this form.""")

st.header("Next steps")

st.markdown("""**:green[You can now run the Empirical Legal Research Kickstarter.]** A spreadsheet which hopefully has the data you seek will be available for download.

You can also download a record of your entries.

""")

#Warning
if st.session_state.gpt_model == 'gpt-4o-mini':
    st.warning('A low-cost GPT model will answer your questions. Please reach out to Ben Chen at ben.chen@sydney.edu.au if you would like to use the flagship model instead.')

if st.session_state.gpt_model == "gpt-4o":
    st.warning('An expensive GPT model will answer your questions. Please be cautious.')

run_button = st.button('RUN the program')

keep_button = st.button('DOWNLOAD your entries')

reset_button = st.button(label='RESET to start afresh', type = 'primary',  help = "Press to process new search terms or questions.")

#Display need resetting message if necessary
if st.session_state.need_resetting == 1:
    if ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output) > 0)):
        st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')

# %% [markdown]
# ## Previous responses and outputs

# %%
#Create placeholder download buttons if previous entries and results in st.session_state:

if ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output)>0)):
    
    #Load previous entries and results
    
    df_master = st.session_state.df_master
    df_individual_output = st.session_state.df_individual_output

    #Buttons for downloading entries
    st.subheader('Looking for your previous entries and results?')

    st.write('Previous entries')

    entries_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_entries'

    csv = convert_df_to_csv(df_master)

    ste.download_button(
        label="Download your previous entries as a CSV (for use in Excel etc)", 
        data = csv,
        file_name=entries_output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    xlsx = convert_df_to_excel(df_master)
    
    ste.download_button(label='Download your previous entries as an Excel spreadsheet (XLSX)',
                        data=xlsx,
                        file_name=entries_output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )

    json = convert_df_to_json(df_master)
    
    ste.download_button(
        label="Download your previous entries as a JSON", 
        data = json,
        file_name= entries_output_name + '.json', 
        mime= "application/json", 
    )

    st.write('Previous results')

    output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'

    csv_output = convert_df_to_csv(df_individual_output)
    
    ste.download_button(
        label="Download your previous results as a CSV (for use in Excel etc)", 
        data = csv_output,
        file_name= output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    excel_xlsx = convert_df_to_excel(df_individual_output)
    
    ste.download_button(label='Download your previous results as an Excel spreadsheet (XLSX)',
                        data=excel_xlsx,
                        file_name= output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )
    
    json_output = convert_df_to_json(df_individual_output)
    
    ste.download_button(
        label="Download your previous results as a JSON", 
        data = json_output,
        file_name= output_name + '.json', 
        mime= "application/json", 
    )

    st.page_link('pages/AI.py', label="ANALYSE your previous spreadsheet with an AI", icon = '🤔')

# %% [markdown]
# # Save and run

# %%
if preview_button:
    
    df_master = create_df()
    
    judgments_url = search_url(df_master)
    
    open_page(judgments_url)

# %%
if run_button:

    #Check whether search terms entered

    all_search_terms = str(catchwords_entry) + str(legislation_entry) + str(cases_cited_entry) + str(case_name_mnc_entry) + str(judge_entry) + str(reported_citation_entry) + str(file_number_entry) + str(npa_entry) + str(with_all_the_words_entry) + str(with_at_least_one_of_the_words_entry) + str(without_the_words_entry) + str(phrase_entry) + str(proximity_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    elif int(consent) == 0:
        st.warning("You must click on 'Yes, I agree.' to run the program.")

    elif ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output)>0)):
        st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')

        st.session_state['need_resetting'] = 1
            
    elif ((st.session_state.own_account == True) and (st.session_state.gpt_api_key_validity == False)):
            
        st.warning('You have not validated your API key.')
        quit()

    elif ((st.session_state.own_account == True) and (len(gpt_api_key_entry) < 20)):

        st.warning('You have not entered a valid API key.')
        quit()  
        
    else:
        
        st.write('Your results will be available for download soon. The estimated waiting time is about 2-3 minutes per 10 judgments.')
        #st.write('If this program produces an error or an unexpected spreadsheet, please double-check your search terms and try again.')

        with st.spinner("Running... Please :red[don't change] your entries (yet)."):

            try:

                #Create spreadsheet of responses
                df_master = create_df()

                #Activate user's own key or mine
                if st.session_state.own_account == True:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    API_key = st.secrets["openai"]["gpt_api_key"]
                
                openai.api_key = API_key

                #Produce results
                df_individual_output = run(df_master)
        
                #Keep results in session state
                st.session_state["df_individual_output"] = df_individual_output
        
                st.session_state["df_master"] = df_master

                #Change session states
                st.session_state['need_resetting'] = 1
                
                st.session_state["page_from"] = 'pages/FCA.py'
        
                #Write results
        
                st.success("Your results are now available for download. Thank you for using the Empirical Legal Research Kickstarter!")
                
                #Button for downloading results
                output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'
        
                csv_output = convert_df_to_csv(df_individual_output)
                
                ste.download_button(
                    label="Download your results as a CSV (for use in Excel etc)", 
                    data = csv_output,
                    file_name= output_name + '.csv', 
                    mime= "text/csv", 
        #            key='download-csv'
                )
        
                excel_xlsx = convert_df_to_excel(df_individual_output)
                
                ste.download_button(label='Download your results as an Excel spreadsheet (XLSX)',
                                    data=excel_xlsx,
                                    file_name= output_name + '.xlsx', 
                                    mime='application/vnd.ms-excel',
                                   )
        
                json_output = convert_df_to_json(df_individual_output)
                
                ste.download_button(
                    label="Download your results as a JSON", 
                    data = json_output,
                    file_name= output_name + '.json', 
                    mime= "application/json", 
                )
        
                st.page_link('pages/AI.py', label="ANALYSE your spreadsheet with an AI", icon = '🤔')

                    
                #Keep record on Google sheet
                #Obtain google spreadsheet       
                #conn = st.connection("gsheets_nsw", type=GSheetsConnection)
                #df_google = conn.read()
                #df_google = df_google.fillna('')
                #df_google=df_google[df_google["Processed"]!='']
                #df_master["Processed"] = datetime.now()
                #df_master.pop("Your GPT API key")
                #df_to_update = pd.concat([df_google, df_master])
                #conn.update(worksheet="CTH", data=df_to_update, )
            
            except Exception as e:
                st.error('Your search terms may not return any judgments. Please press the PREVIEW button above to double-check.')
                st.exception(e)



# %%
if keep_button:

    #Check whether search terms entered

    all_search_terms = str(catchwords_entry) + str(legislation_entry) + str(cases_cited_entry) + str(case_name_mnc_entry) + str(judge_entry) + str(reported_citation_entry) + str(file_number_entry) + str(npa_entry) + str(with_all_the_words_entry) + str(with_at_least_one_of_the_words_entry) + str(without_the_words_entry) + str(phrase_entry) + str(proximity_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    elif ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output)>0)):
        st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')
        
        if 'need_resetting' not in st.session_state:
            
            st.session_state['need_resetting'] = 1
            
    else:
            
        df_master = create_df()
    
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
    clear_cache_except_validation_df_master()
    st.rerun()

# %%
