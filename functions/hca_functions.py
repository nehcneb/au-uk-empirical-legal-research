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
import pypdf
import io
from io import BytesIO
from io import StringIO

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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # High Court of Australia search engine

# %%
from functions.common_functions import link, is_date, list_value_check, au_date

# %%
#Collections available

hca_collections = ['Judgments 2000-present', 'Judgments 1948-1999', '1 CLR - 100 CLR (judgments 1903-1958)']


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

@st.cache_data
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

@st.cache_data
def hca_pdf_judgment(url):
    pdf_url = url.replace('showCase', 'downloadPdf')
    headers = {'User-Agent': 'whatever'}
    r = requests.get(pdf_url, headers=headers)
    remote_file_bytes = io.BytesIO(r.content)
    pdfdoc_remote = pypdf.PdfReader(remote_file_bytes)
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

@st.cache_data
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

@st.cache_data
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

@st.cache_data
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

@st.cache_resource
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
                        after_date = '', 
                        before_date = '', 
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

        if is_date(after_date, fuzzy=False):

            after_date_datetime = parser.parse(after_date,dayfirst=True)
    
            if date_datetime < after_date_datetime:
    
                exclude_status = True

        if is_date(before_date, fuzzy=False):

            before_date_datetime = parser.parse(before_date, dayfirst=True)
    
            if date_datetime > before_date_datetime:
    
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

@st.cache_data
def hca_search_results_to_judgment_links_filtered_df(url_search_results, 
                                     judgment_counter_bound,
                                      collection, 
                                    #hca_df, 
                                    own_parties_include, 
                                    own_parties_exclude, 
                                    #own_min_year, 
                                    #own_max_year, 
                                    after_date, 
                                     before_date, 
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
                            after_date, 
                           before_date, 
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
#hca_role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from specific paragraphs, pages or sections, provide the paragraph or page numbers or section names as part of your answer. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". '

system_instruction = role_content #hca_role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#Obtain parameters

@st.cache_data
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
                                    df_master.loc[0, 'Decision date is after'],
                                      df_master.loc[0, 'Decision date is before'], 
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
        gpt_model = "gpt-4o-2024-08-06"
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

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in hca_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
#Obtain parameters

@st.cache_data
def hca_batch(df_master):
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
                                    df_master.loc[0, 'Decision date is after'],
                                      df_master.loc[0, 'Decision date is before'], 
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

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in hca_metalabels_droppable:
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

    #Need to convert date column to string

    if 'Date' in df_individual.columns:

        df_individual['Date'] = df_individual['Date'].astype(str)
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)
    
    return batch_record_df_individual

