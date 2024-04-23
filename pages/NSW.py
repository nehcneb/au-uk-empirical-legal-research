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
import requests
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


# %%
#today
day = datetime.now().strftime("%-d")
month = datetime.now().strftime("%B")
year = datetime.now().strftime("%Y")
today = day + ' ' + month + ' ' + year
today_in_nums = str(datetime.now())[0:10]
today_month = day + ' ' + month
today_words = datetime.now().strftime('%A')

# %%
# Generate placeholder list of errors
errors_list = set()


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer')

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter (NSW)",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %% [markdown]
# # CaseLaw NSW functions and parameters

# %%
#Auxiliary lists

nsw_courts =["Court of Appeal", "Court of Criminal Appeal", "Supreme Court"] #, "All of the above Courts"]
headnotes_choices = ["Catchwords", "Before", "Decision date(s)", "Hearing date(s)", "Date(s) of order",  "Jurisdiction", "Decision", "Legislation cited", "Cases cited", "Texts cited", "Category", "Parties", "File number", "Representation", "Decision under appeal", "All of the above"]
search_criteria = ['Free text', 'Case name', 'Before', 'Catchwords', 'Party names', 'Medium neutral citation', 'Decision date from', 'Decision date to', 'File number', 'Legislation cited', 'Cases cited']
meta_labels_droppable = ["Catchwords", "Before", "Decision date(s)", "Hearing date(s)", "Date(s) of order",  "Jurisdiction", "Decision", "Legislation cited", "Cases cited", "Texts cited", "Category", "Parties", "File number", "Representation", "Decision under appeal"]

def search_terms_str(df):

    output = ''
    
    search_terms = df[search_criteria]

    for i in search_terms.loc[0]:
        output = output + str(i)

    return output



# %%
#function to create dataframe
def create_df():

    #submission time
    timestamp = datetime.now()

    #Personal info entries
    
    name = name_entry
    email = email_entry
    gpt_api_key = gpt_api_key_entry

    #NSW court choices
    
    courts_list = courts_entry
    courts = ', '.join(courts_list)
    
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

    #Judgment counter bound
    
    judgments_counter_bound_ticked = judgments_counter_bound_entry
    if int(judgments_counter_bound_ticked) > 0:
        judgments_counter_bound = 10
    else:
        judgments_counter_bound = 10000

    #metadata choice

    meta_data_choice = meta_data_entry
    
    #headnotes choice    
#    headnotes_list = headnotes_entry
#    headnotes = ', '.join(headnotes_list)


    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
    gpt_questions = gpt_questions_entry[0: 1000]

    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
           'New South Wales Courts to Cover': courts, 
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
           'Enter your question(s) for GPT': gpt_questions, 
            'Tick to use GPT': gpt_activation_status 
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
    
#    df_master_new.to_json(current_dir + '/df_master.json', orient = 'split', compression = 'infer')
#    df_master_new.to_excel(current_dir + '/df_master.xlsx', index=False)

#    if len(df_master_new) > 0:
        
    return df_master_new

#    else:
#        return 'Error: spreadsheet of reponses NOT generated.' 


# %%
#Define format functions for headnotes choice, courts choice, and GPT questions

#Create list of all headnotes choices
headnotes_choices_string = str(headnotes_choices)

#Remove 'All of the above' from list of all headnotes choices
#headnotes_choices.remove('All of the above')

#Create function to convert the string of chosen headnotes choices to a list
def headnotes_choice(x):
    y = x.split(', ')
    individual_choices = []
 
    if 'All of the above' in x:
        return headnotes_choices

    else:
        for i in y:
            if i == 'All of the above':
                individual_choices.append(i)
        return individual_choices

#Create list of all court choices in NSWCaseLaw Scraper notation

#NSW_courts_string = 'Court of Appeal, Court of Criminal Appeal, Supreme Court'
#NSW_courts_string = 'Court of Appeal, Court of Criminal Appeal, Supreme Court, All of the above Courts'
#nsw_courts = NSW_courts_string.split(', ')

#Remove 'All of the above' from list of all court choices
#nsw_courts.remove('All of the above Courts')

#Create function to convert the string of chosen courts to a list; 13 = NSWSC, 3 = NSWCA, 4 = NSWCCA
#For more, see https://github.com/Sydney-Informatics-Hub/nswcaselaw/blob/main/src/nswcaselaw/constants.py

def court_choice(x):
    individual_choice = []
    if len(x) < 5:
        individual_choice = [3, 4, 13]
    else:
        y = x.split(', ')
        for i in y:
            if i == 'Court of Appeal':
                individual_choice.append(3)
            if i == 'Court of Criminal Appeal':
                individual_choice.append(4)
            if i == 'Supreme Court':
                individual_choice.append(13)           
    
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


# %% [markdown]
# # GPT functions and parameters

# %%
#Module and costs

GPT_model = "gpt-3.5-turbo-0125"

GPT_input_cost = 1/1000*0.0005 
GPT_output_cost = 1/1000*0.0015

#Upperbound on number of engagements with GPT

GPT_use_bound = 3

print(f"\nPrior number of GPT uses is capped at {GPT_use_bound} times.")

#Upperbound on the length of questions for GPT

answers_characters_bound = 1000

print(f"\nQuestions for GPT are capped at {answers_characters_bound} characters.")

#Upperbound on number of judgments to scrape

judgments_counter_bound = 10

print(f"\nNumber of judgments to scrape per request is capped at {judgments_counter_bound}.")

#Pause between judgment scraping

scraper_pause = 5

print(f"\nThe pause between judgment scraping is {scraper_pause} second.")

#Lowerbound on length of judgment text to proccess, in tokens

judgment_text_lower_bound = 1000

print(f"\nThe lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.")




# %%
#Define function to determine eligibility for GPT use

#Define a list of privileged email addresses with unlimited GPT uses

privileged_emails = st.secrets["secrets"]["privileged_emails"].replace(' ', '').split(',')

def prior_GPT_uses(email_address, df_online):
    # df_online variable should be the online df_online
    prior_use_counter = 0
    for i in df_online.index:
        if ((df_online.loc[i, "Your email address"] == email_address) 
            and (int(df_online.loc[i, "Tick to use GPT"]) > 0) 
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
encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
#Tokens estimate function
def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

#Define judgment input function for JSON approach

#Token limit covering both GTP input and GPT output is 16385, each token is about 4 characters
tokens_cap = int(16385 - 1500)
#characters_limit_half = tokens_cap*4/2

def judgment_prompt_json(judgment_json):

#    if type(judgment_json["judgment"]) == list:
#        judgment_to_string = " \n\n ".join(judgment_json["judgment"])
#    else:
    judgment_to_string = judgment_json["judgment"]
    
#    judgment_json["judgment"] = judgment_to_string.replace("\\n", "\n")
    
    judgment_content = 'Based on the metadata and judgment in the following JSON: """' + str(judgment_json) + '""",'

    if len(judgment_content) <= tokens_cap:
        
        return judgment_content

    else:
        
        meta_data_len=len(judgment_content) - len(judgment_to_string)
        
        judgment_char_capped = int((tokens_cap - meta_data_len)*4)
        
        judgment_string_trimmed = judgment_to_string[ : int(judgment_char_capped/2)] + judgment_to_string[-int(judgment_char_capped/2): ]

        judgment_json["judgment"] = judgment_string_trimmed        
        
        judgment_content_capped = 'Based on the metadata and judgment in the following JSON: """' + str(judgment_json) + ','
        
        return judgment_content_capped



# %%
#Define system role content for GPT
role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a specific paragraph in the judgment, provide the paragraph number as part of your answer. If you cannot answer any of the questions based on the judgment or metadata, do not make up information, but instead write "answer not found".'

intro_for_GPT = [{"role": "system", "content": role_content}]


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#IN USE

def GPT_json_tokens(questions_json, judgment_json, API_key):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   

    
    judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json) + 'you will be given questions to answer in JSON form.'}]
        
    #Create answer format
    
    q_keys = [*questions_json]
    
    answers_json = {}
    
    for q_index in q_keys:
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific paragraph numbers in the judgment or specific sections in the metadata.'})
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": str(questions_json).replace("\'", '"') + ' Give responses in the following JSON form: ' + str(answers_json).replace("\'", '"')}]
    
    #Create messages in one prompt for GPT
    messages_for_GPT = intro_for_GPT + judgment_for_GPT + question_for_GPT
    
#   return messages_for_GPT

            
    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=GPT_model,
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
def engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, API_key):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # "Judgment length in tokens (up to 15635 given to GPT)"
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
        df_individual.loc[judgment_index, "Judgment length in tokens (up to 15635 given to GPT)"] = judgment_tokens       

        #Indicate whether judgment truncated
        
        df_individual.loc[judgment_index, "Judgment truncated (if given to GPT)?"] = ''       
        
        if judgment_tokens <= tokens_cap:
            
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
            GPT_output_list = GPT_json_tokens(questions_json, judgment_json, API_key) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_output_list[0]
        
        else:
            answers_dict = {}    
            for q_index in question_keys:
                #Increases judgment index by 2 to ensure consistency with Excel spreadsheet
                answer = 'Placeholder answer for ' + ' judgment ' + str(int(judgment_index) + 2) + ' ' + str(q_index)
                answers_dict.update({q_index: answer})
            
            #Own calculation of GPT costs for Placeholder answer fors

            #Calculate capped judgment tokens

            judgment_capped_tokens = num_tokens_from_string(judgment_prompt_json(judgment_json), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(str(questions_json), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = role_content + 'you will be given questions to answer in JSON form.' + ' Give responses in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific paragraph numbers in the judgment or specific sections in the metadata.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            input_tokens = judgment_capped_tokens + questions_tokens + other_tokens
            
            GPT_output_list = [answers_dict, answers_tokens, input_tokens]

        #Create GPT question headings and append answers to individual spreadsheets

        for question_index in question_keys:
            question_heading = question_index + ': ' + questions_json[question_index]
            df_individual.loc[judgment_index, question_heading] = answers_dict[question_index]

        #Calculate and append GPT finish time and time difference to individual df
        GPT_finish_time = datetime.now()
        
        GPT_time_difference = GPT_finish_time - GPT_start_time

        df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()

        #Calculate GPT costs

        GPT_cost = GPT_output_list[1]*GPT_output_cost + GPT_output_list[2]*GPT_input_cost

        #Calculate and append GPT cost to individual df
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %%
#Obtain parameters

def run(df_master):
    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
#    df_master['Information to Collect from Judgment Headnotes'] = df_master['Information to Collect from Judgment Headnotes'].apply(headnotes_choice)
    df_master['New South Wales Courts to Cover'] = df_master['New South Wales Courts to Cover'].apply(court_choice)
    df_master['Enter your question(s) for GPT'] = df_master['Enter your question(s) for GPT'][0: answers_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your question(s) for GPT'].apply(GPT_label_dict)
    
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
    
    #Do search
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    query = Search(courts=df_master.loc[0, 'New South Wales Courts to Cover'], 
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
                   pause = 0
                  )
    
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
    
            pause.seconds(scraper_pause)
            
        else:
            break

    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Check length of judgment text, replace with raw html if smaller than lower boound

    for judgment_index in df_individual.index:
        judgment_raw_text = str(df_individual.loc[judgment_index, "judgment"])
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
            
            pause.seconds(scraper_pause)

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
    
    #GPT model and costs

    API_key = df_master.loc[0, 'Your GPT API key'] 
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Tick to use GPT'])
    
    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, API_key)
    
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


# %%
def search_url(df_master):
    df_master = df_master.fillna('')
    
    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
#    df_master['Information to Collect from Judgment Headnotes'] = df_master['Information to Collect from Judgment Headnotes'].apply(headnotes_choice)
    df_master['New South Wales Courts to Cover'] = df_master['New South Wales Courts to Cover'].apply(court_choice)
    #df_master['Enter your question(s) for GPT'] = df_master['Enter your question(s) for GPT'][0: answers_characters_bound].apply(split_by_line)
    #df_master['questions_json'] = df_master['Enter your question(s) for GPT'].apply(GPT_label_dict)
    
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
    
    query = Search(courts=df_master.loc[0, 'New South Wales Courts to Cover'], 
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
                   pause = scraper_pause
                  )
    return query.url


# %% [markdown]
# # Streamlit form, functions and parameters

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
#Create form

with st.form("GPT_input_form") as df_responses:
    return_button = st.form_submit_button('RETURN to previous page')
    
    st.header("You have selected to study :blue[judgments of select New South Wales courts].")

    #Search terms

    st.markdown("""**Please enter your search terms.** This program will collect (ie scrape) the first 10 judgments returned by your search terms.

For search tips, please visit NSW Caselaw at https://www.caselaw.nsw.gov.au/search/advanced. This section mimics their Advanced Search function.
""")
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to Cover more judgments, courts, or tribunals.')

    st.subheader("New South Wales Courts to Cover")

    courts_entry = st.multiselect('Select the Courts to cover', nsw_courts)

    st.caption("All Courts listed in the above menu will be covered if left blank")

    st.subheader("Your Search Terms")

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

    #Cap number of judgments
#    judgments_counter_bound_entry = st.checkbox('Untick to collect potentially more than 10 judgments', value = True)

    judgments_counter_bound_entry = judgments_counter_bound

    st.markdown("""You can preview the judgments returned by your search terms on NSW Caselaw after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
    """)
    
    preview_button = st.form_submit_button('PREVIEW on NSW Caselaw (in a popped up window)')

    
#    st.subheader("Information to Collect from Judgment Headnotes")
    
#    st.markdown("""Please select what information from judgment headnotes you would like to obtain.
#Case name, link to NSW Caselaw, and medium neutral citation are always included.
#""")
#    st.caption('The code used to extract judgment headnotes is available at https://github.com/Sydney-Informatics-Hub/nswcaselaw. Such extraction does not require engagement with GPT.')

#    headnotes_entry = st.multiselect("Please select", headnotes_choices)

    st.header("Judgment Metadata Collection")
    
    st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 
    
Case name and medium neutral citation are always included with your results.
""")
    
    meta_data_entry = st.checkbox('Tick to include metadata in your results', value = False)

    
    st.header("Use GPT as Your Research Assistant")

#    st.markdown("**You have three (3) opportunities to engage with GPT through the Empirical Legal Research Kickstarter. Would you like to use one (1) of these opportunities now?**")

    st.markdown("**Would you like GPT to answer questions about each judgment returned by your search terms?**")
    
    gpt_activation_entry = st.checkbox('Tick to use GPT', value = False)

    st.markdown("""You must enter your name and email address if you wish to use GPT.
""")
    #    st.markdown("""You must enter an API key if you wish to use GPT to analyse more than 10 judgments. 
#To obtain an API key, first sign up for an account with OpenAI at 
#https://platform.openai.com/signup. You can then find your API key at https://platform.openai.com/api-keys.
#""")
    
    name_entry = st.text_input("Your name")
    email_entry = st.text_input("Your email address")
#    gpt_api_key_entry = st.text_input("Your GPT API key")


    st.caption("Released by OpenAI, GPT is a family of large language models (ie a generative AI that works on language). Answers to your questions will be generated by model gpt-3.5-turbo-0125. Due to a technical limitation, the model will be instructed to 'read' up to approximately 11,726 words from each judgment.")

    st.markdown("""Please consider trying the Empirical Legal Research Kickstarter without asking GPT any questions first. You can, for instance, obtain the judgments satisfying your search criteria and extract the judgment metadata without using GPT.
""")

    st.caption("Engagement with GPT is costly and funded by a grant.  Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per judgment. The exact cost for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced (as elaborated at https://openai.com/pricing for model gpt-3.5-turbo-0125). You will be given ex-post cost estimates.")

    st.subheader("Enter your question(s) for GPT")
    
    st.markdown("""You may enter one or more questions. **Please enter one question per line or per paragraph.**

GPT is instructed to avoid giving answers which cannot be obtained from the relevant judgment itself. This is to minimise the risk of giving incorrect information (ie hallucination).

You may enter at most 1000 characters here.
    """)

    gpt_questions_entry = st.text_area("", height= 200, max_chars=1000) 

    st.header("Consent")

    st.markdown("""By running the Empirical Legal Research Kickstarter, you agree that the data and/or information this form provides will be temporarily stored on one or more of Ben Chen's electronic devices and/or one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to GPT for the same purpose should you choose to use GPT.
""")
    
    consent =  st.checkbox('Yes, I agree.', value = False)

    st.markdown("""If you do not agree, then please feel free to close this form. Any data or information this form provides will neither be received by Ben Chen nor be sent to GPT.
""")

    st.header("Next Steps")

    st.markdown("""**You can now run the Empirical Legal Research Kickstarter.** A spreadsheet which hopefully has the data you seek will be available for download in about 2-3 minutes.

You can also download a record of your responses.
    
""")

    run_button = st.form_submit_button('RUN the Empirical Legal Research Kickstarter')

    keep_button = st.form_submit_button('DOWNLOAD your form responses')




# %% [markdown]
# # Save and run

# %%
if preview_button:

    gpt_api_key_entry = ''

    df_master = create_df()

    judgments_url = search_url(df_master)

    open_page(judgments_url)



# %%
if run_button:

    #Using own GPT

    gpt_api_key_entry = st.secrets["openai"]["gpt_api_key"]

    #Create spreadsheet of responses
    df_master = create_df()

    #Obtain google spreadsheet

    #conn = st.connection("gsheets_nsw", type=GSheetsConnection)
    #df_google = conn.read()
    #df_google = df_google.fillna('')
    #df_google=df_google[df_google["Processed"]!='']


    if int(consent) == 0:
        st.write("You must click on 'Yes, I agree.' to run the Empirical Legal Research Kickstarter.")

    elif (('@' not in df_master.loc[0, 'Your email address']) & (int(df_master.loc[0]["Tick to use GPT"]) > 0)):
        st.write('You must enter a valid email address to use GPT')

   # elif ((int(df_master.loc[0]["Tick to use GPT"]) > 0) & (prior_GPT_uses(df_master.loc[0, "Your email address"], df_google) >= GPT_use_bound)):
        #st.write('At this pilot stage, each user may use GPT at most 3 times. Please feel free to email Ben at ben.chen@gsydney.edu.edu if you would like to use GPT again.')
    
   # elif ((int(df_master.loc[0]["Tick to use GPT"]) > 0) & (len(df_master.loc[0]["Your GPT API key"]) < 20)):
       # st.write("You must enter a valid API key for GPT.")

#    elif len(courts_entry) == 0:
#        st.write('Please select at least one court.')

    elif search_terms_str(df_master) == 'NoneNone':
        st.write('Please enter at least one search term.')

    else:

        st.markdown("""Your results will be available for download soon. The estimated waiting time is about 2-3 minutes.

If the program produces an error (in red) or an unexpected spreadsheet, please double-check your search terms and try again.
""")

        #Upload placeholder record onto Google sheet
       # df_plaeceholdeer = pd.concat([df_google, df_master])
        #conn.update(worksheet="NSW", data=df_plaeceholdeer, )

        #Produce results

        df_individual = run(df_master)

        df_individual_output = tidying_up(df_master, df_individual)

#        df_individual_output = df_individual

        #Keep record on Google sheet
        
        #df_master["Processed"] = datetime.now()

        df_master.pop("Your GPT API key")
        
        #df_to_update = pd.concat([df_google, df_master])
        
        #conn.update(worksheet="NSW", data=df_to_update, )

        st.write("Your results are now available for download. Thank you for using the Empirical Legal Research Kickstarter.")
        
        #Button for downloading results
        output_name = df_master.loc[0, 'Your name'] + '_' + str(today_in_nums) + '_results'


        csv_output = convert_df_to_csv(df_individual_output)
        
        ste.download_button(
            label="Download your results as a CSV (for use in Excel etc)", 
            data = csv_output,
            file_name= output_name + '.csv', 
            mime= "text/csv", 
#            key='download-csv'
        )

        json_output = convert_df_to_json(df_individual_output)
        
        ste.download_button(
            label="Download your results as a JSON", 
            data = json_output,
            file_name= output_name + '.json', 
            mime= "application/json", 
        )



# %%
if keep_button:

    #Using own GPT API key here

    gpt_api_key_entry = ''
    
    df_master = create_df()

    df_master.pop("Your GPT API key")

    df_master.pop("Processed")
    
    if search_terms_str(df_master) == 'NoneNone':
        st.write('Please enter at least one search term.')

    else:

        responses_output_name = df_master.loc[0, 'Your name'] + '_' + str(today_in_nums) + '_responses'

        #Produce a file to download

        csv = convert_df_to_csv(df_master)
        
        ste.download_button(
            label="Download as a CSV (for use in Excel etc)", 
            data = csv,
            file_name=responses_output_name + '.csv', 
            mime= "text/csv", 
#            key='download-csv'
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
