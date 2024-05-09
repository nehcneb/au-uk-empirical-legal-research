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
from datetime import datetime
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

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#OpenAI
import openai
import tiktoken

#Google
from google.oauth2 import service_account

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb

# %%
#Whether users are allowed to use their account
from extra_functions import own_account_allowed

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

# %%
#Get current directory
current_dir = os.getcwd()


# %%
#today
today_in_nums = str(datetime.now())[0:10]

# %%
# Generate placeholder list of errors
errors_list = set()


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer')

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

#Excel metadata
excel_author = 'The Empirical Legal Research Kickstarter'
excel_description = 'A 2022 University of Sydney Research Accelerator (SOAR) Prize partially funded the development of the Empirical Legal Research Kickstarter, which generated this spreadsheet.'

def convert_df_to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_urls': False}})
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    workbook.set_properties({"author": excel_author, "comments": excel_description})
    worksheet = writer.sheets['Sheet1']
#    format1 = workbook.add_format({'num_format': '0.00'}) 
    worksheet.set_column('A:A', None)#, format1)  
    writer.save()
    processed_data = output.getvalue()
    return processed_data

# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %% [markdown]
# # UK Courts search engine

# %%
#Pause between judgment scraping

#scraper_pause = 5

#print(f"The pause between judgment scraping is {scraper_pause} second.\n")

scraper_pause_mean = int((15-5)/2)

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")


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
    
    #Free text

    query = query_entry
    
    #dates        
    
    from_day= '',
    from_month='', 
    from_year='', 

    if from_date_entry != 'None':

        try:
            from_day = str(from_date_entry.strftime('%d'))
            from_month = str(from_date_entry.strftime('%m'))
            from_year = str(from_date_entry.strftime('%Y'))

        except:
            pass

    
    to_day= '',
    to_month='', 
    to_year='', 

    if to_date_entry != 'None':

        try:
            to_day = str(to_date_entry.strftime('%d'))
            to_month = str(to_date_entry.strftime('%m'))
            to_year = str(to_date_entry.strftime('%Y'))

        except:
            pass
    
    #Courts
    courts_list = courts_entry
    court_string = ', '.join(courts_list)
    court = court_string
    
    #Other entries
    party = party_entry
    judge =  judge_entry

    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
    
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
            'Free text': query,
           'From date': from_day, 
            'From month': from_month,
            'From year': from_year,
            'To day': to_day,
            'To month': to_month,
            'To year' : to_year,
            'Courts' : court, 
            'Party' : party,
            'Judge' : judge, 
            'Metadata inclusion' : meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your question(s) for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status, 
          'Use own account': own_account,
            'Use latest version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
    
#    df_master_new.to_json(current_dir + '/df_master.json', orient = 'split', compression = 'infer')
#    df_master_new.to_excel(current_dir + '/df_master.xlsx', index=False)

#    if len(df_master_new) > 0:
        
    return df_master_new

#    else:
#        return 'Error: spreadsheet of reponses NOT generated.' 

# %%
#Initialize default courts

uk_courts_default_list = ['United Kingdom Supreme Court',
 'Privy Council',
 'Court of Appeal Civil Division',
 'Court of Appeal Criminal Division',
 'High Court (England & Wales) Administrative Court',
 'High Court (England & Wales) Admiralty Court',
 'High Court (England & Wales) Chancery Division',
 'High Court (England & Wales) Commercial Court',
 'High Court (England & Wales) Family Division',
 'High Court (England & Wales) Intellectual Property Enterprise Court',
 "High Court (England & Wales) King's/Queen's Bench Division",
 'High Court (England & Wales) Mercantile Court',
 'High Court (England & Wales) Patents Court',
 'High Court (England & Wales) Senior Courts Costs Office',
 'High Court (England & Wales) Technology and Construction Court'
]


# %%
#Define format functions for courts choice, and GPT questions

#auxiliary lists and variables
uk_courts ={'United Kingdom Supreme Court': 'uksc',
'Privy Council': 'ukpc',  
'Court of Appeal Civil Division': 'ewca%2Fciv', 
 'Court of Appeal Criminal Division':  'ewca%2Fcrim',  
'High Court (England & Wales) Administrative Court': 'ewhc%2Fadmin',
'High Court (England & Wales) Admiralty Court': 'ewhc%2Fadmlty',  
'High Court (England & Wales) Chancery Division': 'ewhc%2Fch',  
'High Court (England & Wales) Commercial Court': 'ewhc%2Fcomm',  
'High Court (England & Wales) Family Division': 'ewhc%2Ffam',  
'High Court (England & Wales) Intellectual Property Enterprise Court': 'ewhc%2Fipec',  
"High Court (England & Wales) King's/Queen's Bench Division" : 'ewhc%2Fkb',
'High Court (England & Wales) Mercantile Court': 'ewhc%2Fmercantile',  
'High Court (England & Wales) Patents Court': 'ewhc%2Fpat',  
'High Court (England & Wales) Senior Courts Costs Office': 'ewhc%2Fscco',  
'High Court (England & Wales) Technology and Construction Court': 'ewhc%2Ftcc',  
'Court of Protection': 'ewcop',  
'Family Court': 'ewfc',  
'Employment Appeal Tribunal': 'eat',  
'Administrative Appeals Chamber': 'ukut%2Faac',  
'Immigration and Asylum Chamber': 'ukut%2Fiac',
'Lands Chamber': 'ukut%2Flc',  
'Tax and Chancery Chamber': 'ukut%2Ftcc',  
'General Regulatory Chamber': 'ukftt%2Fgrc',  
'Tax Chamber' : 'ukftt%2Ftc'
}

uk_courts_list = list(uk_courts.keys())

def court_choice(x):
    individual_choice = []
    if len(x) < 5:
        pass #If want no court to be covered absent choice
        #for i in uk_courts.keys():
            #individual_choice.append(uk_courts[i])
    else:
        y = x.split(', ')
        for j in y:
            individual_choice.append(uk_courts[j])
    
    return individual_choice
    

#Create function to split a string into a list by line
def split_by_line(x):
    y = x.split('\n')
    for i in y:
        if len(i) == 0:
            y.remove(i)
    return y

#Create function to split a list into a dictionary for list items longer than 10 characters
#Apply split_by_line() before the following function
def GPT_label_dict(x_list):
    GPT_dict = {}
    for i in x_list:
        if len(i) > 10:
            GPT_index = x_list.index(i) + 1
            i_label = 'GPT question ' + f'{GPT_index}'
            GPT_dict.update({i_label: i})
    return GPT_dict

#Functions for tidying up

#Tidy up hyperlink
def link(x):
    y =str(x).replace('.uk/id', '.uk')
    value = '=HYPERLINK("' + y + '")'
    return value



# %%
#Function turning search terms to search results url
def uk_search(query= '', 
              from_day= '',
              from_month='', 
              from_year='', 
              to_day='', 
              to_month='', 
              to_year='', 
              court = [], 
              party = '', 
              judge = ''
             ):
    base_url = "https://caselaw.nationalarchives.gov.uk/judgments/search?per_page=50&order=relevance"
    params = {'query' : query, 
              'from_day' : from_day,
              'from_month' : from_month, 
              'from_year' : from_year, 
              'to_day' : to_day, 
              'to_month' : to_month, 
              'to_year' : to_year, 
              'court' : court, 
              'party' : party, 
              'judge' : judge}

    response = requests.get(base_url, params=params)
    response.raise_for_status()

    proper_url = str(response.url).replace('%25', '%')
    
    return proper_url


# %%
#Define function turning search results url to links to judgments
def search_results_to_judgment_links(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")
    hrefs = soup.find_all('a', href=True)
    links = []
    
    #Start counter
    
    counter = 1
    
    for link in hrefs:
        if ((counter <= judgment_counter_bound) and ('a href="/' in str(link)) and '">' in str(link) and '?' in str(link)):
            link_direct = 'https://caselaw.nationalarchives.gov.uk' + str(link).split('?')[0][9:] + '/data.xml'
            links.append(link_direct.replace('.uk/id', '.uk'))
            counter = counter + 1
    
    for ending in range(100):
        if counter <=judgment_counter_bound:
            url_next_page = url_search_results + '&page=2' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
    
            #Check if stll more results
            if 'No results have been found' not in str(soup_judgment_next_page):
                hrefs_next_page = soup_judgment_next_page.find_all('a', href=True)
                for extra_link in hrefs_next_page:
                    if ((counter <= judgment_counter_bound) and ('a href="/' in str(extra_link)) and '">' in str(extra_link) and '?' in str(extra_link)):
                        extra_link_direct = 'https://caselaw.nationalarchives.gov.uk' + str(extra_link).split('?')[0][9:] + '/data.xml'
                        links.append(extra_link_direct.replace('.uk/id', '.uk'))
                        counter = counter + 1
            else:
                break
            
            pause.seconds(np.random.randint(5, 15))

    return links


# %%
#Meta labels and judgment combined

meta_labels_droppable = ['Date', 
                         'Court', 
                         'Case number', 
                         'Judge(s) (non-exhaustiveive)', 
                         'Parties', 
                         'Header'
                        ]

    
def meta_judgment_dict(judgment_url_xml):
    page = requests.get(judgment_url_xml)
    soup = BeautifulSoup(page.content, "lxml")
    
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to The National Archives' : '', 
                'Date' : '',
                'Court' : '', 
                'Case number': '',
                'Judge(s) (non-exhaustiveive)' : [], 
                'Parties' : [],
                'Header' : '',
                'Judgment': ''
                }
    try:
        judgment_dict['Case name'] = soup.find("frbrname")['value']
        judgment_dict['Medium neutral citation'] = soup.find("uk:cite").getText()
        judgment_dict['Hyperlink to The National Archives'] = link(soup.find("frbruri")['value'])
        judgment_dict['Date'] = soup.find("frbrdate")['date']
        judgment_dict['Court'] = soup.find("uk:court").getText()
        judgment_dict['Header'] = soup.find('header').getText()
        if judgment_dict['Header'][0:1] == '\n':
            judgment_dict['Header'] = judgment_dict['Header'][1: ]
        judgment_dict['Case number'] = soup.find("docketnumber").getText()
    except:
        pass
    
    for person in soup.find_all("tlcperson"):
        if 'judge' in str(person):
            judgment_dict['Judge(s) (non-exhaustiveive)'].append(person["showas"])
        else:
            judgment_dict['Parties'].append(person["showas"])
    
    #Get judgment content as a list of headings and paras, but not enumeration/paragraph number
    #for text in soup.find_all('content'):
    #    judgment_dict['Judgment'].append(text.getText())

    #Get judgment

    pause.seconds(np.random.randint(5, 15))

    html_link = judgment_url_xml.replace('/data.xml', '')
    page_html = requests.get(html_link)
    soup_html = BeautifulSoup(page_html.content, "lxml")
    
    judgment_text = soup_html.get_text(separator="\n", strip=True)

    try:
        before_end_of_doc = judgment_text.split('End of document')[0]
        after_skip_to_end = before_end_of_doc.split('Skip to end')[1]
        judgment_text = after_skip_to_end
        
    except:
        pass

    judgment_dict['Judgment'] = judgment_text
    
    #try:
     #   judgment_text = str(soup.find_all('content'))
    #except:
      #  judgment_text= soup.get_text(strip=True)
        
    return judgment_dict


# %% [markdown]
# # GPT functions and parameters

# %%
#Check validity of API key

def is_api_key_valid(key_to_check):
    openai.api_key = key_to_check
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": 'Who is Taylor Swift?'}], 
            max_tokens = 5
        )
    except:
        return False
    else:
        return True


# %%
#Module, costs and upperbounds

#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-3.5-turbo-0125"

#Upperbound on number of engagements with GPT

#GPT_use_bound = 3

#print(f"\nPrior number of GPT uses is capped at {GPT_use_bound} times.")

#Define input and output costs, token caps and maximum characters
#each token is about 4 characters

def gpt_input_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_input_cost = 1/1000000*0.5
        
    if gpt_model == "gpt-4-turbo":
        gpt_input_cost = 1/1000000*10
    return gpt_input_cost

def gpt_output_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_output_cost = 1/1000000*0.5
        
    if gpt_model == "gpt-4-turbo":
        gpt_output_cost = 1/1000000*10
        
    return gpt_output_cost

def tokens_cap(gpt_model):
    
    if gpt_model == "gpt-3.5-turbo-0125":
        tokens_cap = int(16385 - 2000) #For GPT-3.5-turbo, token limit covering both input and output is 16385,  while the output limit is 4096.
    
    if gpt_model == "gpt-4-turbo":
        tokens_cap = int(128000 - 6000) #For GPT-4-turbo, token limit covering both input and output is 128000, while the output limit is 4096.

    return tokens_cap
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#Upperbound on the length of questions for GPT
#if 'question_characters_bound' not in st.session_state:
#    st.session_state['question_characters_bound'] = 1000

question_characters_bound = 1000

print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")

#Upperbound on number of judgments to scrape

#Default judgment counter bound

default_judgment_counter_bound = 10

if 'judgments_counter_bound' not in st.session_state:
    st.session_state['judgments_counter_bound'] = default_judgment_counter_bound

print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")


# %%
#Define function to determine eligibility for GPT use

#Define a list of privileged email addresses with unlimited GPT uses

privileged_emails = st.secrets["secrets"]["privileged_emails"].replace(' ', '').split(',')

def prior_GPT_uses(email_address, df_online):
    # df_online variable should be the online df_online
    prior_use_counter = 0
    for i in df_online.index:
        if ((df_online.loc[i, "Your email address"] == email_address) 
            and (int(df_online.loc[i, "Use GPT"]) > 0) 
            and (len(df_online.loc[i, "Processed"])>0)
           ):
            prior_use_counter += 1
    if email_address in privileged_emails:
        return 0
    else:
        return prior_use_counter

#Define function to check whether email is educational or government
def check_edu_gov(email_address):
    #Return 1 if educational or government, return 0 otherwise
    end=email_address.split('@')[1]
    if (('.gov' in end) or ('.edu' in end) or ('.ac' in end)):
        return 1
    else:
        return 0



# %%
#Tokens estimate preliminaries
#encoding = tiktoken.get_encoding("cl100k_base")
#encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

#Tokens estimate function
def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

#Define judgment input function for JSON approach

#Token limit covering both GTP input and GPT output is 16385, each token is about 4 characters
#characters_limit_half = int((16385*4)/2-1500)
#tokens_cap(gpt_model) = int(16385 - 1500)

def judgment_prompt_json(judgment_json, gpt_model):
                
    judgment_content = 'Based on the metadata and judgment in the following JSON:  """'+ str(judgment_json) + '"""'

    judgment_content_tokens = num_tokens_from_string(judgment_content, "cl100k_base")
    
    if judgment_content_tokens <= tokens_cap(gpt_model):
        
        return judgment_content

    else:
        
        meta_data_len = judgment_content_tokens - num_tokens_from_string(judgment_json['Judgment'], "cl100k_base")
        
        judgment_chars_capped = int((tokens_cap(gpt_model) - meta_data_len)*4)
        
        judgment_string_trimmed = judgment_json['Judgment'][ :int(judgment_chars_capped/2)] + judgment_json['Judgment'][-int(judgment_chars_capped/2): ]

        judgment_json["Judgment"] = judgment_string_trimmed     
        
        judgment_content_capped = 'Based on the metadata and judgment in the following JSON:  """'+ str(judgment_json) + '"""'
        
        return judgment_content_capped



# %%
#Define system role content for GPT
role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in string form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a specific paragraph in the judgment, provide the paragraph number as part of your answer. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found".'

intro_for_GPT = [{"role": "system", "content": role_content}]


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#IN USE

def GPT_json_tokens(questions_json, judgment_json, gpt_model):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   

    judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json, gpt_model)}]

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]
    
    #Create answer format
    
    q_keys = [*questions_json]
    
    answers_json = {}
    
    for q_index in q_keys:
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific paragraph numbers in the judgment or specific sections in the metadata.'})
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": str(questions_json).replace("\'", '"') + ' Give responses in the following JSON form: ' + str(answers_json).replace("\'", '"')}]
    
    #Create messages in one prompt for GPT
    messages_for_GPT = intro_for_GPT + judgment_for_GPT + json_direction + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        for q_index in q_keys:
            answers_json[q_index] = error
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by judgment then question, with input and output tokens given by GPT itself
#IN USE

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*
def engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, gpt_model):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Judgment length in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    question_keys = [*questions_json]
    
    for judgment_index in df_individual.index:
        
        judgment_json = df_individual.to_dict('index')[judgment_index]
        
        #Calculate and append number of tokens of judgment, regardless of whether given to GPT
        judgment_tokens = num_tokens_from_string(str(judgment_json), "cl100k_base")
        df_individual.loc[judgment_index, f"Judgment length in tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = judgment_tokens       

        #Indicate whether judgment truncated
        
        df_individual.loc[judgment_index, "Judgment truncated (if given to GPT)?"] = ''       
        
        if judgment_tokens <= tokens_cap(gpt_model):
            
            df_individual.loc[judgment_index, "Judgment truncated (if given to GPT)?"] = 'No'
            
        else:
            
            df_individual.loc[judgment_index, "Judgment truncated (if given to GPT)?"] = 'Yes'

        #Create columns for respondent's GPT cost, time
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each judgment, gives answers as a string containing a dictionary

        if int(GPT_activation) > 0:
            GPT_output_list = GPT_json_tokens(questions_json, judgment_json, gpt_model) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_output_list[0]

            #Calculate and append GPT finish time and time difference to individual df
            GPT_finish_time = datetime.now()
            
            GPT_time_difference = GPT_finish_time - GPT_start_time
    
            df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()

        
        else:
            answers_dict = {}    
            for q_index in question_keys:
                #Increases judgment index by 2 to ensure consistency with Excel spreadsheet
                answer = 'Placeholder answer for ' + ' judgment ' + str(int(judgment_index) + 2) + ' ' + str(q_index)
                answers_dict.update({q_index: answer})
            
            #Own calculation of GPT costs for Placeholder answer fors

            #Calculate capped judgment tokens

            judgment_capped_tokens = num_tokens_from_string(judgment_prompt_json(judgment_json, gpt_model), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(str(questions_json), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = role_content + 'you will be given questions to answer in JSON form.' + ' Give responses in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific paragraph numbers in the judgment or specific sections in the metadata.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            input_tokens = judgment_capped_tokens + questions_tokens + other_tokens
            
            GPT_output_list = [answers_dict, answers_tokens, input_tokens]

    	#Create GPT question headings, append answers to individual spreadsheets, and remove template/erroneous answers

        for question_index in question_keys:
            question_heading = question_index + ': ' + questions_json[question_index]
            df_individual.loc[judgment_index, question_heading] = answers_dict[question_index]
            
            if 'Your answer to the question with index GPT question' in str(answers_dict[question_index]):
                df_individual.loc[judgment_index, question_heading] = f'Error for judgment {str(int(judgment_index)+2)}, GPT question {question_index}. Please try again.'

        #Calculate GPT costs

        GPT_cost = GPT_output_list[1]*gpt_output_cost(gpt_model) + GPT_output_list[2]*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %%
#Obtain parameters

def run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your question(s) for GPT'] = df_master['Enter your question(s) for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your question(s) for GPT'].apply(GPT_label_dict)
    df_master['Courts'] = df_master['Courts'].apply(court_choice)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    url_search_results = uk_search(query= df_master.loc[0, 'Free text'], 
                                   from_day= df_master.loc[0, 'From date'],
                                   from_month=df_master.loc[0, 'From month'], 
                                   from_year=df_master.loc[0, 'From year'], 
                                   to_day=df_master.loc[0, 'To day'], 
                                   to_month=df_master.loc[0, 'To month'], 
                                   to_year=df_master.loc[0, 'To year'], 
                                   court= df_master.loc[0, 'Courts'], 
                                   party = df_master.loc[0, 'Party'], 
                                   judge = df_master.loc[0, 'Judge']
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
    
    df_individual = pd.read_json(json_individual)

    #For UK, convert date to string so as to avoid Excel producing random numbers for dates
    df_individual['Date'] = df_individual['Date'].astype(str)
    
    #GPT model

    if df_master.loc[0, 'Use latest version of GPT'] == True:
        gpt_model = "gpt-4-turbo"
    else:        
        gpt_model = "gpt-3.5-turbo-0125"
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, gpt_model)

    df_updated.pop('Judgment')

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

    df_master['Courts'] = df_master['Courts'].apply(court_choice)
    
    #Combining catchwords into new column
    
    #Conduct search
    
    url = uk_search(query= df_master.loc[0, 'Free text'], 
                                   from_day= df_master.loc[0, 'From date'],
                                   from_month=df_master.loc[0, 'From month'], 
                                   from_year=df_master.loc[0, 'From year'], 
                                   to_day=df_master.loc[0, 'To day'], 
                                   to_month=df_master.loc[0, 'To month'], 
                                   to_year=df_master.loc[0, 'To year'], 
                                   court= df_master.loc[0, 'Courts'], 
                                   party = df_master.loc[0, 'Party'], 
                                   judge = df_master.loc[0, 'Judge']
                                  )
    return url


# %%
def tips():
    st.markdown(""":green[**DO's**:]
- :green[Do break down complex tasks into simple sub-tasks.]
- :green[Do give clear and detailed instructions (eg specify steps required to complete a task).]
- :green[Do use the same terminology as the relevant judgments themselves.]
- :green[Do give exemplar answers.]
- :green[Do manually check some or all answers.]
- :green[Do revise questions to get better answers.]
- :green[Do evaluate answers on the same sample of judgments (ie the "training" sample).]
""")

    st.markdown(""":red[**Don'ts**:]
- :red[Don't ask questions which go beyond the relevant judgment itself.]
- :red[Don't ask difficult maths questions.]
- :red[Don't skip manual evaluation.]
""")

    st.markdown(""":orange[**Maybe's**:]
- :orange[Maybe ask for reasoning.]
- :orange[Maybe re-run the same questions and manually check any inconsistent answers.]
""")

    st.caption('For more tips, please see https://platform.openai.com/docs/guides/prompt-engineering.')


# %% [markdown]
# # Streamlit form, functions and parameters

# %% [markdown]
# ## Function definitions

# %%
#Function to open url
def open_page(url):
    open_script= """
        <script type="text/javascript">
            window.open('%s', '_blank').focus();
        </script>
    """ % (url)
    html(open_script)


# %%
def clear_cache_except_validation_df_master():
    keys = list(st.session_state.keys())
    if 'gpt_api_key_validity' in keys:
        keys.remove('gpt_api_key_validity')
    if 'df_master' in keys:
        keys.remove('df_master')
    for key in keys:
        st.session_state.pop(key)


# %%
def tips():
    st.markdown(""":green[**DO's**:]
- :green[Do break down complex tasks into simple sub-tasks.]
- :green[Do give clear and detailed instructions (eg specify steps required to complete a task).]
- :green[Do use the same terminology as the relevant judgments themselves.]
- :green[Do give exemplar answers.]
- :green[Do manually check some or all answers.]
- :green[Do revise questions to get better answers.]
- :green[Do evaluate answers on the same sample of judgments (ie the "training" sample).]
""")

    st.markdown(""":red[**Don'ts**:]
- :red[Don't ask questions which go beyond the relevant judgment itself.]
- :red[Don't ask difficult maths questions.]
- :red[Don't skip manual evaluation.]
""")

    st.markdown(""":orange[**Maybe's**:]
- :orange[Maybe ask for reasoning.]
- :orange[Maybe re-run the same questions and manually check for inconsistency.]
""")

    st.caption('For more tips, please see https://platform.openai.com/docs/guides/prompt-engineering.')


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default_courts

if 'default_courts' not in st.session_state:
    st.session_state['default_courts'] = []

# %%
#Initialize default values

if 'gpt_enhancement_entry' not in st.session_state:
    st.session_state['gpt_enhancement_entry'] = False

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

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
#Create form for court selection

return_button = st.button('RETURN to first page')

st.header(f"You have selected to study :blue[judgments of select United Kingdom courts and tribunals].")

#st.header("Judgment Search Criteria")

st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.

For search tips, please visit The National Archives at https://caselaw.nationalarchives.gov.uk/structured_search. This section mimics their case law search function.
""")
st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to cover more judgments.')

st.subheader("UK courts and tribunals to cover")

default_on = st.checkbox('Prefill the Supreme Court, the Court of Appeal, and the High Court of England and Wales')

if default_on:

    st.session_state.default_courts = uk_courts_default_list

else:
    st.session_state.default_courts = []

courts_entry = st.multiselect(label = 'Select or type in the courts and tribunals to cover', options = uk_courts_list, default = st.session_state.default_courts)
    
#st.caption("All courts and tribunals listed in this menu will be covered if left blank.")

#Search terms

st.subheader("Your search terms")

query_entry = st.text_input('Free text')

from_date_entry = st.date_input('From date', value = None, format="DD/MM/YYYY")

to_date_entry = st.date_input('to date', value = None, format="DD/MM/YYYY")

st.caption('For information about judgment availability, please visit https://caselaw.nationalarchives.gov.uk/structured_search.')

judge_entry = st.text_input('Judge name')

party_entry = st.text_input('Party name')

st.markdown("""You can preview the judgments returned by your search terms on the National Archives after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")

preview_button = st.button('PREVIEW on the National Archives (in a popped up window)')

st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the names of the parties and so on. 

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

st.caption("Use of GPT is costly and funded by a grant. For the model used by default, Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per judgment. The exact cost for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced (as elaborated at https://openai.com/pricing for model gpt-3.5-turbo-0125). You will be given ex-post cost estimates.")

st.subheader("Enter your question(s) for each judgment")

st.markdown("""GPT will answer your question(s) for **each** judgment based only on information from **that** judgment. 

*Please enter one question per line or per paragraph.*""")

gpt_questions_entry = st.text_area(f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound) 

st.caption(f"By default, answers to your questions will be generated by model gpt-3.5-turbo-0125. Due to a technical limitation, this model will read up to approximately {round(tokens_cap('gpt-3.5-turbo-0125')*3/4)} words from each judgment.")

if st.toggle('Tips for using GPT'):
    tips()

st.markdown("""GPT is instructed to avoid giving answers which cannot be obtained from the relevant judgment itself. This is to minimise the risk of giving incorrect information (ie hallucination).""")

if st.toggle('See the instruction given to GPT'):
    st.write(f"*{intro_for_GPT[0]['content']}*")

if own_account_allowed() > 0:

    
    st.subheader(':orange[Enhance program capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum nunber of judgments to process? You can do so with your own GPT account.
    """)
    
    own_account_entry = st.toggle('Use my own GPT account')
    
    if own_account_entry:
    
        st.session_state["own_account"] = True
    
        st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage at https://platform.openai.com/signup. You can then find your API key at https://platform.openai.com/api-keys.
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
    
        st.markdown("""**:green[You can use the latest version of GPT model (gpt-4-turbo),]** which is :red[20 times more expensive, per character] than the default model (gpt-3.5-turbo) which you can use for free.""")  
        
        gpt_enhancement_entry = st.checkbox('Use the latest GPT model', value = False)
        st.caption('For more on pricing for different GPT models, please see https://openai.com/api/pricing.')
        
        if gpt_enhancement_entry == True:
        
            st.session_state.gpt_model = "gpt-4-turbo"
            st.session_state.gpt_enhancement_entry = True

        else:
            
            st.session_state.gpt_model = "gpt-3.5-turbo-0125"
            st.session_state.gpt_enhancement_entry = False
        
        st.write(f'**:green[You can increase the maximum number of judgments to process.]** The default maximum is {default_judgment_counter_bound}.')
        
        judgments_counter_bound_entry = round(st.number_input(label = 'Enter the maximum number of judgments up to 100', min_value=1, max_value=100, value=default_judgment_counter_bound))
    
        st.session_state.judgments_counter_bound = judgments_counter_bound_entry
    
        st.write(f'*GPT model {st.session_state.gpt_model} will answer any questions based on up to approximately {round(tokens_cap(st.session_state.gpt_model)*3/4)} words from each judgment, for up to {st.session_state.judgments_counter_bound} judgments.*')
    
    else:
        
        st.session_state["own_account"] = False
    
        st.session_state.gpt_model = "gpt-3.5-turbo-0125"

        st.session_state.gpt_enhancement_entry = False

        st.session_state.judgments_counter_bound = default_judgment_counter_bound
    
        #st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]
    
    #judgments_counter_bound_entry = round(judgments_counter_bound_entry_raw)
       


# %% [markdown]
# ## Consent and next steps

# %%
st.header("Consent")

st.markdown("""By running the Empirical Legal Research Kickstarter, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False)

st.markdown("""If you do not agree, then please feel free to close this form.""")

st.header("Next steps")

st.markdown("""**:green[You can now run the Empirical Legal Research Kickstarter.]** A spreadsheet which hopefully has the data you seek will be available for download in about 2-3 minutes.

You can also download a record of your responses.
""")

#Warning
#if st.session_state.gpt_model == 'gpt-3.5-turbo-0125':
    #st.warning('A low-cost AI will answer your question(s). Please check at least some of the answers.')

#if st.session_state.gpt_model == "gpt-4-turbo":
    #st.warning('An expensive AI will answer your question(s). Please be cautious.')

run_button = st.button('RUN the program')

keep_button = st.button('DOWNLOAD your form responses')

reset_button = st.button(label='RESET to start afresh', type = 'primary',  help = "Press to process new search terms or questions.")

#Display need resetting message if necessary
if 'need_resetting' in st.session_state:
#if st.session_state.need_resetting == 1:
    st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')


# %% [markdown]
# ## Previous responses and outputs

# %%
#Create placeholder download buttons if previous responses and results in st.session_state:

if (('df_master' in st.session_state) and ('df_individual_output' in st.session_state)):

    #Load previous responses and results

    df_master = st.session_state.df_master
    df_individual_output = st.session_state.df_individual_output

    #Buttons for downloading responses

    st.subheader('Looking for your previous form responses?')

    responses_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'

    csv = convert_df_to_csv(df_master)

    ste.download_button(
        label="Download your previous responses as a CSV (for use in Excel etc)", 
        data = csv,
        file_name=responses_output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    xlsx = convert_df_to_excel(df_master)
    
    ste.download_button(label='Download your previous responses as an Excel spreadsheet (XLSX)',
                        data=xlsx,
                        file_name=responses_output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )

    json = convert_df_to_json(df_master)
    
    ste.download_button(
        label="Download your previous responses as a JSON", 
        data = json,
        file_name= responses_output_name + '.json', 
        mime= "application/json", 
    )

    #Button for downloading results

    st.subheader('Looking for your previous results?')

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

    st.page_link('pages/AI.py', label="ANALYSE your spreadsheet with an AI", icon = '🤔')



# %% [markdown]
# # Save and run

# %%
if preview_button:

    gpt_api_key_entry = ''

    df_master = create_df()

    judgments_url = search_url(df_master)
    
#    df_master['Courts'] = df_master['Courts'].apply(court_choice)

#    judgments_url =  uk_search(query= df_master.loc[0, 'Free text'], 
##                                   from_day= df_master.loc[0, 'From date'],
 #                                  from_month=df_master.loc[0, 'From month'], 
 #                                  from_year=df_master.loc[0, 'From year'], 
 #                                  to_day=df_master.loc[0, 'To day'], 
 #                                  to_month=df_master.loc[0, 'To month'], 
 #                                  to_year=df_master.loc[0, 'To year'], 
 #                                  court= df_master.loc[0, 'Courts'], 
 #                                  party = df_master.loc[0, 'Party'], 
 #                                  judge = df_master.loc[0, 'Judge']
 #                                 )

    open_page(judgments_url)


# %%
if run_button:
    
    all_search_terms = str(query_entry) + str(from_date_entry) + str(to_date_entry) + str(judge_entry) + str(party_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif len(courts_entry) == 0:
        st.write('Please select at least one court to cover.')
        
    elif int(consent) == 0:
        st.warning("You must click on 'Yes, I agree.' to run the program.")

    elif (('df_master' in st.session_state) and ('df_individual_output' in st.session_state)):
        st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')
        
        if 'need_resetting' not in st.session_state:
            
            st.session_state['need_resetting'] = 1

    elif ((st.session_state.own_account == True) and (st.session_state.gpt_api_key_validity == False)):
            
        st.warning('You have not validated your API key.')
        quit()

    elif ((st.session_state.own_account == True) and (len(gpt_api_key_entry) < 20)):

        st.warning('You have not entered a valid API key.')
        quit()  
        
    else:
        
        st.markdown("""Your results will be available for download soon. The estimated waiting time is about 2-3 minutes per 10 judgments.""")
        #st.write('If this program produces an error or an unexpected spreadsheet, please double-check your search terms and try again.')

        with st.spinner('Running...'):

            try:
        
                #Create spreadsheet of responses
                df_master = create_df()

                #Activate user's own key or mine
                if st.session_state.own_account == True:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    API_key = st.secrets["openai"]["gpt_api_key"]
                
                #Produce results
                df_individual_output = run(df_master)
                
                #Keep results in session state
                if "df_individual_output" not in st.session_state:
                    st.session_state["df_individual_output"] = df_individual_output
        
                if "df_master" not in st.session_state:
                    st.session_state["df_master"] = df_master
                
                st.session_state["page_from"] = 'pages/UK.py'
        
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
                #conn.update(worksheet="UK", data=df_to_update, )
            
            except Exception as e:
                st.error('Your search terms may not return any judgments. Please press the PREVIEW button above to double-check.')
                st.exception(e)
                


# %%
if keep_button:

    all_search_terms = str(query_entry) + str(from_date_entry) + str(to_date_entry) + str(judge_entry) + str(party_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif len(courts_entry) == 0:
        st.write('Please select at least one court to cover.')

    elif (('df_master' in st.session_state) and ('df_individual_output' in st.session_state)):
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
