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

# %% [markdown] editable=true slideshow={"slide_type": ""}
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
import urllib.request
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

#Word
import textract



# %%
#Get current directory
current_dir = os.getcwd()


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


# %% jupyter={"source_hidden": true}
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer')

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter (ER)",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Pause between judgment scraping

scraper_pause = 5

print(f"\nThe pause between judgment scraping is {scraper_pause} second.")


# %% [markdown]
# # English Reports search engine

# %% editable=true slideshow={"slide_type": ""}
#function to create dataframe
def create_df():

    #submission time
    timestamp = datetime.now()

    #Personal info entries
    
    name = st.session_state['name']
    email = st.session_state['email']
    gpt_api_key = st.session_state['gpt_api_key']

    #Judgment counter bound
    
    judgments_counter_bound_ticked = judgments_counter_bound_entry
    if int(judgments_counter_bound_ticked) > 0:
        judgments_counter_bound = 10
    else:
        judgments_counter_bound = 10000

    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
    gpt_questions = gpt_questions_entry[0: 1000]
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Enter search query': query_entry,
           'Find (method)': method_entry,
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

methods_list = ['using autosearch', 'this Boolean query', 'any of these words', 'all of these words', 'this phrase', 'this case name']
method_types = ['auto', 'boolean', 'any', 'all', 'phrase', 'title']


# %%
#Function turning search terms to search results url

def er_search(query= '', 
              method = ''
             ):
    base_url = "http://www.commonlii.org/cgi-bin/sinosrch.cgi?" #+ method

    method_index = methods_list.index(method)
    method_type = method_types[method_index]

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
def search_results_to_case_link_pairs(url_search_results, judgment_counter_bound):
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
        if ((counter <= judgment_counter_bound) and (' ER ' in str(link))):
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
                if ((counter <= judgment_counter_bound) and (' ER ' in str(extra_link))):
#                if ((counter <= judgment_counter_bound) and ('commonlii' in str(extra_link)) and ('cases/EngR' in str(extra_link)) and ('LawCite' not in str(extra_link))):
                    case = extra_link.get_text()
                    extra_link_direct = extra_link.get('href')
                    sub_extra_link = extra_link_direct.replace('.html', '.pdf').split('cases')[1].split('.pdf')[0]
                    pdf_extra_link = 'http://www.commonlii.org/uk/cases' + sub_extra_link + '.pdf'
                    dict_object = { 'case':case, 'link_direct': pdf_extra_link}
                    case_link_pairs.append(dict_object)
                    counter = counter + 1

            pause.seconds(scraper_pause)
            
        else:
            break
    
    return case_link_pairs


# %%
#Convert case-link pairs to judgment text

def judgment_text(case_link_pair):
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

def meta_judgment_dict(case_link_pair):
    
    judgment_dict = {'Case name': '',
                     'Medium neutral citation' : '', 
                     'English Reports': '', 
                     'Nominate Reports': '', 
                     'Year' : '', 
                     'Hyperlink to CommonLII': '', 
                     'Judgment': ''
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
    judgment_dict['Judgment'] = judgment_text(case_link_pair)

#    pause.seconds(scraper_pause)
    
    #try:
     #   judgment_text = str(soup.find_all('content'))
    #except:
      #  judgment_text= soup.get_text(strip=True)
        
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

#Upperbound on number of judgments to scrape

judgments_counter_bound = 10

print(f"\nNumber of judgments to scrape per request is capped at {judgments_counter_bound}.")


#Lowerbound on length of judgment text to proccess, in tokens

judgment_text_lower_bound = 500

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
tokens_cap = int(16385 - 2500)

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
role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in string form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a specific page in the judgment, provide the page number as part of your answer. If you cannot answer any of the questions based on the judgment or metadata, do not make up information, but instead write "answer not found".'

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
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific page numbers in the judgment or specific sections in the metadata.'})
    
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
        # "Judgment length in tokens (up to 14635 given to GPT)"
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
        df_individual.loc[judgment_index, "Judgment length in tokens (up to 14635 given to GPT)"] = judgment_tokens       

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

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers in the judgment or specific sections in the metadata.", "cl100k_base")

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

    url_search_results = er_search(query= df_master.loc[0, 'Enter search query'], 
                                   method = df_master.loc[0, 'Find (method)']
                                  )
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_link_pairs = search_results_to_case_link_pairs(url_search_results, judgments_counter_bound)

    for case_link_pair in case_link_pairs:

        judgment_dict = meta_judgment_dict(case_link_pair)
        judgments_file.append(judgment_dict)
        pause.seconds(scraper_pause)
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT
    
    API_key = df_master.loc[0, 'Your GPT API key'] 
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Tick to use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, API_key)

    df_updated.pop('Judgment')
    
    return df_updated


# %%
def search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    url = er_search(query= df_master.loc[0, 'Enter search query'],
                    method= df_master.loc[0, 'Find (method)']
                   )
    return url


# %% [markdown]
# # Streamlit form, functions and parameters

# %% editable=true slideshow={"slide_type": ""}
#Function to open url
def open_page(url):
    open_script= """
        <script type="text/javascript">
            window.open('%s', '_blank').focus();
        </script>
    """ % (url)
    html(open_script)


# %%
#Define source text for display
source_text_raw = st.session_state['source'][0].lower()+st.session_state['source'][1:]

if "(" in source_text_raw:
    source_text = source_text_raw.split("(")[0]
else:
    source_text = source_text_raw

# %% editable=true slideshow={"slide_type": ""}
#Create form

with st.form("GPT_input_form") as df_responses:
#    st.title("The Empirical Legal Research Kickstarter")
#    st.subheader("A Pilot for the English Reports")

    return_button = st.form_submit_button('RETURN to previous page')

    st.header(f"You have selected to study :blue[{source_text}].")
    
    #Search terms
    
    st.markdown("""This program will collect (ie scrape) the first 10 judgments returned by your search terms.

For search tips, please visit CommonLII at http://www.commonlii.org/form/search1.html?mask=uk/cases/EngR. This section mimics their search function.
""")
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to cover more judgments.')
    
    st.subheader("Judgment Search Criteria")

    method_entry = st.selectbox('Find (search method)', methods_list, index=1)
    
    query_entry = st.text_input('Enter search query')
        
    judgments_counter_bound_entry = judgments_counter_bound

    st.markdown("""You can preview the judgments returned by your search terms on CommonLII after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
    """)
    
    preview_button = st.form_submit_button('PREVIEW on CommonLII (in a popped up window)')

    st.header("Use GPT as Your Research Assistant")

    st.markdown("**You have three (3) opportunities to engage with GPT through the Empirical Legal Research Kickstarter. Would you like to use one (1) of these opportunities now?**")

    gpt_activation_entry = st.checkbox('Tick to use GPT', value = False)

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

    st.subheader("Consent")

    st.markdown("""By submitting this form to run the Empirical Legal Research Kickstarter, you agree that the data and/or information this form provides will be temporarily stored on one or more of Ben Chen's electronic devices and/or one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to GPT for the same purpose should you choose to use GPT.
""")
    
    consent =  st.checkbox('Yes, I agree.', value = False)

    st.markdown("""If you do not agree, then please feel free to close this form. Any data or information this form provides will neither be received by Ben Chen nor be sent to GPT.
""")

    st.header("Next Steps")

    st.markdown("""**:green[You can run the Empirical Legal Research Kickstarter].** A spreadsheet which hopefully has the data you seek will be available for download in about 2-3 minutes.

You can also download a record of your responses.
    
""")

    run_button = st.form_submit_button('RUN the Empirical Legal Research Kickstarter')

    keep_button = st.form_submit_button('DOWNLOAD your form responses')

#    sub_reset_button = st.form_submit_button('Reset', type = 'primary')



# %% [markdown]
# # Save and run

# %%
if preview_button:

    gpt_api_key_entry = ''

    df_master = create_df()

    judgments_url = search_url(df_master)

    open_page(judgments_url)


# %% editable=true slideshow={"slide_type": ""}
if run_button:

    #Using own GPT

    gpt_api_key_entry = st.secrets["openai"]["gpt_api_key"]

    #Create spreadsheet of responses
    df_master = create_df()

    #Obtain google spreadsheet

   # conn = st.connection("gsheets_uk", type=GSheetsConnection)
    #df_google = conn.read()
    #df_google = df_google.fillna('')
    #df_google=df_google[df_google["Processed"]!='']

    if int(consent) == 0:
        st.write("You must click on 'Yes, I agree.' to run the Empirical Legal Research Kickstarter.")

    elif (('@' not in df_master.loc[0, 'Your email address']) & (int(df_master.loc[0]["Tick to use GPT"]) > 0)):
        st.write('You must enter a valid email address to use GPT')
        
    #elif ((int(df_master.loc[0]["Tick to use GPT"]) > 0) & (prior_GPT_uses(df_master.loc[0, "Your email address"], df_google) >= GPT_use_bound)):
       # st.write('At this pilot stage, each user may use GPT at most 3 times. Please feel free to email Ben at ben.chen@gsydney.edu.edu if you would like to use GPT again.')
    
    #elif ((int(df_master.loc[0]["Tick to use GPT"]) > 0) & (len(df_master.loc[0]["Your GPT API key"]) < 20)):
        #st.write("You must enter a valid API key for GPT.")

    else:

        st.write("Your results will be available for download soon. The estimated waiting time is about 2-3 minutes.")

        #Upload placeholder record onto Google sheet
        #df_plaeceholdeer = pd.concat([df_google, df_master])
        #conn.update(worksheet="UK", data=df_plaeceholdeer, )

        #Produce results

        df_individual_output = run(df_master)

        #Keep record on Google sheet
        
        df_master["Processed"] = datetime.now()

        df_master.pop("Your GPT API key")
        
        #df_to_update = pd.concat([df_google, df_master])
        
        #conn.update(worksheet="UK", data=df_to_update, )

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


# %% editable=true slideshow={"slide_type": ""}
if return_button:
    
    st.switch_page("Home.py")


# %% editable=true slideshow={"slide_type": ""}
#if sub_reset_button:
#    for key in st.session_state.keys():
#        del st.session_state[key]

#    st.write("Any information provided has been cleared. To use this program, you must re-enter your responses from the beginning")
