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
import PyPDF2
import io
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
# # Canada search engine

# %%
#Scrape javascript

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By

options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--headless")
options.add_argument('--no-sandbox')  
options.add_argument('--disable-dev-shm-usage')  

@st.cache_resource
def get_driver():
    return webdriver.Chrome(
        #service=Service(
            #ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        #),
        options=options,
    )

browser = get_driver()

browser.implicitly_wait(10)
browser.set_page_load_timeout(10)


# %%
from common_functions import link


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

    #Juridiction
    jurisdiction = jurisdiction_entry
    
    #Court
    court = st.session_state.court

    #Year entry
    #year = st.session_state.year

    #Can't get noteup/discussion to work given dynamic
    #Noteup entry

    #cite = cited_entry
        
    #Other entries
    case_name_mnc = case_name_mnc_entry
    phrase = phrase_entry

    #Court/tribunal types

    court_tribunal_type = court_tribunal_type_entry
    
    #dates
    
    on_this_date = ''

    if on_this_date_entry != 'None':

        try:

            on_this_date = on_this_date_entry.strftime("%Y-%m-%d")

        except:
            pass
        
    
    before_date = ''

    if before_date_entry != 'None':

        try:

            before_date = before_date_entry.strftime("%Y-%m-%d")
            
        except:
            pass

    
    after_date = ''

    if after_date_entry != 'None':
        
        try:
            after_date = after_date_entry.strftime("%Y-%m-%d")
            
        except:
            pass

    #Subjects

    subjects = ''

    try:
        
        subjects = ",".join(subjects_entry)
        
    except:
        
        pass
    
    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
    
    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry[0: 1000]
    
    except:
        print('GPT questions not entered.')

    #metadata choice

    meta_data_choice = meta_data_entry
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Jurisdictions': jurisdiction, 
           'Courts': court, 
           'Case name, citation or docket': case_name_mnc, 
            'Document text': phrase,
               'Court or tribunal type': court_tribunal_type, 
           'Decision date is': on_this_date,
            'Decision date is after': after_date,
            'Decision date is before': before_date,
               'Subjects': subjects, 
            #'Noteup/Discussion': cited, 
            #'Year': year,
            'Metadata inclusion' : meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status,
           'Use own account': own_account,
            'Use latest version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
            
    return df_master_new


# %%
#Define format functions for jurisdiction choice, and GPT questions

all_ca_jurisdictions = {'All': '', 
                    'Canada (Federal)': 'ca', 
                    'British Columbia': 'bc', 
                    'Alberta': 'ab', 
                    'Saskatchewan': 'sk',
                    'Manitoba': 'mb', 
                    'Ontario': 'on', 
                    'Quebec': 'qc', 
                    'New Brunswick': 'nb', 
                    'Nova Scotia': 'ns', 
                    'Prince Edward Island': 'pe', 
                    'Newfoundland and Labrador': 'nl', 
                    'Yukon': 'yk', 
                    'Northwest Territories': 'nt', 
                    'Nunavut': 'nu'}

all_ca_jurisdictions_list = list(all_ca_jurisdictions.keys())


# %%
#Canadian federal courts, tribunals and boards

ca_courts = {'All': '', 
 'Supreme Court of Canada': 'scc',
 'Supreme Court of Canada - Applications for Leave': 'scc-l',
 'Judicial Committee of the Privy Council - Canadian cases': 'ukjcpc',
 'Federal Court of Appeal': 'fca',
 'Federal Court': 'fc',
 'Tax Court of Canada': 'tcc',
 'Exchequer Court of Canada': 'exch',
 'Court Martial Appeal Court of Canada': 'cmac',
 'Courts Martial': 'cm',
 'Foreign reported decisions': 'forep',
 'Canada Agricultural Review Tribunal': 'cart',
 'Canada Energy Regulator': 'cer',
 'Canada Industrial Relations Board': 'cirb',
 'Canadian Broadcast Standards Council': 'cbsc',
 'Canadian Human Rights Tribunal': 'chrt',
 'Canadian International Trade Tribunal': 'citt',
 'Canadian Investment Regulatory Organization': 'ciro',
 'College of Immigration and Citizenship Consultants': 'cicc',
 'Commissioner of Patents': 'cacp',
 'Competition Tribunal': 'cact',
 'Copyright Board of Canada': 'cb',
 'Environmental Protection Tribunal of Canada': 'eptc',
 'Federal Commission of Inquiry': 'caci',
 'Federal Public Sector Labour Relations and Employment Board': 'pslreb',
 'Immigration and Refugee Board of Canada': 'irb',
 'Information Commissioner of Canada': 'oic',
 'Investment Industry Regulatory Organization of Canada': 'iiroc',
 'Labour Arbitration Awards': 'cala',
 'Mutual Fund Dealers Association of Canada': 'camfda',
 'Occupational Health and Safety Tribunal Canada': 'ohstc',
 'Pay Equity Commissioner': 'pec',
 'Privacy Commissioner of Canada': 'pcc',
 'Public Servants Disclosure Protection Tribunal': 'psdpt',
 'Public Service Labour Relations Board': 'pssrb',
 'Public Service Staffing Tribunal': 'psst',
 'Ship-source Oil Pollution Fund': 'sopf',
 'Social Security Tribunal of Canada': 'sst',
 'Specific Claims Tribunal Canada': 'sct',
 'Trademarks Opposition Board': 'tmob',
 'Transportation Appeal Tribunal of Canada': 'tatc',
 'Veterans Review and Appeal Board of Canada': 'vrab'}


# %%
#British Columbia courts tribunals and boards

bc_courts = {'All':'', 
 'Court of Appeal for British Columbia': 'bcca',
 'Supreme Court of British Columbia': 'bcsc',
 'Provincial Court of British Columbia': 'bcpc',
 'British Columbia College of Nurses and Midwives': 'bccnm',
 'British Columbia Container Trucking Commissioner': 'bcctc',
 'British Columbia Employment Standards Tribunal': 'bcest',
 'British Columbia Environmental Appeal Board': 'bceab',
 'British Columbia Hospital Appeal Board': 'bchab',
 'British Columbia Human Rights Tribunal': 'bchrt',
 'British Columbia Liquor and Cannabis Regulation Branch': 'bclcrb',
 'British Columbia Review Board': 'bcrb',
 'British Columbia Securities Commission': 'bcsec',
 "British Columbia Workers' Compensation Appeal Tribunal": 'bcwcat',
 'Civil Resolution Tribunal of British Columbia': 'bccrt',
 'College of Dental Surgeons of British Columbia': 'bccds',
 'College of Physicians and Surgeons of British Columbia': 'bccps',
 'Community Care and Assisted Living Appeal Board': 'bcccalab',
 'Energy Resource Appeal Tribunal': 'bcerat',
 'Engineers and Geoscientists British Columbia': 'bcegbc',
 'Financial Services Tribunal': 'bcfst',
 'Forest Appeals Commission': 'bcfac',
 'Health Professions Review Board of British Columbia': 'bchprb',
 'Information and Privacy Commissioner': 'bcipc',
 'Labour Arbitration Awards': 'bcla',
 'Labour Relations Board': 'bclrb',
 'Law Society of British Columbia': 'lsbc',
 'Office of the Registrar of Lobbyists': 'bcorl',
 'Real Estate Council of British Columbia': 'bcrec',
 'Registrar of Mortgage Brokers': 'bcrmb',
 'Skilled Trades BC Appeal Board': 'bcstab',
 'Superintendent of Financial Institutions': 'bcsfi',
 'Superintendent of Pensions': 'bcsp',
 'Superintendent of Real Estate': 'bcsre'}



# %%
ab_courts = {'All': '', 
 'Court of Appeal of Alberta': 'abca',
 "Court of King's Bench of Alberta": 'abkb',
 'Alberta Court of Justice': 'abcj',
 'Alberta Commission of Inquiry': 'abci',
 'Alberta Employment Standards Appeals': 'abesab',
 'Alberta Environmental Appeal Board': 'abeab',
 'Alberta Grievance Arbitration Awards': 'abgaa',
 'Alberta Human Rights Commission': 'ahrc',
 'Alberta Labour Relations Board': 'alrb',
 'Alberta Land and Property Rights Tribunal': 'ablprt',
 'Alberta Land Compensation Board': 'ablcb',
 'Alberta Law Enforcement Review Board': 'ablerb',
 'Alberta Licence and Community Standards Appeal Board': 'ablcsab',
 'Alberta Municipal Government Board': 'abmgb',
 'Alberta Occupational Health and Safety Appeal Body': 'abohsab',
 'Alberta Public Lands Appeal Board': 'abplab',
 'Alberta Residential Tenancy Dispute Resolution Service': 'abrtdrs',
 'Alberta Securities Commission': 'absec',
 'Alberta Surface Rights Board': 'absrb',
 'Alberta Transportation Safety Board': 'abtsb',
 "Appeals Commission for Alberta Workers' Compensation": 'abwcac',
 'Calgary Assessment Review Board': 'abcgyarb',
 'Calgary Subdivision & Development Appeal Board': 'cgysdab',
 'Chartered Professional Accountants of Alberta': 'abcpa',
 'College of Physicians and Surgeons Discipline Committee': 'abcpsdc',
 'College of Physiotherapists of Alberta': 'abcpt',
 'Edmonton Composite Assessment Review Board': 'abecarb',
 'Edmonton Local Assessment Review Board': 'abelarb',
 'Edmonton Subdivision and Development Appeal Board': 'abesdab',
 'Horse Racing Alberta Appeal Tribunal': 'abhraat',
 'Law Society of Alberta': 'abls',
 'Office of the Information and Privacy Commissioner': 'aboipc',
 'Real Estate Council of Alberta': 'abreca',
 'SafeRoads Alberta': 'absra'}

# %%
sk_courts = {'All': '', 
 'Court of Appeal for Saskatchewan': 'skca',
 "Court of King's Bench for Saskatchewan": 'skkb',
 'Provincial Court of Saskatchewan': 'skpc',
 'Saskatchewan District Court': 'skdc',
 'Saskatchewan Surrogate Court': 'sksu',
 'Saskatchewan Unified Family Court': 'skufc',
 'Appeal Tribunal under the Medical Profession Act': 'skatmpa',
 'Automobile Injury Appeal Commission': 'skaia',
 'Financial and Consumer Affairs Authority of Saskatchewan': 'sksec',
 'Information and Privacy Commissioner': 'skipc',
 'Labour Arbitration Awards': 'skla',
 'Law Society of Saskatchewan': 'sklss',
 'Saskatchewan Assessment Commission': 'skac',
 "Saskatchewan Board of Review under the Farmers' Creditors Arrangement Act, 1934": 'skfca',
 'Saskatchewan College of Pharmacy Professionals': 'skcppdc',
 'Saskatchewan Human Rights Commission': 'skhrc',
 'Saskatchewan Human Rights Tribunal': 'skhrt',
 'Saskatchewan Labour Relations Board': 'sklrb',
 'Saskatchewan Local Government Board': 'sklgb',
 'Saskatchewan Master of Titles': 'skmt',
 'Saskatchewan Municipal Board': 'skmb',
 'Saskatchewan Municipal Boards of Revision': 'skmbr',
 'Saskatchewan Office of Residential Tenancies': 'skort',
 'Saskatchewan Provincial Mediation Board': 'skpmb',
 'Saskatchewan Real Estate Commission': 'skrec'
}


# %%
mb_courts = {'All': '', 
 'Court of Appeal of Manitoba': 'mbca',
 "Court of King's Bench of Manitoba": 'mbkb',
 'Provincial Court of Manitoba': 'mbpc',
 'College of Physicians & Surgeons of Manitoba Discipline Committee': 'mbcpsdc',
 'Labour Arbitration Awards': 'mbla',
 'Law Society of Manitoba': 'mbls',
 'Manitoba Health Appeal Board': 'mbhab',
 'Manitoba Human Rights Commission': 'mbhrc',
 'Manitoba Labour Board': 'mblb',
 'Manitoba Securities Commission': 'mbsec'
}

# %%
on_courts = {'All': '', 
 'Court of Appeal for Ontario': 'onca',
 'Superior Court of Justice': 'onsc',
 'Divisional Court': 'onscdc',
 'Small Claims Court': 'onscsm',
 'Ontario Court of Justice': 'oncj',
 'Agriculture, Food & Rural Affairs Appeal Tribunal': 'onafraat',
 'Alcohol and Gaming Commission of Ontario': 'onagc',
 'Assessment Review Board': 'onarb',
 'Association of Professional Engineers of Ontario': 'onape',
 'Building Code Commission': 'onbcc',
 'Capital Markets Tribunal': 'oncmt',
 'Chartered Professional Accountants of Ontario': 'oncpa',
 'Child and Family Services Review Board': 'oncfsrb',
 'College of Audiologists and Speech-Language Pathologists of Ontario': 'oncaspd',
 'College of Chiropodists of Ontario': 'oncocoo',
 'College of Dental Hygienists of Ontario': 'oncdho',
 'College of Massage Therapists of Ontario': 'oncmto',
 'College of Nurses of Ontario Discipline Committee': 'oncno',
 'College of Occupational Therapists of Ontario': 'oncot',
 'College of Optometrists of Ontario': 'onco',
 'College of Physiotherapists of Ontario': 'oncpo',
 'College of Psychologists of Ontario': 'oncpd',
 'College of Traditional Chinese Medicine Practitioners and Acupuncturists of Ontario': 'onctcmpao',
 'College of Veterinarians of Ontario': 'oncvo',
 'Condominium Authority Tribunal': 'oncat',
 'Consent and Capacity Board': 'onccb',
 'Conservation Review Board': 'onconrb',
 'Criminal Injuries Compensation Board': 'oncicb',
 'Environmental Review Tribunal': 'onert',
 'Financial Services Tribunal': 'onfst',
 'Grievance Settlement Board': 'ongsb',
 'Health Professions Appeal and Review Board': 'onhparb',
 'Health Services Appeal and Review Board': 'onhsarb',
 'Horse Racing Appeal Panel': 'onhrap',
 'Human Rights Tribunal of Ontario': 'onhrt',
 'Information and Privacy Commissioner Ontario': 'onipc',
 'Labour Arbitration Awards': 'onla',
 'Landlord and Tenant Board': 'onltb',
 'Law Society Tribunal': 'onlst',
 'Local Planning Appeal Tribunal': 'onlpat',
 'Mining and Lands Tribunal': 'onmlt',
 'Municipal Integrity Commissioners of Ontario': 'onmic',
 'Normal Farm Practices Protection Board': 'onnfppb',
 'Office of the Ombudsman of Ontario': 'onombud',
 'Ontario Animal Care Review Board': 'onacrb',
 'Ontario Civilian Police Commission': 'oncpc',
 'Ontario College of Early Childhood Educators': 'oncece',
 'Ontario College of Pharmacists Discipline Committee': 'oncpdc',
 'Ontario College of Social Workers and Social Service Workers': 'oncswssw',
 'Ontario College of Teachers': 'onoct',
 'Ontario Court of the Drainage Referee': 'ondr',
 'Ontario Custody Review Board': 'oncrb',
 'Ontario Financial Services Commission - Dispute Resolution Services': 'onfscdrs',
 'Ontario Fire Safety Commission': 'onfsc',
 'Ontario Labour Relations Board': 'onlrb',
 'Ontario Land Tribunal': 'onlt',
 'Ontario Licence Appeal Tribunal': 'onlat',
 'Ontario Pay Equity Hearings Tribunal': 'onpeht',
 'Ontario Physician Payment Review Board': 'onpprb',
 'Ontario Physicians and Surgeons Discipline Tribunal': 'onpsdt',
 'Ontario Public Service Grievance Board': 'onpsgb',
 'Ontario Racing Commission': 'onrc',
 'Ontario Registered Psychotherapists Discipline Tribunal': 'onrpdt',
 'Ontario Securities Commission': 'onsec',
 'Ontario Social Benefits Tribunal': 'onsbt',
 'Ontario Special Education (English) Tribunal': 'onset',
 'Ontario Workplace Safety and Insurance Appeals Tribunal': 'onwsiat',
 'Ontario Workplace Safety and Insurance Board': 'onwsib',
 'Royal College of Dental Surgeons of Ontario': 'onrcdso',
 'Skilled Trades Ontario': 'onst',
 'Toronto Local Appeal Body': 'ontlab'}

# %%
qc_courts = {'All': '', 
 'Court of Appeal of Quebec': 'qcca',
 'Superior Court': 'qccs',
 'Court of Quebec': 'qccq',
 'Municipal Courts': 'qccm',
 'Administrative Tribunal of Québec': 'qctaq',
 'Arbitration - The Guarantee Plan For New Residential Buildings': 'qcoagbrn',
 'Autorité des marchés publics': 'qcamp',
 'Barreau du Québec Disciplinary Council': 'qccdbq',
 'Collège des médecins du Québec Disciplinary Council': 'qccdcm',
 "Comité de discipline de l'organisme d'autoréglementation du courtage immobilier du Québec": 'qcoaciq',
 "Comité de discipline de la Chambre de l'assurance de dommages": 'qccdchad',
 'Comité de discipline de la Chambre de la sécurité financière': 'qccdcsf',
 "Commission d'accès à l'information": 'qccai',
 "Commission d'appel en matière de lésions professionnelles du Québec": 'qccalp',
 "Commission de l'équité salariale": 'qcces',
 'Commission de la fonction publique': 'qccfp',
 'Commission de la santé et de la sécurité du travail': 'qccsst',
 'Commission de protection du territoire agricole du Québec': 'qccptaq',
 "Commission de reconnaissance des associations d'artistes et des associations de producteurs": 'qccraaap',
 'Commission des lésions professionnelles du Québec': 'qcclp',
 'Commission des normes, de l’équité, de la santé et de la sécurité du travail': 'qccnesst',
 'Commission des relations du travail': 'qccrt',
 'Commission des services juridiques': 'qccsj',
 'Commission des transports du Québec': 'qcctq',
 'Commission des valeurs mobilières du Québec': 'qccvm',
 'Commission municipale du Québec': 'qccmnq',
 "Conseil de discipline de l'Ordre des acupuncteurs du Québec": 'qcoaq',
 "Conseil de discipline de l'Ordre des administrateurs agréés du Québec": 'qcadmaq',
 "Conseil de discipline de l'Ordre des agronomes du Québec": 'qcagq',
 "Conseil de discipline de l'Ordre des architectes du Québec": 'qcoarq',
 "Conseil de discipline de l'Ordre des arpenteurs-géomètres du Québec": 'qcoagq',
 "Conseil de discipline de l'Ordre des audioprothésistes du Québec": 'qcoapq',
 "Conseil de discipline de l'Ordre des chiropraticiens du Québec": 'qcocq',
 "Conseil de discipline de l'Ordre des comptables professionnels agréés du Québec": 'qccpa',
 "Conseil de discipline de l'Ordre des criminologues du Québec": 'qccdcrim',
 "Conseil de discipline de l'Ordre des dentistes du Québec": 'qcodq',
 "Conseil de discipline de l'Ordre des ergothérapeutes du Québec": 'qcoeq',
 "Conseil de discipline de l'Ordre des infirmières et infirmiers auxiliaires du Québec": 'qccdoiia',
 "Conseil de discipline de l'Ordre des infirmières et infirmiers du Québec": 'qccdoii',
 "Conseil de discipline de l'Ordre des ingénieurs du Québec": 'qccdoiq',
 "Conseil de discipline de l'Ordre des médecins vétérinaires du Québec": 'qccdomv',
 "Conseil de discipline de l'Ordre des opticiens d'ordonnances du Québec": 'qccdoooq',
 "Conseil de discipline de l'Ordre des optométristes du Québec": 'qcooq',
 "Conseil de discipline de l'Ordre des pharmaciens du Québec": 'qccdopq',
 "Conseil de discipline de l'Ordre des podiatres du Québec": 'qcopodq',
 "Conseil de discipline de l'Ordre des psychologues du Québec": 'qcopq',
 "Conseil de discipline de l'Ordre des sages-femmes du Québec": 'qccdosfq',
 "Conseil de discipline de l'Ordre des sexologues du Québec": 'qcopsq',
 "Conseil de discipline de l'Ordre des techniciens et techniciennes dentaires du Québec": 'qccdottdq',
 "Conseil de discipline de l'Ordre des technologues en imagerie médicale et en radio-oncologie du Québec": 'qcotimro',
 "Conseil de discipline de l'Ordre des technologues professionnels du Québec": 'qcotpq',
 "Conseil de discipline de l'Ordre des urbanistes du Québec": 'qcouq',
 "Conseil de discipline de l'Ordre professionnel de la physiothérapie du Québec": 'qcoppq',
 "Conseil de discipline de l'Ordre professionnel des chimistes du Québec": 'qcochq',
 "Conseil de discipline de l'Ordre professionnel des conseillers en ressources humaines et en relations industrielles agrées du Québec": 'qccdrhri',
 "Conseil de discipline de l'Ordre professionnel des denturologistes du Québec": 'qcodlq',
 "Conseil de discipline de l'Ordre professionnel des évaluateurs agréés du Québec": 'qcoeaq',
 "Conseil de discipline de l'Ordre professionnel des ingénieurs forestiers du Québec": 'qcoifq',
 "Conseil de discipline de l'Ordre professionnel des orthophonistes et audiologistes du Québec": 'qcooaq',
 "Conseil de discipline de l'Ordre professionnel des technologistes médicaux du Québec": 'qcotmq',
 "Conseil de discipline de l'Ordre professionnel des traducteurs, terminologues et interprètes agréés du Québec": 'qcottiaq',
 "Conseil de discipline de l'Ordre professionnel des travailleurs sociaux et des thérapeutes conjugaux et familiaux du Québec": 'qcotstcfq',
 'Conseil de discipline de la Chambre des huissiers de justice du Québec': 'qccdhj',
 'Conseil de discipline de la Chambre des notaires du Québec': 'qccdnq',
 "Conseil de discipline des Conseillers et conseillères d'orientation du Québec": 'qccdccoq',
 'Conseil de discipline des psychoéducateurs et psychoéducatrices du Québec': 'qccdppq',
 'Conseil de la justice administrative': 'qccja',
 'Conseil de la magistrature': 'qccmq',
 'Conseil des services essentiels': 'qccse',
 'Corporation des maîtres électriciens du Québec': 'qccmeq',
 'Corporation of Master Pipe-Mechanics of Québec': 'qccmpmq',
 'Human Rights Tribunal': 'qctdp',
 'Labour Arbitration Awards (including Conférence des arbitres)': 'qcla',
 'Labour Commissioner': 'qcct',
 'Labour Court': 'qctt',
 'Office de la langue française': 'qcolf',
 'Ordre des diététistes-nutritionnistes du Québec': 'qccddtp',
 'Ordre des hygiénistes dentaires du Québec': 'qcohdq',
 'Ordre professionnel des géologues du Québec': 'qcopgq',
 'Ordre professionnel des inhalothérapeutes du Québec': 'qcopiq',
 'Professions Tribunal': 'qctp',
 'Quebec Autorité des marchés financiers': 'qcamf',
 "Régie de l'énergie": 'qcrde',
 'Régie des alcools des courses et des jeux': 'qcracj',
 'Régie des marchés agricoles et alimentaires du Québec': 'qcrmaaq',
 "Régie du Bâtiment - licences d'entrepreneur de construction": 'qcrbq',
 'Tribunal administratif de déontologie policière': 'qctadp',
 'Tribunal administratif des marchés financiers': 'qctmf',
 'Tribunal administratif du logement': 'qctal',
 'Tribunal administratif du travail': 'qctat',
 "Tribunal d'arbitrage (performing, recording and film artists)": 'qctaa',
 "Tribunal d'arbitrage (RQ and CARRA)": 'qcta'}

# %%
nb_courts = {'All': '', 
 'Court of Appeal of New Brunswick': 'nbca',
 "Court of King's Bench of New Brunswick": 'nbkb',
 'Provincial Court': 'nbpc',
 'Board of Inquiry Under the Human Rights Act': 'nbbihra',
 'Financial and Consumer Services Commission': 'nbfcsc',
 'Financial and Consumer Services Tribunal': 'nbfcst',
 'Labour Arbitration Awards': 'nbla',
 'Law Society of New Brunswick': 'nblsb',
 'New Brunswick Assessment and Planning Appeal Board': 'nbapab',
 'New Brunswick College of Pharmacists': 'nbcph',
 'New Brunswick Labour and Employment Board': 'nbleb',
 'New Brunswick Real Estate Association': 'nbrea',
 'Ombud New Brunswick': 'nbombud',
 'Workers’ Compensation Appeals Tribunal': 'nbwcat'}

# %%
ns_courts = {'All': '', 
 'Nova Scotia Court of Appeal': 'nsca',
 'Supreme Court of Nova Scotia': 'nssc',
 'Supreme Court of Nova Scotia (Family Division)': 'nssf',
 'Provincial Court of Nova Scotia': 'nspc',
 'Small Claims Court': 'nssm',
 'Nova Scotia Probate Court': 'nspr',
 'Nova Scotia Family Court': 'nsfc',
 'College of Physicians and Surgeons of Nova Scotia': 'nscps',
 'Labour Arbitration Awards': 'nsla',
 'Nova Scotia Animal Welfare Appeal Board': 'nsawab',
 "Nova Scotia Barristers' Society Hearing Panel": 'nsbs',
 'Nova Scotia Human Rights Commission': 'nshrc',
 'Nova Scotia Labour Board': 'nslb',
 'Nova Scotia Labour Relations Board': 'nslrb',
 'Nova Scotia Labour Standards Tribunal': 'nslst',
 'Nova Scotia Occupational Health and Safety Appeal Panel': 'nsohsap',
 'Nova Scotia Police Review Board': 'nsprb',
 'Nova Scotia Securities Commission': 'nssec',
 'Nova Scotia Serious Incident Response Team': 'nssirt',
 'Nova Scotia Utility and Review Board': 'nsuarb',
 "Nova Scotia Workers' Compensation Appeals Tribunal": 'nswcat',
 'Office of the Information and Privacy Commissioner for Nova Scotia': 'nsoipc'}

# %%
pe_courts = {'All': '', 
 'Prince Edward Island Court of Appeal': 'pescad',
 'Supreme Court of Prince Edward Island': 'pesctd',
 'Provincial Court of Prince Edward Island': 'pepc',
 'Information and Privacy Commissioner': 'peipc',
 'Labour Arbitration Awards': 'pela',
 'Prince Edward Island Human Rights Commission': 'peihrc',
 'Prince Edward Island Labour Relations Board': 'pelrb',
 'Prince Edward Island Regulatory & Appeals Commission': 'peirac'}

# %%
nl_courts = {'All': '', 
 'Court of Appeal of Newfoundland and Labrador': 'nlca',
 'Supreme Court of Newfoundland and Labrador': 'nlsc',
 'Provincial Court of Newfoundland and Labrador': 'nlpc',
 'College of Physicians and Surgeons of Newfoundland and Labrador': 'nlcps',
 'Information and Privacy Commissioner': 'nlipc',
 'Labour Arbitration Awards': 'nlla',
 'Law Society of Newfoundland and Labrador': 'nlls',
 'Newfoundland and Labrador Human Rights Commission': 'nlhrc',
 'Newfoundland and Labrador Labour Relations Board': 'nllrb',
 'Newfoundland and Labrador Pharmacy Board': 'nlpb'}

# %%
yk_courts = {'All': '', 
 'Court of Appeal of Yukon': 'ykca',
 'Supreme Court of Yukon': 'yksc',
 'Territorial Court of Yukon': 'yktc',
 'Small Claims Court of the Yukon': 'yksm',
 'Labour Arbitration Awards': 'ytla',
 'Yukon Human Rights Commission (Board of Adjudication)': 'ykhrc',
 'Yukon Public Service Labour Relations Board': 'ytpslrb',
 'Yukon Residential Tenancies Office': 'ytrto',
 'Yukon Teachers Labour Relations Board': 'yttlrb'}

# %%
nt_courts = {'All': '', 
 'Court of Appeal for the Northwest Territories': 'ntca',
 'Supreme Court of the Northwest Territories': 'ntsc',
 'Territorial Court of the Northwest Territories': 'nttc',
 'Youth Justice Court': 'ntyjc',
 'Employment Standards Appeals Office': 'ntlsb',
 'Human Rights Adjudication Panel': 'nthrap',
 'Labour Arbitration Awards': 'ntla',
 'Law Society of the Northwest Territories': 'ntls',
 'Northwest Territories and Nunavut Workers’ Compensation Appeals Tribunal': 'ntwcat',
 'Northwest Territories Assessment Appeal Tribunal': 'ntaat',
 'Northwest Territories Information and Privacy Commissioner': 'ntipc',
 'Northwest Territories Liquor Licensing Board': 'ntllb',
 'Northwest Territories Office of Superintendent of Securities': 'ntsec',
 'Rental Officer': 'ntro',
 'Yellowknife Development Appeal Board': 'ntydab'}

# %%
nu_courts = {'All': '', 
 'Court of Appeal of Nunavut': 'nuca',
 'Nunavut Court of Justice': 'nucj',
 'Youth Justice Court of Nunavut': 'yjcn',
 'Information and Privacy Commissioner': 'nuipc',
 'Labour Arbitration Awards': 'nula',
 'Law Society of Nunavut': 'nuls',
 'Northwest Territories and Nunavut Workers’ Compensation Appeals Tribunal': 'nuwcat',
 'Nunavut Human Rights Tribunal': 'nuhrt',
 'Nunavut Registrar of Securities': 'nusec'}

# %%
#Jurisdiction to courts

all_ca_jurisdiction_court_pairs = {'All': {'All': 'All'}, 
                                   'Canada (Federal)': ca_courts, 
                                   'British Columbia': bc_courts,
                                  'Alberta': ab_courts, 
                                  'Saskatchewan': sk_courts, 
                                  'Manitoba': mb_courts, 
                                  'Ontario': on_courts, 
                                  'Quebec': qc_courts, 
                                  'New Brunswick': nb_courts, 
                                  'Nova Scotia': ns_courts, 
                                  'Prince Edward Island': pe_courts, 
                                  'Newfoundland and Labrador': nl_courts, 
                                  'Yukon': yk_courts, 
                                  'Northwest Territories': nt_courts, 
                                  'Nunavut': nu_courts}


# %%
court_tribunal_types = {'All courts and tribunals': '', 
'All courts': 'courts', 
'Appeal courts': 'appellate-courts', 
'All tribunals': 'tribunals', 
'Tribunals: labour': 'labor-relations', 
'Tribunals: privacy': 'privacy-commissioner', 
'Tribunals: human rights': 'human-rights', 
'Tribunals: discipline': 'discipline', 
'Tribunals: securities': 'securities'
}

# %%
all_subjects = ['Access to information and privacy', 'Administrative remedies', 'Appeal', 'Arbitration', 'Bankruptcy and insolvency', 'Business', 'Child custody and access', 'Child protection', 'Citizenship and immigration', 'Commerce and industry', 'Constitution', 'Contracts', 'Creditors and debtors', 'Criminal or statutory infractions', 'Damages', 'Defences', 'Environment', 'Evidence', 'Family', 'Guardianship', 'Health and safety', 'Indigenous peoples', 'Insurance', 'Intellectual property', 'International', 'Interpretation', 'Judicial review', 'Labour and employment', 'Motor vehicles', 'Municipalities', 'Negligence', 'Practice and procedure', 'Professions and occupations', 'Property and trusts', 'Public administration', 'Residential tenancies', 'Rights and freedoms', 'Search and seizure', 'Sentencing', 'Support and maintenance', 'Taxation', 'Torts', 'Wills and estates', 'Young offenders']


# %%
#Function turning search terms to search results url
def ca_search(jurisdiction  =  'All', 
              court = 'All', 
              phrase = '', 
              case_name_mnc= '', 
              court_tribunal_type = 'All courts and tribunals', 
              subjects = '', 
             on_this_date = '',
            after_date = '',
            before_date = '',
              #cited = '', 
              #year = ''
             ):

    today = datetime.now().strftime("%Y-%m-%d")
    
    #Default base url with jurisdiction and court to remove if not entered
    base_url = f'https://www.canlii.org/en/jurisdiction_param/#search/type=decision&date=on_this_date_param&startDate=after_date_param&endDate={today}&ccType=type_param&topics=subjects_param&jId=jurisdiction_param,unspecified&text=phrase_param&id=case_name_mnc_param'
    
    #Add jurisdiction, court or year
    if jurisdiction != 'All':

        base_url = base_url.replace('jurisdiction_param', f'{all_ca_jurisdictions[jurisdiction]}')
    else:
        base_url = base_url.replace('&jId=jurisdiction_param,unspecified', '').replace('jurisdiction_param/', '')

    if court != 'All':

        base_url = f'https://www.canlii.org/en/jurisdiction_param/court_param/#search/type=decision&date=on_this_date_param&startDate=after_date_param&endDate={today}&ccType=type_param&topics=subjects_param&ccId=ccid_param&text=phrase_param&id=case_name_mnc_param'

        base_url = base_url.replace('jurisdiction_param', f'{all_ca_jurisdictions[jurisdiction]}')

        if court == 'Supreme Court of Canada':
            
            ccID = 'csc-scc'

        elif court == 'Supreme Court of Canada - Applications for Leave':

            ccID = 'csc-scc-al'

        else:
            ccID = all_ca_jurisdiction_court_pairs[jurisdiction][court]

        base_url = base_url.replace('court_param', f'{all_ca_jurisdiction_court_pairs[jurisdiction][court]}')
        
        base_url = base_url.replace('ccid_param', ccID)
    
    else:
        
        base_url = base_url.replace('&ccId=court_param', '').replace('court_param/', '')

    #if year != '':
    #Year is a browse function

    #Add court or tribunal type

    if court_tribunal_types[court_tribunal_type] != '':
        base_url = base_url.replace('type_param', court_tribunal_types[court_tribunal_type])

    else:
        base_url = base_url.replace('&ccType=type_param', '')

    #Add dates

    if before_date != '':
        base_url = base_url.replace('before_date_param', before_date)

    else:
        print('Decision date is after not entered.')
        #base_url = base_url.replace(f'&endDate={today}', '')

    if after_date != '':
        base_url = base_url.replace('after_date_param', after_date)

    else:
        base_url = base_url.replace('&startDate=after_date_param', '')

    if ((on_this_date != '')  and (before_date == '') and (after_date == '')):
        base_url = base_url.replace('on_this_date_param', on_this_date)

    else:
        base_url = base_url.replace('&date=on_this_date_param', '')

    #Add topics 
    if subjects != '':
        base_url = base_url.replace('subjects_param', subjects)

    else:
        base_url = base_url.replace('&topics=subjects_param', '')

    
    #Add search terms
    
    if phrase != '':
        base_url = base_url.replace('phrase_param', phrase)
    else:
        base_url = base_url.replace('&text=phrase_param', '')

        #base_url += f"&text={phrase}"

    if case_name_mnc != '':
        #base_url += f"&id={case_name_mnc}"
        base_url = base_url.replace('case_name_mnc_param', case_name_mnc)
    else:
        base_url = base_url.replace('&id=case_name_mnc_param', '')

    #Can't get noteup/discussion to work given dynamic

    #if cited != '':
        #base_url += f"&origin1=%2Fen%2Freflex%2F937222.html&nquery1={cited}"
    
    response = requests.get(base_url)
    response.raise_for_status()
    # Process the response (e.g., extract relevant information)
    # Your code here...
    return response.url


# %%
def search_results_to_judgment_links(url_search_results, judgment_counter_bound):
    #Start counter
    
    counter = 1
    
    #Load page
    
    #browser = webdriver.Firefox(options=opts)

    #browser = get_driver()
    
    browser.get(url_search_results)
    
    elements = browser.find_elements(By.CLASS_NAME, "result ")
    
    #Get number of results
    case_num = len(elements)
    
    #print(f"Elements: {case_num}")
    
    #pause.seconds(np.random.randint(10, 20))
    
    while case_num <= judgment_counter_bound:
    
        if '<div id="loadMoreResults" class="d-print-none" style="display:none;">' not in browser.page_source:
    
            load_more = browser.find_element(By.ID, "loadMoreResults")
            
            #pause.seconds(np.random.randint(10, 20))
            
            browser.execute_script("arguments[0].click();", load_more);
            
            elements = browser.find_elements(By.CLASS_NAME, "result ")
    
            case_num = len(elements)
    
        else:
            break
    
    #print(f"Elements: {case_num}")
    
    #Start collecting cases
    case_links = []
    
    for element in elements:
        
        if counter <= judgment_counter_bound:
            case_info_raw = element.text
            case_name = case_info_raw.split('\n')[1]
            
            url = element.get_attribute('innerHTML').split('data-lbh-document-url="')[1].split('" data-lbh-path')[0]
            
            case_info = {'name': case_name, 'url': url}
            
            case_links.append(case_info['url'])
            
            counter = counter + 1
    
        else:
            break

    return case_links


# %%
meta_labels = ['lbh-document-url', 'lbh-title', "lbh-citation", "lbh-decision-date", "lbh-collection", "lbh-jurisdiction", "lbh-keywords", "lbh-subjects"]
meta_names = ['Hyperlink to CanLII', 'Case name', "Medium neutral citation", "Decision date", "Collection", "Jurisdiction", "Keywords", "Subjects"]


# %%
meta_labels_droppable = ["Decision date", "Collection", "Jurisdiction", "Keywords", "Subjects", 'Court', 'File number', 'Other citations', 'Most recent unfavourable mention']


# %%
#meta_dict = {}

#for name in meta_names:
    #index = meta_names.index(name)
    #meta_dict.update({name: meta_labels[index]})

# %%
meta_dict = {
 'Case name': 'lbh-title',
    'Hyperlink to CanLII': 'lbh-document-url',
 'Medium neutral citation': 'lbh-citation',
 'Decision date': 'lbh-decision-date',
 'Court': 'lbh-collection',
 'Jurisdiction': 'lbh-jurisdiction',
 'Keywords': 'lbh-keywords',
 'Subjects': 'lbh-subjects'}


# %%
def meta_judgment_dict(judgment_url):

    headers = {'User-Agent': 'whatever'}
    page = requests.get(judgment_url, headers=headers)
    soup = BeautifulSoup(page.content, "lxml")
    meta_tags = soup.find_all("meta")
    
    judgment_dict = {}

    #Attach metadata
    for meta in meta_dict.keys():
        try:
            meta_content = soup.select(f'meta[name={meta_dict[meta]}]')[0].attrs["content"]
        except:
            meta_content = ''
        judgment_dict.update({meta: meta_content})

    judgment_dict['Hyperlink to CanLII'] = link(judgment_dict['Hyperlink to CanLII'])

    #Date, case number, citations
    
    extra_metas = soup.find_all('div', class_ = "row py-1")
    
    for meta in extra_metas:
        #if 'date:' in meta.text.lower():
            #judgment_dict.update({'Date': meta.text})
    
        if 'file number:' in meta.text.lower():
            judgment_dict.update({'File number': meta.text.replace('\n', '').replace('File number:', '').replace('File numbers:', '')})
    
        #if 'citation:' in meta.text.lower():
            #judgment_dict.update({'Citation': meta.text})
    
        if 'other citation' in meta.text.lower():
            judgment_dict.update({'Other citations': meta.text.replace('\n', '').replace('Other citation:', '').replace('Other citations:', '')})

        if 'Most recent unfavourable mention' in meta.text.lower():
            judgment_dict.update({'Most recent unfavourable mention': meta.text.replace('\n', '').replace('Most recent unfavourable mention:', '')})

    #Judgment text

    judgment_text = soup.find('div', class_ ='documentcontent').get_text(strip=True)

    judgment_dict.update({'judgment': judgment_text})
    
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
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    url_search_results = ca_search(jurisdiction  = df_master.loc[0, 'Jurisdictions'],
                                   court = df_master.loc[0, 'Courts'], 
                                   phrase = df_master.loc[0, 'Document text'], 
                                   case_name_mnc= df_master.loc[0, 'Case name, citation or docket'],
                                  subjects = df_master.loc[0, 'Subjects'],
                                   court_tribunal_type = df_master.loc[0, 'Court or tribunal type'], 
                                   on_this_date = df_master.loc[0, 'Decision date is'],
                                    after_date = df_master.loc[0, 'Decision date is after'],
                                    before_date = df_master.loc[0, 'Decision date is before'], 
                                   #cited = '', 
                                   #year = ''
                                  )
        
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    judgments_links = search_results_to_judgment_links(url_search_results, judgments_counter_bound)

    for link in judgments_links:

        judgment_dict = meta_judgment_dict(link)

        judgments_file.append(judgment_dict)
        pause.seconds(np.random.randint(10, 20))
    
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
    
    #Combining catchwords into new column
    
    #Conduct search
    
    url = ca_search(jurisdiction  = df_master.loc[0, 'Jurisdictions'],
                                   court = df_master.loc[0, 'Courts'], 
                                   phrase = df_master.loc[0, 'Document text'], 
                                   case_name_mnc= df_master.loc[0, 'Case name, citation or docket'],
                                  subjects = df_master.loc[0, 'Subjects'],
                                   court_tribunal_type = df_master.loc[0, 'Court or tribunal type'], 
                                   on_this_date = df_master.loc[0, 'Decision date is'],
                                    after_date = df_master.loc[0, 'Decision date is after'],
                                    before_date = df_master.loc[0, 'Decision date is before'], 
                                   #cited = '', 
                                   #year = ''
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

# %%
#Canada specific session states

#Disable toggles
if 'all_jurisdiction' not in st.session_state:
    st.session_state["all_jurisdiction"] = 'All'

#Disable toggles
if 'court' not in st.session_state:
    st.session_state["court"] = 'All'

if 'year' not in st.session_state:
    st.session_state["year"] = ''


# %% [markdown]
# ## Form before AI

# %%
#Create form

return_button = st.button('RETURN to first page')

st.header(f"You have selected to study :blue[judgments of the Canadian courts, boards and tribunals].")

#    st.header("Judgment Search Criteria")

st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.
""")

st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')

st.subheader("Court, board or tribunal to cover")

jurisdiction_entry  = st.selectbox(label = 'Select or type in the jurisdiction to cover', options = list(all_ca_jurisdictions.keys()), index = list(all_ca_jurisdictions.keys()).index('All'))

st.session_state["all_jurisdiction"] = jurisdiction_entry

if st.session_state.all_jurisdiction != 'All':

    #st.write(all_ca_jurisdiction_court_pairs[st.session_state.all_jurisdiction])
    
    courts_entry = st.selectbox(label = 'Select or type in the court, board or tribunal to cover', options = list(all_ca_jurisdiction_court_pairs[st.session_state.all_jurisdiction].keys()), index = list(all_ca_jurisdiction_court_pairs[st.session_state.all_jurisdiction].keys()).index('All'))

    st.session_state["court"] = courts_entry

else:
    st.session_state["court"] = 'All'

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [CanLII](https://www.canlii.org/en/). This section largely mimics their judgments search function except the noteup/discussion function.
""")

phrase_entry = st.text_input('Document text')

case_name_mnc_entry = st.text_input("Case name, citation or docket")

court_tribunal_type_entry = st.selectbox("Court or tribunal type", options = list(court_tribunal_types.keys()), index = 0)

on_this_date_entry = st.date_input('Decision date is', value = None, format="YYYY-MM-DD", min_value = date(1800, 1, 1))

after_date_entry = st.date_input('Decision date is after', value = None, format="YYYY-MM-DD", min_value = date(1800, 1, 1))

before_date_entry = st.date_input('Decision date is before', value = None, format="YYYY-MM-DD", min_value = date(1800, 1, 1))

subjects_entry = st.multiselect(label = 'Subjects', options = all_subjects)
st.caption('If left blank, all subjects will be covered.')

#Can't get Noteup/Discussion to work given dynamic
#cited_entry = st.text_input('Noteup/Discussion: cited case names, legislation titles, citations or dockets')

#Year and month are browse functions, need a separate url getter

#if st.session_state.court != 'All':

    #year_entry = st.text_input(label = 'Choose a year')

    #link_to_canlii = f"https://www.canlii.org/en/{all_ca_jurisdictions[st.session_state.all_jurisdiction]}/{all_ca_jurisdiction_court_pairs[st.session_state.all_jurisdiction][st.session_state.court]}/"

    #st.caption(f'[Relatively earlier]({link_to_canlii}) judgments will not be collected.')
    
    #if year_entry:
        
        #wrong_number_warning = f'You have not entered a valid year. The program will not filter any search results by year.'
    
        #try:
    
            #year_int = int(year_entry)

            #if ((year_int >= 1800) and (year_int <= datetime.now().year)):
    
                #st.session_state["year"] = year_entry
            
            #else:
                
                #st.warning(wrong_number_warning)
                
                #st.session_state["year"] = ''
        
        #except:
            #st.warning(wrong_number_warning)
            #st.session_state["year"] = ''
#else:
    #st.session_state["year"] = '' 
 
st.markdown("""You can preview the judgments returned by your search terms on the CanLII after you have entered some search terms.

You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")

preview_button = st.button('PREVIEW on the CanLII (in a popped up window)')

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

    #Check whether search terms entered

    ca_search_terms = str(case_name_mnc_entry)  + str(phrase_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry) + str(subjects_entry)
    
    if ca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
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
        
        st.write('Your results will be available for download soon. The estimated waiting time is about 2-3 minutes per 10 judgments.')
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
                
                st.session_state["page_from"] = 'pages/FCA.py'
        
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
                #conn.update(worksheet="CTH", data=df_to_update, )
            
            except Exception as e:
                st.error('Your search terms may not return any judgments. Please press the PREVIEW button above to double-check.')
                st.exception(e)



# %%
if keep_button:

    #Check whether search terms entered

    ca_search_terms = str(case_name_mnc_entry)  + str(phrase_entry) + str(on_this_date_entry) + str(after_date_entry) + str(before_date_entry) + str(subjects_entry)
    
    if ca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    elif ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual_output)>0)):
        st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')
        
        if 'need_resetting' not in st.session_state:
            
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

# %%
