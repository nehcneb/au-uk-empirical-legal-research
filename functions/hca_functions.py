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
import pypdf
import io
from io import BytesIO
from io import StringIO

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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input
#Import variables
from functions.common_functions import huggingface, today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # High Court of Australia search engine

# %%
from functions.common_functions import link, is_date, list_value_check, date_parser, split_title_mnc

# %%
#Collections available
hca_collections = ['Judgments 2000-present', 'Judgments 1948-1999', '1 CLR - 100 CLR (judgments 1903-1958)']


# %%
#Function turning search terms to search results url AND number of search results

#@st.cache_data(show_spinner = False)
def hca_search(collection = hca_collections[0], 
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

    #Get url_search_results
    url_search_results = response.url

    #Get number of search results and soup
    soup = BeautifulSoup(response.content, "lxml")
    number_of_results = soup.find("span", id="itemTotal").text
    results_count = int(float(number_of_results.replace(',', '')))
                        
    return {'results_url': url_search_results, 'results_count': results_count, 'soup': soup}
    


# %%
#Define function turning search results url to cases_w_mnc_links to judgments
#NOT IN USE

#@st.cache_data(show_spinner = False)
def hca_search_results_to_judgment_links(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")

    #Start counter
    
    counter = 0
    
    #Get number of pages
    #There are up to 20 pages per page
    number_of_pages = soup.find("span", id="lastItem").text
    
    #Start cases_w_mnc_links list
    cases_w_mnc_links = []
    
    #Get first page of results
    raw_links = soup.find_all(class_='case')

    #Get list of catchwords
    catchwords_list = soup.find_all("div", {"class": "well"})
        
    null_result = soup.find_all('div', {'class' : 'well', 'id': 'top'})
    
    for result in null_result:
        if result in catchwords_list:
            catchwords_list.remove(result)
    
    if len(raw_links) > 0:
    
        for raw_link in raw_links:
            raw_link_index = raw_links.index(raw_link)
            if counter < judgment_counter_bound:
                link = 'https://eresources.hcourt.gov.au' + raw_link['href']
                case_name_mnc = split_title_mnc(raw_link.get_text().strip())
                case_name = case_name_mnc[0]
                mnc = case_name_mnc[1]

                catchwords = ''

                try:               
                    catchwords = catchwords_list[raw_link_index].get_text(strip = True)

                except:
                    print(f"{case['Case name']}: can't get 'Catchwords'")

                cases_w_mnc_links.append({'Case name': case_name, 'Medium neutral citation': mnc, 'Hyperlink to High Court Judgments Database': link, 'Catchwords': catchwords})
                
                counter += 1
                #print(counter)
            else:
                break
    
    #Go to next page if still below judgment_counter_bound
        
    if int(number_of_pages) > 1:
            
        if counter < judgment_counter_bound:

            pause.seconds(np.random.randint(5, 15))
            
            for page_raw in range(1, int(number_of_pages)):
                page = page_raw + 1
                url_search_results_new_page = url_search_results + f'&page={page}'
                page_new_page = requests.get(url_search_results_new_page)
                soup_new_page = BeautifulSoup(page_new_page.content, "lxml")
                raw_links_new_page = soup_new_page.find_all(class_='case')
            
                if len(raw_links_new_page) > 0:

                    #Get list of catchwords
                    catchwords_list = soup_new_page.find_all("div", {"class": "well"})
                    null_result = soup_new_page.find_all('div', {'class' : 'well', 'id': 'top'})
                    
                    for result in null_result:
                        if result in catchwords_list:
                            catchwords_list.remove(result)
                
                    for raw_link in raw_links_new_page:
                        if counter < judgment_counter_bound:
                            link = 'https://eresources.hcourt.gov.au' + raw_link['href']

                            case_name_mnc = split_title_mnc(raw_link.get_text().strip())
                            case_name = case_name_mnc[0]
                            mnc = case_name_mnc[1]

                            catchwords = ''
            
                            try:               
                                catchwords = catchwords_list[raw_link_index].get_text(strip = True)
            
                            except:
                                print(f"{case['Case name']}: can't get 'Catchwords'")
            
                            cases_w_mnc_links.append({'Case name': case_name, 'Medium neutral citation': mnc, 'Hyperlink to High Court Judgments Database': link, 'Catchwords': catchwords})

                            counter += 1
                            #print(counter)
                        else:
                            break
                else:
                    break

    #Get more metadata
    for case in cases_w_mnc_links:
        mnc = case['Medium neutral citation']

        index_list = hca_df.index[hca_df['mnc'].str.contains(mnc, case=False, na=False, regex=False)].tolist()

        if len(index_list) > 0:
            index = index_list[0]
    
            for meta in ['Date', 'Before', 'Reported']:
                try:
                    case.update({meta: hca_df.loc[int(index), meta.lower()]})
                except:
                    print(f"{case['Case name']}: can't get '{meta}'")
    
                try:
                    case.update({'Case number': hca_df.loc[int(index), 'case_number']})
                except:
                    print(f"{case['Case name']}: can't get 'Case number'")
        else:
            print(f"{case['Case name']}: can't get 'Date', 'Before', 'Reported' and 'Case number'")

    return cases_w_mnc_links



# %%
#Define function for judgment link containing PDF

@st.cache_data(show_spinner = False, ttl=600)
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

#@st.cache_data(show_spinner = False)
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
    
    try:
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
        judgment_dict['judgment'] = hca_pdf_judgment(judgment_url)

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
        
    return judgment_dict


# %%
#If judgment link contains 'showbyHandle'

#@st.cache_data(show_spinner = False)
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

    try:
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
            judgment_dict['judgment'] = ''
                
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

    except Exception as e:
        print(f"{judgment_dict['Case name']}: judgment not scrapped")
        print(e)
    
    return judgment_dict


# %%
#Slow way of finding a case from mnc

@st.cache_data(show_spinner = False, ttl=600)
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

@st.cache_data(show_spinner = False, ttl=600)
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
#Load hca_data

@st.cache_resource(show_spinner = False)
def hca_load_data(url):
    df = pd.read_csv(url)
    return df

hca_data_url = 'https://raw.githubusercontent.com/nehcneb/au-uk-empirical-legal-research/main/hca_data.csv'

#response = requests.get(hca_data_url)

#hca_df = pd.read_csv(StringIO(response.text))

hca_df = hca_load_data(hca_data_url)


# %%
#Function to excluding unwanted jugdments

#@st.cache_data(show_spinner = False)
def hca_judgment_to_exclude(case_info,
                        collection, 
                        own_parties_include, 
                        own_parties_exclude, 
                        after_date, 
                        before_date, 
                        #own_case_numbers_include = [], 
                        #own_case_numbers_exclude = [], 
                        own_judges_include, 
                        own_judges_exclude
                       ):

    #Default status is not to exclude
    exclude_status = False

    #Exclude parties

    parties_to_include = str(own_parties_include).replace(';', ',').split(',')

    if 'None' in parties_to_include:
        parties_to_include.remove('None')

    if '' in parties_to_include:
        parties_to_include.remove('')
    
    #st.write(f"parties_to_include == {parties_to_include}")
    
    if len(parties_to_include) > 0:
        
        party_inclusion_counter = 0
        
        for party in parties_to_include:
            
            if ((len(party) > 0) and (party.lower() in case_info['Case name'].lower())):
    
                party_inclusion_counter += 1

        #st.write(f"party_inclusion_counter=={party_inclusion_counter}")
        
        if party_inclusion_counter == 0:
        
            #st.write(f'Excluded based on party')
            
            exclude_status = True

    parties_to_exclude = str(own_parties_exclude).replace(';', ',').split(',')

    if 'None' in parties_to_exclude:
        parties_to_exclude.remove('None')

    if '' in parties_to_exclude:
        parties_to_exclude.remove('')
    
    #st.write(f"parties_to_exclude == {parties_to_exclude}")

    if len(parties_to_exclude) > 0:
    
        for party in parties_to_exclude:
            
            if ((len(party) > 0) and (party.lower() in case_info['Case name'].lower())):


                #st.write(f'Excluded based on party == {party}')

                exclude_status = True
            
                break

    #Exclude Date

    if is_date(case_info['Date'], fuzzy=False):
        
        date_datetime = parser.parse(case_info['Date'], dayfirst=True)
        
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

    #potential_year_raw_list = case_info['Case name'].split('[')

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

    if type(case_info['Before']) == str:

        judges_to_include = str(own_judges_include).replace(';', ',').split(',')

        if 'None' in judges_to_include:
            judges_to_include.remove('None')

        if '' in judges_to_include:
            judges_to_include.remove('')
        
        #st.write(f"judges_to_include == {judges_to_include}")

        if len(judges_to_include) > 0:
        
            judge_inclusion_counter = 0
                    
            for judge in judges_to_include:
    
                judge = judge.lower().replace('.', '').replace(' j', '').replace(' cj', '').replace(' acj', '').replace(' jj', '')
                
                if ((len(judge) > 2) and (judge.lower() in case_info['Before'].lower())):
    
                    judge_inclusion_counter += 1

            #st.write(f"judge_inclusion_counter=={judge_inclusion_counter}")
            
            if judge_inclusion_counter == 0:
    
                #st.write(f'Excluded based on judge')
    
                exclude_status = True
        
        judges_to_exclude = str(own_judges_exclude).replace(';', ',').split(',')

        if 'None' in judges_to_exclude:
            
            judges_to_exclude.remove('None')

        if '' in judges_to_exclude:
            judges_to_exclude.remove('')
        
        #st.write(f"judges_to_exclude == {judges_to_exclude}")

        if len(judges_to_exclude) > 0:
        
            for judge in judges_to_exclude:
    
                judge = judge.lower().replace('.', '').replace(' j', '').replace(' cj', '').replace(' acj', '').replace(' jj', '')
                
                if ((len(judge) > 2) and (judge.lower() in case_info['Before'].lower())):
                
                    exclude_status = True
    
                    #st.write(f'Excluded based on judge == {judge}')
                
                    break

    #st.write(f"exclude_status == {exclude_status}")
    
    return exclude_status


# %%
#Function to get judgment links with filters

@st.cache_data(show_spinner = False, ttl=600)
def hca_search_results_to_judgment_links_filtered_df(_soup, 
                                                     url_search_results, 
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
    #Soup, url_search_results are from hca_search
        
    #Start counter
    
    counter = 1
    
    #Get number of pages
    #There are up to 20 pages per page
    number_of_pages = _soup.find("span", id="lastItem").text

    #Start links list
    #links = []

    case_infos = []

    for page_raw in range(0, int(number_of_pages)):
        
        if counter <= judgment_counter_bound:
                        
            page = page_raw + 1

            #First page already scraped
            if page == 1:
                soup_page = _soup
            else:
                url_search_results_page = url_search_results + f'&page={page}'
        
                page_page = requests.get(url_search_results_page)
        
                soup_page = BeautifulSoup(page_page.content, "lxml")
    
            #Get raw links and names of cases
            
            raw_links = soup_page.find_all(class_='case')

            for raw_link in raw_links:

                if counter <= judgment_counter_bound:

                    index = raw_links.index(raw_link)
                    #mnc = '[' + raw_link.text.split('[')[-1]
                    case_name_mnc = split_title_mnc(raw_link.get_text().strip())
                    case_name = case_name_mnc[0]
                    mnc = case_name_mnc[1]

                    #Try to get case info from hca_df
                    try:
                        index_list = hca_df.index[hca_df['mnc'].str.contains(mnc, case=False, na=False, regex=False)].tolist()
                        index = index_list[0]
                        
                        case_info = {'Case name': case_name, #hca_df.loc[int(index), 'case'], 
                                     'Medium neutral citation': mnc, #New
                                     'Hyperlink to High Court Judgments Database': 'https://eresources.hcourt.gov.au' + raw_link['href'], 
                                     'Reported': hca_df.loc[int(index), 'reported'],
                                     'Before': hca_df.loc[int(index), 'before'],
                                     'Date': hca_df.loc[index, 'date']
                                    }

                        #st.write(case_info)
                        
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
                            
                            #links.append(case_info['Hyperlink to High Court Judgments Database'])
                            case_infos.append(case_info)


                            #st.write(f'{mnc} included.')
                            
                            counter += 1 
    
                            #case_infos.append(case_info)
                        
                    except Exception as e:
                        print(f"Can't get case info for {mnc}.")
                        print(e)
                
                else:
                    break

        else:
            break    

        pause.seconds(np.random.randint(5, 15))

    return case_infos


# %%
#Function to getting a list of years for adding to search terms
def hca_year_range(collection, after_date, before_date):

    years_list = []

    #Get year start and end depending on collection
    if len(after_date) > 0:
        year_start = int(after_date.split('-')[-1])
    else:
        for year in ['2000', '1948', '1903']:
            if year in collection:
                year_start = int(year)
                break
            
    if len(before_date) > 0:
        year_end = before_date.split('-')[-1]
    else:
        if '2000' in collection:
            year_end = datetime.now().year
        else:
            for year in ['1999', '1958']:
                if year in collection:
                    year_end = int(year)
                    break

    if len(after_date) + len(before_date) > 0:
        try:    
            years = list(range(int(year_start), int(year_end) + 1))
            years_list = sorted(years, reverse = True)
        except:
            print("after_date or before_date given but can't get year range.")

    return years_list
    


# %%
#Function to getting a list of judges for adding to search terms
def hca_judge_list(collection, own_judges_include, own_judges_exclude):

    judges_list = []
    
    if '1903' not in collection:
        
        if len(str(own_judges_include)) > 0:
    
            judges_list_raw = str(own_judges_include).replace(';', ',').split(',')

            if 'None' in judges_list_raw:
                judges_list_raw.remove('None')

            if '' in judges_list_raw:
                judges_list_raw.remove('')
            
            for judge in judges_list_raw:
                
                if isinstance(judge, tuple):
                    judge = judge[0]
                
                if judge.lower() not in ['cj', 'acj', 'j', 'jj']:
                    
                    judges_list.append(judge)
                
        if len(str(own_judges_exclude)) > 0:
    
            judges_list_raw = str(own_judges_exclude).replace(';', ',').split(',')

            if 'None' in judges_list_raw:
                judges_list_raw.remove('None')

            if '' in judges_list_raw:
                judges_list_raw.remove('')
            
            for judge in judges_list_raw:

                if isinstance(judge, tuple):
                    
                    judge = judge[0]

                if judge.lower() not in ['cj', 'acj', 'j', 'jj']:
                    
                    if judge in judges_list:
                        
                        judges_list.remove(judge)
    
    return judges_list
    


# %%
#Function to getting a list of parties for adding to search terms
def hca_party_list(collection, own_parties_include, own_parties_exclude):

    parties_list = []

    if '1903' not in collection:
        
        if len(str(own_parties_include)) > 0:
    
            parties_list_raw = str(own_parties_include).replace(';', ',').split(',')

            if 'None' in parties_list_raw:
                parties_list_raw.remove('None')

            if '' in parties_list_raw:
                parties_list_raw.remove('')
            
            for party in parties_list_raw:
                
                if isinstance(party, tuple):
                    party = party[0]
                                    
                parties_list.append(party)
                
        if len(str(own_parties_exclude)) > 0:
    
            parties_list_raw = str(own_parties_exclude).replace(';', ',').split(',')

            if 'None' in parties_list_raw:
                parties_list_raw.remove('None')

            if '' in parties_list_raw:
                parties_list_raw.remove('')
            
            for party in parties_list_raw:

                if isinstance(party, tuple):
                    party = party[0]

                if party in parties_list:
                
                    parties_list.remove(party)

    return parties_list
    


# %%
#Function to getting a list of years, judges or parties for adding to search terms
def hca_terms_to_add(years_list, parties_list):
    
    terms_to_add = []

    if ((len(years_list) == 0) and (len(parties_list) == 0)):
        
        print("Filtering by years and parties not entered.")

    elif ((len(years_list) > 0) and (len(parties_list) == 0)):

        for year in years_list:
            
            term = str(year)
            
            if term not in terms_to_add:
                
                terms_to_add.append(term)

    elif ((len(years_list) > 0) and (len(parties_list) > 0)):

        for year in years_list:

            for party in parties_list:

                term = f"{str(year)} {party}"
    
                if term not in terms_to_add:
                    
                    terms_to_add.append(term)

    else: #((len(years_list) == 0)and (len(parties_list) > 0)):

            for party in parties_list:
            
                term = f"{party}"

                if term not in terms_to_add:
                    
                    terms_to_add.append(term)

    return terms_to_add
    


# %%
#Search function for adding year and judge, if entered, to search terms 
#@st.cache_data(show_spinner = False)
def hca_enhanced_search(collection, 
               quick_search, 
               #citation = '', 
                full_text,
                judgments_counter_bound,
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

    #Initialise return list
    case_infos = []

    #st.write(f'collection == {collection}. after_date == {after_date}. own_judges_include == {own_judges_include}.')
    
    #Get lists of years, judges and parties to loop through if entered  
    years_list = hca_year_range(collection = collection, after_date = after_date, before_date = before_date)
    parties_list = hca_party_list(collection = collection, own_parties_include = own_parties_include, own_parties_exclude = own_parties_exclude)

    terms_to_add = hca_terms_to_add(years_list = years_list, parties_list = parties_list)

    #st.write(f'years_list == {years_list}. parties_list == {parties_list}.')

    #st.write(f'terms_to_add == {terms_to_add}.')

    #Determine whether need to loop through lists of years or parties
    if len(terms_to_add) == 0:

        print(f'Searching based on collection == {collection}, quick_search = {quick_search}, full_text = {full_text}')
        
        soup_url = hca_search(collection = collection, 
                                quick_search = quick_search, 
                                full_text = full_text
                                )
    
        soup = soup_url['soup']
    
        search_results_url = soup_url['results_url']
                    
        case_infos = hca_search_results_to_judgment_links_filtered_df(soup, 
                                                                    search_results_url, 
                                                                    judgments_counter_bound,
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
                                                                    )
        
    else: #len(terms_to_add) > 0:
        
        for term in terms_to_add:

            if len(case_infos) < judgments_counter_bound:
            
                quick_search_w_extra = f'{quick_search} {term}'

                print(f'Searching based on collection == {collection}, quick_search = {quick_search_w_extra}, full_text = {full_text}')
                
                #st.write(f"quick_search_w_extra == {quick_search_w_extra}")
                
                soup_url = hca_search(collection = collection, 
                            quick_search = quick_search_w_extra, 
                            full_text = full_text
                            )
    
                soup = soup_url['soup']
            
                search_results_url = soup_url['results_url']
    
                #st.write(f"search_results_url == {search_results_url}")
                
                case_infos_w_extra = hca_search_results_to_judgment_links_filtered_df(soup, 
                                                                            search_results_url, 
                                                                            judgments_counter_bound,
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
                                                                            )
                    
                for case_info in case_infos_w_extra:
                    
                    if case_info not in case_infos:
                        
                        case_infos.append(case_info)
                
                pause.seconds(np.random.randint(5, 15))

    return case_infos
    


# %%
#Function to get link to search results and number of results

def hca_search_url(df_master):
    df_master = df_master.fillna('')
    
    #Conduct search
    
    results_url_count = hca_search(collection = df_master.loc[0, 'Collection'], 
                        quick_search = df_master.loc[0, 'Quick search'], 
                        full_text = df_master.loc[0, 'Full text search']
                        )
    results_url = results_url_count['results_url']
    results_count = results_url_count['results_count']
    
    #If mnc entered
    if len(df_master.loc[0, 'Search for medium neutral citation']) > 0:
        #direct_link = hca_mnc_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])
        direct_link = hca_citation_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])

        if len(direct_link) > 0:
            
            url = direct_link

            results_count = '1'
    
    search_results_soup = results_url_count['soup']
    
    return {'results_url': results_url, 'results_count': results_count, 'soup': search_results_soup}
    


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json, gpt_batch_input
#Import variables
from functions.gpt_functions import question_characters_bound, role_content, basic_model, flagship_model


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction



# %%
#Jurisdiction specific instruction
#hca_role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from specific paragraphs, pages or sections, provide the paragraph or page numbers or section names as part of your answer. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". '

system_instruction = role_content #hca_role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#For getting judgments directly from the High Court if not available in OALC

@st.cache_data(show_spinner = False, ttl=600)
def hca_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_infos = hca_enhanced_search(collection = df_master.loc[0, 'Collection'], 
                        quick_search = df_master.loc[0, 'Quick search'], 
                        full_text = df_master.loc[0, 'Full text search'],
                    judgments_counter_bound = judgments_counter_bound,
                    own_parties_include = df_master.loc[0, 'Parties include'], 
                    own_parties_exclude = df_master.loc[0, 'Parties do not include'], 
                    #own_min_year, 
                    #own_max_year, 
                    after_date = df_master.loc[0, 'Decision date is after'], 
                     before_date = df_master.loc[0, 'Decision date is before'], 
                    #own_case_numbers_include, 
                    #own_case_numbers_exclude, 
                    own_judges_include = df_master.loc[0, 'Judges include'], 
                    own_judges_exclude = df_master.loc[0, 'Judges do not include']
                    )
    
    if huggingface == False: #If not running on HuggingFace
        
        #Get judgments from HCA database
        for case in case_infos:
            judgment_link = case['Hyperlink to High Court Judgments Database']
            
            if 'showbyHandle' in judgment_link:
                
                judgment_dict = hca_meta_judgment_dict_alt(judgment_link)
    
            else: #If 'showCase' in judgment_link:
    
                judgment_dict = hca_meta_judgment_dict(judgment_link)
    
            for key in judgment_dict.keys():
                if key not in case.keys():
                    case.update({key: judgment_dict[key]}) 
            
            judgments_file.append(case)
            
            pause.seconds(np.random.randint(5, 15))
    
        #Add judgment if mnc entered
    
        if len(df_master.loc[0, 'Search for medium neutral citation']) > 0:
            
            direct_link = hca_citation_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])
    
            if len(direct_link) > 0:
                
                judgment_dict_direct = hca_meta_judgment_dict(direct_link)
                
                judgments_file.append(judgment_dict_direct)
            
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
        for decision in judgments_file:
            
            #Append judgments from oalc first
            if decision['Medium neutral citation'] in mnc_judgment_dict.keys():
                
                decision.update({'judgment': mnc_judgment_dict[decision['Medium neutral citation']]})

                print(f"{decision['Case name']} {decision['Medium neutral citation']}: got judgment from OALC")
                
            else: #Get judgment from HCA if can't get from oalc
                
                direct_link = hca_citation_to_link(df_master.loc[0, 'Collection'], decision['Medium neutral citation'])
        
                if len(direct_link) > 0:
                    
                    judgment_dict_direct = hca_meta_judgment_dict(direct_link)

                    for key in judgment_dict_direct.keys():
                        if key not in decision.keys():
                            decision.update({key: judgment_dict_direct[key]})

                    print(f"{decision['Case name']} {decision['Medium neutral citation']}: got judgment from the High Court directly")
                    
                    pause.seconds(np.random.randint(5, 15))

    #Make judgment_link clickable
    for decision in judgments_file:
        if '=HYPERLINK' not in decision['Hyperlink to High Court Judgments Database']:
            clickable_link =  link(decision['Hyperlink to High Court Judgments Database'])
            decision.update({'Hyperlink to High Court Judgments Database': clickable_link})
    
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
        gpt_model = flagship_model
    else:        
        gpt_model = basic_model
        
    #apply GPT_individual to each respondent's judgment spreadsheet

    #Need to convert date column to string

    if 'Date' in df_individual.columns:

        df_individual['Date'] = df_individual['Date'].astype(str)
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
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

@st.cache_data(show_spinner = False, ttl=600)
def hca_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []

    #Conduct search
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_infos = hca_enhanced_search(collection = df_master.loc[0, 'Collection'], 
                        quick_search = df_master.loc[0, 'Quick search'], 
                        full_text = df_master.loc[0, 'Full text search'],
                    judgments_counter_bound = judgments_counter_bound,
                    own_parties_include = df_master.loc[0, 'Parties include'], 
                    own_parties_exclude = df_master.loc[0, 'Parties do not include'], 
                    #own_min_year, 
                    #own_max_year, 
                    after_date = df_master.loc[0, 'Decision date is after'], 
                     before_date = df_master.loc[0, 'Decision date is before'], 
                    #own_case_numbers_include, 
                    #own_case_numbers_exclude, 
                    own_judges_include = df_master.loc[0, 'Judges include'], 
                    own_judges_exclude = df_master.loc[0, 'Judges do not include']
                    )
    
    if huggingface == False: #If not running on HuggingFace
        
        #Get judgments from HCA database
        for case in case_infos:
            judgment_link = case['Hyperlink to High Court Judgments Database']
            
            if 'showbyHandle' in judgment_link:
                
                judgment_dict = hca_meta_judgment_dict_alt(judgment_link)
    
            else: #If 'showCase' in judgment_link:
    
                judgment_dict = hca_meta_judgment_dict(judgment_link)
    
            for key in judgment_dict.keys():
                if key not in case.keys():
                    case.update({key: judgment_dict[key]}) 
            
            judgments_file.append(case)
            
            pause.seconds(np.random.randint(5, 15))
    
        #Add judgment if mnc entered
    
        if len(df_master.loc[0, 'Search for medium neutral citation']) > 0:
            
            direct_link = hca_citation_to_link(df_master.loc[0, 'Collection'], df_master.loc[0, 'Search for medium neutral citation'])
    
            if len(direct_link) > 0:
                
                judgment_dict_direct = hca_meta_judgment_dict(direct_link)
                
                judgments_file.append(judgment_dict_direct)
            
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
        for decision in judgments_file:
            
            #Append judgments from oalc first
            if decision['Medium neutral citation'] in mnc_judgment_dict.keys():
                
                decision.update({'judgment': mnc_judgment_dict[decision['Medium neutral citation']]})
                
                print(f"{decision['Case name']} {decision['Medium neutral citation']}: got judgment from OALC")

            else: #Get judgment from HCA if can't get from oalc
                
                direct_link = hca_citation_to_link(df_master.loc[0, 'Collection'], decision['Medium neutral citation'])
        
                if len(direct_link) > 0:
                    
                    judgment_dict_direct = hca_meta_judgment_dict(direct_link)

                    for key in judgment_dict_direct.keys():
                        if key not in decision.keys():
                            decision.update({key: judgment_dict_direct[key]})

                    print(f"{decision['Case name']} {decision['Medium neutral citation']}: got judgment from the High Court directly")

                    pause.seconds(np.random.randint(5, 15))

    #Make judgment_link clickable
    for decision in judgments_file:
        if '=HYPERLINK' not in decision['Hyperlink to High Court Judgments Database']:
            clickable_link =  link(decision['Hyperlink to High Court Judgments Database'])
            decision.update({'Hyperlink to High Court Judgments Database': clickable_link})
    
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
        gpt_model = flagship_model
    else:        
        gpt_model = basic_model
        
    #apply GPT_individual to each respondent's judgment spreadsheet

    #Need to convert date column to string

    if 'Date' in df_individual.columns:

        df_individual['Date'] = df_individual['Date'].astype(str)
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)
    
    return batch_record_df_individual


# %%
