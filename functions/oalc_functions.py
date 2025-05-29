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

# %%
from datasets import load_dataset
#from datasets import DatasetInfo
#from datasets import load_dataset_builder
#from datasets import get_dataset_split_names
from datasets import load_from_disk
import os
import streamlit as st
import requests
import re
import pause


# %%
from functions.common_functions import split_title_mnc, judgment_text_lower_bound, huggingface
#from common_functions import split_title_mnc


# %%
#Decide whether to use Umar Butler's or mine
corpus_dir = 'lawtodata/oalc_cases'
#corpus_dir = 'umarbutler/open-australian-legal-corpus'

# %%
#How many times to try to get cases from OALC

try_max = 3


# %% [markdown]
# # Download corpus then search

# %%
#Load corpus

@st.cache_resource(show_spinner = False, ttl=600)
def load_corpus():

    #Determine whether to load corpus remotely or locally
    current_dir = ''
    try:
        current_dir = os.getcwd()
        print(f"current_dir == {current_dir}")
    except Exception as e:
        print(f"current_dir not generated.")
        print(e)
    
    if 'Users/Ben' not in current_dir: #If running on Huggingface or Github Actions

        if 'lawtodata' in corpus_dir:
        
            corpus = load_dataset(corpus_dir, split='train', revision='refs/convert/parquet')#, streaming=True)

        else: #'umarbutler' in corpus_dir:
            
            corpus = load_dataset(corpus_dir, split='corpus') # Set `keep_in_memory` to `True` if you wish to load the entire corpus into memory.

    else:        
        #If running locally
        corpus = load_from_disk(st.secrets['huggingface']['oalc_cases_local_path']) #keep_in_memory=False, 

    return corpus



# %%
#Function for getting texts from a list of cases then match with the mnc

#@st.cache_data(show_spinner = False)
def get_judgment_from_oalc_direct(mnc_list):

    #Load corpus
    corpus = load_corpus()

    #Get judgments from corpus
    mnc_judgment_dict = {}
    for mnc in mnc_list:
        mnc_judgment_dict.update({mnc: ''})
        
    records = corpus.filter(lambda x: split_title_mnc(x['citation'])[1] in mnc_list)

    for record in records:
        mnc = split_title_mnc(record['citation'])[1]
        if mnc in mnc_judgment_dict.keys():
            judgment = record['text']
            mnc_judgment_dict[mnc] = judgment

    #Remove any blank or very short judgments
    mncs_to_pop = []
    
    for mnc in mnc_judgment_dict.keys():
        if len(mnc_judgment_dict[mnc]) < judgment_text_lower_bound*4: #judgment_text_lower_bound is in tokens, each token ~= 4 characters
            mncs_to_pop.append(mnc)

    for mnc in mncs_to_pop:
        mnc_judgment_dict.pop(mnc)
    
    return mnc_judgment_dict
    


# %% [markdown]
# # Search without downloading corpus

# %%
#Based on https://huggingface.co/docs/dataset-viewer/en/filter

def oalc_filter(dataset, 
                #split, 
                config = 'default', 
                where = None, 
                orderby = None, 
                offset = None, 
                length = None
               ):

    base_url = "https://datasets-server.huggingface.co/filter"

    try: #If running locally
        HF_TOKEN = st.secrets["huggingface"]["hf_token"]
        
    except: #If running on Huggingface or Github Actions
        HF_TOKEN = os.environ['HF_TOKEN']

    if 'lawtodata' in dataset:
        
        split = 'train'
    
    if 'umarbutler' in dataset:
        
        split = 'corpus'

        config = 'default'
        
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    params = {
    'dataset':dataset, #the dataset name, for example nyu-mll/glue or mozilla-foundation/common_voice_10_0
    'config': config, #the subset name, for example cola
    'split': split, #the split name, for example train
    'where': where, #the filter condition
    'orderby': orderby, #the order-by clause
    'no_answer': 'true', 
    'offset': offset, #the offset of the slice, for example 150
    'length': length
        }

    try:
        response = requests.get(base_url, params=params, headers=headers)
    
        #print(response.url)
    
        #print(response.content)

        #print('Sucessfully obtained cases from OLAC.')
        
        return response.json()

    except Exception as e:

        print(f'Failed to obtain cases from OLAC due to error: {e}')

        return {}
        


# %%
#Function for getting texts from a list of cases then match with the mnc, without downloading

#@st.cache_data(show_spinner = False)
def get_judgment_from_oalc(mnc_list):

    print(f"To obtain from {corpus_dir}: mnc_list == {mnc_list}")


    #Initialise return value
    mnc_judgment_dict = {}

    if len(mnc_list) > 0:
        
        #Figure out jurisdiction
        subset = 'default'
        
        if 'nsw' in mnc_list[0].lower():
            subset = 'nsw_caselaw'
        
        if 'fca' in mnc_list[0].lower():
            subset = 'federal_court_of_australia'
        
        if 'hca' in mnc_list[0].lower():
            subset = 'high_court_of_australia'
        
        #Create list of mncs for use in the where argument of oalc_filter
        where_list = []
    
        for mnc in mnc_list:
            search_str = f"""
            "citation" ILIKE '%{mnc}'
            """
            where_list.append(search_str)
    
        where_str = ' OR '.join(where_list)
    
        #Create dict of mncs and judgments
        for mnc in mnc_list:
            mnc_judgment_dict.update({mnc: ''})

        #Try x times to get data from OALC
        try_counter = 1
        
        while try_counter <= try_max:
            
            try:
        
                #Get judgments from corpus online
                data = oalc_filter(dataset = corpus_dir, 
                             #split = 'train', 
                           config = subset, 
                            where = where_str, 
                             #where = """
                             #("citation" ILIKE '%[1995] FCA 23' OR "citation" ILIKE '%[1995] HCA 1')
                             #""", 
                             #orderby = '"date" DESC NULLS LAST', 
                             length = len(mnc_list))
            
                #print(data)
                                
                for case in data["rows"]:
                    citation = case['row']['citation']
                    mnc = split_title_mnc(citation)[1]
                    if mnc in mnc_judgment_dict.keys():
                        judgment = case['row']['text']
                        mnc_judgment_dict[mnc] = judgment

                print(f"Got cases from OALC after {try_counter} try.")

                try_counter += try_max
            
            except Exception as e:
                
                print(f"Can't get case from OALC after {try_counter} try due to error: {e}")

                try_counter += 1

                pause.seconds(10)

        #Remove any blank or very short judgments
        mncs_to_pop = []

        #judgment_text_lower_bound = 2000
        
        for mnc in mnc_judgment_dict.keys():
            if len(mnc_judgment_dict[mnc]) < judgment_text_lower_bound*4: #judgment_text_lower_bound is in tokens, each token ~= 4 characters
                mncs_to_pop.append(mnc)
    
        for mnc in mncs_to_pop:
            mnc_judgment_dict.pop(mnc)
    
    return mnc_judgment_dict


# %%
#mnc_list = ['[2015] NSWSC 52', '[2015] NSWSC 186', '[2015] NSWSC 172', '[2021] NSWSC 1406', '[1999] NSWSC 1028']
#get_judgment_from_oalc(mnc_list)

# %%
#Based on  https://huggingface.co/docs/dataset-viewer/en/search

#NOT IN USE

def oalc_search(dataset, split, config = 'default', query = None, orderby = None, offset = None, length = None):

    base_url = "https://datasets-server.huggingface.co/search"

    try: #If running locally
        HF_TOKEN = st.secrets["huggingface"]["hf_token"]
        
    except: #If running on Huggingface or Github Actions
        HF_TOKEN = os.environ['HF_TOKEN']

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    params = {
    'dataset':dataset, #the dataset name, for example nyu-mll/glue or mozilla-foundation/common_voice_10_0
    'config': config, #the subset name, for example cola
    'split': split, #the split name, for example train
    'query': query, #the filter condition
    'orderby': orderby, #the order-by clause
    'no_answer': 'true', 
    'offset': offset, #the offset of the slice, for example 150
    'length': length
        }
    
    response = requests.get(base_url, params=params, headers=headers)
    
    return response.json()


# %%

# %%
