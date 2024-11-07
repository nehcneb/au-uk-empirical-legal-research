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
#import pypdf
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
from functions.common_functions import huggingface, today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # Federal Courts search engine

# %%
from functions.common_functions import link, split_title_mnc

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

@st.cache_data(show_spinner = False)
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

    #Get search url
    results_url = response.url

    #Get the number of search results
    results_count = int(0)

    try:
        soup = BeautifulSoup(response.content, "lxml")
        results_num_raw = soup.find('p', {'class': 'txarial'})
        results_num_raw_text = results_num_raw.get_text(strip = True)
        results_count = results_num_raw_text.split('\r\n')[0].split(' ')[-1]
        results_count = int(float(results_count))

    except:
        print("Can't get the number of search results")

    #Get soup
    soup = BeautifulSoup(response.content, "lxml")

    return {'soup': soup, 'results_url': results_url, 'results_count': results_count}


# %%
#Define function turning search results url to case_infos to judgments

@st.cache_data(show_spinner = False)
def fca_search_results_to_judgment_links(_soup, judgment_counter_bound):
    
    #_soup is from scraping per fca_search
    
    #Start counter

    counter = 0
    
    # Get case_infos of first 20 results
    
    case_infos = []

    results_list = _soup.find_all('div', attrs={'class' : 'result'})
    
    for result in results_list:
        if counter < judgment_counter_bound:

            #Initialise default values
            title = ''
            case_name = ''
            mnc = ''
            link_to_case = ''
            date = ''
            judge = ''
            catchwords = ''
            subject = ''
            
            #Get full title
            
            title = result.h3.get_text(strip = True)

            #Get case name and mnc
            case_name_mnc = split_title_mnc(title)
            
            case_name = case_name_mnc[0]
            
            mnc = case_name_mnc[1]
            
            if '(PDF' in mnc:
                mnc = mnc.replace('(PDF', '')
            
            #Get link to case
            link_to_case = result.h3.find('a').get('href')

            #Get decision date, subject area, judge
            date_area_court_str = str(result.find('p', attrs={'class' : 'meta'}))
            date_area_court_raw = str(date_area_court_str).split('<span class="divide"></span>')

            date = date_area_court_raw[0].replace('<p class="meta">', '')
            
            if len(date) > 0:
                if date[-1] == ' ':
                    date = date[: -1]
            
            judge = date_area_court_raw[-1].replace('</p>', '')
            
            subject = result.find('p', attrs={'class' : 'meta'}).text.replace(date, '').replace(judge, '')
            
            if len(subject) > 0:
                if subject[0] == ' ':
                    subject = subject[1:]

            #Get catchwords
            catchwords = ''
            try:
                catchwords = result.find('p', attrs={'class' : 'summary'}).get_text(strip = True)
            except:
                print(f"{case_name}: can't get catchwords")
            
            case_info = {'Case name': case_name,
                 'Medium neutral citation': mnc,
                'Hyperlink to Federal Court Digital Law Library' : link_to_case,
                'Judge': judge,
                 'Judgment_Dated' : date,  
                 'Catchwords' : catchwords,  
                 'Subject' : subject,  
                        }
            case_infos.append(case_info)
            counter = counter + 1
            #print(counter)

    #Go beyond first 20 results

    #Auxiliary list for getting more pages of search results
    further_page_ending_list = []
    for i in range(100):
        further_page_ending = 20 + i
        if ((str(further_page_ending)[-1] =='1') & (str(further_page_ending)[0] not in ['3', '5', '7', '9', '11'])):
            further_page_ending_list.append(str(further_page_ending))
    
    for ending in further_page_ending_list:
        
        if counter < judgment_counter_bound:

            pause.seconds(np.random.randint(5, 15))

            url_next_page = url_search_results + '&start_rank=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            
            results_list = _soup.find_all('div', attrs={'class' : 'result'})

            #Check if stll more results
            if len(results_list) == 0:
                break
                
            else:
                for result in results_list:
                    if counter < judgment_counter_bound:
            
                        #Initialise default values
                        title = ''
                        case_name = ''
                        mnc = ''
                        link_to_case = ''
                        date = ''
                        judge = ''
                        catchwords = ''
                        subject = ''
                        
                        #Get full title
                        
                        title = result.h3.get_text(strip = True)
            
                        #Get case name and mnc
                        case_name_mnc = split_title_mnc(title)
                        
                        case_name = case_name_mnc[0]
                        
                        mnc = case_name_mnc[1]
                        
                        if '(PDF' in mnc:
                            mnc = mnc.replace('(PDF', '')
                        
                        #Get link to case
                        link_to_case = result.h3.find('a').get('href')
            
                        #Get decision date, subject area, judge
                        date_area_court_str = str(result.find('p', attrs={'class' : 'meta'}))
                        date_area_court_raw = str(date_area_court_str).split('<span class="divide"></span>')
            
                        date = date_area_court_raw[0].replace('<p class="meta">', '')
                        
                        if len(date) > 0:
                            if date[-1] == ' ':
                                date = date[: -1]
                        
                        judge = date_area_court_raw[-1].replace('</p>', '')
                        
                        subject = result.find('p', attrs={'class' : 'meta'}).text.replace(date, '').replace(judge, '')
                        
                        if len(subject) > 0:
                            if subject[0] == ' ':
                                subject = subject[1:]
            
                        #Get catchwords
                        catchwords = ''
                        try:
                            catchwords = result.find('p', attrs={'class' : 'summary'}).get_text(strip = True)
                        except:
                            print(f"{case_name}: can't get catchwords")
                            
                        case_info = {'Case name': case_name,
                             'Medium neutral citation': mnc,
                            'Hyperlink to Federal Court Digital Law Library' : link_to_case,
                            'Judge': judge,
                             'Judgment_Dated' : date,  
                             'Catchwords' : catchwords,  
                             'Subject' : subject,  
                                    }
                        case_infos.append(case_info)
                        counter = counter + 1
                        #print(counter)

    return case_infos


# %%
#Meta labels and judgment combined
#IN USE
fca_metalabels = ['Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to']
#'MNC', 
fca_metalabels_droppable = ['Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to', 'Order']

@st.cache_data(show_spinner = False)
def fca_meta_judgment_dict(case_info):
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to Federal Court Digital Law Library' : '', 
                #'MNC' : '',  
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

    try:
    
        if 'Case name' in case_info.keys():
            judgment_dict['Case name'] = case_info['Case name']
    
        if 'Medium neutral citation' in case_info.keys():
            judgment_dict['Medium neutral citation'] = case_info['Medium neutral citation']
    
        #Attach hyperlink
    
        judgment_url = case_info['Hyperlink to Federal Court Digital Law Library']
        
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

            #Attach judgment pdf text
            try:
                judgment_pdf_raw = pdf_judgment(judgment_url)
                judgment_dict['judgment'] = judgment_pdf_raw
                
            except:
                pass
        
    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
    
    return judgment_dict


# %%
#Preliminary function for changing names for any PDF judgments
#NOT IN USE

@st.cache_data(show_spinner = False)
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
            
            pause.seconds(np.random.randint(5, 15))

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
#NOT IN USE

def fca_pdf_name(name_mnc_list, mnc):
    #Placeholder
    name = 'Not working properly because judgment in PDF. References to paragraphs likely to pages or wrong.' 
    
    for i in name_mnc_list:
        if mnc in i:
            name_raw = i.split(' ' + mnc)[0]
            name = name_raw.replace('Cached: ', '')
            
    return name



# %%
@st.cache_data(show_spinner = False)
def fca_search_url(df_master):
    df_master = df_master.fillna('')
        
    #Conduct search
    
    results_url_num = fca_search(court = df_master.loc[0, 'Courts'], 
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

    results_url = results_url_num['results_url']
    results_count = results_url_num['results_count']
    search_results_soup = results_url_num['soup']
    
    return {'results_url': results_url, 'results_count': results_count, 'soup': search_results_soup}
    


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
#For getting judgments directly from the Federal Court without checking OALC first
#NOT IN USE

@st.cache_data(show_spinner = False)
def fca_run_direct(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    search_results_soup = fca_search(court = df_master.loc[0, 'Courts'], 
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
                    )['soup']
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    #Get relevant cases
    case_infos = fca_search_results_to_judgment_links(search_results_soup, judgments_counter_bound)

    for case_info in case_infos:
        judgment_dict = fca_meta_judgment_dict(case_info)
        case_info.update({'judgment': str(judgment_dict)})
        
        #Make judgment_link clickable
        clickable_link = link(case_info['Hyperlink to Federal Court Digital Law Library'])
        case_info.update({'Hyperlink to Federal Court Digital Law Library': clickable_link})

        judgments_file.append(case_info)
        pause.seconds(np.random.randint(5, 15))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)

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
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    #Pop judgment
    if 'judgment' in df_updated:
        df_updated.pop('judgment')
        
    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in fca_metalabels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
#For getting judgments from the Federal Court if unavailable in OALC

@st.cache_data(show_spinner = False)
def fca_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Conduct search    
    search_results_soup = fca_search(court = df_master.loc[0, 'Courts'], 
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
                    )['soup']
    
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    #Get relevant cases
    case_infos = fca_search_results_to_judgment_links(search_results_soup, judgments_counter_bound)

    #Create judgments file
    judgments_file = []
    
    if huggingface == False: #If not running on HuggingFace
        
        for case_info in case_infos:
            judgment_dict = fca_meta_judgment_dict(case_info)
            case_info.update({'judgment': str(judgment_dict)})
            
            #Make judgment_link clickable
            clickable_link = link(case_info['Hyperlink to Federal Court Digital Law Library'])
            case_info.update({'Hyperlink to Federal Court Digital Law Library': clickable_link})
            
            judgments_file.append(case_info)

            print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from the Federal Court directly")
            
            pause.seconds(np.random.randint(5, 15))

    else: #If running on HuggingFace

        #Load oalc
        from functions.oalc_functions import load_corpus, get_judgment_from_oalc

        #Create a list of mncs for HuggingFace:
        mnc_list = []

        for case in case_infos:

            #add search results to json
            judgments_file.append(case)

            #Add mnc to list for HuggingFace
            mnc_list.append(case['Medium neutral citation'])

        #Get judgments from oalc first
        mnc_judgment_dict = get_judgment_from_oalc(mnc_list)
            
        #Append judgment to judgments_file 
        for case_info in judgments_file:
            
            #Append judgments from oalc first
            if case_info['Medium neutral citation'] in mnc_judgment_dict.keys():
                
                case_info.update({'judgment': mnc_judgment_dict[case_info['Medium neutral citation']]})

                print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from OALC")

            else: #Get judgment from FCA if can't get from oalc
                judgment_dict_direct = fca_meta_judgment_dict(case_info)
                case_info.update({'judgment': str(judgment_dict_direct)})
                
                print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from the Federal Court directly")

                pause.seconds(np.random.randint(5, 15))

            #Make judgment_link clickable
            clickable_link = link(case_info['Hyperlink to Federal Court Digital Law Library'])
            case_info.update({'Hyperlink to Federal Court Digital Law Library': clickable_link})

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
    
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
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    #Pop jugdment
    if 'judgment' in df_updated:
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in fca_metalabels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
#Obtain parameters

@st.cache_data(show_spinner = False)
def fca_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Conduct search    
    search_results_soup = fca_search(court = df_master.loc[0, 'Courts'], 
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
                    )['soup']
    
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    #Get relevant cases
    case_infos = fca_search_results_to_judgment_links(search_results_soup, judgments_counter_bound)

    #Create judgments file
    judgments_file = []
    
    if huggingface == False: #If not running on HuggingFace
        
        for case_info in case_infos:
            judgment_dict = fca_meta_judgment_dict(case_info)
            case_info.update({'judgment': str(judgment_dict)})
            
            #Make judgment_link clickable
            clickable_link = link(case_info['Hyperlink to Federal Court Digital Law Library'])
            case_info.update({'Hyperlink to Federal Court Digital Law Library': clickable_link})
            
            judgments_file.append(case_info)

            print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from the Federal Court directly")

            pause.seconds(np.random.randint(5, 15))

    else: #If running on HuggingFace

        #Load oalc
        from functions.oalc_functions import load_corpus, get_judgment_from_oalc

        #Create a list of mncs for HuggingFace:
        mnc_list = []

        for case in case_infos:

            #add search results to json
            judgments_file.append(case)

            #Add mnc to list for HuggingFace
            mnc_list.append(case['Medium neutral citation'])

        #Get judgments from oalc first
        mnc_judgment_dict = get_judgment_from_oalc(mnc_list)
            
        #Append judgment to judgments_file 
        for case_info in judgments_file:
            
            #Append judgments from oalc first
            if case_info['Medium neutral citation'] in mnc_judgment_dict.keys():
                
                case_info.update({'judgment': mnc_judgment_dict[case_info['Medium neutral citation']]})

                print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from OALC")
            
            else: #Get judgment from FCA if can't get from oalc
                judgment_dict_direct = fca_meta_judgment_dict(case_info)
                case_info.update({'judgment': str(judgment_dict_direct)})
                
                print(f"{case_info['Case name']} {case_info['Medium neutral citation']}: got judgment from the Federal Court directly")

                pause.seconds(np.random.randint(5, 15))

            #Make judgment_link clickable
            clickable_link = link(case_info['Hyperlink to Federal Court Digital Law Library'])
            case_info.update({'Hyperlink to Federal Court Digital Law Library': clickable_link})

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
                        
    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in fca_metalabels_droppable:
            if meta_label in df_individual.columns:
                df_individual.pop(meta_label)
    
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
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)
    
    return batch_record_df_individual

# %%
