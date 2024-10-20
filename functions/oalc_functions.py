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


# %%
#Determine if running on HuggingFace
current_dir = ''
try:
    current_dir = os.getcwd()
    print(f"current_dir == {current_dir}")
except Exception as e:
    print(f"current_dir not generated.")
    print(e)

huggingface = False

if '/home/user/app' in current_dir:
    huggingface = True

print(f'huggingface == {huggingface}')


# %%
from functions.common_functions import split_title_mnc
#from common_functions import split_title_mnc


# %%
#Load corpus

@st.cache_resource(show_spinner = False)
def load_corpus():

    #Generate current directory, just to check whether running on Github Actions or locally
    current_dir = ''
    try:
        current_dir = os.getcwd()
        print(current_dir)
    except Exception as e:
        print(f"current_dir not generated.")
        print(e)
    
    if 'Users/Ben' in current_dir: #If running locally
        corpus = load_from_disk(st.secrets['huggingface']['oalc_local_path']) #keep_in_memory=False, 
    else:
        corpus = load_dataset('umarbutler/open-australian-legal-corpus', split='corpus')#, streaming=True)

    return corpus
    


# %%
#Function for getting texts from a list of cases then match with the mnc

@st.cache_data(show_spinner = False)
def get_judgment_from_olac(mnc_list):

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
        if len(mnc_judgment_dict[mnc]) < 1000:
            mncs_to_pop.append(mnc)

    for mnc in mncs_to_pop:
        mnc_judgment_dict.pop(mnc)
    
    return mnc_judgment_dict

