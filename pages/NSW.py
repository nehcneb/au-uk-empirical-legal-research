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
import PyPDF2
import io

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#NSWCaseLaw
from nswcaselaw.search import Search

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
# # CaseLaw NSW functions and parameters

# %%
#Pause between judgment scraping

#scraper_pause = 5

#print(f"The pause between judgment scraping is {scraper_pause} second.\n")

scraper_pause_mean = int((15-5)/2)

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")



# %%
#Lowerbound on length of judgment text to proccess, in tokens

judgment_text_lower_bound = 1000

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")


# %%
#Auxiliary lists
search_criteria = ['Free text', 'Case name', 'Before', 'Catchwords', 'Party names', 'Medium neutral citation', 'Decision date from', 'Decision date to', 'File number', 'Legislation cited', 'Cases cited']
meta_labels_droppable = ["Catchwords", "Before", "Decision date(s)", "Hearing date(s)", "Date(s) of order",  "Jurisdiction", "Decision", "Legislation cited", "Cases cited", "Texts cited", "Category", "Parties", "File number", "Representation", "Decision under appeal"]


# %%
#List of nsw courts

#For showing as menu
nsw_courts =["Court of Appeal", 
             "Court of Criminal Appeal", 
             "Supreme Court", 
             'Land and Environment Court (Judges)', 
             'Land and Environment Court (Commissioners)', 
             'District Court', 
             'Local Court',
             "Children's Court", 
             'Compensation Court', 
             'Drug Court', 
             'Industrial Court',
             'Industrial Relations Commission (Judges)', 
             'Industrial Relations Commission (Commissioners)'
            ] #, "All of the above Courts"]

#For positioning
nsw_courts_positioning = ["Placeholder", "Children's Court",
 'Compensation Court',
 'Court of Appeal',
 'Court of Criminal Appeal',
 'District Court',
 'Drug Court',
 'Industrial Court',
 'Industrial Relations Commission (Commissioners)',
 'Industrial Relations Commission (Judges)',
 'Land and Environment Court (Commissioners)',
 'Land and Environment Court (Judges)',
 'Local Court',
 'Supreme Court']

#Default courts
nsw_default_courts = ["Court of Appeal", "Court of Criminal Appeal", "Supreme Court"]

# %%
#List of NSW tribunals

nsw_tribunals = ['Administrative Decisions Tribunal (Appeal Panel)',
 'Administrative Decisions Tribunal (Divisions)',
 'Civil and Administrative Tribunal (Administrative and Equal Opportunity Division)',
 'Civil and Administrative Tribunal (Appeal Panel)',
 'Civil and Administrative Tribunal (Consumer and Commercial Division)',
 'Civil and Administrative Tribunal (Enforcement)',
 'Civil and Administrative Tribunal (Guardianship Division)',
 'Civil and Administrative Tribunal (Occupational Division)',
 'Dust Diseases Tribunal',
 'Equal Opportunity Tribunal',
 'Fair Trading Tribunal',
 'Legal Services Tribunal',
 'Medical Tribunal',
 'Transport Appeal Boards']

nsw_tribunals_positioning = ['Placeholder',
 'Administrative Decisions Tribunal (Appeal Panel)',
 'Administrative Decisions Tribunal (Divisions)',
 'Civil and Administrative Tribunal (Administrative and Equal Opportunity Division)',
 'Civil and Administrative Tribunal (Appeal Panel)',
 'Civil and Administrative Tribunal (Consumer and Commercial Division)',
 'Civil and Administrative Tribunal (Enforcement)',
 'Civil and Administrative Tribunal (Guardianship Division)',
 'Civil and Administrative Tribunal (Occupational Division)',
 'Dust Diseases Tribunal',
 'Equal Opportunity Tribunal',
 'Fair Trading Tribunal',
 'Legal Services Tribunal',
 'Medical Tribunal',
 'Transport Appeal Boards']


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
        #This is the user's entered API key whether valid or invalid, not necessarily the one used to produce outputs
    except:
        print('API key not entered')

    #Own account status
    own_account = st.session_state.own_account
    
    #Judgment counter bound
    judgments_counter_bound = st.session_state.judgments_counter_bound

    #GPT enhancement
    gpt_enhancement = st.session_state.gpt_enhancement_entry
    
    #NSW court choices

    courts_list = courts_entry

    courts = ', '.join(courts_list)
    
    #NSW tribunals choices
    
    tribunals_list = tribunals_entry

    tribunals = ', '.join(tribunals_list)

    #Search terms
    
    body = body_entry
    title = title_entry
    before = before_entry
    catchwords = catchwords_entry
    party = party_entry
    mnc = mnc_entry

    startDate = ''

    if startDate_entry != 'None':

        try:

            startDate = startDate_entry.strftime('%d/%m/%Y')

        except:
            pass
        
    endDate = ''

    if endDate_entry != 'None':
        
        try:
            endDate = endDate_entry.strftime('%d/%m/%Y')
            
        except:
            pass
    
    fileNumber = fileNumber_entry
    legislationCited = legislationCited_entry
    casesCited = casesCited_entry

    #metadata choice

    meta_data_choice = meta_data_entry
    
    #headnotes choice    
#    headnotes_list = headnotes_entry
#    headnotes = ', '.join(headnotes_list)

    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry

    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry[0: 1000]
    
    except:
        print('GPT questions not entered.')

    #Create row
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
           'Courts': courts,
           'Tribunals': tribunals, 
           'Free text': body, 
           'Case name': title, 
           'Before' : before, 
           'Catchwords' : catchwords, 
           'Party names' : party, 
           'Medium neutral citation': mnc, 
           'Decision date from': startDate, 
           'Decision date to': endDate, 
           'File number': fileNumber, 
           'Legislation cited': legislationCited,
           'Cases cited': casesCited, 
#           'Information to Collect from Judgment Headnotes': headnotes,
            'Metadata inclusion' : meta_data_choice,
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
#Create function to convert the string of chosen courts to a list; 13 = NSWSC, 3 = NSWCA, 4 = NSWCCA
#For more, see https://github.com/Sydney-Informatics-Hub/nswcaselaw/blob/main/src/nswcaselaw/constants.py

def court_choice(x):
    individual_choice = []

    if len(x) < 5:
        pass #If want to select no court absent any choice
        #individual_choice = [3, 4, 13] #If want to select NSWSC, CA and CCA absent any choice
        #for j in range(1, len(nsw_courts_positioning)):
            #individual_choice.append(j) #If want to select all courts absent any choice
    else:
        y = x.split(', ')
        for i in y:
            individual_choice.append(nsw_courts_positioning.index(i))            
    
    return individual_choice

def tribunal_choice(x):
    individual_choice = []

    if len(x) < 5:
        pass #If want to select no tribunal absent any choice
        #for j in range(1, len(nsw_tribunals_positioning)):
            #individual_choice.append(j) #If want to select all tribunals absent any choice
    else:
        y = x.split(', ')
        for i in y:
            individual_choice.append(nsw_tribunals_positioning.index(i))            
    
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

#Tidy up dates
def date(x):
    if len(str(x)) >0:
        return str(x).split()[0]
    else:
        return str(x)

# Headnotes fields
headnotes_fields = ["Free text", "Case name", "Before", "Decision date(s)", "Catchwords", "Hearing date(s)", "Date(s) of order",  "Jurisdiction", "Decision", "Legislation cited", "Cases cited", "Texts cited", "Category", "Parties", "Medium neutral citation", "Decision date from", "Decision date to", "File number", "Representation", "Decision under appeal"]
headnotes_keys = ["body", "title", "before", "decisionDate", "catchwords", "hearingDates", "dateOfOrders", "jurisdiction", "decision", "legislationCited", "casesCited", "textsCited", "category", "parties", "mnc", "startDate", "endDate", "fileNumber", "representation", "decisionUnderAppeal"]

#Functions for tidying up headings of columns

#Tidy up hyperlink
def link(x):
    link='https://www.caselaw.nsw.gov.au'+ str(x)
    value = '=HYPERLINK("' + link + '")'
    return value

#Tidy up medium neutral citation

def mnc_cleaner(x):
    if '[' in x:
        x_clean=str(x).split("[")
        y = '[' + x_clean[1]
        return y
    else:
        return x



# %%
#Define function for short judgments, which checks if judgment is in PDF
#returns a list of judgment type and judgment text

def short_judgment(html_link):
    page_html = requests.get(html_link)
    soup_html = BeautifulSoup(page_html.content, "lxml")

    judgment_type = ''

    #Check if judgment contains PDF link
    PDF_raw_link = soup_html.find('a', text='See Attachment (PDF)')
    
    if str(PDF_raw_link).lower() != 'none':
        PDF_link = 'https://www.caselaw.nsw.gov.au' + PDF_raw_link.get('href')    
        headers = {'User-Agent': 'whatever'}
        r = requests.get(PDF_link, headers=headers)
        remote_file_bytes = io.BytesIO(r.content)
        pdfdoc_remote = PyPDF2.PdfReader(remote_file_bytes)
        text_list = []
        
        for page in pdfdoc_remote.pages:
            text_list.append(page.extract_text())

        judgment_type = 'pdf'
        
        return [judgment_type, str(text_list)]

    #Return html text if no PDF
    else:
        judgment_text = soup_html.get_text(separator="\n", strip=True)
        judgment_type = 'html'

        return [judgment_type, judgment_text]


# %%
def search_url(df_master):
    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Courts'] = df_master['Courts'].apply(court_choice)
    df_master['Tribunals'] = df_master['Tribunals'].apply(tribunal_choice)

    #df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    #df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Combining catchwords into new column
    
    search_dict = {'body': df_master.loc[0, 'Free text']}
    search_dict.update({'title': df_master.loc[0, 'Case name']})
    search_dict.update({'before': df_master.loc[0, 'Before']})
    search_dict.update({'catchwords': df_master.loc[0, 'Catchwords']})
    search_dict.update({'party': df_master.loc[0, 'Party names']})
    search_dict.update({'mnc': df_master.loc[0, 'Medium neutral citation']})
    search_dict.update({'startDate': df_master.loc[0, 'Decision date from']})
    search_dict.update({'endDate': df_master.loc[0, 'Decision date to']})
    search_dict.update({'fileNumber': df_master.loc[0, 'File number']})
    search_dict.update({'legislationCited': df_master.loc[0, 'Legislation cited']})
    search_dict.update({'casesCited': df_master.loc[0, 'Cases cited']})
    df_master.loc[0, 'SearchCriteria']=[search_dict]

    #Conduct search
    
    query = Search(courts=df_master.loc[0, 'Courts'], 
                   tribunals=df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, "SearchCriteria"]['body'], 
                   title = df_master.loc[0, "SearchCriteria"]['title'], 
                   before = df_master.loc[0, "SearchCriteria"]['before'], 
                   catchwords = df_master.loc[0, "SearchCriteria"]['catchwords'], 
                   party = df_master.loc[0, "SearchCriteria"]['party'], 
                   mnc = df_master.loc[0, "SearchCriteria"]['mnc'], 
                   startDate = date(df_master.loc[0, "SearchCriteria"]['startDate']), 
                   endDate = date(df_master.loc[0, "SearchCriteria"]['endDate']),
                   fileNumber = df_master.loc[0, "SearchCriteria"]['fileNumber'], 
                   legislationCited  = df_master.loc[0, "SearchCriteria"]['legislationCited'], 
                   casesCited = df_master.loc[0, "SearchCriteria"]['legislationCited'],
                   pause = np.random.randint(5, 15)
                  )
    return query.url


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
#encoding = tiktoken.encoding_for_model(gpt_model)

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    #Tokens estimate function
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    
    return num_tokens

#Define judgment input function for JSON approach

#characters_limit_half = tokens_cap(gpt_model)*4/2

def judgment_prompt_json(judgment_json, gpt_model):

    judgment_to_string = judgment_json["judgment"]
        
    judgment_content = 'Based on the metadata and judgment in the following JSON: """'+ str(judgment_json) + '"""'

    if len(judgment_content) <= tokens_cap(gpt_model):
        
        return judgment_content

    else:
        
        meta_data_len=len(judgment_content) - len(judgment_to_string)
        
        judgment_char_capped = int((tokens_cap(gpt_model) - meta_data_len)*4)
        
        judgment_string_trimmed = judgment_to_string[ : int(judgment_char_capped/2)] + judgment_to_string[-int(judgment_char_capped/2): ]

        judgment_json["judgment"] = judgment_string_trimmed        
        
        judgment_content_capped = 'Based on the metadata and judgment in the following JSON:  """'+ str(judgment_json) + '"""'
        
        return judgment_content_capped



# %%
#Define system role content for GPT
role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a specific paragraph in the judgment, provide the paragraph number as part of your answer. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found".'

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
     
#    df_master['Information to Collect from Judgment Headnotes'] = df_master['Information to Collect from Judgment Headnotes'].apply(headnotes_choice)
    df_master['Courts'] = df_master['Courts'].apply(court_choice)
    df_master['Tribunals'] = df_master['Tribunals'].apply(tribunal_choice)
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Do search

    search_dict = {'body': df_master.loc[0, 'Free text']}
    search_dict.update({'title': df_master.loc[0, 'Case name']})
    search_dict.update({'before': df_master.loc[0, 'Before']})
    search_dict.update({'catchwords': df_master.loc[0, 'Catchwords']})
    search_dict.update({'party': df_master.loc[0, 'Party names']})
    search_dict.update({'mnc': df_master.loc[0, 'Medium neutral citation']})
    search_dict.update({'startDate': df_master.loc[0, 'Decision date from']})
    search_dict.update({'endDate': df_master.loc[0, 'Decision date to']})
    search_dict.update({'fileNumber': df_master.loc[0, 'File number']})
    search_dict.update({'legislationCited': df_master.loc[0, 'Legislation cited']})
    search_dict.update({'casesCited': df_master.loc[0, 'Cases cited']})
    df_master.loc[0, 'SearchCriteria']=[search_dict]

    #Conduct search
    
    query = Search(courts=df_master.loc[0, 'Courts'], 
                   tribunals=df_master.loc[0, 'Tribunals'], 
                   body = df_master.loc[0, "SearchCriteria"]['body'], 
                   title = df_master.loc[0, "SearchCriteria"]['title'], 
                   before = df_master.loc[0, "SearchCriteria"]['before'], 
                   catchwords = df_master.loc[0, "SearchCriteria"]['catchwords'], 
                   party = df_master.loc[0, "SearchCriteria"]['party'], 
                   mnc = df_master.loc[0, "SearchCriteria"]['mnc'], 
                   startDate = date(df_master.loc[0, "SearchCriteria"]['startDate']), 
                   endDate = date(df_master.loc[0, "SearchCriteria"]['endDate']),
                   fileNumber = df_master.loc[0, "SearchCriteria"]['fileNumber'], 
                   legislationCited  = df_master.loc[0, "SearchCriteria"]['legislationCited'], 
                   casesCited = df_master.loc[0, "SearchCriteria"]['legislationCited'],
                   pause = np.random.randint(5, 15)
                  )

    #Create judgments file
    judgments_file = []

    #Counter to limit search results to append
    counter = 0

    #Go through search results
    
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
    
    for decision in query.results():
        if counter < judgments_counter_bound:
    
            decision.fetch()
            decision_v=decision.values
                                    
            #add search results to json
            judgments_file.append(decision_v)
            counter +=1
    
            pause.seconds(np.random.randint(5, 15))
            
        else:
            break

    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Check length of judgment text, replace with raw html if smaller than lower boound

    for judgment_index in df_individual.index:

        #Checking if judgment text has been scrapped
        try:
            judgment_raw_text = str(df_individual.loc[judgment_index, "judgment"])
            
        except Exception as e:
            
            df_individual.loc[judgment_index, "judgment"] = ['Error. Judgment text not scrapped.']
            judgment_raw_text = str(df_individual.loc[judgment_index, "judgment"])
            print(f'{df_individual.loc[judgment_index, "title"]}: judgment text scraping error.')
            print(e)
            
        if num_tokens_from_string(judgment_raw_text, "cl100k_base") < judgment_text_lower_bound:
            html_link = 'https://www.caselaw.nsw.gov.au'+ df_individual.loc[judgment_index, "uri"]

#            page_html = requests.get(html_link)
#            soup_html = BeautifulSoup(page_html.content, "lxml")
#            judgment_text = soup_html.get_text(separator="\n", strip=True)

            judgment_type_text = short_judgment(html_link)

            #attach judgment text
            df_individual.loc[judgment_index, "judgment"] = judgment_type_text[1]

            #identify pdf judgment

            if judgment_type_text[0] == 'pdf':
                try:
                    mnc_raw = df_individual.loc[judgment_index, "mnc"]
                    df_individual.loc[judgment_index, "title"] =  mnc_raw.split(' [')[0]
                    df_individual.loc[judgment_index, "mnc"] = '[' + mnc_raw.split(' [')[1]
                    df_individual.loc[judgment_index, "catchwords"] = 'Not working properly because judgment in PDF. References to paragraphs likely to pages or wrong.'
                except:
                    pass
            
            pause.seconds(np.random.randint(5, 15))

    #Rename column titles
    
    try:
        df_individual['Hyperlink to NSW Caselaw'] = df_individual['uri'].apply(link)
        df_individual.pop('uri')
    except:
        pass
    
    for col_name in headnotes_keys:
        if col_name in df_individual.columns:
            col_index = headnotes_keys.index(col_name)
            new_col_name = headnotes_fields[col_index]
            df_individual[new_col_name] = df_individual[col_name]
            df_individual.pop(col_name)
    
    #Instruct GPT
    
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
    
    return df_updated


# %%
#function to tidy up output

def tidying_up(df_master, df_individual):

    #Reorganise columns

    old_columns = list(df_individual.columns)
    
    for i in ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw']:
        if i in old_columns:
            old_columns.remove(i)
    
    new_columns = ['Case name', 'Medium neutral citation', 'Hyperlink to NSW Caselaw'] + old_columns
    
    df_individual = df_individual.reindex(columns=new_columns)

    #Drop metadata if not wanted
    
    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in meta_labels_droppable:
            try:
                df_individual.pop(meta_label)
            except:
                pass
    
    #Remove judgment and uri columns
    try:
        df_individual.pop("judgment")
        df_individual.pop("uri")
        
    except:
        pass
        
    #Check case name, medium neutral citation 

    for k in df_individual.index:
        if ' [' in df_individual.loc[k, "Case name"]:
            case_name_proper = df_individual.loc[k, "Case name"].split(' [')[0]
            mnc_proper = '[' + df_individual.loc[k, "Case name"].split(' [')[-1]
            df_individual.loc[k, "Case name"] = case_name_proper
            df_individual.loc[k, "Medium neutral citation"] = mnc_proper
        elif ' [' in df_individual.loc[k, "Medium neutral citation"]:
            case_name_proper = df_individual.loc[k, "Medium neutral citation"].split(' [')[0]
            mnc_proper = '[' + df_individual.loc[k, "Medium neutral citation"].split(' [')[-1]
            df_individual.loc[k, "Case name"] = case_name_proper
            df_individual.loc[k, "Medium neutral citation"] = mnc_proper
    
    return df_individual


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

if 'default_courts' not in st.session_state:
    st.session_state['default_courts'] = []

if 'default_tribunals' not in st.session_state:
    st.session_state['default_tribunals'] = []

if 'gpt_enhancement_entry' not in st.session_state:
    st.session_state['gpt_enhancement_entry'] = False

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if "df_individual_output" not in st.session_state:
    st.session_state["df_individual_output"] = []

if "df_master" not in st.session_state:
    st.session_state["df_master"] = []

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

st.header("You have selected to study :blue[judgments of the New South Wales courts and tribunals].")

#Search terms

st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.

For search tips, please visit NSW Caselaw at https://www.caselaw.nsw.gov.au/search/advanced. This section mimics their Advanced Search function.
""")
st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to cover more judgments.')

st.subheader("NSW courts and tribunals to cover")

default_on_courts = st.checkbox('Prefill the Court of Appeal, the Court of Criminal Appeal, and the Supreme Court')

if default_on_courts:

    st.session_state.default_courts = nsw_default_courts

else:
    st.session_state.default_courts = []

courts_entry = st.multiselect(label = 'Select or type in the courts to cover', options = nsw_courts, default = st.session_state.default_courts)

tribunals_entry = st.multiselect(label = 'Select or type in the tribunals to cover', options = nsw_tribunals, default = st.session_state.default_tribunals)

#st.caption(f"All courts and tribunals listed in these menus will be covered if left blank.")

st.subheader("Your search terms")

catchwords_entry = st.text_input("Catchwords")

body_entry = st.text_input("Free text (searches the entire judgment)") 

title_entry = st.text_input("Case name")

before_entry = st.text_input("Before")

st.caption("Name of judge, commissioner, magistrate, member, registrar or assessor")

party_entry = st.text_input("Party names")

mnc_entry = st.text_input("Medium neutral citation")

st.caption("Must include square brackets eg [2022] NSWSC 922")

startDate_entry = st.date_input("Decision date from (01/01/1999 the earliest)", value = None, format="DD/MM/YYYY")

st.caption("Pre-1999 decisions are usually not available at NSW Caselaw and will unlikely to be collected (see https://www.caselaw.nsw.gov.au/about).")

endDate_entry = st.date_input("Decision date to", value = None,  format="DD/MM/YYYY")

fileNumber_entry = st.text_input("File number")

legislationCited_entry = st.text_input("Legislation cited")

casesCited_entry = st.text_input("Cases cited")

st.markdown("""You can preview the judgments returned by your search terms on NSW Caselaw after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")

preview_button = st.button('PREVIEW on NSW Caselaw (in a popped up window)')

#    headnotes_entry = st.multiselect("Please select", headnotes_choices)

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

st.caption("Use of GPT is costly and funded by a grant. For the model used by default, Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per judgment. The exact cost for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced (as elaborated at https://openai.com/pricing for model gpt-3.5-turbo-0125). You will be given ex-post cost estimates.")

st.subheader("Enter your questions for each judgment")

st.markdown("""Please enter one question **per line or per paragraph**. GPT will answer your questions for **each** judgment based only on information from **that** judgment. """)

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

#if st.session_state.gpt_model == "gpt-4-turbo":
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

if ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output) > 0)):
    
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

    all_search_terms = str(catchwords_entry) + str(body_entry) + str(title_entry) + str(before_entry) + str(party_entry) + str(mnc_entry) + str(startDate_entry) + str(endDate_entry) + str(fileNumber_entry) + str(legislationCited_entry) + str(casesCited_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    elif (len(courts_entry) == 0) and (len(tribunals_entry) == 0):
        st.write('Please select at least one court or tribunal to cover.')

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

            #Create spreadsheet of responses
            df_master = create_df()
            
            #Activate user's own key or mine
            if st.session_state.own_account == True:
                
                API_key = df_master.loc[0, 'Your GPT API key']

            else:
                API_key = st.secrets["openai"]["gpt_api_key"]
                
            #Produce results
            df_individual = run(df_master)

            #Check if judgments found
            if len(df_individual) > 0:
        
                df_individual_output = tidying_up(df_master, df_individual)

                #Keep results in session state
                st.session_state["df_individual_output"] = df_individual_output#.astype(str)
        
                st.session_state["df_master"] = df_master

                #Change session states
                st.session_state['need_resetting'] = 1
                
                st.session_state["page_from"] = 'pages/NSW.py'
        
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
                #conn.update(worksheet="NSW", data=df_to_update, )

    
            else:
                st.error('Your search terms may not return any judgments. Please press the PREVIEW button above to double-check.')
            


# %%
if keep_button:

    #Check whether search terms entered

    all_search_terms = str(catchwords_entry) + str(body_entry) + str(title_entry) + str(before_entry) + str(party_entry) + str(mnc_entry) + str(startDate_entry) + str(endDate_entry) + str(fileNumber_entry) + str(legislationCited_entry) + str(casesCited_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif (len(courts_entry) == 0) and (len(tribunals_entry) == 0):
        st.write('Please select at least one court or tribunal to cover.')

    elif ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output)>0)):
        st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')

        if 'need_resetting' not in st.session_state:
            
            st.session_state['need_resetting'] = 1
            
    else:
        
        df_master = create_df()

        #Pop unnecessary columns
    
        df_master.pop("Your GPT API key")
    
        df_master.pop("Processed")

        #Create outputs
    
        responses_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'
    
        #Buttons for downloading responses
    
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
