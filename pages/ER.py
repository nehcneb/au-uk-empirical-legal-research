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
from common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner, save_input
#Import variables
from common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # English Reports search engine

# %%
from common_functions import link


# %%
#function to create dataframe
def er_create_df():

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
        
    #GPT choice and entry
    try:
        gpt_activation_status = gpt_activation_entry
    except:
        gpt_activation_status = False
    
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
          'Metadata inclusion': True, #Placeholder even though no metadata collected
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status,
              'Use own account': own_account,
            'Use flagship version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
        
    return df_master_new


# %%
#list of search methods

er_methods_list = ['using autosearch', 'this Boolean query', 'any of these words', 'all of these words', 'this phrase', 'this case name']
er_method_types = ['auto', 'boolean', 'any', 'all', 'phrase', 'title']


# %%
#Function turning search terms to search results url

def er_search(query= '', 
              method = ''
             ):
    base_url = "http://www.commonlii.org/cgi-bin/sinosrch.cgi?" #+ method

    method_index = er_methods_list.index(method)
    method_type = er_method_types[method_index]

    query_text = query

    params = {'meta' : '/commonlii', 
              'mask_path' : '+uk/cases/EngR+', 
              'method' : method_type,
              'query' : query_text
             }

    response = requests.get(base_url, params=params)
    
    return response.url


# %%
#Define function turning search results url to case_link_pairs to judgments

@st.cache_data
def er_search_results_to_case_link_pairs(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")
    hrefs = soup.find_all('a', href=True)
    case_link_pairs = []

    #number of search results
    docs_found_string = str(soup.find_all('span', {'class' : 'ndocs'})).split('Documents found:')[1].split('<')[0].replace(' ', '')
    docs_found = int(docs_found_string)
    
    #Start counter
    counter = 1
    
    for link in hrefs:
        if ((counter <= judgment_counter_bound) and (' ER ' in str(link)) and ('cases' in str(link))):
#        if ((counter <= judgment_counter_bound) and ('commonlii' in str(link)) and ('cases/EngR' in str(link)) and ('LawCite' not in str(link))):
            case = link.get_text()
            link_direct = link.get('href')
            sub_link = link_direct.replace('.html', '.pdf').split('cases')[1].split('.pdf')[0]
            pdf_link = 'http://www.commonlii.org/uk/cases' + sub_link + '.pdf'
            dict_object = { 'case':case, 'link_direct': pdf_link}
            case_link_pairs.append(dict_object)
            counter = counter + 1
        
    for ending in range(20, docs_found, 20):
        if counter <= min(judgment_counter_bound, docs_found):
            url_next_page = url_search_results + ';offset=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            
            hrefs_next_page = soup_judgment_next_page.find_all('a', href=True)
            for extra_link in hrefs_next_page:
                if ((counter <= judgment_counter_bound) and (' ER ' in str(extra_link)) and ('cases' in str(extra_link))):
#                if ((counter <= judgment_counter_bound) and ('commonlii' in str(extra_link)) and ('cases/EngR' in str(extra_link)) and ('LawCite' not in str(extra_link))):
                    case = extra_link.get_text()
                    extra_link_direct = extra_link.get('href')
                    sub_extra_link = extra_link_direct.replace('.html', '.pdf').split('cases')[1].split('.pdf')[0]
                    pdf_extra_link = 'http://www.commonlii.org/uk/cases' + sub_extra_link + '.pdf'
                    dict_object = { 'case':case, 'link_direct': pdf_extra_link}
                    case_link_pairs.append(dict_object)
                    counter = counter + 1

            pause.seconds(np.random.randint(5, 15))
            
        else:
            break

    #If no need to get rid of repetitions
    #return case_link_pairs
    
    #Get rid of repetitions
    case_link_pairs_no_repeats = []

    for case_link_pair in case_link_pairs:
        if  case_link_pair not in case_link_pairs_no_repeats:
            case_link_pairs_no_repeats.append(case_link_pair)
            
    return case_link_pairs_no_repeats
    


# %%
#Convert case-link pairs to judgment text

@st.cache_data
def er_judgment_text(case_link_pair):
    url = case_link_pair['link_direct']
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

def er_meta_judgment_dict(case_link_pair):
    
    judgment_dict = {'Case name': '',
                     'Medium neutral citation' : '', 
                     'English Reports': '', 
                     'Nominate Reports': '', 
                     'Hyperlink to CommonLII': '', 
                     'Year' : '', 
                     'judgment': ''
                    }

    case_name = case_link_pair['case']
    year = case_link_pair['link_direct'].split('EngR/')[-1][0:4]
    case_num = case_link_pair['link_direct'].split('/')[-1].replace('.pdf', '')
    mnc = '[' + year + ']' + ' EngR ' + case_num

    er_cite = ''
    nr_cite = ''
        
    try:
        case_name = case_link_pair['case'].split('[')[0][:-1]
        nr_cite = case_link_pair['case'].split(';')[1][1:]
        er_cite = case_link_pair['case'].split(';')[2][1:]
    except:
        pass
                
    judgment_dict['Case name'] = case_name
    judgment_dict['Medium neutral citation'] = mnc
    judgment_dict['English Reports'] = er_cite
    judgment_dict['Nominate Reports'] = nr_cite
    judgment_dict['Year'] = year
    judgment_dict['Hyperlink to CommonLII'] = link(case_link_pair['link_direct'])
    judgment_dict['judgment'] = er_judgment_text(case_link_pair)

#    pause.seconds(np.random.randint(5, 15))
    
    #try:
     #   er_judgment_text = str(soup.find_all('content'))
    #except:
      #  er_judgment_text= soup.get_text(strip=True)
        
    return judgment_dict


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from gpt_functions import question_characters_bound


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

role_content_er = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a part of the judgment or metadata, include a reference to that part of the judgment or metadata. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". The "judgment" field of the JSON given to you sometimes contains judgments for multiple cases. If you detect multiple judgments in the "judgment" field, please provide answers only for the specific case identified in the "Case name" field of the JSON given to you.'

system_instruction = role_content_er

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
def er_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    url_search_results = er_search(query= df_master.loc[0, 'Enter search query'], 
                                   method = df_master.loc[0, 'Find (method)']
                                  )
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_link_pairs = er_search_results_to_case_link_pairs(url_search_results, judgments_counter_bound)

    for case_link_pair in case_link_pairs:

        judgment_dict = er_meta_judgment_dict(case_link_pair)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(5, 15))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT

    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    df_updated.pop('judgment')
    
    return df_updated


# %%
def er_search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    url = er_search(query= df_master.loc[0, 'Enter search query'],
                    method= df_master.loc[0, 'Find (method)']
                   )
    return url


# %% [markdown]
# # For vision, ER only

# %%
import pdf2image
from PIL import Image
import math
from math import ceil


# %%
#Import functions
from gpt_functions import get_image_dims, calculate_image_token_cost


# %%
#Convert case-link pairs to judgment text

@st.cache_data
def er_judgment_tokens_b64(case_link_pair):

    output_b64 = {'judgment':[], 'tokens_raw': 0}
    
    url = case_link_pair['link_direct']
    headers = {'User-Agent': 'whatever'}
    r = requests.get(url, headers=headers)
    bytes_data = io.BytesIO(r.content)
    
    images = pdf2image.convert_from_bytes(bytes_data.read(), timeout=30, fmt="jpeg")
    
    for image in images[ : len(images)]:

        output = BytesIO()
        image.save(output, format='JPEG')
        im_data = output.getvalue()
        
        image_data = base64.b64encode(im_data)
        if not isinstance(image_data, str):
            # Python 3, decode from bytes to string
            image_data = image_data.decode()
        data_url = 'data:image/jpg;base64,' + image_data

        #b64 = base64.b64encode(image_raw).decode('utf-8')

        b64_to_attach = data_url
        #b64_to_attach = f"data:image/png;base64,{b64}"

        output_b64['judgment'].append(b64_to_attach)
    
    for image_b64 in output_b64['judgment']:

        output_b64['tokens_raw'] = output_b64['tokens_raw'] + calculate_image_token_cost(image_b64, detail="auto")
    
    return output_b64
    


# %%
#Meta labels and judgment combined

def er_meta_judgment_dict_b64(case_link_pair):
    
    judgment_dict = {'Case name': '',
                     'Medium neutral citation' : '', 
                     'English Reports': '', 
                     'Nominate Reports': '', 
                     'Hyperlink to CommonLII': '', 
                     'Year' : '', 
                     'judgment': '', 
                     'tokens_raw': 0
                    }

    case_name = case_link_pair['case']
    year = case_link_pair['link_direct'].split('EngR/')[-1][0:4]
    case_num = case_link_pair['link_direct'].split('/')[-1].replace('.pdf', '')
    mnc = '[' + year + ']' + ' EngR ' + case_num

    er_cite = ''
    nr_cite = ''
        
    try:
        case_name = case_link_pair['case'].split('[')[0][:-1]
        nr_cite = case_link_pair['case'].split(';')[1][1:]
        er_cite = case_link_pair['case'].split(';')[2][1:]
    except:
        pass
                
    judgment_dict['Case name'] = case_name
    judgment_dict['Medium neutral citation'] = mnc
    judgment_dict['English Reports'] = er_cite
    judgment_dict['Nominate Reports'] = nr_cite
    judgment_dict['Year'] = year
    judgment_dict['Hyperlink to CommonLII'] = link(case_link_pair['link_direct'])
    judgment_dict['judgment'] = er_judgment_tokens_b64(case_link_pair)['judgment']
    judgment_dict['tokens_raw'] = er_judgment_tokens_b64(case_link_pair)['tokens_raw']

#    pause.seconds(np.random.randint(5, 15))
    
    #try:
     #   er_judgment_text = str(soup.find_all('content'))
    #except:
      #  er_judgment_text= soup.get_text(strip=True)
        
    return judgment_dict


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#For gpt-4o vision

@st.cache_data
def er_GPT_b64_json(questions_json, judgment_json, gpt_model, system_instruction):
    #'question_json' variable is a json of questions to GPT

    #file_for_GPT = [{"role": "user", "content": file_prompt(file_triple, gpt_model) + 'you will be given questions to answer in JSON form.'}]

    #Add images to messages to GPT
    image_content_value = [{"type": "text", "text": 'Based on the following images:'}]

    for image_b64 in judgment_json['judgment']:
        image_message_to_attach = {"type": "image_url", "image_url": {"url": image_b64,}}
        image_content_value.append(image_message_to_attach)

    image_content = [{"role": "user", 
                      "content": image_content_value
                     }
                  ]

    #Create metadata content

    metadata_content = [{"role": "user", "content": ''}]

    metadata_json_raw = judgment_json

    for key in ['Hyperlink to CommonLII', 'judgment', 'tokens_raw']:
        try:
            metadata_json_raw.pop(key)
        except:
            print(f'Unable to remove {key} from metadata_json_raw')

    metadata_json = metadata_json_raw

    if 'judgment' not in metadata_json.keys():
        metadata_content = [{"role": "user", "content": 'Based on the following metadata:' + str(metadata_json)}]

    #Create json direction content

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    file_for_GPT = image_content + metadata_content + json_direction
    
    #Create answer format
    
    q_keys = [*questions_json]
    
    answers_json = {}
    
    for q_index in q_keys:
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific page numbers or sections of the judgment.'})
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json) + ' Give responses in the following JSON form: ' + json.dumps(answers_json)}]
    
    #Create messages in one prompt for GPT
    #ER specific intro

    intro_for_GPT = [{"role": "system", "content": system_instruction}]

    messages_for_GPT = intro_for_GPT + file_for_GPT + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}, 
            temperature = 0.2, 
            top_p = 0.2
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        #return [answers_dict, output_tokens, prompt_tokens]

        #Check answers

        if check_questions_answers() > 0:
            
            try:
                redacted_output = GPT_answers_check(answers_dict, gpt_model, answers_check_system_instruction)
        
                redacted_answers_dict = redacted_output[0]
        
                redacted_answers_output_tokens = redacted_output[1]
        
                redacted_answers_prompt_tokens = redacted_output[2]
        
                return [redacted_answers_dict, output_tokens + redacted_answers_output_tokens, prompt_tokens + redacted_answers_prompt_tokens]

                print('Answers checked.')
                
            except Exception as e:
    
                print('Answers check failed.')
    
                print(e)
    
                return [answers_dict, output_tokens, prompt_tokens]

        else:

            print('Answers not checked.')
            
            return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        print('GPT failed to produce answers.')

        for q_index in q_keys:
            answers_json[q_index] = error
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by judgment then question, with input and output tokens given by GPT itself
#For gpt-4o vision

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*

@st.cache_data
def er_engage_GPT_b64_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Length of first 10 pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()

    #Make a copy of questions for making headings later
    unchecked_questions_json = questions_json.copy()

    #Check questions for privacy violation

    if check_questions_answers() > 0:
    
        try:
    
            labels_output = GPT_questions_check(questions_json, gpt_model, questions_check_system_instruction)
    
            labels_output_tokens = labels_output[1]
    
            labels_prompt_tokens = labels_output[2]
        
            questions_json = checked_questions_json(questions_json, labels_output)

            print('Questions checked.')
    
        except Exception as e:
            
            print('Questions check failed.')
            
            print(e)
    
            labels_output_tokens = 0
            
            labels_prompt_tokens = 0

    else:

        print('Questions not checked.')
        
        labels_output_tokens = 0
        
        labels_prompt_tokens = 0
    
    question_keys = [*questions_json]

    for judgment_index in df_individual.index:
        
        judgment_json = df_individual.to_dict('index')[judgment_index]
        
        #Calculate and append number of tokens of judgment, regardless of whether given to GPT
        #judgment_json['tokens_raw'] = num_tokens_from_string(str(judgment_json), "cl100k_base")

        df_individual.loc[judgment_index, f"Tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = judgment_json['tokens_raw']       

        #Indicate whether judgment truncated
        
        df_individual.loc[judgment_index, "judgment truncated (if given to GPT)?"] = ''       
        
        if judgment_json['tokens_raw'] <= tokens_cap(gpt_model):
            
            df_individual.loc[judgment_index, "judgment truncated (if given to GPT)?"] = 'No'
            
        else:
            
            df_individual.loc[judgment_index, "judgment truncated (if given to GPT)?"] = 'Yes'

        #Create columns for respondent's GPT cost, time
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each judgment, gives answers as a string containing a dictionary

        if int(GPT_activation) > 0:
            GPT_judgment_json = er_GPT_b64_json(questions_json, judgment_json, gpt_model, system_instruction) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_judgment_json[0]

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

            judgment_capped_tokens = min(judgment_json['tokens_raw'], tokens_cap(gpt_model))

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(json.dumps(questions_json), "cl100k_base")

            #Calculate metadata tokens

            metadata_tokens = 0
            
            metadata_json_for_counting = judgment_json

            for key in ['Hyperlink to CommonLII', 'judgment', 'tokens_raw']:
                try:
                    metadata_json_for_counting.pop(key)
                except:
                    print(f'Unable to remove {key} from metadata_json_for_counting')        

            if 'judgment' not in metadata_json_for_counting.keys():
                metadata_tokens = metadata_tokens + num_tokens_from_string(str(metadata_json_for_counting), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = system_instruction + 'you will be given questions to answer in JSON form.' + ' Give responses in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers or sections of the judgment.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            input_tokens = judgment_capped_tokens + questions_tokens + metadata_tokens + other_tokens
            
            GPT_judgment_json = [answers_dict, answers_tokens, input_tokens]

        #Create GPT question headings and append answers to individual spreadsheets

        for question_index in question_keys:
            #If not checking questions
            #question_heading = question_index + ': ' + questions_json[question_index]

            #If checking questions
            question_heading = question_index + ': ' + unchecked_questions_json[question_index]

            df_individual.loc[judgment_index, question_heading] = answers_dict[question_index]

        #Calculate GPT costs

        #Calculate GPT costs

        #If check for questions
        GPT_cost = (GPT_judgment_json[1] + labels_output_tokens/len(df_individual))*gpt_output_cost(gpt_model) + (GPT_judgment_json[2] + labels_prompt_tokens/len(df_individual))*gpt_input_cost(gpt_model)

        #If no check for questions
        #GPT_cost = GPT_judgment_json[1]*gpt_output_cost(gpt_model) + GPT_judgment_json[2]*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual
    


# %%
#For gpt-4o vision

@st.cache_data
def er_run_b64(df_master):

    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    url_search_results = er_search(query= df_master.loc[0, 'Enter search query'], 
                                   method = df_master.loc[0, 'Find (method)']
                                  )
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_link_pairs = er_search_results_to_case_link_pairs(url_search_results, judgments_counter_bound)

    for case_link_pair in case_link_pairs:

        judgment_dict = er_meta_judgment_dict_b64(case_link_pair)
        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(5, 15))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT

    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    questions_json = df_master.loc[0, 'questions_json']
            
    #apply GPT_individual to each respondent's judgment spreadsheet

    df_updated = er_engage_GPT_b64_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    #Remove redundant columns

    for column in ['tokens_raw', 'judgment']:
        try:
            df_updated.pop(column)
        except:
            print(f"No {column} column.")

    return df_updated


# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from common_functions import open_page, clear_cache_except_validation_df_master, tips


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

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
    st.session_state.df_master.loc[0, 'Enter search query'] = None
    st.session_state.df_master.loc[0, 'Find (method)'] = 'this Boolean query'

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
if st.session_state.page_from != "pages/ER.py": #Need to add in order to avoid GPT page from showing form of previous page
    
    #Create form
    
    return_button = st.button('RETURN to first page')
    
    st.header(f"You have selected to study :blue[the English Reports].")
    
    #Search terms
    
    #    st.header("Judgment Search Criteria")
    
    st.markdown("""**:green[Please enter your search terms.]** This app will collect (ie scrape) the first 10 judgments returned by your search terms.
""")
    
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments.')

    reset_button = st.button(label='RESET', type = 'primary')

    st.subheader("Your search terms")
    
    st.markdown("""For search tips, please visit [CommonLII](http://www.commonlii.org/form/search1.html?mask=uk/cases/EngR). This section mimics their search function.
""")
    
    method_entry = st.selectbox(label = 'Find', options = er_methods_list, index= er_methods_list.index(st.session_state.df_master.loc[0, 'Find (method)']))
    
    query_entry = st.text_input(label = 'Enter search query', value = st.session_state.df_master.loc[0, 'Enter search query'])
        
    st.markdown("""You can preview the judgments returned by your search terms after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")
    
    preview_button = st.button(label = 'PREVIEW on CommonLII (in a popped up window)', type = 'primary')


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
        
        df_master = er_create_df()
    
        judgments_url = er_search_url(df_master)
    
        open_page(judgments_url)


    # %%
    if keep_button:
    
        all_search_terms = str(query_entry)
            
        if all_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
    
        else:
                                
            df_master = er_create_df()
    
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

        df_master = er_create_df()

        save_input(df_master)

        st.session_state["page_from"] = 'pages/ER.py'
    
        st.switch_page("Home.py")

    # %%
    if reset_button:
        st.session_state.pop('df_master')

        #clear_cache()
        st.rerun()

    # %%
    if next_button:
    
        all_search_terms = str(query_entry)
        
        if all_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
        
        else:
        
            df_master = er_create_df()
    
            save_input(df_master)

            #Check search results
            er_url_to_check = er_search_url(df_master)
            er_html = requests.get(er_url_to_check, headers={'User-Agent': 'whatever'})
            er_soup = BeautifulSoup(er_html.content, "lxml")
            if 'Documents found:   0' in str(er_soup):
                st.error(no_results_msg)
                
            else:
                st.session_state["page_from"] = 'pages/ER.py'
                
                st.switch_page('pages/GPT.py')
