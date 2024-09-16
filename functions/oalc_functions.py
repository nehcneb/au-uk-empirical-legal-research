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
from datasets import load_dataset_builder
from datasets import get_dataset_split_names
from datasets import load_from_disk


# %%
corpus = load_from_disk('/Users/Ben/Library/CloudStorage/OneDrive-TheUniversityofSydney(Staff)/My OneDrive/corpus.hf')

# %%
corpus.info


# %%
#Get mnc from olca citation if court is given
#D/W

def get_mnc_w_court(court, olac_citation):
    
    mnc_raw = ''
    
    olac_citation_list = olac_citation.split('[')
    
    for item in olac_citation_list:
    
        if court.lower() in item.lower():
            mnc_raw = item
            
            break

    try:

        mnc_list = mnc_raw.lower().split(' ')

        court_index = mnc_list.indeolac_citation(court.lower())
    
        mnc = f"[{mnc_list[court_index-1]} {court.upper()} {mnc_list[court_index+1]}"
    
        return mnc

    except:
    
        return mnc_raw



# %%
#Get mnc from olca citation if court is not given
#olca citation doesn't have text like 'this decision has been amended etc'

def get_mnc(olac_citation):
    
    mnc = '[' + olac_citation.split('[')[-1]
    
    return mnc



# %%
#test_mnc = '[1992] HCA 23' #Mabo
test_mnc = '[2003] NSWCA 10' #Harris v Digital Pulse
#test_mnc = '[1997] HCA 45' #Re Davison

# %%
#test_case = corpus.filter(lambda x: get_mnc_w_court('NSWCA', x['citation']) == test_mnc)
#test_case[0]['citation']

# %%
#Use the approach of getting a list of relevant mncs and then scraping the judgment text from oalc

test_mnc_list = ['[1992] HCA 23', '[2003] NSWCA 10', '[1997] HCA 45']

test_case_alt = corpus.filter(lambda x: get_mnc(x['citation']) in test_mnc_list)

# %%
test_case_alt[2]['citation']

# %%
type(test_case_alt[0])

# %%
