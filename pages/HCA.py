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
from dateutil.parser import parse
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
from io import StringIO


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
from google.oauth2 import service_account

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

# %% [markdown]
# # High Court of Australia search engine

# %%
from common_functions import link, is_date, list_value_check, au_date

# %%
#Collections available

hca_collections = ['Judgments 2000-present', 'Judgments 1948-1999', '1 CLR - 100 CLR (judgments 1903-1958)']


# %%
#function to create dataframe
def hca_create_df():

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

    #Other entries
    collection = collection_entry
    quick_search = quick_search_entry
    citation =  citation_entry

    full_text = ''
    try:
        full_text = full_text_entry

    except:
        print('Full text not entered.')

    #Can't figure out how to add the following based on the HCA's filtered search function
    #parties_include = parties_include_entry
    #parties_not_include = parties_not_include_entry
    #year_is = year_is_entry
    #year_is_not = year_is_not_entry
    #case_number = case_number_entry
    #judges_include = judges_include_entry
    #judges_not_include = judges_not_include_entry

    #The following are based on my own filter

    own_parties_include = ''

    try:
        own_parties_include = own_parties_include_entry
    
    except:
        
        print('Parties to include not entered.')

    own_parties_exclude = ''

    try:
        own_parties_exclude = own_parties_exclude_entry

    except:
        print('Parties to exclude not entered.')

    #own_case_numbers_include = ['']

    #try:
        #own_case_numbers_include_list = own_case_numbers_include_entry.replace(';', ',').split(',')

        #for case_number in own_case_numbers_include_list:
            
            #own_case_numbers_include.append(case_number)
        
    #except:
        #print('Case numbers to include not entered.')

    #own_case_numbers_exclude = ['']

    #try:
        #own_case_numbers_exclude_list = own_case_numbers_exclude_entry.replace(';', ',').split(',')

        #for case_number in own_case_numbers_exclude_list:
            
            #own_case_numbers_exclude.append(case_number)
        
    #except:
        
        #print('Case numbers to exclude not entered.')
        
    own_judges_include = ''

    try:
        own_judges_include = own_judges_include_entry
    
    except:
        print('judges to include not entered.')

    own_judges_exclude = ''

    try:
        own_judges_exclude = own_judges_exclude_entry

    except:
        print('judges to exclude not entered.')

    #Dates
    
    before_date = ''

    try:

        before_date = str(before_date_entry.strftime('%d')) + '-' + str(before_date_entry.strftime('%B'))[:3] + '-' + str(before_date_entry.strftime('%Y'))

    except:
        print('Decision date is before not entered')
        pass

    
    after_date = ''
    
    try:
        after_date = str(after_date_entry.strftime('%d'))  + '-' + str(after_date_entry.strftime('%B'))[:3]  + '-' + str(after_date_entry.strftime('%Y'))
        
    except:
        print('Decision date is after not entered')
    
    #GPT choice and entry
    gpt_activation_status = False
   
    try:
        gpt_activation_status = gpt_activation_entry

    except:
        print('GPT activation status not entered.')
    
    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry[0: 1000]
    
    except:
        print('GPT questions not entered.')

    #metadata choice

    meta_data_choice = True

    try:

        meta_data_choice = meta_data_entry
    
    except:
        print('Metadata choice not entered.')        
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Collection' : collection, 
            'Quick search': quick_search, 
            'Search for medium neutral citation': citation, 
             'Full text search': full_text, 
            #Can't figure out how to add the following based on the HCA's filtered search function
           #'Parties include': parties_include, 
            #'Parties do not include': parties_not_include, 
            #'Year is': year_is, 
            #'Year is not': year_is_not, 
            #'Case number': case_number, 
            #'Judges include': judges_include, 
            #'Judges do not include': judges_not_include, 
               #The following are based on my own filter
           'Parties include': own_parties_include, 
            'Parties do not include': own_parties_exclude, 
            #'Before this year': own_min_year, 
            #'After this year': own_max_year, 
           'Decision date is after': after_date,
            'Decision date is before': before_date, 
           #'Case numbers include': own_case_numbers_include, 
            #'Case numbers do not include': own_case_numbers_exclude, 
            'Judges include': own_judges_include, 
            'Judges do not include': own_judges_exclude, 
           #The following are common to all pages
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
#Function turning search terms to search results url AND number of search results
def hca_search(collection = '', 
               quick_search = '', 
               #citation = '', 
                full_text = ''):
    #Default base url is for judgments 2000-current
    #base_url = 'https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term='
    base_url = 'https://eresources.hcourt.gov.au/search?col=0'
    
    if collection == 'Judgments 2000-present':
    
        #base_url = 'https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term='
        base_url = 'https://eresources.hcourt.gov.au/search?col=0'

    if collection == 'Judgments 1948-1999':
        #base_url = 'https://eresources.hcourt.gov.au/search?col=1&facets=&srch-Term='

        base_url = 'https://eresources.hcourt.gov.au/search?col=1'
    
    if collection == '1 CLR - 100 CLR (judgments 1903-1958)':
        #base_url = 'https://eresources.hcourt.gov.au/search?col=2&facets=&srch-Term='

        base_url = 'https://eresources.hcourt.gov.au/search?col=2'
    
    params = {'qsrch-term': quick_search, 
              #'Citation_ST': citation, 
              'srch-term': full_text
             }

    #Get response page
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    # Process the response (e.g., extract relevant information)
    # Your code here...

    #Get url_search_results
    url_search_results = response.url

    #Get number of search results
    soup = BeautifulSoup(response.content, "lxml")
    number_of_results = soup.find("span", id="itemTotal").text
        
    return {'url': url_search_results, 'results_num': number_of_results}


# %%
#Define function turning search results url to links to judgments
def hca_search_results_to_judgment_links(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")

    #Start counter
    
    counter = 1
    
    #Get number of pages
    #There are up to 20 pages per page
    number_of_pages = soup.find("span", id="lastItem").text
    
    #Start links list
    links = []
    
    #Get first page of results
    raw_links = soup.find_all(class_='case')
    
    if len(raw_links) > 0:
    
        for raw_link in raw_links:
            if counter <= judgment_counter_bound:
                link = 'https://eresources.hcourt.gov.au' + raw_link['href']
                links.append(link)
                counter += 1
            else:
                break
    
    #Go to next page if still below judgment_counter_bound
    if counter <= judgment_counter_bound:
        if int(number_of_pages) > 1:
            pause.seconds(np.random.randint(5, 15))
            for page_raw in range(1, int(number_of_pages)):
                page = page_raw + 1
                url_search_results_new_page = url_search_results + f'&page={page}'
                page_new_page = requests.get(url_search_results_new_page)
                soup_new_page = BeautifulSoup(page_new_page.content, "lxml")
                raw_links_new_page = soup_new_page.find_all(class_='case')
            
                if len(raw_links_new_page) > 0:
                
                    for raw_link in raw_links_new_page:
                        if counter <= judgment_counter_bound:
                            link = 'https://eresources.hcourt.gov.au' + raw_link['href']
                            links.append(link)
                            counter += 1
                        else:
                            break
                else:
                    break
    

    return links



# %%
#Define function for judgment link containing PDF
def hca_pdf_judgment(url):
    pdf_url = url.replace('showCase', 'downloadPdf')
    headers = {'User-Agent': 'whatever'}
    r = requests.get(pdf_url, headers=headers)
    remote_file_bytes = io.BytesIO(r.content)
    pdfdoc_remote = PyPDF2.PdfReader(remote_file_bytes)
    text_list = []

    for page in pdfdoc_remote.pages:
        text_list.append(page.extract_text())
    
    return str(text_list)



# %%
#Meta labels and judgment combined
#IN USE
hca_meta_labels_droppable = ['Reported', 'Date', 'Case number', 'Before', 'Catchwords', 'Order']


# %%
#If judgment link contains 'showCase'

def hca_meta_judgment_dict(judgment_url):
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to High Court Judgments Database' : '', 
                 'Reported': '', 
                 'Date' : '',  
                 'Case number' : '',  
                 'Before' : '',  
                 'Catchwords' : '',  
                'Order': '', 
                'judgment' : ''
                }
    
    #Attach hyperlink

    judgment_dict['Hyperlink to High Court Judgments Database'] = link(judgment_url)
    
    page = requests.get(judgment_url)
    soup = BeautifulSoup(page.content, "lxml")

    #Case name
    judgment_dict['Case name'] = soup.find('title').text

    #Medium neutral citation
    year = judgment_url.split('showCase/')[1][0:4]
    num = judgment_url.split('HCA/')[1]
    
    judgment_dict['Medium neutral citation'] = f'[{year}] HCA {num}'

    #Reported, decision date, before

    h2_tags = soup.find_all('h2')

    if len(h2_tags) > 0:
        
        for h2 in soup.find_all('h2'):
            if 'clr' in h2.text.lower():
                
                judgment_dict['Reported'] = h2.text
    
            elif is_date(h2.text, fuzzy=False):
    
                judgment_dict['Date'] = h2.text
    
            elif 'before' in h2.text.lower():
                judgment_dict['Before'] = h2.text.replace('Before', '').replace('before', '').replace('Catchwords', '').replace('catchwords', '').replace('\n', '').replace('\t', '').replace('  ', '')
    
            else:
                continue
    
    #Case number

    case_number_list = soup.find_all(string=re.compile('Case Number'))

    if len(case_number_list) > 0:
        
        judgment_dict['Case number'] = case_number_list[0].split('Case Number')[1].replace(': ', '')

    #Checking

    if len(str(judgment_dict['Reported'])) < 5:

        try:
            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Reported'] = hca_df.loc[int(index), 'reported']

        except:
            print(f"Can't get reported for {judgment_dict['Medium neutral citation']}")

    if is_date(str(judgment_dict['Date']), fuzzy=False) == False:

        try:
            
            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Date'] = hca_df.loc[index, 'date']

        except:
            print(f"Can't get date for {judgment_dict['Medium neutral citation']}")

    if len(str(judgment_dict['Before'])) < 3:

        try:
    
            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Before'] = hca_df.loc[int(index), 'before']

    
        except:
            print(f"Can't get before for {judgment_dict['Medium neutral citation']}")

    if len(str(judgment_dict['Case number'])) < 3:

        try:

            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Case number'] = hca_df.loc[int(index), 'case_number']

    
        except:
            print(f"Can't get case number for {judgment_dict['Medium neutral citation']}")
    
    #Catchwords

    catchwords_list = soup.find_all('div', class_='well')

    if len(catchwords_list) > 0:
        
        judgment_dict['Catchwords'] = catchwords_list[0].text

    #Judgment text
    try:

        judgment_dict['judgment'] = hca_pdf_judgment(judgment_url)
        
    except Exception as e:
        print(e)
        judgment_dict['judgment'] = 'Error. Judgment not available or not downloaded.'
        judgment_dict['Case name'] = judgment_dict['Case name'] + '. Error. Judgment not available or not downloaded.'

    return judgment_dict
    


# %%
#If judgment link contains 'showbyHandle'

def hca_meta_judgment_dict_alt(judgment_url):
    
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to High Court Judgments Database' : '', 
                 'Reported': '', 
                 'Date' : '',  
                 'Case number' : '',  
                 'Before' : '',  
                 'Catchwords' : '',
                'Order': '',
                'judgment' : ''
                }
    
    #Attach hyperlink

    judgment_dict['Hyperlink to High Court Judgments Database'] = link(judgment_url)
    
    page = requests.get(judgment_url)
    soup = BeautifulSoup(page.content, "lxml")

    #Case name
    judgment_dict['Case name'] = soup.find('title').text

    #Judgment text

    judgment_list = soup.find_all("div", {"class": "opinion"})
    
    judgment_pdfs_list = soup.find_all('a', {'class': 'btn btn-success'})
    
    if len(judgment_list) > 0:

        judgment_dict['judgment'] = judgment_list[0].text

    elif len(judgment_pdfs_list) > 0:
        raw_link = judgment_pdfs_list[0]['href']
        pdf_link = 'https://eresources.hcourt.gov.au' + raw_link
        judgment_dict['judgment'] = hca_pdf_judgment(pdf_link)

    else:
        judgment_dict['judgment'] = 'Error. Judgment not available or not downloaded.'
        
        judgment_dict['Case name'] = judgment_dict['Case name'] + '. Error. Judgment not available or not downloaded.'

    #Catchwords

    catchwords_list = soup.find_all("div", {"class": "Catchphrases"})

    if len(catchwords_list) > 0:
        judgment_dict['Catchwords'] = catchwords_list[0].text
    
    #Medium neutral citation meta tag
    mnc_list = soup.find_all("div", {"class": "MNC"})

    if len(mnc_list):

        judgment_dict['Medium neutral citation'] = mnc_list[0].text

    elif len(judgment_pdfs_list) > 0:

        mnc_raw = judgment_pdfs_list[0]['href'].replace('/downloadPdf/', '').replace('/', '')

        year = mnc_raw.lower().split('hca')[0]

        num = mnc_raw.lower().split('hca')[1]

        judgment_dict['Medium neutral citation'] = f"[{year}] HCA {num}"

    #Before
    judges_list = soup.find_all("div", {"class": "judges-title"})

    if len(judges_list) > 0:

        judgment_dict['Before'] = judges_list[0].text


    #Order
    order_list = soup.find_all("div", {"class": "order-text"})

    if len(order_list) > 0:

        order = order_list[0].text#.replace('\n            ', '')

        judgment_dict['Order'] = order

    #Reported, decision date, before

    h2_tags = soup.find_all('h2')

    if len(h2_tags) > 0:
        
        for h2 in soup.find_all('h2'):
            if 'clr' in h2.text.lower():
                
                judgment_dict['Reported'] = h2.text
    
            elif is_date(h2.text, fuzzy=False):
    
                judgment_dict['Date'] = h2.text
    
            elif 'before' in h2.text.lower():
                judgment_dict['Before'] = h2.text.replace('Before', '').replace('before', '').replace('Catchwords', '').replace('catchwords', '').replace('\n', '').replace('\t', '').replace('  ', '')
    
            else:
                continue

    #Checking

    if len(str(judgment_dict['Reported'])) < 5:

        try:
            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Reported'] = hca_df.loc[int(index), 'reported']

        except:
            print(f"Can't get reported for {judgment_dict['Medium neutral citation']}")

    if is_date(str(judgment_dict['Date']), fuzzy=False) == False:

        try:
            
            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Date'] = hca_df.loc[index, 'date']

        except:
            print(f"Can't get date for {judgment_dict['Medium neutral citation']}")

    if len(str(judgment_dict['Before'])) < 3:

        try:
    
            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Before'] = hca_df.loc[int(index), 'before']

    
        except:
            print(f"Can't get before for {judgment_dict['Medium neutral citation']}")

    if len(str(judgment_dict['Case number'])) < 3:

        try:

            index_list = hca_df.index[hca_df['mnc'].str.contains(judgment_dict['Medium neutral citation'], case=False, na=False, regex=False)].tolist()
            index = index_list[0]
    
            judgment_dict['Case number'] = hca_df.loc[int(index), 'case_number']

    
        except:
            print(f"Can't get case number for {judgment_dict['Medium neutral citation']}")
    
    return judgment_dict


# %%
#Slow way of finding a case from mnc

def hca_mnc_to_link_browse(collection, year, num):

    #Default judgment without the prefix https://eresources.hcourt.gov.au
    judgment_url_raw = ''

    if collection == 'Judgments 2000-present':
                    
        base_url = 'https://eresources.hcourt.gov.au/browse?col=0&facets=dateDecided'

    if collection == 'Judgments 1948-1999':

        base_url = 'https://eresources.hcourt.gov.au/browse?col=1&facets=dateDecided'
    
    if collection == '1 CLR - 100 CLR (judgments 1903-1958)':
        
        base_url = 'https://eresources.hcourt.gov.au/browse?col=2&facets=dateDecided'
    
    params = {'srch-term': year}
    
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "lxml")

    pause.seconds(np.random.randint(5, 15))

    #Get list of pages

    pages_list = []
    
    options = soup.find_all('option')
        
    for option in options:
        if len(option.text) < 4:
            pages_list.append(option.text)
    
    for page in pages_list:
        
        page_start = (int(page) - 1)*20

        params_page = {'srch-term': year, 'page': page_start}

        response_page = requests.get(base_url, params=params_page)
        
        response_page.raise_for_status()
        
        soup_page = BeautifulSoup(response_page.content, "lxml")

        cases_list = soup_page.find_all(class_='case')

        for case in cases_list:

            if f'HCA {num}' in str(case):
                judgment_url_raw = case['href']
                break
            else:
                continue

        if (('showbyHandle' in judgment_url_raw) or ('showCase' in judgment_url_raw)):
            break
            
        else:
            pause.seconds(np.random.randint(5, 15))
            continue

    return 'https://eresources.hcourt.gov.au' + judgment_url_raw



# %%
#Function for turning citation to judgment_url
def hca_citation_to_link(collection, citation):

    #Placeholder error url
    judgment_url = f'https://eresources.hcourt.gov.au/showCase/1900/HCA/1'
    
    #Use mnc if entered
    if 'hca' in citation.lower():
       
        try:
            citation_formatted = citation.replace(' ', '').replace('[', '').replace(']', '')

            year = citation_formatted.lower().split('hca')[0]
            
            num = citation_formatted.lower().split('hca')[1]
            
            #Checking if year and num are indeed integers
            year_int = int(year)
            num_int = int(num)
            
            judgment_url = f'https://eresources.hcourt.gov.au/showCase/{year_int}/HCA/{num_int}'

        except Exception as e:
            print('MNC entered but error.')
            print(e)

    else: #Get mnc from hca_df if not entered
        try:
            index_list = hca_df.index[hca_df['reported'].str.contains(citation, case=False, na=False)].tolist()
            index = index_list[0]            
        except:
            try:
                index_list = hca_df.index[hca_df['name'].str.contains(citation, case=False, na=False)].tolist()
                index = index_list[0]
            except:
                try:
                    index_list = hca_df.index[hca_df['date'].str.contains(citation, case=False, na=False)].tolist()
                    index = index_list[0]
                
                except Exception as e:
                    print('Citation entered but not found.')
                    print(e)
                
        try:
            mnc = hca_df.loc[int(index), 'mnc']
    
            citation_formatted = mnc.replace(' ', '').replace('[', '').replace(']', '')
    
            year = citation_formatted.lower().split('hca')[0]
            
            num = citation_formatted.lower().split('hca')[1]
    
            #Checking if year and num are indeed integers
            year_int = int(year)
            num_int = int(num)
    
            judgment_url = f'https://eresources.hcourt.gov.au/showCase/{year_int}/HCA/{num_int}'
            
            return judgment_url
        
        except Exception as e:
            print('Citation entered but error.')
            print(e)


    #Check if judgment_url works
    page = requests.get(judgment_url)
    soup = BeautifulSoup(page.content, "lxml")

    if (('The case could not be found on the database.' not in soup.text) and ('There were no matching cases.'  not in soup.text)):

        return judgment_url

    else:
        #Check if direct link to PDF works
        try:
            pdf_url = judgment_url.replace('showCase', 'downloadPdf')
            
            page = requests.get(pdf_url)
        
            soup = BeautifulSoup(page.content, "lxml")
    
            if (('The case could not be found on the database.' not in soup.text) and ('There were no matching cases.'  not in soup.text)):
    
                return pdf_url
    
            else:
                #Try to use HCA's browse function to get link to case
                judgment_url = hca_mnc_to_link_browse(collection, year, num)
    
                return judgment_url
    
        except Exception as e:
            print("Can't get case url for citation")
            print(e)
            return ''


# %%
#Function for turning mnc to judgment_url
def hca_mnc_to_link(collection, mnc):
#NOT in use
    
    mnc_formatted = mnc.replace(' ', '').replace('[', '').replace(']', '')
    
    if 'HCA' in mnc_formatted:

        year = mnc_formatted.split('HCA')[0]
        
        num = mnc_formatted.split('HCA')[1]
       
        try:
            #Checking if year and num are indeed integers
            year_int = int(year)
            num_int = int(num)
            
            judgment_url = f'https://eresources.hcourt.gov.au/showCase/{year_int}/HCA/{num_int}'

            page = requests.get(judgment_url)
            
            soup = BeautifulSoup(page.content, "lxml")

            if (('The case could not be found on the database.' not in soup.text) and ('There were no matching cases.'  not in soup.text)):

                return judgment_url

            else:
                
                judgment_url = f'https://eresources.hcourt.gov.au/downloadPdf/{year_int}/HCA/{num_int}'

                page = requests.get(judgment_url)
            
                soup = BeautifulSoup(page.content, "lxml")

                if (('The case could not be found on the database.' not in soup.text) and ('There were no matching cases.'  not in soup.text)):

                    return judgment_url

                else:
                    
                    judgment_url = hca_mnc_to_link_browse(collection, year, num)

                    return judgment_url

        except Exception as e:
            print(e)
            return ''
            
    else:
        return ''



# %%
#Functions for minimum and maximum year

def hca_min_max_year(collection):
#NOT IN USE
    
    if collection == 'Judgments 2000-present':

        min_year = int(2000)

        max_year = datetime.now().year

    if collection == 'Judgments 1948-1999':
        
        min_year = int(1948)

        max_year = int(1999)
    
    if collection == '1 CLR - 100 CLR (judgments 1903-1958)':

        min_year = int(1903)

        max_year = int(1958)

    return {'min_year': min_year, 'max_year': max_year}

def hca_year_check(year_entry):
#NOT IN USE


    #Default validity
    validity = False
    
    try:
        
        if (len(str(int(year_entry))) == 4):     
            
            validity = True

    except:
        print('Year entry invalid.')
        
    return validity

def hca_min_year_validity(collection, min_year_entry):
    #NOT IN USE

    if hca_year_check(min_year_entry) == False:
        
        return False
    
    elif int(min_year_entry) <= hca_min_max_year(collection)['min_year']:
        
        return False
        
    else:
        
        return True

def hca_max_year_validity(collection, max_year_entry):
    #NOT IN USE

    if hca_year_check(max_year_entry) == False:
        
        return False
    
    elif int(max_year_entry) >= hca_min_max_year(collection)['max_year']:
        
        return False
        
    else:
        return True



# %%
#Load hca_data

@st.cache_data
def hca_load_data(url):
    df = pd.read_csv(url)
    return df

hca_data_url = 'https://raw.githubusercontent.com/nehcneb/au-uk-empirical-legal-research/main/hca_data.csv'

#response = requests.get(hca_data_url)

#hca_df = pd.read_csv(StringIO(response.text))

hca_df = hca_load_data(hca_data_url)


# %%
#Function to excluding unwanted jugdments

def hca_judgment_to_exclude(case_info = {},
                        collection = '', 
                        own_parties_include = '', 
                        own_parties_exclude = '', 
                        before_date = '', 
                        after_date = '', 
                        #own_case_numbers_include = [], 
                        #own_case_numbers_exclude = [], 
                        own_judges_include = '', 
                        own_judges_exclude = ''
                       ):

    #Default status is not to exclude
    exclude_status = False

    #Exclude parties

    for party in own_parties_include.replace(';', ',').split(','):
        
        if ((len(party) > 0) and (party.lower() not in case_info['name'].lower())):
        
            exclude_status = True
        
            break

    for party in own_parties_exclude.replace(';', ',').split(','):
        
        if ((len(party) > 0) and (party.lower() in case_info['name'].lower())):
        
            exclude_status = True
        
            break

    #Exclude date

    if is_date(case_info['date'], fuzzy=False):
        
        date_datetime = parser.parse(case_info['date'], dayfirst=True)
        
        #if collection != 'Judgments 2000-present':
            #Reducing 100 because if year is 2 digits, parser assumes current century
            
            #date_datetime = date_datetime - relativedelta(years = 100) 

        if is_date(before_date, fuzzy=False):

            before_date_datetime = parser.parse(before_date, dayfirst=True)
    
            if date_datetime > before_date_datetime:
    
                exclude_status = True

        if is_date(after_date, fuzzy=False):

            after_date_datetime = parser.parse(after_date,dayfirst=True)
    
            if date_datetime < after_date_datetime:
    
                exclude_status = True

    #Exclude year

    #potential_year_list = []

    #potential_year_raw_list = case_info['name'].split('[')

    #for potential_year in potential_year_raw_list:

        #try:
            #year_decided_raw = int(potential_year[0:4])
            
            #potential_year_list.append(year_decided_raw)

        #except:
            
            #print('Potential year value is not integer')

    #if len(potential_year_list) > 0:
    #Defining year_decided here to avoid the possibility of year not being picked up
        #year_decided = potential_year_list[-1]

        #if len(own_min_year) >= 4:
    
            #try:       
    
                #if year_decided < int(own_min_year):
        
                    #exclude_status = True
            
            #except:
                #print('Case not excluded for earlier than min year')
    
        #if len(own_max_year) >= 4:
    
            #try:        
    
                #if year_decided > int(own_max_year):
        
                    #exclude_status = True
    
            #except:
                #print('Case not excluded for later than max year')

    #Exclude judges

    if type(case_info['before']) == str:
        
        #if len(case_info['before']) > 2:
    
        for judge in own_judges_include.replace(';', ',').split(','):

            judge = judge.replace('.', '').replace(' J', '').replace(' CJ', '').replace(' ACJ', '').replace(' JJ', '')
            
            if ((len(judge) > 2) and (judge.lower() not in case_info['before'].lower())):
            
                exclude_status = True
            
                break
    
        for judge in own_judges_exclude.replace(';', ',').split(','):

            judge = judge.replace('.', '').replace(' J', '').replace(' CJ', '').replace(' ACJ', '').replace(' JJ', '')
            
            if ((len(judge) > 2) and (judge.lower() in case_info['before'].lower())):
            
                exclude_status = True
            
                break
    
    return exclude_status



# %%
#Function to get judgment links with filters

def hca_search_results_to_judgment_links_filtered_df(url_search_results, 
                                     judgment_counter_bound,
                                      collection, 
                                    #hca_df, 
                                    own_parties_include, 
                                    own_parties_exclude, 
                                    #own_min_year, 
                                    #own_max_year, 
                                    before_date, 
                                    after_date, 
                                    #own_case_numbers_include, 
                                    #own_case_numbers_exclude, 
                                    own_judges_include, 
                                    own_judges_exclude
                                                ):
    
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")
        
    #Start counter
    
    counter = 1
    
    #Get number of pages
    #There are up to 20 pages per page
    number_of_pages = soup.find("span", id="lastItem").text

    #Start links list
    links = []
            
    for page_raw in range(0, int(number_of_pages)):
        
        if counter <= judgment_counter_bound:
                        
            page = page_raw + 1
            
            url_search_results_page = url_search_results + f'&page={page}'
    
            page_page = requests.get(url_search_results_page)
    
            soup_page = BeautifulSoup(page_page.content, "lxml")
    
            #Get raw links and names of cases
            
            raw_links = soup_page.find_all(class_='case')

            case_infos = []

            for raw_link in raw_links:
                index = raw_links.index(raw_link)
                mnc = '[' + raw_link.text.split('[')[-1]

                #Try to get case info from hca_df
                try:
                    index_list = hca_df.index[hca_df['mnc'].str.contains(mnc, case=False, na=False, regex=False)].tolist()
                    index = index_list[0]
                    
                    case_info = {'name': hca_df.loc[int(index), 'case'], 
                                 'url': 'https://eresources.hcourt.gov.au' + raw_link['href'], 
                                 'reported': hca_df.loc[int(index), 'reported'],
                                 'before': hca_df.loc[int(index), 'before'],
                                 'date': hca_df.loc[index, 'date']
                                }
                    
                    case_infos.append(case_info)
                    
                except Exception as e:
                    print(f"Can't get case info for {mnc}.")
                    print(e)
    
            #Add cases from case_infos unless filtered out or counter reached
            
            for case_info in case_infos:
                if counter <= judgment_counter_bound:
                    if hca_judgment_to_exclude(case_info, 
                            collection, 
                            own_parties_include, 
                            own_parties_exclude, 
                            before_date, 
                            after_date, 
                            #own_case_numbers_include = [], 
                            #own_case_numbers_exclude = [], 
                            own_judges_include, 
                            own_judges_exclude
                           ) == False:
                        
                        links.append(case_info['url'])
                        
                        counter += 1
                        
                else:
                    break
            
            pause.seconds(np.random.randint(5, 15))

        else:
            break    

    return links


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from gpt_functions import question_characters_bound, default_judgment_counter_bound#, role_content#, intro_for_GPT


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

# %%
#Jurisdiction specific instruction
hca_role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from specific paragraphs, pages or sections, provide the paragraph or page numbers or section names as part of your answer. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". '

system_instruction = hca_role_content

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

def hca_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    url_search_results = hca_search(collection = df_master.loc[0, 'Collection'], 
                        quick_search = df_master.loc[0, 'Quick search'], 
                        full_text = df_master.loc[0, 'Full text search']
                        )['url']
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    #Use the following if don't want to filter results
    #judgments_links = hca_search_results_to_judgment_links(url_search_results, judgments_counter_bound)
    
    #Use the following if want to filter results. Will be slow.
    judgments_links = hca_search_results_to_judgment_links_filtered_df(url_search_results, 
                                     judgments_counter_bound,
                                    #hca_df, 
                                    df_master.loc[0, 'Collection'], 
                                    df_master.loc[0, 'Parties include'], 
                                    df_master.loc[0, 'Parties do not include'], 
                                   df_master.loc[0, 'Decision date is before'], 
                                    df_master.loc[0, 'Decision date is after'], 
                                    #df_master.loc[0, 'Case numbers include'], 
                                    #df_master.loc[0, 'Case numbers do not include'], 
                                    df_master.loc[0, 'Judges include'], 
                                    df_master.loc[0, 'Judges do not include'])

    for link in judgments_links:

        if 'showbyHandle' in link:
            
            judgment_dict = hca_meta_judgment_dict_alt(link)

        else: #If 'showCase' in link:

            judgment_dict = hca_meta_judgment_dict(link)
    
        judgments_file.append(judgment_dict)
        
        pause.seconds(np.random.randint(5, 15))

    #Add judgment if mnc entered

    if len(df_master.loc[0, 'Search for medium neutral citation']) > 0:
        #direct_link = hca_mnc_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])
        direct_link = hca_citation_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])

        if len(direct_link) > 0:
            
            judgment_dict_direct = hca_meta_judgment_dict(direct_link)
            
            judgments_file.append(judgment_dict_direct)
        
            pause.seconds(np.random.randint(5, 15))
            
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet

    #Need to convert date column to string

    df_individual['Date'] = df_individual['Date'].astype(str)
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in hca_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
#Function to get link to search results and number of results

def hca_search_url(df_master):
    df_master = df_master.fillna('')
    
    #Combining catchwords into new column
    
    #Conduct search
    
    url_num_dict = hca_search(collection = df_master.loc[0, 'Collection'], 
                        quick_search = df_master.loc[0, 'Quick search'], 
                        full_text = df_master.loc[0, 'Full text search']
                        )
    url = url_num_dict['url']
    results_num = url_num_dict['results_num']
    
    #If mnc entered

    if len(df_master.loc[0, 'Search for medium neutral citation']) > 0:
        #direct_link = hca_mnc_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])
        direct_link = hca_citation_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])

        if len(direct_link) > 0:
            
            url = direct_link

            results_num = '1'
    
    return {'url': url, 'results_num': results_num}
    


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
    st.session_state.df_master.loc[0, 'Collection'] = 'Judgments 2000-present' 
    st.session_state.df_master.loc[0, 'Quick search'] = None
    st.session_state.df_master.loc[0, 'Full text search'] = None 
    st.session_state.df_master.loc[0, 'Search for medium neutral citation'] = None 
    st.session_state.df_master.loc[0, 'Parties include'] = None 
    st.session_state.df_master.loc[0, 'Parties do not include'] = None 
    st.session_state.df_master.loc[0, 'Decision date is before'] = None 
    st.session_state.df_master.loc[0, 'Decision date is after'] = None 
    #st.session_state.df_master.loc[0, 'Case numbers include'] = None 
    #st.session_state.df_master.loc[0, 'Case numbers do not include'] = None 
    st.session_state.df_master.loc[0, 'Judges include'] = None 
    st.session_state.df_master.loc[0, 'Judges do not include']  = None

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

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

# %%
#Number of search results to display
#if 'number_of_results' not in st.session_state:

    #st.session_state['number_of_results'] = '0'


# %%
#Filtering message status
#if 'filtering_message' not in st.session_state:
    #st.session_state['filtering_message'] = False

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
if st.session_state.page_from != "pages/HCA.py": #Need to add in order to avoid GPT page from showing form of previous page

    #Create form
    
    return_button = st.button('RETURN to first page')
    
    st.header(f"You have selected to study :blue[judgments of the High Court of Australia].")
    
    #    st.header("Judgment Search Criteria")
    
    st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.
""")
    
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')
    
    st.subheader("Jugdments to cover")
    
    collection_entry = st.selectbox(label = 'Select or type in the collection of judgments to cover', options = hca_collections, index = list_value_check(hca_collections, st.session_state.df_master.loc[0, 'Collection']))
    
    st.subheader("Your search terms")
    
    st.markdown("""For search tips, please visit the [High Court Judgments Database](https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term=). This section largely mimics their judgments search function except the filter function.
""")
    
    quick_search_entry = st.text_input(label = 'Quick search (search party names and catchwords)', value = st.session_state.df_master.loc[0, 'Quick search'])
    
    citation_entry = st.text_input(label = 'Search for medium neutral citation (eg [2014] HCA 1)', value = st.session_state.df_master.loc[0, 'Search for medium neutral citation'])
    st.caption('CLR or other citations may work only up to 2014.')
    
    #if citation_entry:
        #if 'hca' not in citation_entry.lower():
            
            #st.error('Sorry, this pilot program only searches for medium neutral citation (eg [2014] HCA 1).')
    
    if collection_entry != '1 CLR - 100 CLR (judgments 1903-1958)':
    
        full_text_entry = st.text_input(label = 'Full text search', value = st.session_state.df_master.loc[0, 'Full text search'])
    
    else:
        full_text_entry = ''
    
    st.markdown("""You can preview the judgments returned by your search terms on the High Court Judgments Database after you have entered some search terms.
    
You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")
    
    preview_button = st.button(label = 'PREVIEW on the High Court Judgments Database (in a pop-up window)', type = 'primary')
    
    #if st.session_state.number_of_results != '0':
    
        #hca_results_num_button = st.button('DISPLAY the number of results')
        
        #if hca_results_num_button:
    
    results_num_button = st.button(label = 'SHOW the number of judgments found', disabled = ('number_of_results' not in st.session_state), help = 'Press PREVIEW first.')
    
    if results_num_button:
    
        if len(st.session_state.df_master) > 0:
    
            if int(st.session_state.number_of_results) == 0:
    
                st.error(f'There are {st.session_state.number_of_results} results. Please change your search terms.')
    
            elif int(st.session_state.number_of_results) == 1:
        
                st.success(f'There is {st.session_state.number_of_results} result.')
        
            else:
            
                st.success(f'There are {st.session_state.number_of_results} results.')
    
        else:
    
            st.warning('Please enter some search terms and press the PREVIEW button first.')
            
        #hca_results_num()
    
    #The following filters are not based on HCA's filter at https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term=
    
    filter_toggle = st.toggle("Filter your search results")
    
    if filter_toggle:
    
        #st.subheader("Filter your search results")
        
        st.warning("Filtering your search results may *significantly* prolong the program processing time. The PREVIEW and SHOW buttons will *not* reflect your search filters.")
        
        own_parties_include_entry = st.text_input(label = 'Parties include (separate parties by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Parties include'])
        st.caption('If entered, then this program will only process cases that include at least one of the parties entered.')
        
        own_parties_exclude_entry = st.text_input(label = 'Parties do not include (separate parties by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Parties do not include'])
        st.caption('If entered, then this program will only process cases that do not include any of the parties entered.')
        
        after_date_entry = st.date_input(label = 'Decision date is after', value = au_date(st.session_state.df_master.loc[0, 'Decision date is before']), format="DD/MM/YYYY", min_value = date(1800, 1, 1))
        
        before_date_entry = st.date_input(label = 'Decision date is before', value = au_date(st.session_state.df_master.loc[0, 'Decision date is before']), format="DD/MM/YYYY", min_value = date(1800, 1, 1))
    
        #own_min_year_entry = st.text_input('After this year')
        
        #if own_min_year_entry:
    
            #own_hca_min_year_validity = hca_year_check(own_min_year_entry)
        
            #if not own_hca_min_year_validity:
                    
                #st.error('You have not entered a year.')
            
        #own_max_year_entry = st.text_input('Before this year')
        
        #if own_max_year_entry:
    
            #own_hca_max_year_validity = hca_year_check(own_max_year_entry)
    
            #if not own_hca_max_year_validity:
        
                #st.error('You have not entered a year.')
    
        #if ((own_parties_include_entry) or (own_parties_exclude_entry) or (bool(after_date_entry) == True) or (bool(before_date_entry) == True)):
            
            #st.session_state['filtering_message'] = True
            
        #else:
            #st.session_state['filtering_message'] = False
    
        
        if collection_entry != '1 CLR - 100 CLR (judgments 1903-1958)':
        
            #own_case_numbers_include_entry = st.text_input(label = 'Case numbers include (separate case numbers by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Case numbers include']) 
            #st.caption('If entered, then this program will only process cases with at least one of the case numbers entered.')
        
            #own_case_numbers_exclude_entry = st.text_input(label = 'Case numbers do not include (separate case numbers by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Case numbers do not include']) 
            #st.caption('If entered, then this program will only process cases without any of the case numbers entered.')
        
            own_judges_include_entry = st.text_input(label = 'Judges include (separate judges by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Judges include'])
            st.caption('If entered, then this program will only process cases heared by at least one of the judges entered.')
            
            own_judges_exclude_entry = st.text_input(label = 'Judges do not include (separate judges by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Judges do not include'])
            st.caption('If entered, then this program will only process cases not heared by any of the judges entered.')
            
            #if ((own_judges_include_entry) or (own_judges_exclude_entry)):
                #st.session_state['filtering_message'] = True
    
            #else:
                #st.session_state['filtering_message'] = False
        
        else:
            #own_case_numbers_include_entry = ''
            #own_case_numbers_exclude_entry = ''
            own_judges_include_entry = ''
            own_judges_exclude_entry = ''
    
    #if st.session_state.filtering_message == True:
        
        #st.warning("Filtering your search results may significantly prolong the program processing time.")
        
    st.subheader("Judgment metadata collection")
    
    st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 
    
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
    
        df_master = hca_create_df()
    
        st.session_state['df_master'] = df_master
    
        judgments_url_num = hca_search_url(df_master)
        
        judgments_url = judgments_url_num['url']
    
        judgments_num = judgments_url_num['results_num']
    
        st.session_state['number_of_results'] = judgments_num
    
        open_page(judgments_url)
        
        #st.rerun

    # %%
    if keep_button:
    
        #Check whether search terms entered
    
        all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry)
        
        if all_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
                
        else:
                
            df_master = hca_create_df()

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
    #if reset_button:
        #clear_cache_except_validation_df_master()
        #st.rerun()

    # %%
    if next_button:
        all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry)
            
        if all_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')

        else:
        
            df_master = hca_create_df()
            
            st.session_state['df_master'] = df_master
            
            st.session_state["page_from"] = 'pages/HCA.py'
            
            st.switch_page('pages/GPT.py')
