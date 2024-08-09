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
from dateutil.parser import parse
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import pandas as pd

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste


# %%
def own_account_allowed():
    return 1


# %%
def check_questions_answers():
    return 1


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
        parse(string, fuzzy=fuzzy)
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
#Pause between judgment scraping

scraper_pause_mean = int((15-5)/2)

#print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")


# %%
#Lowerbound on length of judgment text to proccess, in tokens

judgment_text_lower_bound = 5000


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer', default_handler=str)

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

def convert_df_to_excel(df):
    #Excel metadata
    excel_author = 'The Empirical Legal Research Kickstarter'
    excel_description = 'A 2022 University of Sydney Research Accelerator (SOAR) Prize partially funded the development of the Empirical Legal Research Kickstarter, which generated this spreadsheet.'
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
#Define function to determine eligibility for GPT use

#Define a list of privileged email addresses with unlimited GPT uses

def prior_GPT_uses(email_address, df_online):
    privileged_emails = st.secrets["secrets"]["privileged_emails"].replace(' ', '').split(',')
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
#Tidy up medium neutral citation
def mnc_cleaner(x):
    if '[' in x:
        x_clean=str(x).split("[")
        y = '[' + x_clean[1]
        return y
    else:
        return x



# %%
#Tidy up hyperlink
def link(x):
    value = '=HYPERLINK("' + str(x) + '")'
    return value



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
        if '.' in string:
            output = int(string.split('.')[0])
        else:
            output = int(string)
        return output
    except:
        return int(default_judgment_counter_bound)


# %%
#String to integer
def str_to_int_page(string):
    try:
        if '.' in string:
            output = int(string.split('.')[0])
        else:
            output = int(string)
        return output
    except:
        return int(default_page_bound)


# %%
def streamlit_cloud_date_format(date):
    local_now = datetime.now().astimezone()
    time_zone = local_now.tzname()
    if time_zone in ['AEST', 'ACST', 'AWST', 'BST']:
        date_to_send = parser.parse(date, dayfirst=True).strftime("%d/%m/%Y")
    else:
        date_to_send = parser.parse(date, dayfirst=True).strftime("%m/%d/%Y")
    return date_to_send
    
