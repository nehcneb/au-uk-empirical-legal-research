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
import urllib
from urllib.request import urlretrieve
import os
#import pypdf
import io
from io import BytesIO
import ast
import math
import mammoth

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

#Conversion to text
#import fitz
#from io import StringIO
#from io import BytesIO
#import mammoth
#from doc2docx import convert

# %%
#Import functions
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input, date_parser, pdf_judgment, docx_judgment, str_to_int
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # HKLII search engine

# %%
#Scrape javascript

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--headless")
options.add_argument('--no-sandbox')  
options.add_argument('--disable-dev-shm-usage')  

#@st.cache_resource(show_spinner = False, ttl=600)
def get_driver():
    return webdriver.Chrome(options=options)



# %% [markdown]
# ## Definitions

# %%
hklii_sortby_dict = {'Relevance': 'relevance', 'Date descending': 'dateDesc', 'Date ascending': 'dateAsc'}

# %%
hklii_sortby_keys = [*hklii_sortby_dict.keys()]
hklii_sortby_values = [*hklii_sortby_dict.values()]

# %%
#Copied from page source of https://www.hklii.hk/advancedsearch
hklii_dbs_list = [{"id":2,"name":"Court of Appeal","abbr":"hkca","lang":"EN","path":"/en/cases/hkca/","cat":"C"},{"id":4,"name":"Court of Final Appeal","abbr":"hkcfa","lang":"EN","path":"/en/cases/hkcfa/","cat":"C"},{"id":5,"name":"United Kingdom Privy Council Judgments for Hong Kong","abbr":"ukpc","lang":"EN","path":"/en/cases/ukpc/","cat":"C"},{"id":7,"name":"Court of First Instance","abbr":"hkcfi","lang":"EN","path":"/en/cases/hkcfi/","cat":"C"},{"id":9,"name":"District Court","abbr":"hkdc","lang":"EN","path":"/en/cases/hkdc/","cat":"C"},{"id":11,"name":"Family Court","abbr":"hkfc","lang":"EN","path":"/en/cases/hkfc/","cat":"C"},{"id":13,"name":"Competition Tribunal","abbr":"hkct","lang":"EN","path":"/en/cases/hkct/","cat":"C"},{"id":15,"name":"Lands Tribunal","abbr":"hkldt","lang":"EN","path":"/en/cases/hkldt/","cat":"C"},{"id":17,"name":"Coroner\'s Court","abbr":"hkcrc","lang":"EN","path":"/en/cases/hkcrc/","cat":"C"},{"id":19,"name":"Labour Tribunal","abbr":"hklat","lang":"EN","path":"/en/cases/hklat/","cat":"C"},{"id":21,"name":"Magistrates\' Courts","abbr":"hkmagc","lang":"EN","path":"/en/cases/hkmagc/","cat":"C"},{"id":23,"name":"Small Claims Tribunal","abbr":"hksct","lang":"EN","path":"/en/cases/hksct/","cat":"C"},{"id":25,"name":"Obscene Articles Tribunal","abbr":"hkoat","lang":"EN","path":"/en/cases/hkoat/","cat":"C"},{"id":27,"name":"Hong Kong Ordinances","abbr":"ord","lang":"EN","path":"/en/legis/ord/","cat":"L"},{"id":29,"name":"Hong Kong Regulations","abbr":"reg","lang":"EN","path":"/en/legis/reg/","cat":"L"},{"id":31,"name":"Hong Kong Constitutional Instruments","abbr":"instrument","lang":"EN","path":"/en/legis/instrument/","cat":"L"},{"id":33,"name":"Arrangements with the Macao SAR","abbr":"hktmc","lang":"EN","path":"/en/legis/hktmc/","cat":"T"},{"id":35,"name":"Arrangements with the Mainland","abbr":"hktml","lang":"EN","path":"/en/legis/hktml/","cat":"T"},{"id":37,"name":"Bilateral Agreements Concluded by the HKSAR Government","abbr":"bahkg","lang":"EN","path":"/en/legis/bahkg/","cat":"T"},{"id":39,"name":"Bilateral Agreements Concluded by the Central People\'s Government","abbr":"bacpg","lang":"EN","path":"/en/legis/bacpg/","cat":"T"},{"id":41,"name":"Treaties","abbr":"hkts","lang":"EN","path":"/en/legis/hkts/","cat":"T"},{"id":42,"name":"Hong Kong International Arbitration Centre","abbr":"hkiac","lang":"EN","path":"/en/other/hkiac/","cat":"O"},{"id":44,"name":"Law Reform Commission Consultation Papers","abbr":"hklrccp","lang":"EN","path":"/en/other/hklrccp/","cat":"O"},{"id":46,"name":"Law Reform Commission Reports","abbr":"hklrcr","lang":"EN","path":"/en/other/hklrcr/","cat":"O"},{"id":48,"name":"Office of the Privacy Commissioner for Personal Data Administrative Appeals Board Decisions","abbr":"pcpdaab","lang":"EN","path":"/en/other/pcpdaab/","cat":"O"},{"id":50,"name":"Office of the Privacy Commissioner for Personal Data Complaint Case Notes","abbr":"pcpdc","lang":"EN","path":"/en/other/pcpdc/","cat":"O"},{"id":51,"name":"Historical Laws of Hong Kong","abbr":"histlaw","lang":"EN","path":"/en/legis/histlaw/","cat":"H"},{"id":53,"name":"Practice Directions","abbr":"pd","lang":"EN","path":"/en/other/pd/","cat":"P"},{"id":26,"name":"香港条例","abbr":"ord","lang":"SC","path":"/sc/legis/ord/","cat":"L"},{"id":54,"name":"法律改革委员会报告书","abbr":"hklrcr","lang":"SC","path":"/sc/other/hklrcr/","cat":"O"},{"id":55,"name":"法律改革会咨询文件","abbr":"hklrccp","lang":"SC","path":"/sc/other/hklrccp/","cat":"O"},{"id":58,"name":"个人资料私隐专员公署投诉个案简述","abbr":"pcpdc","lang":"SC","path":"/sc/other/pcpdc/","cat":"O"},{"id":60,"name":"香港附属法例","abbr":"reg","lang":"SC","path":"/sc/legis/reg/","cat":"L"},{"id":61,"name":"香港宪法文件","abbr":"instrument","lang":"SC","path":"/sc/legis/instrument/","cat":"L"},{"id":1,"name":"上訴法庭","abbr":"hkca","lang":"TC","path":"/tc/cases/hkca/","cat":"C"},{"id":3,"name":"終審法院","abbr":"hkcfa","lang":"TC","path":"/tc/cases/hkcfa/","cat":"C"},{"id":6,"name":"原訟法庭","abbr":"hkcfi","lang":"TC","path":"/tc/cases/hkcfi/","cat":"C"},{"id":8,"name":"區域法院","abbr":"hkdc","lang":"TC","path":"/tc/cases/hkdc/","cat":"C"},{"id":10,"name":"家事法庭","abbr":"hkfc","lang":"TC","path":"/tc/cases/hkfc/","cat":"C"},{"id":12,"name":"競爭事務審裁處","abbr":"hkct","lang":"TC","path":"/tc/cases/hkct/","cat":"C"},{"id":14,"name":"土地審裁處","abbr":"hkldt","lang":"TC","path":"/tc/cases/hkldt/","cat":"C"},{"id":16,"name":"死因裁判法庭","abbr":"hkcrc","lang":"TC","path":"/tc/cases/hkcrc/","cat":"C"},{"id":18,"name":"勞資審裁處","abbr":"hklat","lang":"TC","path":"/tc/cases/hklat/","cat":"C"},{"id":20,"name":"裁判法院","abbr":"hkmagc","lang":"TC","path":"/tc/cases/hkmagc/","cat":"C"},{"id":22,"name":"小額錢債審裁處","abbr":"hksct","lang":"TC","path":"/tc/cases/hksct/","cat":"C"},{"id":24,"name":"淫褻物品審裁處","abbr":"hkoat","lang":"TC","path":"/tc/cases/hkoat/","cat":"C"},{"id":28,"name":"香港附屬法例","abbr":"reg","lang":"TC","path":"/tc/legis/reg/","cat":"L"},{"id":30,"name":"香港憲法文件","abbr":"instrument","lang":"TC","path":"/tc/legis/instrument/","cat":"L"},{"id":32,"name":"香港特別行政區與澳門特別行政區之間的安排","abbr":"hktmc","lang":"TC","path":"/tc/legis/hktmc/","cat":"T"},{"id":34,"name":"香港特別行政區與內地之間的安排","abbr":"hktml","lang":"TC","path":"/tc/legis/hktml/","cat":"T"},{"id":36,"name":"中央人民政府達成的雙邊協定","abbr":"bacpg","lang":"TC","path":"/tc/legis/bacpg/","cat":"T"},{"id":38,"name":"香港特別行政區政府達成的雙邊協定","abbr":"bahkg","lang":"TC","path":"/tc/legis/bahkg/","cat":"T"},{"id":40,"name":"公約","abbr":"hkts","lang":"TC","path":"/tc/legis/hkts/","cat":"T"},{"id":43,"name":"法律改革委員會諮詢文件","abbr":"hklrccp","lang":"TC","path":"/tc/other/hklrccp/","cat":"O"},{"id":45,"name":"法律改革委員會報告書","abbr":"hklrcr","lang":"TC","path":"/tc/other/hklrcr/","cat":"O"},{"id":47,"name":"個人資料私隱專員公署行政上訴委員會裁決","abbr":"pcpdaab","lang":"TC","path":"/tc/other/pcpdaab/","cat":"O"},{"id":49,"name":"個人資料私隱專員公署投訴個案簡述","abbr":"pcpdc","lang":"TC","path":"/tc/other/pcpdc/","cat":"O"},{"id":52,"name":"實務指示","abbr":"pd","lang":"TC","path":"/tc/other/pd/","cat":"P"},{"id":59,"name":"香港條例","abbr":"ord","lang":"TC","path":"/tc/legis/ord/","cat":"L"}]

# %%
#Create dict of databases and language- and type-specific lists of databases
hklii_dbs_dict = {}
hklii_en_cases_list = []
hklii_en_legis_list = []
hklii_en_other_list = []
hklii_c_cases_list = []
hklii_c_legis_list = []
hklii_c_other_list = []

for source in hklii_dbs_list:
    source_name = source['name']
    hklii_dbs_dict.update({source_name: source})

    lang = source['lang']
    cat = source['cat']

    if lang  == 'EN':

        if cat == 'C':

            hklii_en_cases_list.append(source_name)
            
        elif cat in ['L', 'T', 'H']:

            hklii_en_legis_list.append(source_name)

        else:

            hklii_en_other_list.append(source_name)

    else:

        if cat == 'C':

            hklii_c_cases_list.append(source_name)
            
        elif cat in ['L', 'T', 'H']:

            hklii_c_legis_list.append(source_name)

        else:

            hklii_c_other_list.append(source_name)
            
    

# %%
#Function for changing selection menu for type on Streamlit

def dict_value_or_none(some_dict, some_key):

    if (some_key in [None, '']) or (not isinstance(some_dict, dict)):

        return None
    
    elif some_key not in some_dict.keys():
        
        return None
    
    else:

        return_value = some_dict[some_key]

        if isinstance(return_value, dict):
            
            return_value = [*return_value.keys()]
        
        return return_value
    


# %% [markdown]
# ## Search engine

# %%
from functions.common_functions import link


# %%
def hklii_get_judgment(case_info):
    
    judgment_url = case_info['Hyperlink to HKLII']

    case_info['Hyperlink to HKLII'] = link(case_info['Hyperlink to HKLII'])

    browser = get_driver()
    
    browser.get(judgment_url)

    #Get judgment text
    extracted_text = ''

    try:
        #Wait until text present
    
        text_present = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, '//form[@name="search_body"]|//div[@class="case-content mt-6 mb-10 pl-md-2 pr-md-2 pl-lg-4 pr-lg-4"]')))

        extracted_text = text_present.text
    
        #soup = BeautifulSoup(browser.page_source, "lxml")

        #extracted_text = soup.find('form', attrs={'name': 'search_body'}).get_text()
    
    except Exception as e:

        print(f"{case_info['Title']}: can't get extracted_text due to error: {e}")
    
    #Add meta

    soup = BeautifulSoup(browser.page_source, "lxml")
    
    meta_labels = soup.find_all('span', class_ = 'spec_infolabel darkgrey-text')
    meta_texts = soup.find_all('span', class_ = 'spec_infoval darkgrey-text')

    if len(meta_labels) == len(meta_texts):

        for meta_counter in range(0, len(meta_labels)):

            try:

                meta_label = meta_labels[meta_counter].get_text(strip = True)
                meta_text = meta_texts[meta_counter].get_text(strip = True)

                case_info.update({meta_label: meta_text})

            except Exception as e:
                
                print(f"{case_info['Title']}: can't get meta label indexed {meta_counter} due to error: {e}")

    #Add appeal history if any
    appeals = soup.find_all('a', class_ = 'apphislink')

    for appeal_counter in range(0, len(appeals)):
        
        try:
    
            appeal_text = appeals[appeal_counter].get_text(strip = True)
            
            appeal_link = 'https://www.hklii.hk' + appeals[appeal_counter]['href']

            case_info.update({f"Appeal {(appeal_counter + 1)}": appeal_text})

            case_info.update({f"Hyperlink to appeal {(appeal_counter + 1)}": link(appeal_link)})
            
        except Exception as e:
            
            print(f"{case_info['Title']}: can't get appeal history indexed {appeal_counter} due to error: {e}")

    #Add judgment text at the end
    case_info.update({'extracted_text': extracted_text})
    
    browser.quit()
    
    return case_info


# %%

# %%
class hklii_search_tool:

    def __init__(self, 
                citation = None,
                title = None,
                captitle = None,
                parties = None, 
                coram = None,
                representation = None, 
                charge = None,
                text = None, 
                anyword = None, 
                phrase = None,
                min_date = None,
                max_date = None,
                dbs_en_cases = [],
                dbs_en_legis = [],
                dbs_en_other = [],
                dbs_c_cases = [],
                dbs_c_legis = [],
                dbs_c_other = [],
                sortby = hklii_sortby_keys[0],
                judgment_counter_bound = default_judgment_counter_bound
                ):

        #Initialise parameters
        self.citation = citation
        self.title = title        
        self.captitle = captitle
        self.parties = parties 
        self.coram = coram
        self.representation = representation 
        self.charge = charge
        self.text = text
        self.anyword = anyword         
        self.phrase = phrase 
        self.min_date = min_date
        self.max_date = max_date
        
        self.dbs = []
        
        for db_list in [dbs_en_cases, dbs_en_legis, dbs_en_other, dbs_c_cases, dbs_c_legis, dbs_c_other]:

            if isinstance(db_list, str):

                db_list = ast.literal_eval(db_list)

            for db in db_list:

                self.dbs.append(db)
        
        self.sortby = sortby
        
        self.judgment_counter_bound = judgment_counter_bound
        
        self.page = 1
        
        self.results_count = 0

        self.total_pages = 1
        
        self.results_url = ''
        
        self.soup = None
        
        self.case_infos = []
    
    #Function for getting search results
    def get_url(self):

        #Reset infos of cases found
        self.case_infos = []
        
        params_raw = []

        if self.citation:

            params_raw.append(('citation', self.citation))

        if self.title:

            params_raw.append(('title', self.title))

        if self.captitle:

            params_raw.append(('captitle', self.captitle))        

        if self.parties:

            params_raw.append(('parties', self.parties))        

        if self.coram:

            params_raw.append(('coram', self.coram))        

        if self.representation:

            params_raw.append(('representation', self.representation))        

        if self.charge:

            params_raw.append(('charge', self.charge))        
        
        if self.text:

            params_raw.append(('text', self.text))

        if self.anyword:

            params_raw.append(('anyword', self.anyword))
        
        if self.phrase:

            params_raw.append(('phrase', self.phrase))        

        if self.min_date:

            self.min_date = date_parser(self.min_date)

            self.min_date = self.min_date.strftime("%d/%m/%Y")

            params_raw.append(('min_date', self.min_date))        
     
        if self.max_date:

            self.max_date = date_parser(self.max_date)

            self.max_date = self.max_date.strftime("%d/%m/%Y")
                                                       
            params_raw.append(('max_date', self.max_date))        

        if len(self.dbs) > 0:                

            if len(self.dbs) > 0:

                db_ids = []

                for db_name in self.dbs:

                    db_id = str(hklii_dbs_dict[db_name]['id'])

                    db_ids.append(db_id)

                db_ids_param = ",".join(db_ids)

                params_raw.append(('dbs', db_ids_param))        
                        
        #Save params
        params = urllib.parse.urlencode(params_raw, quote_via=urllib.parse.quote, safe=',')
        
        #API url
        base_url = 'https://www.hklii.hk/search?searchType=advanced'

        self.results_url = base_url + '&' + params

    def search(self):

        if len(self.results_url) == 0:

            self.get_url()

        print(f"self.results_url == {self.results_url}")

        browser = get_driver()
        
        browser.get(self.results_url)
        #browser.refresh()

        #Get results count
                    
        #Wait until results are present on page
        result_elements = Wait(browser, 30).until(EC.presence_of_all_elements_located((By.XPATH, '//p[@class="resultcontent"]|//span[contains(text(), "No results matched")]')))

        #results_count_raw = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, '//div[@class="v-data-footer__pagination"]')))

        #results_count_raw = Wait(browser, 30).until(EC.presence_of_element_located((By.XPATH, '//span[@class="statval darkgrey-text"]')))
        
        soup = BeautifulSoup(browser.page_source, "lxml")

        if "No results matched" not in str(soup):

            results_count_raw = soup.find('div', class_ = "v-data-footer__pagination").text

            
            if len(re.findall(r'(\d+)', results_count_raw)) > 0:
            
                results_count_str = re.findall(r'(\d+)', results_count_raw)[-1]
            
                if isinstance(results_count_str, tuple):
            
                    results_count_str = results_count_str[0]
                
                self.results_count = int(results_count_str)
        
        else:
            
            self.results_count = 0

        #20 results per page
        self.total_pages = math.ceil(self.results_count/20)

        print(f"Found {self.results_count} results on {self.total_pages} pages")

        #Sort results if needed
        if (self.results_count > 0) and (self.sortby != hklii_sortby_keys[0]):
        
            sort_button = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, f'//button[@value="{hklii_sortby_dict[self.sortby]}"]')))

            sort_button.click()

            #Wait until results are present on page
            result_elements = Wait(browser, 30).until(EC.presence_of_all_elements_located((By.XPATH, '//p[@class="resultcontent"]')))
        
        #Start getting results

        #Next page if available and needed
        while (self.page <= self.total_pages) and (len(self.case_infos) < min(self.judgment_counter_bound, self.results_count)):

            print(f"Getting results from page {self.page} of {self.total_pages}")
            
            #Determine if need to turn a page
            if self.page > 1:
        
                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))

                #Click on next page button
                
                next_page_button = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, f'//button[@aria-label="Goto Page {self.page}"]')))

                browser.execute_script("arguments[0].click();", next_page_button)
            
                #Wait until results are present on page
                result_elements = Wait(browser, 30).until(EC.presence_of_all_elements_located((By.XPATH, '//p[@class="resultcontent"]')))

            #Add results to case_infos
            soup = BeautifulSoup(browser.page_source, "lxml")

            #Get results in table form where each 4 cells are for one document: database, Title, citation, date
            tabular_list = soup.find_all('p', class_ ='resultcontent')
            
            #Each 4 urls are for one document
            url_list = soup.find_all('a', class_ ='routing')
                    
            cell_counter = 0

            #Add entries to self.case_infos
            for cell in tabular_list:

                if len(self.case_infos) < min(self.judgment_counter_bound, self.results_count):
            
                    if cell_counter % 4 == 0:
                    
                        case_info = {
                                    'Title': '',
                                     'Hyperlink to HKLII': '', 
                                    'Citations': '',
                                    'Database': '',
                                    'Date': ''
                                    }
                
                        case_info['Database'] = cell.text
                
                        case_info['Hyperlink to HKLII'] = 'https://www.hklii.hk' + url_list[cell_counter]['href']
                
                    if cell_counter % 4 == 1:
                
                        case_info['Title'] = cell.text
                
                    if cell_counter % 4 == 2:
                
                        case_info['Citations'] = cell.text
                
                    if cell_counter % 4 == 3:
                        
                        case_info['Date'] = cell.text
                
                        self.case_infos.append(case_info)

                else:
                    
                    break
            
                cell_counter += 1

            #Increase page count if needed
            if self.page == math.ceil(len(self.case_infos)/20):

                self.page += 1

        #Quit/close selenium when done
        browser.quit()

    def get_judgments(self):

        self.case_infos_w_judgments = []

        #Search if not done yet
        if len(self.case_infos) == 0:

            self.search()
        
        #Get judgments from cases shown on the initial page (page 1)
        for case_info in self.case_infos:
            
            if len(self.case_infos_w_judgments) < self.judgment_counter_bound:

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))

                #Attach judgment text and urls to case_info dict
                case_info_w_judgment = hklii_get_judgment(case_info)
        
                self.case_infos_w_judgments.append(case_info_w_judgment)
                
                print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments.")


# %%
def hklii_search_preview(df_master):
    
    df_master = df_master.fillna('')
            
    #Conduct search

    hklii_search = hklii_search_tool( 
                    citation = df_master.loc[0, 'Citation'],
                    title = df_master.loc[0, 'Case name'],
                    captitle = df_master.loc[0, 'Legislation name'],
                    parties = df_master.loc[0, 'Parties of judgment'], 
                    coram = df_master.loc[0, 'Coram of judgment'],
                    representation = df_master.loc[0, 'Parties representation'], 
                    charge = df_master.loc[0, 'Charge'],
                    text = df_master.loc[0, 'All of these words'], 
                    anyword = df_master.loc[0, 'Any of these words'], 
                    phrase = df_master.loc[0, 'Exact phrase'],
                    min_date = df_master.loc[0, 'Start date'],
                    max_date = df_master.loc[0, 'End date'],
                    dbs_en_cases = df_master.loc[0, 'English case databases'],
                    dbs_en_legis = df_master.loc[0, 'English legislation databases'],
                    dbs_en_other = df_master.loc[0, 'English other databases'],
                    dbs_c_cases = df_master.loc[0, '中文判案書資料庫'],
                    dbs_c_legis = df_master.loc[0, '中文法例資料庫'],
                    dbs_c_other = df_master.loc[0, '其他中文資料庫'],
                    sortby = df_master.loc[0, 'Sort by'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )

    hklii_search.search()
    
    results_count = hklii_search.results_count
    case_infos = hklii_search.case_infos

    results_url = hklii_search.results_url

    #st.write(results_url)
    
    return {'results_url': results_url, 'results_count': results_count, 'case_infos': case_infos}


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import basic_model, flagship_model
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Jurisdiction specific instruction

role_content_hklii = """You are a legal research assistant helping an academic researcher to answer questions about a public legal document. You will be provided with the document and metadata in JSON form. 
Please answer questions based only on information contained in the document and metadata. Where your answer comes from a part of the document or metadata, include a page or paragraph reference to that part of the document or metadata. 
If you cannot answer the questions based on the document or metadata, do not make up information, but instead write "answer not found". 
The JSON given to you is in English or Chinese or both. Please answer questions based on either or both languages. 
"""

#Respond in JSON form. In your response, produce as many keys as you need. 

#system_instruction = role_content_hklii

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def hklii_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
        
    hklii_search = hklii_search_tool( 
                    citation = df_master.loc[0, 'Citation'],
                    title = df_master.loc[0, 'Case name'],
                    captitle = df_master.loc[0, 'Legislation name'],
                    parties = df_master.loc[0, 'Parties of judgment'], 
                    coram = df_master.loc[0, 'Coram of judgment'],
                    representation = df_master.loc[0, 'Parties representation'], 
                    charge = df_master.loc[0, 'Charge'],
                    text = df_master.loc[0, 'All of these words'], 
                    anyword = df_master.loc[0, 'Any of these words'], 
                    phrase = df_master.loc[0, 'Exact phrase'],
                    min_date = df_master.loc[0, 'Start date'],
                    max_date = df_master.loc[0, 'End date'],
                    dbs_en_cases = df_master.loc[0, 'English case databases'],
                    dbs_en_legis = df_master.loc[0, 'English legislation databases'],
                    dbs_en_other = df_master.loc[0, 'English other databases'],
                    dbs_c_cases = df_master.loc[0, '中文判案書資料庫'],
                    dbs_c_legis = df_master.loc[0, '中文法例資料庫'],
                    dbs_c_other = df_master.loc[0, '其他中文資料庫'],
                    sortby = df_master.loc[0, 'Sort by'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )

    hklii_search.search()

    hklii_search.get_judgments()
    
    for judgment_json in hklii_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = flagship_model
    else:        
        gpt_model = basic_model
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    #Pop judgment and appendices
    if pop_judgment() > 0:
        if 'extracted_text' in df_updated.columns:
            df_updated.pop('extracted_text')

    #Pop empty columns (eg columns of Chinese original, English translation)
    df_updated.replace("", np.nan, inplace=True)
    df_updated.dropna(how='all', axis=1, inplace=True)
    df_updated.replace(np.nan, '', inplace=True)
    
    return df_updated
    


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def hklii_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
        
    hklii_search = hklii_search_tool( 
                    citation = df_master.loc[0, 'Citation'],
                    title = df_master.loc[0, 'Case name'],
                    captitle = df_master.loc[0, 'Legislation name'],
                    parties = df_master.loc[0, 'Parties of judgment'], 
                    coram = df_master.loc[0, 'Coram of judgment'],
                    representation = df_master.loc[0, 'Parties representation'], 
                    charge = df_master.loc[0, 'Charge'],
                    text = df_master.loc[0, 'All of these words'], 
                    anyword = df_master.loc[0, 'Any of these words'], 
                    phrase = df_master.loc[0, 'Exact phrase'],
                    min_date = df_master.loc[0, 'Start date'],
                    max_date = df_master.loc[0, 'End date'],
                    dbs_en_cases = df_master.loc[0, 'English case databases'],
                    dbs_en_legis = df_master.loc[0, 'English legislation databases'],
                    dbs_en_other = df_master.loc[0, 'English other databases'],
                    dbs_c_cases = df_master.loc[0, '中文判案書資料庫'],
                    dbs_c_legis = df_master.loc[0, '中文法例資料庫'],
                    dbs_c_other = df_master.loc[0, '其他中文資料庫'],
                    sortby = df_master.loc[0, 'Sort by'],
                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                    )

    hklii_search.search()

    hklii_search.get_judgments()
    
    for judgment_json in hklii_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

    df_individual = pd.read_json(json_individual)

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

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)
    
    return batch_record_df_individual
