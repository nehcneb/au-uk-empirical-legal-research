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
import urllib.request
import io

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
    return df.to_json(orient = 'split', compression = 'infer', default_handler=str)

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
# # Kercher Reports search engine

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
    
    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
    
    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry[0: question_characters_bound]
    
    except:
        print('GPT questions not entered.')
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Enter search query': query_entry,
           'Find (method)': method_entry,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
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
#Define format functions for GPT questions    

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
    y =str(x)#.replace('.uk/id', '.uk')
    value = '=HYPERLINK("' + y + '")'
    return value


# %%
#list of search methods

methods_list = ['Full text', 'Titles only', 'This Boolean query', 'Any of these words', 'All of these words']
method_types = ['auto', 'title', 'boolean', 'any', 'all']


# %%
#Function turning search terms to search results url

def kr_search(query= '', 
              method = ''
             ):
    base_url = "https://www.austlii.edu.au/cgi-bin/sinosrch.cgi?"

    method_index = methods_list.index(method)
    method_type = method_types[method_index]

    query_text = query

    params = {#'meta' : ';',
              'mask_path' : 'au/cases/nsw/NSWSupC', 
              'method' : method_type,
              'query' : query_text
             }

    response = requests.get(base_url, params=params)
    
    return response.url


# %%
#Define function turning search results url to case_link_pairs to judgments
def search_results_to_case_link_pairs(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    headers = {'User-Agent': 'whatever'}
    page = requests.get(url_search_results, headers=headers)
    soup = BeautifulSoup(page.content, "lxml")
    hrefs = soup.find_all('a', href=True)
    case_link_pairs = []

    #number of search results
    docs_found_string = str(soup.find('title')).split('AustLII:')[1].split('documents')[0].replace(' ', '')
    docs_found = int(docs_found_string)

    #Start counter
    counter = 1
    
    for link in hrefs:
        if ((counter <= judgment_counter_bound) and (' NSWSupC ' in str(link)) and ('LawCite' not in str(link))):
#        if ((counter <= judgment_counter_bound) and ('AustLII' in str(link)) and ('cases/EngR' in str(link)) and ('LawCite' not in str(link))):
            case = link.get_text()
            link_direct = link.get('href')
            link = 'https://www.austlii.edu.au' + link_direct.split('?context')[0]
            dict_object = { 'case': case, 'link_direct': link}
            case_link_pairs.append(dict_object)
            counter = counter + 1
        
    for ending in range(10, docs_found, 10):
        if counter <= min(judgment_counter_bound, docs_found):
            url_next_page = url_search_results + ';offset=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page, headers=headers)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            
            hrefs_next_page = soup_judgment_next_page.find_all('a', href=True)
            for extra_link in hrefs_next_page:
                if ((counter <= judgment_counter_bound) and (' NSWSupC ' in str(extra_link)) and ('LawCite' not in str(link))):
#                if ((counter <= judgment_counter_bound) and ('AustLII' in str(extra_link)) and ('cases/EngR' in str(extra_link)) and ('LawCite' not in str(extra_link))):
                    case = extra_link.get_text()
                    extra_link_direct = extra_link.get('href')
                    extra_link = 'https://www.austlii.edu.au' + extra_link_direct.split('?context')[0]
                    dict_object = { 'case': case, 'link_direct': extra_link}
                    case_link_pairs.append(dict_object)
                    counter = counter + 1

            pause.seconds(np.random.randint(5, 15))
            
        else:
            break
    
    return case_link_pairs


# %%
#Convert case-link pairs to judgment text

def judgment_text(case_link_pair):
    url = case_link_pair['link_direct']
    headers = {'User-Agent': 'whatever'}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, "lxml")
    text = soup.get_text()
    try:
        text = soup.get_text().split('Print (pretty)')[0].split('\n Any \n')[-1]
    except:
        pass
    
    return text
        


# %%
#Meta labels and judgment combined

def meta_judgment_dict(case_link_pair):
    
    judgment_dict = {'Case name': '',
                     'Medium neutral citation' : '', 
                     'Other reports': '', 
                     'Hyperlink to AustLII': '', 
                     'Date' : '', 
                     'Judgment': ''
                    }

    case_name = case_link_pair['case']
    date = case_link_pair['case'].split('(')[-1].replace(')', '')
    year = case_link_pair['case'].split('[')[1][0:4]
    case_number_raw = case_link_pair['case'].split('NSWSupC ')[1].split(' (')[0]
    
    if ";" in case_number_raw:
        case_number = case_number_raw.split(';')[0]
    else:
        case_number = case_number_raw
    
    mnc = '[' + year +']' + ' NSWSupC ' + case_number
    nr_cite = ''
        
    try:
        case_name = case_link_pair['case'].split('[')[0][:-1]
        nr_cite = case_link_pair['case'].split('; ')[1].replace(' (' + date + ')', '')
    except:
        pass
                
    judgment_dict['Case name'] = case_name
    judgment_dict['Medium neutral citation'] = mnc
    judgment_dict['Other reports'] = nr_cite
    judgment_dict['Date'] = date
    judgment_dict['Hyperlink to AustLII'] = link(case_link_pair['link_direct'])
    judgment_dict['Judgment'] = judgment_text(case_link_pair)

#    pause.seconds(np.random.randint(5, 15))
    
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
            messages=[{"role": "user", "content": '1+1='}], 
            max_tokens = 1
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
        
    if gpt_model == "gpt-4o":
        gpt_input_cost = 1/1000000*5
    return gpt_input_cost

def gpt_output_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_output_cost = 1/1000000*1.5
        
    if gpt_model == "gpt-4o":
        gpt_output_cost = 1/1000000*15
        
    return gpt_output_cost

def tokens_cap(gpt_model):
    
    if gpt_model == "gpt-3.5-turbo-0125":
        tokens_cap = int(16385 - 1500) #For GPT-3.5-turbo, token limit covering both input and output is 16385,  while the output limit is 4096.
    
    if gpt_model == "gpt-4o":
        tokens_cap = int(128000 - 6000) #For gpt-4o, token limit covering both input and output is 128000, while the output limit is 4096.

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
role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in string form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a specific page in the judgment, provide the page number as part of your answer. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found".'

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
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific page numbers in the judgment or specific sections in the metadata.'})
    
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

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers in the judgment or specific sections in the metadata.", "cl100k_base")

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
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    url_search_results = kr_search(query= df_master.loc[0, 'Enter search query'], 
                                   method = df_master.loc[0, 'Find (method)']
                                  )
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_link_pairs = search_results_to_case_link_pairs(url_search_results, judgments_counter_bound)

    for case_link_pair in case_link_pairs:

        judgment_dict = meta_judgment_dict(case_link_pair)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(5, 15))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    df_individual = pd.read_json(json_individual)

    #For KR, convert date to string so as to avoid Excel producing random numbers for dates
    df_individual['Date'] = df_individual['Date'].astype(str)

    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use latest version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-3.5-turbo-0125"
            
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, gpt_model)

    df_updated.pop('Judgment')
    
    return df_updated


# %%
def search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    url = kr_search(query= df_master.loc[0, 'Enter search query'],
                    method= df_master.loc[0, 'Find (method)']
                   )
    return url


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

#Initialize enhanced prompt
if 'prompt_prefill' not in st.session_state:
    st.session_state["prompt_prefill"] = ''

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

st.header(f"You have selected to study :blue[the Kercher Reports].")

#    st.header("Judgment Search Criteria")

st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.

For search tips, please visit AustLII at https://www.austlii.edu.au/cgi-bin/viewdb/au/cases/nsw/NSWSupC/. This section mimics their search function.
""")
st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to cover more judgments.')

st.subheader("Your search terms")

method_entry = st.selectbox('Find', methods_list, index=0)

query_entry = st.text_input('Enter search query')
    
st.markdown("""You can preview the judgments returned by your search terms on AustLII after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")

preview_button = st.button('PREVIEW on AustLII (in a popped up window)')


# %% [markdown]
# ## Form for AI and account

# %%
st.header("Use GPT as your research assistant")

st.markdown("**:green[Would you like GPT to answer questions about the judgments returned by your search terms?]**")

st.markdown("""Please consider trying this program without asking GPT any questions first. You can, for instance, obtain the judgments satisfying your search criteria and extract the judgment metadata without using GPT.
""")

gpt_activation_entry = st.checkbox('Use GPT', value = False)

st.caption("Use of GPT is costly and funded by a grant. For the model used by default, Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per judgment. The exact cost for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced (as elaborated at https://openai.com/pricing for model gpt-3.5-turbo-0125). You will be given ex-post cost estimates.")

st.subheader("Enter your questions for each judgment")

st.markdown("""Please enter one question **per line or per paragraph**. GPT will answer your questions for **each** judgment based only on information from **that** judgment. """)


gpt_questions_entry = st.text_area(f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound) 

st.caption(f"By default, answers to your questions will be generated by model gpt-3.5-turbo-0125. Due to a technical limitation, this model will read up to approximately {round(tokens_cap('gpt-3.5-turbo-0125')*3/4)} words from each judgment.")

st.markdown("""GPT is instructed to avoid giving answers which cannot be obtained from the relevant judgment itself. This is to minimise the risk of giving incorrect information (ie hallucination).""")

if st.toggle('See the instruction given to GPT'):
    st.write(f"*{intro_for_GPT[0]['content']}*")

if st.toggle('Tips for using GPT'):
    tips()

    
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
    
        st.markdown("""**:green[You can use the latest version of GPT model (gpt-4o),]** which is :red[10 times more expensive, per character] than the default model (gpt-3.5-turbo) which you can use for free.""")  
        
        gpt_enhancement_entry = st.checkbox('Use the latest GPT model', value = False)
        st.caption('For more on pricing for different GPT models, please see https://openai.com/api/pricing.')
        
        if gpt_enhancement_entry == True:
        
            st.session_state.gpt_model = "gpt-4o"
            st.session_state.gpt_enhancement_entry = True
    
        else:
            
            st.session_state.gpt_model = "gpt-3.5-turbo-0125"
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
    
        st.session_state.gpt_model = "gpt-3.5-turbo-0125"
    
        st.session_state.gpt_enhancement_entry = False
    
        st.session_state.judgments_counter_bound = default_judgment_counter_bound
    
        #st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]
    
    #judgments_counter_bound_entry = round(judgments_counter_bound_entry_raw)
       


# %% [markdown]
# ## Consent and next steps

# %%
st.header("Consent")

st.markdown("""By running this program, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False)

st.markdown("""If you do not agree, then please feel free to close this form.""")

st.header("Next steps")

st.markdown("""**:green[You can now run the Empirical Legal Research Kickstarter.]** A spreadsheet which hopefully has the data you seek will be available for download.

You can also download a record of your entries.

""")

#Warning
#if st.session_state.gpt_model == 'gpt-3.5-turbo-0125':
    #st.warning('A low-cost AI will answer your questions. Please check at least some of the answers.')

#if st.session_state.gpt_model == "gpt-4o":
    #st.warning('An expensive AI will answer your questions. Please be cautious.')

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

    all_search_terms = str(query_entry)
        
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
                st.session_state["df_individual_output"] = df_individual_output
        
                st.session_state["df_master"] = df_master

                #Change session states
                st.session_state['need_resetting'] = 1
                
                st.session_state["page_from"] = 'pages/KR.py'
        
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
                #conn.update(worksheet="KR", data=df_to_update, )
        

            except Exception as e:
                st.error('Your search terms may not return any judgments. Please press the PREVIEW button above to double-check.')
                st.exception(e)



# %%
if keep_button:

    all_search_terms = str(query_entry)
        
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
