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
from io import BytesIO

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb

# %%
#Import functions
from common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner 
#Import variables
from common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

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

def uk_court_choice(x):
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


#Tidy up hyperlink
def uk_link(x):
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
            
            pause.seconds(np.random.randint(10, 20))

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
                'judgment': ''
                }
    try:
        judgment_dict['Case name'] = soup.find("frbrname")['value']
        judgment_dict['Medium neutral citation'] = soup.find("uk:cite").getText()
        judgment_dict['Hyperlink to The National Archives'] = uk_link(soup.find("frbruri")['value'])
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
    #    judgment_dict['judgment'].append(text.getText())

    #Get judgment

    pause.seconds(np.random.randint(10, 20))

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

    judgment_dict['judgment'] = judgment_text
    
    #try:
     #   judgment_text = str(soup.find_all('content'))
    #except:
      #  judgment_text= soup.get_text(strip=True)
        
    return judgment_dict


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from gpt_functions import question_characters_bound, default_judgment_counter_bound, role_content#, intro_for_GPT


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

# %%
#Jurisdiction specific instruction
system_instruction = role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-3.5-turbo-0125"
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#Upperbound on number of judgments to scrape
if 'judgments_counter_bound' not in st.session_state:
    st.session_state['judgments_counter_bound'] = default_judgment_counter_bound


# %%
#Obtain parameters

def run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)
    
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
        pause.seconds(np.random.randint(10, 20))
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #For UK, convert date to string so as to avoid Excel producing random numbers for dates
    df_individual['Date'] = df_individual['Date'].astype(str)
    
    #GPT model

    if df_master.loc[0, 'Use latest version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        gpt_model = "gpt-3.5-turbo-0125"
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    df_updated.pop('judgment')

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

    df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)
    
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


# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from common_functions import open_page, clear_cache_except_validation_df_master, tips


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

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_master' not in st.session_state:

    st.session_state['df_master'] = pd.DataFrame([])

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])
    
#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

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
""")

st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments.')

st.subheader("Courts and tribunals to cover")

default_on = st.checkbox('Prefill the Supreme Court, the Privy Council, the Court of Appeal, the High Court of England & Wales')

if default_on:

    st.session_state.default_courts = uk_courts_default_list

else:
    st.session_state.default_courts = []

courts_entry = st.multiselect(label = 'Select or type in the courts and tribunals to cover', options = uk_courts_list, default = st.session_state.default_courts)
    
#st.caption("All courts and tribunals listed in this menu will be covered if left blank.")

#Search terms

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [The National Archives](https://caselaw.nationalarchives.gov.uk/structured_search). This section mimics their search function.
""")

query_entry = st.text_input('Free text')

from_date_entry = st.date_input('From date', value = None, format="DD/MM/YYYY", min_value = date(1900, 1, 1))

to_date_entry = st.date_input('to date', value = None, format="DD/MM/YYYY", min_value = date(1900, 1, 1))

st.caption('[Relatively earlier](https://caselaw.nationalarchives.gov.uk/structured_search) judgments are not available.')

judge_entry = st.text_input('Judge name')

party_entry = st.text_input('Party name')

st.markdown("""You can preview the judgments returned by your search terms on The National Archives after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")

preview_button = st.button('PREVIEW on The National Archives (in a popped up window)')

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

st.caption("Use of GPT is costly and funded by a grant. For the model used by default (gpt-3.5-turbo-0125), Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per judgment. The [exact cost](https://openai.com/pricing) for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced. You will be given ex-post cost estimates.")

st.subheader("Enter your questions for each judgment")

st.markdown("""Please enter one question **per line or per paragraph**. GPT will answer your questions for **each** judgment based only on information from **that** judgment. """)

st.markdown("""GPT is instructed to avoid giving answers which cannot be obtained from the relevant judgment itself. This is to minimise the risk of giving incorrect information (ie hallucination).""")

if st.toggle('See the instruction given to GPT'):
    st.write(f"{intro_for_GPT[0]['content']}")

if st.toggle('Tips for using GPT'):
    tips()

gpt_questions_entry = st.text_area(f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound) 

#Disable toggles while prompt is not entered or the same as the last processed prompt
if gpt_activation_entry:
    
    if gpt_questions_entry:
        st.session_state['disable_input'] = False
        
    else:
        st.session_state['disable_input'] = True
else:
    st.session_state['disable_input'] = False
    
st.caption(f"By default, answers to your questions will be generated by model gpt-3.5-turbo-0125. Due to a technical limitation, this model will read up to approximately {round(tokens_cap('gpt-3.5-turbo-0125')*3/4)} words from each judgment.")

if own_account_allowed() > 0:
    
    st.subheader(':orange[Enhance program capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum nunber of judgments to process? You can do so with your own GPT account.
    """)
    
    own_account_entry = st.toggle('Use my own GPT account',  disabled = st.session_state.disable_input)
    
    if own_account_entry:
    
        st.session_state["own_account"] = True
    
        st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage [here](https://platform.openai.com/signup). You can then create and find your API key [here](https://platform.openai.com/api-keys).
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
        st.caption('Click [here](https://openai.com/api/pricing) for pricing information on different GPT models.')
        
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

# %% [markdown]
# ## Consent and next steps

# %%
st.header("Consent")

st.markdown("""By running this program, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False, disabled = st.session_state.disable_input)

st.markdown("""If you do not agree, then please feel free to close this form.""")

st.header("Next steps")

st.markdown("""**:green[You can now run the Empirical Legal Research Kickstarter.]** A spreadsheet which hopefully has the data you seek will be available for download.

You can also download a record of your entries.

""")

#Warning
if st.session_state.gpt_model == 'gpt-3.5-turbo-0125':
    st.warning('A low-cost GPT model will answer your questions. Please reach out to Ben Chen at ben.chen@sydney.edu.au if you would like to use the latest model instead.')

if st.session_state.gpt_model == "gpt-4o":
    st.warning('An expensive GPT model will answer your questions. Please be cautious.')

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
    
    all_search_terms = str(query_entry) + str(from_date_entry) + str(to_date_entry) + str(judge_entry) + str(party_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif len(courts_entry) == 0:
        st.write('Please select at least one court to cover.')
        
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

        with st.spinner("Running... Please :red[don't change] your entries (yet)."):

            try:
                
                #Create spreadsheet of responses
                df_master = create_df()

                #Activate user's own key or mine
                if st.session_state.own_account == True:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    API_key = st.secrets["openai"]["gpt_api_key"]

                openai.api_key = API_key

                #Produce results
                df_individual_output = run(df_master)
                
                #Keep results in session state
                st.session_state["df_individual_output"] = df_individual_output
    
                st.session_state["df_master"] = df_master

                #Change session states
                st.session_state['need_resetting'] = 1
                
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

    elif ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output)>0)):
        st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')
                    
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
