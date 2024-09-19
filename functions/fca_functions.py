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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_range_check, au_date, save_input, pdf_judgment
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # Federal Courts search engine

# %%
from functions.common_functions import link

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
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json, gpt_batch_input
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
#Jurisdiction specific instruction
system_instruction = role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]


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
        gpt_model = "gpt-4o-2024-08-06"
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
#Obtain parameters

@st.cache_data
def fca_batch(df_master):
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
                    
    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in fca_metalabels_droppable:
            try:
                df_updated.pop(meta_label)
            except Exception as e:
                print(f'{meta_label} not popped.')
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
    
    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)
    
    return batch_record_df_individual
