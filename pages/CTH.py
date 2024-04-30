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

#OpenAI
import openai
import tiktoken

#Google
from google.oauth2 import service_account

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb

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

#Upperbound on number of judgments to scrape

judgments_counter_bound = 10

print(f"\nNumber of judgments to scrape per request is capped at {judgments_counter_bound}.")

#Pause between judgment scraping

scraper_pause = 5

print(f"\nThe pause between judgment scraping is {scraper_pause} second.")


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
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
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
# # Federal Courts search engine

# %%
#Define format functions for headnotes choice, courts choice, and GPT questions

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
    value = '=HYPERLINK("' + str(x) + '")'
    return value



# %%
#function to create dataframe
def create_df():

    #submission time
    timestamp = datetime.now()

    #Personal info entries
    
    name = name_entry
    email = email_entry
    gpt_api_key = gpt_api_key_entry



    #dates
    
    on_this_date = ''

    if on_this_date_entry != 'None':

        try:

            on_this_date = on_this_date_entry.strftime('%d/%m/%Y') + on_this_date_entry.strftime('%d') + before_date_entry.strftime('%B').lower()[:3] + on_this_date_entry.strftime('Y')

        except:
            pass
        
    
    before_date = ''

    if before_date_entry != 'None':

        try:

            before_date = str(before_date_entry.strftime('%d')) + str(before_date_entry.strftime('%B')).lower()[:3] + str(before_date_entry.strftime('%Y'))

        except:
            pass

    
    after_date = ''

    if after_date_entry != 'None':
        
        try:
            after_date = str(after_date_entry.strftime('%d')) + str(after_date_entry.strftime('%B')).lower()[:3] + str(after_date_entry.strftime('%Y'))
            
        except:
            pass
    

    #Other entries
    case_name_mnc = case_name_mnc_entry
    judge =  judge_entry
    reported_citation = reported_citation_entry
    file_number = file_number_entry
    npa = npa_entry
    with_all_the_words = with_all_the_words_entry
    with_at_least_one_of_the_words = with_at_least_one_of_the_words_entry
    without_the_words = without_the_words_entry
    phrase = phrase_entry
    proximity = proximity_entry
    legislation = legislation_entry
    cases_cited = cases_cited_entry
    catchwords = catchwords_entry 
    
    #Judgment counter bound
    
    judgments_counter_bound_ticked = judgments_counter_bound_entry
    if int(judgments_counter_bound_ticked) > 0:
        judgments_counter_bound = 10
    else:
        judgments_counter_bound = 10000

    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
    gpt_questions = gpt_questions_entry[0: 1000]

    #metadata choice

    meta_data_choice = meta_data_entry
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
           'Case name or medium neutral citation': case_name_mnc, 
           'Judge' : judge, 
            'Reported citation' : reported_citation, 
            'File number': file_number,
            'National practice area': npa,
            'With all the words': with_all_the_words,
            'With at least one of the words': with_at_least_one_of_the_words,
            'Without the words': without_the_words,
            'Phrase': phrase,
            'Proximity': proximity,
            'On this date': on_this_date,
            'After date': after_date,
            'Before date': before_date,
            'Legislation': legislation,
            'Cases cited': cases_cited,
            'Catchwords' : catchwords, 
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
#Function turning search terms to search results url
def fca_search(case_name_mnc= '', 
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
    base_url = "https://search2.fedcourt.gov.au/s/search.html?collection=judgments&sort=date&meta_v_phrase_orsand=judgments%2FJudgments%2Ffca"
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
    return response.url


# %%
#Auxiliary list for getting more pages of search results
further_page_ending_list = []
for i in range(100):
    further_page_ending = 20 + i
    if ((str(further_page_ending)[-1] =='1') & (str(further_page_ending)[0] not in ['3', '5', '7', '9', '11'])):
        further_page_ending_list.append(str(further_page_ending))


# %%
#Define function turning search results url to links to judgments
def search_results_to_judgment_links(url_search_results, judgment_counter_bound):
    #Scrape webpage of search results
    page = requests.get(url_search_results)
    soup = BeautifulSoup(page.content, "lxml")

    #Start counter

    counter = 1
    
    # Get links of first 20 results
    links_raw = soup.find_all("a", href=re.compile("fca"))
    links = []
    
    for i in links_raw:
        if (('title=' in str(i)) and (counter <=judgment_counter_bound)):
            remove_title = str(i).split('" title=')[0]
            remove_leading_words = remove_title.replace('<a href="', '')
            if 'a class=' not in remove_leading_words:
                links.append(remove_leading_words)
                counter = counter + 1

    #Go beyond first 20 results

    for ending in further_page_ending_list:
        if counter <=judgment_counter_bound:
            url_next_page = url_search_results + '&start_rank=' + f"{ending}"
            page_judgment_next_page = requests.get(url_next_page)
            soup_judgment_next_page = BeautifulSoup(page_judgment_next_page.content, "lxml")
            links_next_page_raw = soup_judgment_next_page.find_all("a", href=re.compile("fca"))

            #Check if stll more results
            if len(links_next_page_raw) > 0:
                for i in links_next_page_raw:
                    if 'title=' in str(i):
                        remove_title = str(i).split('" title=')[0]
                        remove_leading_words = remove_title.replace('<a href="', '')
                        if 'a class=' not in remove_leading_words:
                            links.append(remove_leading_words)
                            counter = counter + 1

            else:
                break

    return links


# %%
#judgment url to word document
#NOT in use
def link_to_doc(url_judgment):
    page_judgment = requests.get(url_judgment)
    soup_judgment = BeautifulSoup(page_judgment.content, "lxml")
    link_word_raw = soup_judgment.find_all('a', string=re.compile('Word'))
    if len(link_word_raw)> 0:
        link_to_word = str(link_word_raw).split('>')[0].replace('[<a href="', '')
        return link_to_word
    else:
        return url_judgment


# %%
#Define function for judgment link containing PDF
def pdf_judgment(url):
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
#IN USE
meta_labels = ['MNC', 'Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to']
meta_labels_droppable = ['Year', 'Appeal', 'File_Number', 'Judge', 'Judgment_Dated', 'Catchwords', 'Subject', 'Words_Phrases', 'Legislation', 'Cases_Cited', 'Division', 'NPA', 'Sub_NPA', 'Pages', 'All_Parties', 'Jurisdiction', 'Reported', 'Summary', 'Corrigenda', 'Parties', 'FileName', 'Asset_ID', 'Date.published', 'Appeal_to', 'Order']

def meta_judgment_dict(judgment_url):
    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to FCA Digital Law Library' : '', 
                'MNC' : '',  
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
                'Judgment' : ''
                }

    
    #Attach hyperlink

    judgment_dict['Hyperlink to FCA Digital Law Library'] = link(judgment_url)
    
    page = requests.get(judgment_url)
    soup = BeautifulSoup(page.content, "lxml")
    meta_tags = soup.find_all("meta")

    #Attach meta tags
    if len(meta_tags)>0:
        for tag_index in range(len(meta_tags)):
            meta_name = meta_tags[tag_index].get("name")
            if meta_name in meta_labels:
                meta_content = meta_tags[tag_index].get("content")
                judgment_dict[meta_name] = meta_content

    #Check if not gets taken to a PDF

    if '.pdf' not in judgment_url.lower():
    
        try:
            judgment_dict['Case name'] = judgment_dict['MNC'].split('[')[0]
            judgment_dict['Medium neutral citation'] = '[' + judgment_dict['MNC'].split('[')[1]
            del judgment_dict['MNC']
    
        except:
            pass

        #Attach order_text and judgment
    
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
        
        judgment_dict['Judgment'] = judgment_text
        judgment_dict['Order'] = order_text

    #Check if gets taken to a PDF

    else:
        #Attach case name
        judgment_dict['Case name'] = 'Not working properly because judgment in PDF. References to paragraphs likely to pages or wrong.'

        #Attach judgment pdf text
        try:
            judgment_pdf_raw = pdf_judgment(judgment_url)
            judgment_dict['Judgment'] = judgment_pdf_raw
            
        except:
            pass
    
        #Attach medium neutral citation
        try:
            mnc_raw = judgment_url.split('/')[-1].replace('.pdf', '')

            for court_i in ['fca', 'fcafc']:
                if court_i in mnc_raw.lower():
                    mnc_list = mnc_raw.lower().split(court_i)
                    judgment_dict['Medium neutral citation'] = '[' + mnc_list[0] + '] ' + court_i.upper()  + ' ' +  mnc_list[1]
            
            del judgment_dict['MNC']
    
        except:
            pass        

    return judgment_dict

    

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
#characters_limit_half = int((16385*4)/2-1500)
tokens_cap = int(16385 - 1500)

def judgment_prompt_json(judgment_json):
                
    judgment_content = 'Based on the metadata and judgment in the following JSON:  """'+ str(judgment_json) + '""",'

    judgment_content_tokens = num_tokens_from_string(judgment_content, "cl100k_base")
    
    if judgment_content_tokens <= tokens_cap:
        
        return judgment_content

    else:
        
        meta_data_len = judgment_content_tokens - num_tokens_from_string(judgment_json['Judgment'], "cl100k_base")
        
        judgment_chars_capped = int((tokens_cap - meta_data_len)*4)
        
        judgment_string_trimmed = judgment_json['Judgment'][ :int(judgment_chars_capped/2)] + judgment_json['Judgment'][-int(judgment_chars_capped/2): ]

        judgment_json["Judgment"] = judgment_string_trimmed     
        
        judgment_content_capped = 'Based on the metadata and judgment in the following JSON:  """'+ str(judgment_json) + '""",'
        
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
     
    df_master['Enter your question(s) for GPT'] = df_master['Enter your question(s) for GPT'][0: answers_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your question(s) for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    url_search_results = fca_search(case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
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
                     after_date = df_master.loc[0, 'After date'], 
                     before_date = df_master.loc[0, 'Before date'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'] 
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
        pause.seconds(scraper_pause)
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
    
    #Rename column titles
    
#    try:
#        df_individual['Hyperlink (double click)'] = df_individual['Hyperlink'].apply(link)
#        df_individual.pop('Hyperlink')
#    except:
#        pass
    
    #Instruct GPT
    
    API_key = df_master.loc[0, 'Your GPT API key'] 
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Tick to use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, API_key)

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
    
    #Combining catchwords into new column
    
    #Conduct search
    
    url = fca_search(case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
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
                     after_date = df_master.loc[0, 'After date'], 
                     before_date = df_master.loc[0, 'Before date'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'] 
                    )
    return url


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
def clear_cache():
    keys = list(st.session_state.keys())
    for key in keys:
        st.session_state.pop(key)


# %%
#Create form

with st.form("GPT_input_form") as df_responses:

    return_button = st.form_submit_button('RETURN to first page')
    
    st.header(f"You have selected to study :blue[judgments of the Federal Court of Australia].")

#    st.header("Judgment Search Criteria")
    
    st.markdown("""**Please enter your search terms.** This program will collect (ie scrape) the first 10 judgments returned by your search terms.

For search tips, please visit the Federal Court Digital Law Library at https://www.fedcourt.gov.au/digital-law-library/judgments/search. This section mimics their judgments search function.
""")
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')
    
    st.subheader("Your Search Terms")

    catchwords_entry = st.text_input('Catchwords')

    legislation_entry = st.text_input('Legislation')

    cases_cited_entry = st.text_input('Cases cited')

    case_name_mnc_entry = st.text_input("Case name or medium neutral citation")
    
    judge_entry = st.text_input('Judge')

    reported_citation_entry = st.text_input('Reported citation')

    file_number_entry = st.text_input('File number')

    npa_entry = st.text_input('National practice area')

    with_all_the_words_entry = st.text_input('With ALL the words')

    with_at_least_one_of_the_words_entry = st.text_input('With at least one of the words')

    without_the_words_entry = st.text_input('Without the words')

    phrase_entry = st.text_input('Phrase')

    proximity_entry  = st.text_input('Proximity')

    on_this_date_entry = st.date_input('On this date', value = None, format="DD/MM/YYYY")

    after_date_entry = st.date_input('After date', value = None, format="DD/MM/YYYY")
    
    before_date_entry = st.date_input('Before date', value = None, format="DD/MM/YYYY")

    st.caption('Relatively earlier judgments will not be collected. For information about judgment availability, please visit https://www.fedcourt.gov.au/digital-law-library/judgments/judgments-faq.')

    judgments_counter_bound_entry = judgments_counter_bound

    st.markdown("""You can preview the judgments returned by your search terms on the Federal Court Digital Law Library after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")
    
    preview_button = st.form_submit_button('PREVIEW on the Federal Court Digital Law Library (in a popped up window)')

    st.header("Judgment Metadata Collection")
    
    st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 
    
Case name and medium neutral citation are always included with your results.
""")
    
    meta_data_entry = st.checkbox('Tick to include metadata in your results', value = False)


    st.header("Use GPT as Your Research Assistant")

#    st.markdown("**You have three (3) opportunities to engage with GPT through the Empirical Legal Research Kickstarter. Would you like to use one (1) of these opportunities now?**")

    st.markdown("**Would you like GPT to answer questions about each judgment returned by your search terms?**")

    st.markdown("""Please consider trying the Empirical Legal Research Kickstarter without asking GPT any questions first. You can, for instance, obtain the judgments satisfying your search criteria and extract the judgment metadata without using GPT.
""")
    
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

    st.caption("Released by OpenAI, GPT is a family of large language models (ie a generative AI that works on language). Engagement with GPT is costly and funded by a grant.  Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per judgment. The exact cost for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced (as elaborated at https://openai.com/pricing for model gpt-3.5-turbo-0125). You will be given ex-post cost estimates.")

    st.subheader("Enter your question(s) for GPT")
    
    st.markdown("""You may enter one or more questions. **Please enter one question per line or per paragraph.**

GPT is instructed to avoid giving answers which cannot be obtained from the relevant judgment itself. This is to minimise the risk of giving incorrect information (ie hallucination).

You may enter at most 1000 characters here.
    """)

    gpt_questions_entry = st.text_area("", height= 200, max_chars=1000) 

    st.caption("Answers to your questions will be generated by model gpt-3.5-turbo-0125. Due to a technical limitation, the model will be instructed to 'read' up to approximately 11,726 words from each judgment.")

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




# %%
#Create placeholder download buttons if previous responses and results in st.session_state:

if 'df_master' and 'df_individual_output' in st.session_state:

    if st.button(label='RESET to process new search terms or questions', type = 'primary', help = "Press to run the Empirical Legal Research Kickstarter afresh."):
        clear_cache()
        st.rerun()

    #Load previous responses and results
    
    df_master = st.session_state.df_master
    df_individual_output = st.session_state.df_individual_output

    #Buttons for downloading responses

    csv = convert_df_to_csv(df_master)

    responses_output_name = df_master.loc[0, 'Your name'] + '_' + str(today_in_nums) + '_responses'


    st.subheader('Looking for your previous form responses?')
    
    ste.download_button(
        label="Download your previous responses as a CSV (for use in Excel etc)", 
        data = csv,
        file_name=responses_output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    xlsx = convert_df_to_excel(df_master)
    
    ste.download_button(label='Download your previous responses as an Excel file (XLSX)',
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
    output_name = df_master.loc[0, 'Your name'] + '_' + str(today_in_nums) + '_results'

    csv_output = convert_df_to_csv(df_individual_output)

    st.subheader('Looking for your previous results?')
    
    ste.download_button(
        label="Download your previous results as a CSV (for use in Excel etc)", 
        data = csv_output,
        file_name= output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    excel_xlsx = convert_df_to_excel(df_individual_output)
    
    ste.download_button(label='Download your previous results as an Excel file (XLSX)',
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

    judgments_url =  fca_search(case_name_mnc = df_master.loc[0, 'Case name or medium neutral citation'],
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
                     after_date = df_master.loc[0, 'After date'], 
                     before_date = df_master.loc[0, 'Before date'], 
                     legislation = df_master.loc[0, 'Legislation'], 
                     cases_cited = df_master.loc[0, 'Cases cited'], 
                     catchwords = df_master.loc[0, 'Catchwords'] 
                    )

    open_page(judgments_url)


# %%
if run_button:

    #Check whether search terms entered

    all_search_terms = str(catchwords_entry) + str(legislation_entry) + str(cases_cited_entry) + str(case_name_mnc_entry) + str(judge_entry) + str(reported_citation_entry) + str(file_number_entry) + str(npa_entry) + str(with_all_the_words_entry) + str(with_at_least_one_of_the_words_entry) + str(without_the_words_entry) + str(phrase_entry) + str(proximity_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.write('You must enter some search terms.')

    elif int(consent) == 0:
        st.write("You must click on 'Yes, I agree.' to run the Empirical Legal Research Kickstarter.")

    elif (('@' not in str(email_entry)) & (int(gpt_activation_entry) > 0)):
        st.write('You must enter a valid email address to use GPT.')

    #elif ((int(df_master.loc[0]["Tick to use GPT"]) > 0) & (prior_GPT_uses(df_master.loc[0, "Your email address"], df_google) >= GPT_use_bound)):
        #st.write('At this pilot stage, each user may use GPT at most 3 times. Please feel free to email Ben at ben.chen@gsydney.edu.edu if you would like to use GPT again.')
    
   # elif ((int(df_master.loc[0]["Tick to use GPT"]) > 0) & (len(df_master.loc[0]["Your GPT API key"]) < 20)):
       # st.write("You must enter a valid API key for GPT.")

    else:

        st.markdown("""Your results will be available for download soon. The estimated waiting time is about 2-3 minutes.

If this program produces an error (in red) or an unexpected spreadsheet, please double-check your search terms and try again.
""")

        #Using own GPT

        gpt_api_key_entry = st.secrets["openai"]["gpt_api_key"]
    
        #Create spreadsheet of responses
        df_master = create_df()

        #Upload placeholder record onto Google sheet
        #df_plaeceholdeer = pd.concat([df_google, df_master])
        #conn.update(worksheet="CTH", data=df_plaeceholdeer, )

        #Obtain google spreadsheet
    
        #conn = st.connection("gsheets_cth", type=GSheetsConnection)
        #df_google = conn.read()
        #df_google = df_google.fillna('')
        #df_google=df_google[df_google["Processed"]!='']
    
        #Produce results
        df_individual_output = run(df_master)

        #Keep record on Google sheet
        
        df_master["Processed"] = datetime.now()

        df_master.pop("Your GPT API key")
        
        #df_to_update = pd.concat([df_google, df_master])
        
        #conn.update(worksheet="CTH", data=df_to_update, )

        #Keep results in session state
        if "df_individual_output" not in st.session_state:
            st.session_state["df_individual_output"] = df_individual_output

        if "df_master" not in st.session_state:
            st.session_state["df_master"] = df_master
        
        st.session_state["page_from"] = 'pages/CTH.py'

        #Write results

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

        excel_xlsx = convert_df_to_excel(df_individual_output)
        
        ste.download_button(label='Download your results as an Excel file (XLSX)',
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


# %%
if keep_button:

    #Check whether search terms entered

    all_search_terms = str(catchwords_entry) + str(legislation_entry) + str(cases_cited_entry) + str(case_name_mnc_entry) + str(judge_entry) + str(reported_citation_entry) + str(file_number_entry) + str(npa_entry) + str(with_all_the_words_entry) + str(with_at_least_one_of_the_words_entry) + str(without_the_words_entry) + str(phrase_entry) + str(proximity_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.write('You must enter some search terms.')

    else:
        #Using own GPT API key here
    
        gpt_api_key_entry = ''
        
        df_master = create_df()
    
        df_master.pop("Your GPT API key")
    
        df_master.pop("Processed")
    
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


        xlsx = convert_df_to_excel(df_master)
        
        ste.download_button(label='Download as an Excel file (XLSX)',
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
