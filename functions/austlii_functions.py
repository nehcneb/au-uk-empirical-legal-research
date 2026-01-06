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
#from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
from urllib.request import urlretrieve
import os
import urllib.request
import pypdf
import io
from io import BytesIO
import pdf2image
#from PIL import Image
import math
from math import ceil
import copy

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
#import streamlit_ext as ste
from streamlit_extras.stylable_container import stylable_container

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb


# %%
#Import functions
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input, date_parser, split_title_mnc
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, default_judgment_counter_bound, no_results_msg, search_error_note


# %% [markdown]
# # AustLII search engine

# %%
from functions.common_functions import link, pdf_image_judgment

# %%
#Scrape javascript

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys


options = Options()
options.add_argument("--disable-gpu")
#options.add_argument("--headless")
options.add_argument('--no-sandbox')  
options.add_argument('--disable-dev-shm-usage')  

if 'Users/Ben' not in os.getcwd(): 

    from pyvirtualdisplay import Display
    
    display = Display(visible=0, size=(1200, 1600))  
    display.start()

    options.add_argument("window-size=1200x600")

#@st.cache_resource(show_spinner = False, ttl=600)
def get_driver():

    browser = webdriver.Chrome(options=options)

    browser.implicitly_wait(15)
    browser.set_page_load_timeout(30)

    if 'Users/Ben' in os.getcwd():
        browser.minimize_window()
    
    return browser



# %%
#Definitions for search function

austlii_methods_dict = {'Auto search': 'auto',
                        'Boolean query': 'boolean',
                        'Any of these words': 'any',
                        'All of these words': 'all',
                        'Exact phrase': 'phrase', 
                         'Document title': 'title'
                       }

austlii_sort_dict = {'Relevance': 'relevance',
                    'Citation frequency: most often cited': 'cited-most',
                     'Citation frequency: least often cited': 'cited-least',
                    'Database': 'database',
                     'Date: latest first': 'date-latest', 
                    'Date: earliest first': 'date-earliest', 
                     'Title': 'title', 
                   }

austlii_highlight_dict = {'Yes': '1', 'No': '0'}

# %%
#Initialise default databases

austlii_databases_default_dict = {'All Case Law Databases': 'au/cases'}

# %%
austlii_databases_dict = {'All AustLII Databases': '',
 'All Legislation Databases': 'au/legis',
 'All Case Law Databases': 'au/cases',
 'All Law Journals Databases': 'au/journals',
 'All Secondary Materials Databases (includes journals)': 'au/journals+au/other',
 'Commonwealth: All Primary Materials': 'au/cases/cth au/legis/cth',
 'Commonwealth: All Legislation': 'au/legis/cth',
 'Commonwealth: All Cases': 'au/cases/cth',
 'Commonwealth: Bills': 'au/legis/cth/bill',
 'Commonwealth: Bills Explanatory Memoranda': 'au/legis/cth/bill_em',
 'Commonwealth: Bills Digests': 'au/legis/cth/digest',
 'Commonwealth: Consolidated Acts': 'au/legis/cth/consol_act',
 'Commonwealth: Consolidated Regulations': 'au/legis/cth/consol_reg',
 'Commonwealth: Legislation Tables': 'au/legis/cth/table',
 'Commonwealth: Numbered Acts': 'au/legis/cth/num_act',
 'Commonwealth: Numbered Regulations': 'au/legis/cth/num_reg',
 'Commonwealth: Numbered Regulations Explanatory Statements': 'au/legis/cth/num_reg_es',
 'Commonwealth: Repealed Acts': 'au/legis/cth/repealed_act',
 'Commonwealth: Repealed Regulations': 'au/legis/cth/repealed_reg',
 'Commonwealth: Administrative Appeals Tribunal': 'au/cases/cth/AATA',
 'Commonwealth: Administrative Review Tribunal': 'au/cases/cth/ARTA',
 'Commonwealth: Australian Coal Industry Tribunal': 'au/cases/cth/ACIndT',
 'Commonwealth: Australian Competition Tribunal': 'au/cases/cth/ACompT',
 'Commonwealth: Australian Industrial Relations Commission': 'au/cases/cth/AIRC',
 'Commonwealth: Australian Industrial Relations Commission - Full Bench': 'au/cases/cth/AIRCFB',
 'Commonwealth: Australian Information Commissioner': 'au/cases/cth/AICmr',
 'Commonwealth: Australian Information Commissioner Case Notes': 'au/cases/cth/AICmrCN',
 'Commonwealth: Australian Takeovers Panel': 'au/cases/cth/ATP',
 'Commonwealth: Copyright Tribunal': 'au/cases/cth/ACopyT',
 'Commonwealth: Defence Force Discipline Appeal Tribunal': 'au/cases/cth/ADFDAT',
 'Commonwealth: Fair Work Australia (all)': 'au/cases/cth/FWA au/cases/cth/FWAA au/cases/FWAFB',
 'Commonwealth: Fair Work Commission (all)': 'au/cases/cth/FWC au/cases/cth/FWCFB au/cases/FWCD',
 'Commonwealth: Family Court of Australia': 'au/cases/cth/FamCA',
 'Commonwealth: Family Court of Australia (Full Court)': 'au/cases/cth/FamCAFC',
 'Commonwealth: Federal Circuit and Family Court of Australia - Division 1 Appellate Jurisdiction': 'au/cases/cth/FedCFamC1A',
 'Commonwealth: Federal Circuit and Family Court of Australia - Division 2 General Federal Law': 'au/cases/cth/FedCFamC2G',
 'Commonwealth: Federal Circuit Court of Australia': 'au/cases/cth/FCCA',
 'Commonwealth: Federal Court of Australia': 'au/cases/cth/FCA',
 'Commonwealth: Federal Court of Australia - Full Court': 'au/cases/cth/FCAFC',
 'Commonwealth: Federal Magistrates Court of Australia': 'au/cases/cth/FMCA',
 'Commonwealth: Federal Magistrates Court of Australia - Family Law': 'au/cases/cth/FMCAfam',
 'Commonwealth: High Court of Australia': 'au/cases/cth/HCA',
 'Commonwealth: High Court of Australia Transcripts': 'au/cases/cth/HCATrans',
 'Commonwealth: High Court of Australia Special Leave Dispositions': 'au/cases/cth/HCASL',
 'Commonwealth: High Court of Australia Bulletins': 'au/other/hca/bulletin',
 'Commonwealth: High Court of Australia Appeal Short Particulars': 'au/other/HCAASP',
 'Commonwealth: Human Rights and Equal Opportunity Commission': 'au/cases/cth/HREOCA',
 'Commonwealth: Immigration Review Tribunal': 'au/cases/cth/IRTA',
 'Commonwealth: Industrial Relations Court': 'au/cases/cth/IRCA',
 'Commonwealth: IP Australia - Australian Designs Office': 'au/cases/cth/ADO',
 'Commonwealth: IP Australia - Australian Patent Office': 'au/cases/cth/APO',
 'Commonwealth: IP Australia - Australian Trade Marks Office': 'au/cases/cth/ATMO',
 'Commonwealth: IP Australia - Australian Trade Marks Office - Geographical Indication': 'au/cases/cth/ATMOGI',
 'Commonwealth: Migration Review Tribunal': 'au/cases/cth/MRTA',
 'Commonwealth: National Native Title Tribunal': 'au/cases/cth/NNTTA',
 'Commonwealth: Refugee Review Tribunal': 'au/cases/cth/rrt au/cases/cth/RRTA',
 'Commonwealth: Social Security Appeals Tribunal - Review of Child Support Agency Decisions': 'au/cases/cth/SSATACSA',
 'Commonwealth: Superannuation Complaints Tribunal': 'au/cases/cth/SCTA',
 'Commonwealth: Australian Taxation Office -  All Materials': 'au/other/rulings/ato',
 'Commonwealth: Australian Taxation Office -  All Final Rulings': 'au/other/rulings/ato/ATOCR au/other/rulings/ato/ATOFGRR au/other/rulings/ato/ATOFTR au/other/rulings/ato/ATOGSTR au/other/rulings/ato/ATOITR au/other/rulings/ato/ATOMTR au/other/rulings/ato/ATOMTROS au/other/rulings/ato/ATOPGBR au/other/rulings/ato/ATOPR au/other/rulings/ato/ATOPRP au/other/rulings/ato/ATOSCR au/other/rulings/ato/ATOSGR au/other/rulings/ato/ATOSMSFPR au/other/rulings/ato/ATOSMSFR au/other/rulings/ato/ATOSTR au/other/rulings/ato/ATOSTRNS au/other/rulings/ato/ATOTGR au/other/rulings/ato/ATOTR au/other/rulings/ato/ATOWETR',
 'Commonwealth: Australian Taxation Office -  All Final Determinations': 'au/other/rulings/ato/ATOFTD au/other/rulings/ato/ATOGSTA au/other/rulings/ato/ATOGSTD au/other/rulings/ato/ATOLCTD au/other/rulings/ato/ATOSCD au/other/rulings/ato/ATOSD au/other/rulings/ato/ATOSGD au/other/rulings/ato/ATOSMSFD au/other/rulings/ato/ATOSTD au/other/rulings/ato/ATOTD au/other/rulings/ato/ATOTGD',
 'Commonwealth: Australian Taxation Office -  All Draft Rulings': 'au/other/rulings/ato/ATODFGRR au/other/rulings/ato/ATODFTR au/other/rulings/ato/ATODGSTR au/other/rulings/ato/ATODMTR au/other/rulings/ato/ATODPGBR au/other/rulings/ato/ATODSCR au/other/rulings/ato/ATODSGR au/other/rulings/ato/ATODSMSFR au/other/rulings/ato/ATODTR au/other/rulings/ato/ATODWETR au/other/rulings/ato/ATODLCTD',
 'Commonwealth: Australian Taxation Office -  All Draft Determinations': 'au/other/rulings/ato/ATODGSTD au/other/rulings/ato/ATODSCD au/other/rulings/ato/ATODSD au/other/rulings/ato/ATODSGD au/other/rulings/ato/ATODSMSFD au/other/rulings/ato/ATODSTD au/other/rulings/ato/ATODTD au/other/rulings/ato/ATODTGD au/other/rulings/ato/ATODWETD',
 'Australian Capital Territory: All Primary Materials': 'au/cases/act au/legis/act',
 'Australian Capital Territory: All Legislation': 'au/legis/act',
 'Australian Capital Territory: All Cases': 'au/cases/act',
 'Australian Capital Territory: Bills': 'au/legis/act/bill',
 'Australian Capital Territory: Bills Explanatory Statements': 'au/legis/act/bill_es',
 'Australian Capital Territory: Current Acts': 'au/legis/act/consol_act',
 'Australian Capital Territory: Current Regulations': 'au/legis/act/consol_reg',
 'Australian Capital Territory: Numbered Acts': 'au/legis/act/num_act',
 'Australian Capital Territory: Numbered Ordinances': 'au/legis/act/num_ord',
 'Australian Capital Territory: Numbered Regulations': 'au/legis/act/num_reg',
 'Australian Capital Territory: Numbered Regulations Explanatory Statements': 'au/legis/act/num_reg_es',
 'Australian Capital Territory: Repealed Acts': 'au/legis/act/repealed_act',
 'Australian Capital Territory: Repealed Regulations': 'au/legis/act/repealed_reg',
 'Australian Capital Territory: Administrative Appeals Tribunal': 'au/cases/act/ACTAAT',
 'Australian Capital Territory: Civil and Administrative Tribunal': 'au/cases/act/ACAT',
 'Australian Capital Territory: Court of Appeal': 'au/cases/act/ACTCA',
 'Australian Capital Territory: Discrimination Tribunal': 'au/cases/act/ACTDT',
 'Australian Capital Territory: Health Professions Tribunal': 'au/cases/act/ACTHPT',
 'Australian Capital Territory: Medical Board - Professional Standards Panel': 'au/cases/act/ACTMBPSP',
 'Australian Capital Territory: Residential Tenancies Tribunal': 'au/cases/act/ACTRTT au/cases/act/ACTTT',
 'Australian Capital Territory: Supreme Court': 'au/cases/act/ACTSC',
 'Australian Capital Territory: Tenancy Tribunal': 'au/cases/act/ACTTT',
 "Australian Capital Territory: Ombudsman's Investigation Reports": 'au/other/ACTOmbIRp',
 'New South Wales: All Primary Materials': 'au/cases/nsw au/legis/nsw',
 'New South Wales: All Legislation': 'au/legis/nsw',
 'New South Wales: All Cases': 'au/cases/nsw',
 'New South Wales: Bills': 'au/legis/nsw/bill',
 'New South Wales: Bills Explanatory Notes': 'au/legis/nsw/bill_en',
 'New South Wales: Consolidated Acts': 'au/legis/nsw/consol_act',
 'New South Wales: Consolidated Regulations': 'au/legis/nsw/consol_reg',
 'New South Wales: Numbered Acts': 'au/legis/nsw/num_act',
 'New South Wales: Numbered Regulations': 'au/legis/nsw/num_reg',
 'New South Wales: Numbered Environmental Planning Instruments': 'au/legis/nsw/num_epi',
 'New South Wales: Repealed Acts': 'au/legis/nsw/repealed_act',
 'New South Wales: Repealed Regulations': 'au/legis/nsw/repealed_reg',
 'New South Wales: Administrative Decisions Tribunal': 'au/cases/nsw/NSWADT',
 'New South Wales: Administrative Decisions Tribunal Appeal Panel': 'au/cases/nsw/NSWADTAP',
 "New South Wales: Chief Industrial Magistrate's Court": 'au/cases/nsw/NSWCIMC',
 'New South Wales: Chiropractors Tribunal': 'au/cases/nsw/NSWCHT',
 'New South Wales: Civil and Administrative Tribunal - Administrative and Equal Opportunity': 'au/cases/nsw/NSWCATAD',
 'New South Wales: Civil and Administrative Tribunal - Appeal Panel': 'au/cases/nsw/NSWCATAP',
 'New South Wales: Civil and Administrative Tribunal - Consumer and Commercial': 'au/cases/nsw/NSWCATCD',
 'New South Wales: Civil and Administrative Tribunal - Guardianship ': 'au/cases/nsw/NSWCATGD',
 'New South Wales: Civil and Administrative Tribunal - Occupational ': 'au/cases/nsw/NSWCATOD',
 'New South Wales: Community Services Appeals Tribunal': 'au/cases/nsw/csat',
 'New South Wales: Compensation Court': 'au/cases/nsw/NSWCC',
 'New South Wales: Consumer, Trader and Tenancy Tribunal': 'au/cases/nsw/NSWCTTT',
 'New South Wales: Dental Tribunal ': 'au/cases/nsw/NSWDT',
 'New South Wales: District Court': 'au/cases/nsw/NSWDC',
 'New South Wales: Drug Court': 'au/cases/nsw/NSWDRGC',
 'New South Wales: Dust Diseases Tribunal': 'au/cases/nsw/NSWDDT',
 'New South Wales: Fair Trading Tribunal': 'au/cases/nsw/NSWFTT',
 'New South Wales: Guardianship Tribunal': 'au/cases/nsw/NSWGT',
 'New South Wales: Industrial Relations Commission': 'au/cases/nsw/NSWIRComm',
 'New South Wales: Land and Environment Court': 'au/cases/nsw/NSWLEC',
 'New South Wales: Law Reports': 'au/cases/nsw/NSWLawRp',
 'New South Wales: Medical Professional Standards Committee': 'au/cases/nsw/NSWMPSC',
 'New South Wales: Medical Tribunal': 'au/cases/nsw/NSWMT',
 'New South Wales: Nurses and Midwives Tribunal': 'au/cases/nsw/NSWNMT',
 'New South Wales: Nursing and Midwifery Professional Standards Committee': 'au/cases/nsw/NSWNMPSC',
 'New South Wales: Optometry Tribunal': 'au/cases/nsw/NSWOPT',
 'New South Wales: Pharmacy Board': 'au/cases/nsw/NSWPB',
 'New South Wales: Physiotherapists Tribunal': 'au/cases/nsw/NSWPYT',
 'New South Wales: Privacy Commissioner Cases': 'au/cases/nsw/NSWPrivCmr',
 'New South Wales: Psychologists Tribunal': 'au/cases/nsw/NSWPST',
 'New South Wales: Residential Tribunal': 'au/cases/nsw/NSWRT',
 'New South Wales: State Reports': 'au/cases/nsw/NSWStRp',
 'New South Wales: Strata Schemes Board ': 'au/cases/nsw/NSWSSB',
 'New South Wales: Supreme Court': 'au/cases/nsw/NSWSC',
 'New South Wales: Supreme Court - Court of Appeal': 'au/cases/nsw/NSWCA',
 'New South Wales: Supreme Court - Court of Criminal Appeal': 'au/cases/nsw/NSWCCA',
 'New South Wales: Workers Compensation Commission - Presidential Decisions': 'au/cases/nsw/NSWWCCPD',
 'Northern Territory: All Primary Materials': 'au/cases/nt au/legis/nt',
 'Northern Territory: All Legislation': 'au/legis/nt',
 'Northern Territory: All Cases': 'au/cases/nt',
 'Northern Territory: Bills': 'au/legis/nt/bill',
 'Northern Territory: Bills Explanatory Statements': 'au/legis/nt/bill_es',
 'Northern Territory: Bills Second Reading Speeches': 'au/legis/nt/bill_srs',
 'Northern Territory: Consolidated Acts': 'au/legis/nt/consol_act',
 'Northern Territory: Consolidated Regulations': 'au/legis/nt/consol_reg',
 'Northern Territory: Numbered Acts': 'au/legis/nt/num_act',
 'Northern Territory: Numbered Ordinances': 'au/legis/nt/num_ord',
 'Northern Territory: Numbered Regulations': 'au/legis/nt/num_reg',
 'Northern Territory: Anti-Discrimination Commission': 'au/cases/nt/NTADC',
 'Northern Territory: Health Professional Review Tribunal ': 'au/cases/nt/NTHPRT',
 'Northern Territory: Residential Tenancies Commissioner': 'au/cases/nt/NTRTCmr',
 'Northern Territory: Supreme Court ': 'au/cases/nt/NTSC',
 'Northern Territory: Supreme Court - Court of Appeal': 'au/cases/nt/NTCA',
 'Northern Territory: Supreme Court - Court of Criminal Appeal': 'au/cases/nt/NTCCA',
 'Queensland: All Primary Materials': 'au/cases/qld au/legis/qld',
 'Queensland: All Legislation': 'au/legis/qld',
 'Queensland: All Cases': 'au/cases/qld',
 'Queensland: Bills': 'au/legis/qld/bill',
 'Queensland: Bills Explanatory Notes': 'au/legis/qld/bill_en',
 'Queensland: Consolidated Acts': 'au/legis/qld/consol_act',
 'Queensland: Consolidated Regulations': 'au/legis/qld/consol_reg',
 'Queensland: Historical Acts': 'au/legis/qld/hist_act',
 'Queensland: Numbered Acts': 'au/legis/qld/num_act',
 'Queensland: Anti-Discrimination Tribunal': 'au/cases/qld/QADT',
 'Queensland: Body Corporate and Community Management Commissioner - Adjudicators Orders ': 'au/cases/qld/QBCCMCmr',
 'Queensland: Building Tribunal': 'au/cases/qld/QBT',
 'Queensland: Children Services Tribunal': 'au/cases/qld/QCST',
 'Queensland: Civil and Administrative Tribunal': 'au/cases/qld/QCAT',
 'Queensland: Civil and Administrative Tribunal Appeals': 'au/cases/qld/QCATA',
 'Queensland: Commercial and Consumer Tribunal - All Lists': 'au/cases/qld/QCCTA au/cases/qld/QCCTBCCM au/cases/qld/QCCTB au/cases/qld/QCCTE au/cases/qld/QCCTG au/cases/qld/QCCTL au/cases/qld/QCCTMH au/cases/qld/QCCTPD au/cases/qld/QCCTPAMD au/cases/qld/QCCTRV',
 'Queensland: District Court': 'au/cases/qld/QDC',
 'Queensland: Guardianship and Administration Tribunal': 'au/cases/qld/QGAAT',
 'Queensland: Industrial Court': 'au/cases/qld/QIC',
 'Queensland: Industrial Relations Commission': 'au/cases/qld/QIRComm',
 'Queensland: Information Commissioner ': 'au/cases/qld/QICmr',
 'Queensland: Land and Resources Tribunal': 'au/cases/qld/QLRT',
 'Queensland: Land Court': 'au/cases/qld/QLC',
 'Queensland: Land Appeal Court': 'au/cases/qld/QLAC',
 'Queensland: Liquor Appeals Tribunal': 'au/cases/qld/QLAT',
 'Queensland: Mental Health Court': 'au/cases/qld/QMHC',
 'Queensland: Mining Wardens': 'au/cases/qld/QMW',
 'Queensland: Nursing Tribunal': 'au/cases/qld/QNT',
 'Queensland: Planning and Environment Court': 'au/cases/qld/QPEC',
 'Queensland: Property Agents and Motor Dealers Tribunal': 'au/cases/qld/QPAMDT',
 'Queensland: Racing Appeals Authority': 'au/cases/qld/QRAA',
 'Queensland: Racing Appeals Tribunal': 'au/cases/qld/QRAT',
 'Queensland: Retirement Villages Tribunal': 'au/cases/qld/QRVT',
 'Queensland: Supreme Court': 'au/cases/qld/QSC',
 'Queensland: Supreme Court - Court of Appeal': 'au/cases/qld/QCA',
 'South Australia: All Primary Materials': 'au/cases/sa au/legis/sa',
 'South Australia: All Legislation': 'au/legis/sa',
 'South Australia: All Cases': 'au/cases/sa',
 'South Australia: Bills': 'au/legis/sa/bill',
 'South Australia: Current Acts': 'au/legis/sa/consol_act',
 'South Australia: Current Regulations': 'au/legis/sa/consol_reg',
 'South Australia: Numbered Acts': 'au/legis/sa/num_act',
 'South Australia: Numbered Regulations': 'au/legis/sa/num_reg',
 'South Australia: Proclamations': 'au/legis/sa/proc',
 'South Australia: Chiropractic and Osteopathy Board - Court Prosecutions': 'au/cases/sa/SACHOSBCP',
 'South Australia: Chiropractic and Osteopathy Board - Disciplinary': 'au/cases/sa/SACHOSB',
 'South Australia: Civil and Administrative Tribunal': 'au/cases/sa/SACAT',
 'South Australia: Dental Board': 'au/cases/sa/SADB',
 'South Australia: Dental Professional Conduct Tribunal': 'au/cases/sa/SADPCT',
 'South Australia: District Court': 'au/cases/sa/SADC',
 'South Australia: Environmental Resources and Development Court': 'au/cases/sa/SAERDC',
 'South Australia: Equal Opportunity Tribunal': 'au/cases/sa/SAEOT',
 'South Australia: Industrial Relations Commission': 'au/cases/sa/SAIRComm',
 'South Australia: Industrial Relations Court': 'au/cases/sa/SAIRC',
 'South Australia: Licensing Court': 'au/cases/sa/SALC',
 'South Australia: Liquor and Gambling Commissioner': 'au/cases/sa/SALGCmr',
 'South Australia: Medical Board': 'au/cases/sa/SAMB',
 'South Australia: Pharmacy Board': 'au/cases/sa/SAPHB',
 'South Australia: Podiatry Board': 'au/cases/sa/SAPDB',
 'South Australia: Psychological Board - Court Prosecutions': 'au/cases/sa/SAPSBCP',
 'South Australia: Psychological Board - Disciplinary': 'au/cases/sa/SAPSB',
 'South Australia: Residential Tenancies Tribunal': 'au/cases/sa/SARTT',
 'South Australia: South Australian Law Reports': 'au/cases/sa/SALawRp',
 'South Australia: State Reports': 'au/cases/sa/SAStRp',
 'South Australia: Supreme Court': 'au/cases/sa/SASC',
 'South Australia: Supreme Court - Full Court': 'au/cases/sa/SASCFC',
 'South Australia: Wardens Court': 'au/cases/sa/SAWC',
 'South Australia: WorkCover Levy Review Panel': 'au/cases/sa/SAWLRP',
 'South Australia: WorkCover Premium Review Panel': 'au/cases/sa/SAWPRP',
 'South Australia: Workers Compensation Appeal Tribunal': 'au/cases/sa/SAWCAT',
 'South Australia: Workers Compensation Tribunal': 'au/cases/sa/SAWCT',
 'South Australia: South Australian Government Gazettes': 'au/other/sa_gazette',
 'South Australia: Ombudsman Reports': 'au/other/SAOmbRp',
 'South Australia: Ombudsman FOI Determinations': 'au/other/SAOmbFOI',
 'Tasmania: All Primary Materials': 'au/cases/tas au/legis/tas',
 'Tasmania: All Legislation': 'au/legis/tas',
 'Tasmania: All Cases': 'au/cases/tas',
 'Tasmania: Bills': 'au/legis/tas/bill',
 'Tasmania: Bills Fact Sheets': 'au/legis/tas/bill_fs',
 'Tasmania: Consolidated Acts': 'au/legis/tas/consol_act',
 'Tasmania: Consolidated Regulations': 'au/legis/tas/consol_reg',
 'Tasmania: Numbered Acts': 'au/legis/tas/num_act',
 'Tasmania: Numbered Regulations': 'au/legis/tas/num_reg',
 'Tasmania: Anti-Discrimination Tribunal': 'au/cases/tas/TASADT',
 'Tasmania: Forest Practices Tribunal': 'au/cases/tas/TASFPT',
 'Tasmania: Planning Commission': 'au/cases/tas/TASPComm',
 'Tasmania: Resource Management and Planning Appeal Tribunal': 'au/cases/tas/TASRMPAT',
 'Tasmania: Resource Planning and Development Commission': 'au/cases/tas/TASRPDComm',
 'Tasmania: State Reports': 'au/cases/tas/TASStRp',
 'Tasmania: Supreme Court ': 'au/cases/tas/TASSC',
 'Tasmania: Supreme Court - Full Court': 'au/cases/tas/TASFC',
 'Tasmania: Supreme Court - Court of Criminal Appeal': 'au/cases/tas/TASCCA',
 'Tasmania: Tasmanian Law Reports': 'au/cases/tas/TASLawRp',
 'Tasmania: Tasmanian Reports': 'au/cases/tas/TASRp',
 'Tasmania: Guardianship and Administration Board  ': 'au/cases/tas/TASGAB',
 'Tasmania: Workers Rehabilitation and Compensation Tribunal  ': 'au/cases/tas/TASWRCT',
 'Victoria: All Primary Materials': 'au/cases/vic au/legis/vic',
 'Victoria: All Legislation': 'au/legis/vic',
 'Victoria: All Cases': 'au/cases/vic',
 'Victoria: Anglican Church Legislation': 'au/legis/vic/anglican',
 'Victoria: Bills': 'au/legis/vic/bill',
 'Victoria: Bills Explanatory Memoranda': 'au/legis/vic/bill_em',
 'Victoria: Current Acts': 'au/legis/vic/consol_act',
 'Victoria: Current Regulations': 'au/legis/vic/consol_reg',
 'Victoria: Historical Acts': 'au/legis/vic/hist_act',
 'Victoria: Numbered Acts': 'au/legis/vic/num_act',
 'Victoria: Numbered Regulations': 'au/legis/vic/num_reg',
 'Victoria: Repealed Acts': 'au/legis/vic/rep_reg',
 'Victoria: Repealed Regulations': 'au/legis/vic/rep_reg',
 'Victoria: Administrative Appeals Tribunal': 'au/cases/vic/VICCAT',
 'Victoria: Civil and Administrative Tribunal': 'au/cases/vic/VCAT',
 'Victoria: Dental Practice Board': 'au/cases/vic/VDPB',
 'Victoria: County Court': 'au/cases/vic/VCC',
 'Victoria: Domestic Building Tribunal': 'au/cases/vic/VDBT',
 'Victoria: Heritage Council': 'au/cases/vic/VHerCl',
 'Victoria: Legal Profession Tribunal': 'au/cases/vic/VLPT',
 "Victoria: Magistrates' Court": 'au/cases/vic/VMC',
 'Victoria: Medical Practitioners Board': 'au/cases/vic/VMPB',
 'Victoria: Medical Practitioners Board - Professional Standards Panel': 'au/cases/vic/VMPBPSP',
 'Victoria: Mental Health Review Board': 'au/cases/vic/VMHRB',
 'Victoria: Mental Health Tribunal': 'au/cases/vic/VMHT',
 'Victoria: Office of the Privacy Commissioner Case Notes': 'au/cases/vic/VPrivCmr',
 'Victoria: Physiotherapists Registration Board': 'au/cases/vic/VPYRB',
 'Victoria: Psychologists Registration Board': 'au/cases/vic/VPSRB',
 'Victoria: Planning Panels': 'au/cases/vic/PPV',
 'Victoria: Racing Appeals Tribunal': 'au/cases/vic/VRAT',
 'Victoria: Supreme Court': 'au/cases/vic/VSC',
 'Victoria: Supreme Court - Court of Appeal': 'au/cases/vic/VSCA',
 'Victoria: Victorian Law Reports': 'au/cases/vic/VicLawRp',
 'Victoria: Victorian Reports': 'au/cases/vic/VicRp',
 'Victoria: Government Gazette': 'au/other/vic_gazette',
 'Victoria: State Revenue Office Rulings': 'au/other/rulings/vicsro/VICSROBF au/other/rulings/vicsro/VICSRODT au/other/rulings/vicsro/VICSROFHOG au/other/rulings/vicsro/VICSRODA au/other/rulings/vicsro/VICSROFID au/other/rulings/vicsro/VICSROGEN au/other/rulings/vicsro/VICSROLT au/other/rulings/vicsro/VICSROLTA au/other/rulings/vicsro/VICSROPT au/other/rulings/vicsro/VICSROPTA au/other/rulings/vicsro/VICSROSD au/other/rulings/vicsro/VICSROTAA',
 'Western Australia: All Legislation': 'au/legis/wa',
 'Western Australia: All Cases': 'au/cases/wa',
 'Western Australia: All Primary Materials': 'au/legis/wa au/cases/wa',
 'Western Australia: Bills': 'au/legis/wa/bill',
 'Western Australia: Bills Explanatory Memoranda': 'au/legis/wa/bill_em',
 'Western Australia: Consolidated Acts': 'au/legis/wa/consol_act',
 'Western Australia: Consolidated Regulations': 'au/legis/wa/consol_reg',
 'Western Australia: Numbered Acts': 'au/legis/wa/num_act',
 'Western Australia: Repealed Acts': 'au/legis/wa/rep_act',
 'Western Australia: Repealed Regulations': 'au/legis/wa/rep_reg',
 'Western Australia: Criminal Injuries Compensation Assessor': 'au/cases/wa/WACIC',
 'Western Australia: District Court': 'au/cases/wa/WADC',
 'Western Australia: Family Court': 'au/cases/wa/FCWA',
 'Western Australia: Family Court - Magistrates': 'au/cases/wa/FCWAM',
 'Western Australia: Guardianship and Administration Board': 'au/cases/wa/WAGAB',
 'Western Australia: Information Commissioner ': 'au/cases/wa/WAICmr',
 'Western Australia: Industrial Relations Commission': 'au/cases/wa/WAIRComm',
 'Western Australia: Medical Board': 'au/cases/wa/WAMB',
 'Western Australia: State Administrative Tribunal': 'au/cases/wa/WASAT',
 'Western Australia: Strata Titles Referee': 'au/cases/wa/WASTR',
 'Western Australia: Supreme Court': 'au/cases/wa/WASC',
 'Western Australia: Supreme Court - Court of Appeal': 'au/cases/wa/WASCA',
 'Western Australia: Town Planning Appeal Tribunal ': 'au/cases/wa/WATPAT',
 'Western Australia: Western Australian Law Reports ': 'au/cases/wa/WALawRp',
 'Australasian Legal Scholarship Library': 'au/journals nz/journals',
 'Australian Human Rights Information Centre': 'au/other/ahric',
 'Australian Indigenous Law Library': 'au/other/IndigLRes',
 'Australian Treaties Library': 'au/other/dfat',
 'Australian Planning and Development Law Library': 'au/cases/act/ACAT+au/cases/act/ACTAAT+au/cases/nsw/NSWLEC+au/cases/qld/QLAC+au/cases/qld/QLC+au/cases/qld/QPEC+au/cases/qld/QLRT+au/cases/qld/QBT+au/cases/qld/QCCTB+au/cases/sa/SAERDC+au/cases/tas/TASRMPAT+au/cases/tas/TASRPDComm+au/cases/tas/TASPComm+au/cases/vic/VCAT+au/cases/vic/PPV+au/cases/wa/WASAT+au/cases/wa/WATPAT',
 'Australian Treaty Series': 'au/other/dfat/treaties/ATS',
 'Australian Minor Treaty Actions - Explanatory Statements': 'au/other/dfat/treaties/AMTAES',
 'Australian Treaties - not in force': 'au/other/dfat/treaties/ATNIF',
 'Australasian Law Reform Library': 'au/other/adminrc au/other/actlrc au/other/alrc au/other/clrc au/other/nswlrc nz/other/nzlc au/other/ntlrc au/other/qlrc au/other/taslri au/other/vlrc au/other/walrc au/other/lawreform',
 'Council for Aboriginal Reconciliation': 'au/other/car'}

# %%
austlii_advanced_search_link = 'https://austlii.edu.au/advanced_search.shtml'


# %%
def austlii_selenium_judgment_text(case_info):
    
    url = case_info['Hyperlink to AustLII']

    browser = get_driver()
        
    #Get search results
    browser.get(url)

    #Wait until all judgment text is shown
    judgment_text_present = Wait(browser, 30).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "footer.closing ul.closing-tertiary")))
    
    soup = BeautifulSoup(browser.page_source, "lxml")

    text = soup.get_text()
    try:
        text = soup.get_text().split('Print (pretty)')[0].split('\n Any \n')[-1]
    except:
        pass

    browser.quit()

    return text

#Meta labels and judgment combined

#@st.cache_data(show_spinner = False)
def austlii_selenium_meta_judgment_dict(case_info):
    
    try:
        
        case_info['judgment'] = austlii_selenium_judgment_text(case_info)

    except Exception as e:
        print(f"{case_info['Case name']}: judgment not scrapped")
        print(e)

    case_info['Hyperlink to AustLII'] = link(case_info['Hyperlink to AustLII'])
        
    return case_info


# %%
#Function turning search terms to search results url
class austlii_search_tool:

    def __init__(self,
                 method = list(austlii_methods_dict.keys())[0],
                query= '',
                datelow = None,
                datehigh = None,
                sort = list(austlii_sort_dict.keys())[0],
                highlight = True,
                databases = list(austlii_databases_dict.keys())[0],
                 judgment_counter_bound = default_judgment_counter_bound
             ):

        #Initialise parameters
        self.method = method
        self.query = query
        self.datelow = datelow
        self.datehigh = datehigh
        self.sort = sort
        self.highlight = highlight
        self.databases = databases
        self.judgment_counter_bound = judgment_counter_bound

        #Need to process some parameters
        self.params_processsed = False
        
        self.results_count = 0

        self.total_pages = 0
        
        self.results_url = ''
        
        self.soup = None
        
        self.case_infos = []
        
    #Function for getting url for search results and the soup of first page
    def process_params(self):

        findby = 'sinosrch.cgi?'

        base_url = "https://www.austlii.edu.au/cgi-bin/" + findby
        
        #Convert method choice to param
        try:
            
            self.method = austlii_methods_dict[self.method]
            
        except:
            
            self.method = austlii_methods_dict[list(austlii_methods_dict.keys())[0]]
            
            print(f"Can't get method param. Kept default {self.method}.")

        #(NOT NEED) Initialise list of search terms
        query_list = []

        if self.method == 'boolean':

            advanced_query_query = f'({self.query})'

            query_list.append(advanced_query_query)

        if self.method == 'any':

            any_of_these_words_query_raw_list = self.query.split(' ')

            any_of_these_words_query_raw = ' OR '.join(any_of_these_words_query_raw_list)

            any_of_these_words_query = f"({any_of_these_words_query_raw})"

            query_list.append(any_of_these_words_query)
            
        if self.method == 'all':

            all_of_these_words_query_raw_list = self.query.split(' ')

            all_of_these_words_query_list = []

            for word in all_of_these_words_query_raw_list:

                all_of_these_words_query_list.append(f" ({word}) ")

            all_of_these_words_query = ' AND '.join(all_of_these_words_query_list)

            query_list.append(all_of_these_words_query)

        if self.method == 'phrase':

            exact_phrase_query = f'("{self.query}")'

            query_list.append(exact_phrase_query)

        print(f"Search terms are as follows: {self.query}")

        #Sort param
        try:
            
            self.sort = austlii_sort_dict[self.sort]
            
        except:
            
            self.sort = austlii_sort_dict[list(austlii_sort_dict.keys())[0]]
            
            print(f"Can't get sort param. Kept default {self.sort}.")

        #Highlight param            
        try:
            
            self.highlight = int(bool(self.highlight))
            
        except:
            
            self.highlight = int(bool(True))
            
            print(f"Can't get highlight param. Kept default {self.highlight}.")
            

        #Datelow param
        if self.datelow not in [None, '']:
            
            self.datelow = date_parser(self.datelow)
            
            if not isinstance(self.datelow, datetime):
    
                print("Can't get datelow param.")
        
        #Datehigh param
        if self.datehigh not in [None, '']:
    
            self.datehigh = date_parser(self.datehigh)
            
            if not isinstance(self.datehigh, datetime):
    
                print("Can't get datehigh param.")

        self.params_processsed = True
        
    def search(self):

        #Reset infos of cases found
        self.case_infos = []
        
        if self.params_processsed == False:

            self.process_params()
            
        browser = get_driver()
        
        browser.get(austlii_advanced_search_link)

        #Click on method if not 'auto'

        print(f"self.method == {self.method}")
        
        if self.method != austlii_methods_dict[list(austlii_methods_dict.keys())[0]]:
            
            method_selected = Wait(browser, 30).until(EC.visibility_of_element_located((By.CSS_SELECTOR, f"li.sort-item.query-type[data-type-name='{self.method}'][role='tab']")))
            
            method_selected.click()

        #Enter datelow if entered
        if isinstance(self.datelow, datetime):

            datelow_day = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@name='day1']")))

            datelow_day.send_keys(self.datelow.day)

            datelow_month = Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//select[@name='month1']")))
            
            dropdown_datelow_month = Select(datelow_month)
            
            dropdown_datelow_month.select_by_value(self.datelow.strftime("%m"))

            datelow_year = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@name='year1']")))

            datelow_year.send_keys(self.datelow.year)

        #Enter datehigh if entered
        if isinstance(self.datehigh, datetime):

            datehigh_day = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@name='day2']")))

            datehigh_day.send_keys(self.datehigh.day)

            datehigh_month = Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//select[@name='month2']")))
            
            dropdown_datehigh_month = Select(datehigh_month)
            
            dropdown_datehigh_month.select_by_value(self.datehigh.strftime("%m"))

            datehigh_year = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@name='year2']")))

            datehigh_year.send_keys(self.datehigh.year)

        #Select the database(s) to search...
        
        if 'All AustLII Databases' not in self.databases:

            #Unselect default databses
            select_the_databases_to_search = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Select the database(s) to search')]/label")))
    
            select_the_databases_to_search.click()

            #Select 'Show all'
            show_all = Wait(browser, 30).until(EC.element_to_be_clickable((By.ID, "show-databases")))

            #Scroll to element then click
            browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", show_all)            
            
            show_all.click()
            
           #pause.seconds(np.random.randint(5, 10))
            
            for database in self.databases:
                
                database_checkbox = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, f"//input[@type='checkbox' and @name='mask_path' and @value='{austlii_databases_dict[database]}']/parent::label")))

                #Scroll to element then click
                
                browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", database_checkbox)            
                
                database_checkbox.click()
                    
        #Enter your search (do last)

        search_box = Wait(browser, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@name='query']")))

        #Scroll to element then send enter search terms

        browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_box)            
        
        search_box.send_keys(self.query)

        search_box.send_keys(Keys.ENTER)

        #Wait until search results present
        search_results_num = Wait(browser, 30).until(EC.title_contains("documents found"))
        
        #Get search results url
        self.results_url = browser.current_url

        print(f"self.results_url == {self.results_url}")
        
        #Get soup from first page
        self.soup = BeautifulSoup(browser.page_source, "lxml")

        #Change sorting if not 'By relevance'
        
        if self.sort != austlii_sort_dict[list(austlii_sort_dict.keys())[0]]: 

            #For 'date-earliest' or 'cited-least', need to choose a tab first then select the relevant option
            if self.sort == 'date-earliest':

                date_latest =  Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='page-sort']//a[contains(@href, 'view=date-latest')]")))
    
                date_latest.click()

                date_earliest =  Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='page-sort-2']//a[contains(@href, 'view=date-earliest')]")))
    
                date_earliest.click()

            elif self.sort == 'cited-least':

                cited_most =  Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='page-sort']//a[contains(@href, 'view=cited-most')]")))
    
                cited_most.click()

                cited_least =  Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='page-sort-2']//a[contains(@href, 'view=cited-least')]")))
    
                cited_least.click()
            
            else:
            
                sortby_tab =  Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, f"//div[@id='page-sort']//a[contains(@href, 'view={self.sort}')]")))
    
                sortby_tab.click()

            search_results_num = Wait(browser, 30).until(EC.title_contains("documents found"))

            self.soup = BeautifulSoup(browser.page_source, "lxml")
                                                         
        #print(self.soup)
        
        #Get number of search results
        docs_found_string = re.findall(r'\d+', str(self.soup.find('title')).replace(',', ''))[0]
        
        self.results_count = int(float(docs_found_string))
        self.total_pages = math.ceil(self.results_count/10) #10 results per page

        if self.results_count > 0:

            #Start counter
            counter = 0

            #Initialise default results page showing on screen
            default_results_page = 1

            #print(f"default_results_page == {default_results_page}")
            
            for page in range(1, self.total_pages + 1):
                
                if counter < min(self.results_count, self.judgment_counter_bound):

                    #print(f"Trying to obtain search results on page {page} of {self.total_pages}")

                    #Decide whether there is a need to click 'next' to get the next 10 pages
                    if page >= default_results_page + 10:

                        next_button = Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, '//div[@id="pagination-sort"]//li[@class="next"]/a')))
                        
                        next_button.click()

                        #Increase default results page showing on screen
                        default_results_page += 10

                    #Click on relevant page button if not showing on screen already
                    if page > default_results_page:
                        
                        page_button = Wait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, f'//div[@id="pagination-sort"]//a[text()="{page}"]')))
                        
                        page_button.click()

                    #Wait until results showing
                    results_div = Wait(browser, 30).until(EC.presence_of_element_located((By.XPATH, '//div[@class="card"]//li[@data-count]')))

                    #Update self.soup
                    self.soup = BeautifulSoup(browser.page_source, "lxml")

                    print(f"Obtaining results from page {page} of {self.total_pages}")
                
                else:

                    break
        
                #Get self.case_infos
                hrefs = self.soup.find_all('a', href=re.compile('/cgi-bin/viewdoc'))
                
                for link in hrefs:

                    if counter < self.judgment_counter_bound:
                    
                        case = link.get_text()
                        link_direct = link.get('href')
                        link = 'https://www.austlii.edu.au' + link_direct.split('?context')[0]

                        #Try to get date
                        try:
                            date = case.split('(')[-1].replace(')', '')

                        except:
                            print(f"{case}: Can't get date")
                            date = ''
                            
                        dict_object = {'Case name': split_title_mnc(case)[0], 
                                       'Medium neutral citation': split_title_mnc(case)[1], 
                                       'Hyperlink to AustLII': link,
                                      'Date': date,
                                      }
                        
                        self.case_infos.append(dict_object)
                        
                        counter = counter + 1

                #Pause to aovid getting kicked out
                pause.seconds(np.random.randint(10, 15))

        browser.quit()
        
    def get_judgments(self):

        self.case_infos_w_judgments = []
        
        for case_info in self.case_infos:

            if len(self.case_infos_w_judgments) < min(self.results_count, self.judgment_counter_bound):

                #Pause to avoid getting kicked out
                pause.seconds(np.random.randint(5, 10))

                case_info_w_judgment = austlii_selenium_meta_judgment_dict(case_info)
                        
                self.case_infos_w_judgments.append(case_info_w_judgment)
                    
                print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments.")


# %%
#@st.cache_data(show_spinner = False)
def austlii_search_url(df_master):

    df_master = df_master.fillna('')
    
    #Conduct search
    
    austlii_search = austlii_search_tool(
                method = df_master.loc[0, 'Method'],
                query = df_master.loc[0, 'Enter your search'],
                datelow = df_master.loc[0, 'From date'],
                datehigh = df_master.loc[0, 'To date'],
                sort = df_master.loc[0, 'Sort results by'],
                highlight = df_master.loc[0, 'Highlight search terms in result'],
                databases = df_master.loc[0, 'Databases'],
                judgment_counter_bound = df_master.loc[0, 'Maximum number of judgments']
             )

    austlii_search.search()
    
    return {'results_url': austlii_search.results_url, 'results_count': austlii_search.results_count, 'case_infos': austlii_search.case_infos}



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import basic_model, flagship_model


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, GPT_answers_check, unanswered_questions, checked_questions_json, answers_check_system_instruction


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def austlii_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    austlii_search = austlii_search_tool(
                    method = df_master.loc[0, 'Method'],
                    query = df_master.loc[0, 'Enter your search'],
                    datelow = df_master.loc[0, 'From date'],
                    datehigh = df_master.loc[0, 'To date'],
                    sort = df_master.loc[0, 'Sort results by'],
                    highlight = df_master.loc[0, 'Highlight search terms in result'],
                    databases = df_master.loc[0, 'Databases'],
                    judgment_counter_bound = df_master.loc[0, 'Maximum number of judgments']
                 )
    
    austlii_search.search()

    austlii_search.get_judgments()

    for case_info in austlii_search.case_infos_w_judgments:
        
        judgments_file.append(case_info)
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = flagship_model
    else:        
        gpt_model = basic_model
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        
        df_updated.pop('judgment')
    
    return df_updated

# %%
