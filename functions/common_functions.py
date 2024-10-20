# ---
# jupyter:
#   jupytext:
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
#Preliminaries
import datetime
from datetime import date
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
import pypdf
import io
from io import BytesIO
import pause

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb
import xlsxwriter

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste


# %% [markdown]
# # Scraper, GPT etc

# %%
def own_account_allowed():
    return 1


# %%
def check_questions_answers():
    return 1


# %%
def batch_mode_allowed():
    return 0


# %%
#Default judgment counter bound
default_judgment_counter_bound = 10

# %%
#Default page bound for OWN.py
default_page_bound = 50


# %%
#Check if string is date

#From https://stackoverflow.com/questions/25341945/check-if-string-has-date-any-format

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parser.parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False



# %%
def date_parser(string):
    try:
        date = parser.parse(string, dayfirst=True)
        return date
    except:
        return None



# %%
#today
today_in_nums = str(datetime.now())[0:10]
today = datetime.now().strftime("%d/%m/%Y")

# %%
# Generate placeholder list of errors
errors_list = set()


# %%
#Split title and mnc from full case full title

def split_title_mnc(full_title):
    #Returns a list where first item is full_title and second item mnc

    full_title = str(full_title)
    
    #Get rid of extra spaces
    while '  ' in full_title:
        full_title = full_title.replace('  ', ' ')

    #Get mnc
    mnc = full_title
    if '[' in full_title:
        mnc = '[' + full_title.split('[')[-1]

    #Check if mnc is in [year] COURT XXXX format
    mnc_list = mnc.split(' ')
    
    if len(mnc_list) > 3:
        mnc = f"{mnc_list[0]} {mnc_list[1]} {mnc_list[2]}"

    #Get title 
    if mnc in full_title:
        
        title = full_title.split(mnc)[0]

        if len(title) > 0:
            
            while title[-1] == ' ':
                title = title[:-1]
    else:
        title = full_title
    
    return [title, mnc]



# %%
#Pause between judgment scraping

scraper_pause_mean = int((15-5)/2)

#print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")


# %%
#Lowerbound on length of judgment text to proccess, in tokens

judgment_text_lower_bound = 5000


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer', default_handler=str, indent=4)

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

def convert_df_to_excel(df):
    #Excel metadata
    excel_author = 'LawtoData'
    excel_description = 'A 2022 University of Sydney Research Accelerator (SOAR) Prize and a 2023 Discovery Early Career Researcher Award (DECRA) partially funded the development of LawtoData, which generated this spreadsheet.'
    output = BytesIO()
    #writer = pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_urls': False}})
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
#Funder
funder_msg = "Lawtodata is partially funded by a 2022 University of Sydney Research Accelerator (SOAR) Prize and a 2023 Discovery Early Career Researcher Award (DECRA). Please kindly acknowledge this if you use your requested data to produce any research output. "


# %%
#Tidy up medium neutral citation
def mnc_cleaner(x):
    if '[' in x:
        x_clean=str(x).split("[")
        y = '[' + x_clean[-1]
        return y
    else:
        return x



# %%
#Tidy up hyperlink
def link(x):
    value = '=HYPERLINK("' + str(x) + '")'
    return value



# %%
#Define function for judgment link containing PDF
def pdf_judgment(url):
    headers = {'User-Agent': 'whatever'}
    r = requests.get(url, headers=headers)
    remote_file_bytes = io.BytesIO(r.content)
    pdfdoc_remote = pypdf.PdfReader(remote_file_bytes)
    text_list = []

    for page in pdfdoc_remote.pages:
        text_list.append(page.extract_text())
    
    return str(text_list)



# %%
def tips():
    st.markdown(""":green[**DO's**:]
- :green[Do break down complex tasks into simple sub-tasks.]
- :green[Do give clear and detailed instructions (eg specify steps required to complete a task).]
- :green[Do use the same terminology as the relevant judgments or files themselves.]
- :green[Do give exemplar answers.]
- :green[Do manually check some or all answers.]
- :green[Do revise questions to get better answers.]
- :green[Do evaluate answers on the same sample of judgments or files (ie the "training" sample).]
""")

    st.markdown(""":red[**Don'ts**:]
- :red[Don't ask questions which go beyond the relevant judgments or files themselves.]
- :red[Don't ask difficult maths questions.]
- :red[Don't skip manual evaluation.]
""")

    st.markdown(""":orange[**Maybe's**:]
- :orange[Maybe ask for reasoning.]
- :orange[Maybe re-run the same questions and manually check for inconsistency.]
""")

    st.write('Click [here](https://platform.openai.com/docs/guides/prompt-engineering) for more tips.')


# %%
def list_value_check(some_list, some_value):
    try:
        index = some_list.index(some_value)
        return index
    except:
        return None


# %%
def list_range_check(some_list, some_string):
    selected_list = []
    try:
        raw_list = some_string.split(',')

        for item in raw_list:

            while item[0] == ' ':
                item = item[1:]
            
            if item in some_list:
                selected_list.append(item)

    except:
        print(f'List {str(some_list)} does not contain {some_string}')
 
    return selected_list



# %%
def au_date(x):
    try:
        return parser.parse(x, dayfirst=True)
    except:
        return None


# %%
#String to integer
def str_to_int(string):
    try:
        output = int(float(string))
        return output
    except:
        return int(default_judgment_counter_bound)


# %%
#String to integer
def str_to_int_page(string):
    try:
        output = int(float(string))
        return output
    except:
        return int(default_page_bound)


# %%
#Save jurisdiction specific input
def save_input(df_master):

    keys_to_carry_over = ['Your name', 
                        'Your email address', 
                        'Your GPT API key', 
                        'Maximum number of judgments', 
                        'Maximum number of files',
                        'Maximum number of pages per file',
                        'Language choice',
                        'Enter your questions for GPT', 
                        'Use GPT', 
                        'Use own account', 
                        'Use flagship version of GPT', 
                         'submission_time', 
                         'status', 
                          'jurisdiction_page', 
                          'Consent',
                          #'CourtListener API token' #US specific
                         ]
    
    df_master = df_master.replace({np.nan: None})
    
    for key in st.session_state.df_master.keys():
        
        if key not in keys_to_carry_over:
            try:            
                st.session_state.df_master.loc[0, key]  = df_master.loc[0, key]
            except Exception as e:
                print(f'{key} not saved.')
                print(e)



# %%
#Function to hide own token

def hide_own_token(user_token, own_token):
    if user_token:
        if user_token == own_token:
            return None
        else:
            return user_token
    else:
        return None
        


# %%
#Reverse hyperlink display
def reverse_link(x):
    value = str(x).replace('=HYPERLINK("', '').replace('")', '')
    return value


# %%
no_results_msg = 'Your search terms returned 0 results. Please change your search terms and try again.'


# %% [markdown]
# # Streamlit

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
def clear_cache_except_validation_df_master():
    keys = list(st.session_state.keys())
    if 'df_master' in keys:
        keys.remove('df_master')
    if 'page_from' in keys:
        keys.remove('page_from')
    if 'jurisdiction_page' in keys:
        keys.remove('jurisdiction_page')
    for key in keys:
        st.session_state.pop(key)


# %%
def streamlit_timezone():
    local_now = datetime.now().astimezone()
    time_zone = local_now.tzname()
    if time_zone in ['AEST', 'AEDT', 'ACST', 'AWST', 'BST']:
        return True
    else:
        return False


# %%
def streamlit_cloud_date_format(date):
    local_now = datetime.now().astimezone()
    time_zone = local_now.tzname()
    if time_zone in ['AEST', 'ACST', 'AWST', 'BST']:
        date_to_send = parser.parse(date, dayfirst=True).strftime("%d/%m/%Y")
    else:
        date_to_send = parser.parse(date, dayfirst=True).strftime("%m/%d/%Y")
    return date_to_send


# %%
#Default spinner_text

spinner_text = r"$\textsf{\normalsize In progress... }$"

