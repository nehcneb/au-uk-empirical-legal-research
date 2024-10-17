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
import urllib
from urllib.request import urlretrieve
import os
import pypdf
import io
from io import BytesIO
import ast

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # US search engine

# %% [markdown]
# ## Definitions

# %% [markdown]
# ### Menus and courts

# %%
us_collections = {'Opinions of Federal, State and Territory Courts': 'o',
'Records of Federal Courts': 'r'
}

# %%
us_order_by = {'Relevance': "score desc", #not working on their api
'Newest Cases First': "dateFiled desc",
'Oldest Cases First': "dateFiled asc",
'Most Cited First': "citeCount desc",
'Least Cited First': "citeCount asc"
}

# %%
us_precedential_status = {
'Precedential': "stat_Precedential",
'Non-Precedential': "stat_Non-Precedential",
'Errata': "stat_Errata",
'Separate Opinion': "stat_Separate Opinion",  
'In-chambers': "stat_In-chambers",
'Relating-to orders': "stat_Relating-to orders", 
'Unknown Status': "stat_Unknown Status"
}

# %%
us_fed_app_courts = {'All': None, 
'Supreme Court': 'scotus',
 'First Circuit': 'ca1',
 'Second Circuit': 'ca2',
 'Third Circuit': 'ca3',
 'Fourth Circuit': 'ca4',
 'Fifth Circuit': 'ca5',
 'Sixth Circuit': 'ca6',
 'Seventh Circuit': 'ca7',
 'Eighth Circuit': 'ca8',
 'Ninth Circuit': 'ca9',
 'Tenth Circuit': 'ca10',
 'Eleventh Circuit': 'ca11', 
'D.C. Circuit': 'cadc',}

# %%
us_fed_dist_courts = {'All': None, 
'Federal Circuit': 'cafc',
 'District of Columbia': 'dcd',
 'M.D. Alabama': 'almd',
 'N.D. Alabama': 'alnd',
 'S.D. Alabama': 'alsd',
 'D. Alaska': 'akd',
 'D. Arizona': 'azd',
 'E.D. Arkansas': 'ared',
 'W.D. Arkansas': 'arwd',
 'C.D. California': 'cacd',
 'E.D. California': 'caed',
 'N.D. California': 'cand',
 'S.D. California': 'casd',
 'D. Colorado': 'cod',
 'D. Connecticut': 'ctd',
 'D. Delaware': 'ded',
 'M.D. Florida': 'flmd',
 'N.D. Florida': 'flnd',
 'S.D. Florida': 'flsd',
 'M.D. Georgia': 'gamd',
 'N.D. Georgia': 'gand',
 'S.D. Georgia': 'gasd',
 'D. Hawaii': 'hid',
 'D. Idaho': 'idd',
 'C.D. Illinois': 'ilcd',
 'N.D. Illinois': 'ilnd',
 'S.D. Illinois': 'ilsd',
 'N.D. Indiana': 'innd',
 'S.D. Indiana': 'insd',
 'N.D. Iowa': 'iand',
 'S.D. Iowa': 'iasd',
 'D. Kansas': 'ksd',
 'E.D. Kentucky': 'kyed',
 'W.D. Kentucky': 'kywd',
 'E.D. Louisiana': 'laed',
 'M.D. Louisiana': 'lamd',
 'W.D. Louisiana': 'lawd',
 'D. Maine': 'med',
 'D. Maryland': 'mdd',
 'D. Massachusetts': 'mad',
 'E.D. Michigan': 'mied',
 'W.D. Michigan': 'miwd',
 'D. Minnesota': 'mnd',
 'N.D. Mississippi': 'msnd',
 'S.D. Mississippi': 'mssd',
 'E.D. Missouri': 'moed',
 'W.D. Missouri': 'mowd',
 'D. Montana': 'mtd',
 'D. Nebraska': 'ned',
 'D. Nevada': 'nvd',
 'D. New Hampshire': 'nhd',
 'D. New Jersey': 'njd',
 'D. New Mexico': 'nmd',
 'E.D. New York': 'nyed',
 'N.D. New York': 'nynd',
 'S.D. New York': 'nysd',
 'W.D. New York': 'nywd',
 'E.D. North Carolina': 'nced',
 'M.D. North Carolina': 'ncmd',
 'W.D. North Carolina': 'ncwd',
 'D. North Dakota': 'ndd',
 'N.D. Ohio': 'ohnd',
 'S.D. Ohio': 'ohsd',
 'E.D. Oklahoma': 'oked',
 'N.D. Oklahoma': 'oknd',
 'W.D. Oklahoma': 'okwd',
 'D. Oregon': 'ord',
 'E.D. Pennsylvania': 'paed',
 'M.D. Pennsylvania': 'pamd',
 'W.D. Pennsylvania': 'pawd',
 'D. Rhode Island': 'rid',
 'D. South Carolina': 'scd',
 'D. South Dakota': 'sdd',
 'E.D. Tennessee': 'tned',
 'M.D. Tennessee': 'tnmd',
 'W.D. Tennessee': 'tnwd',
 'E.D. Texas': 'txed',
 'N.D. Texas': 'txnd',
 'S.D. Texas': 'txsd',
 'W.D. Texas': 'txwd',
 'D. Utah': 'utd',
 'D. Vermont': 'vtd',
 'E.D. Virginia': 'vaed',
 'W.D. Virginia': 'vawd',
 'E.D. Washington': 'waed',
 'W.D. Washington': 'wawd',
 'N.D. West Virginia': 'wvnd',
 'S.D. West Virginia': 'wvsd',
 'E.D. Wisconsin': 'wied',
 'W.D. Wisconsin': 'wiwd',
 'D. Wyoming': 'wyd',
 'D. Guam': 'gud',
 'Northern Mariana Islands': 'nmid',
 'D. Puerto Rico': 'prd',
 'Virgin Islands': 'vid'}

# %%
us_fed_hist_courts = {'All': None, 
'D. California (1886)': 'californiad',
 'E.D. Illinois (1978)': 'illinoised',
 'D. Illinois (1855)': 'illinoisd',
 'D. Indiana (1928)': 'indianad',
 'Orleans District Court (1812)': 'orld',
 'D. Ohio (1855)': 'ohiod',
 'D. Pennsylvania (1818)': 'pennsylvaniad',
 'E.D. South Carolina (1965)': 'southcarolinaed',
 'W.D. South Carolina (1965)': 'southcarolinawd',
 'D. Tennessee (1839)': 'tennessed',
 'District Court, Canal Zone (1982)': 'canalzoned'}

# %%
us_bankr_courts = {'All': None, 
'First Circuit': 'bap1',
 'Second Circuit': 'bap2',
 'Sixth Circuit': 'bap6',
 'Eighth Circuit': 'bap8',
 'Ninth Circuit': 'bap9',
 'Tenth Circuit': 'bap10',
 'D. Maine (Appellate)': 'bapme',
 'Massachusetts': 'bapma',
 'M.D. Alabama': 'almb',
 'N.D. Alabama': 'alnb',
 'S.D. Alabama': 'alsb',
 'D. Alaska': 'akb',
 'D. Arizona': 'arb',
 'E.D. Arkansas': 'areb',
 'W.D. Arkansas': 'arwb',
 'C.D. California': 'cacb',
 'E.D. California': 'caeb',
 'N.D. California': 'canb',
 'S.D. California': 'casb',
 'D. Colorado': 'cob',
 'D. Connecticut': 'ctb',
 'D. Delaware': 'deb',
 'District of Columbia': 'dcb',
 'M.D. Florida': 'flmb',
 'N.D. Florida': 'flnb',
 'S.D. Florida': 'flsb',
 'M.D. Georgia': 'gamb',
 'N.D. Georgia': 'ganb',
 'S.D. Georgia': 'gasb',
 'D. Hawaii': 'hib',
 'D. Idaho': 'idb',
 'C.D. Illinois': 'ilcb',
 'N.D. Illinois': 'ilnb',
 'S.D. Illinois': 'ilsb',
 'N.D. Indiana': 'innb',
 'S.D. Indiana': 'insb',
 'N.D. Iowa': 'ianb',
 'S.D. Iowa': 'iasb',
 'D. Kansas': 'ksb',
 'E.D. Kentucky': 'kyeb',
 'W.D. Kentucky': 'kywb',
 'E.D. Louisiana': 'laeb',
 'M.D. Louisiana': 'lamb',
 'W.D. Louisiana': 'lawb',
'D. Maine': 'meb',
 'D. Maryland': 'mdb',
 'D. Massachusetts': 'mab',
 'E.D. Michigan': 'mieb',
 'W.D. Michigan': 'miwb',
 'D. Minnesota': 'mnb',
 'N.D. Mississippi': 'msnb',
 'S.D. Mississippi': 'mssb',
 'E.D. Missouri': 'moeb',
 'W.D. Missouri': 'mowb',
 'D. Montana': 'mtb',
 'D. Nebraska': 'nebraskab',
 'D. Nevada': 'nvb',
 'D. New Hampshire': 'nhb',
 'D. New Jersey': 'njb',
 'D. New Mexico': 'nmb',
 'E.D. New York': 'nyeb',
 'N.D. New York': 'nynb',
 'S.D. New York': 'nysb',
 'W.D. New York': 'nywb',
 'E.D. North Carolina': 'nceb',
 'M.D. North Carolina': 'ncmb',
 'W.D. North Carolina': 'ncwb',
 'D. North Dakota': 'ndb',
 'N.D. Ohio': 'ohnb',
 'S.D. Ohio': 'ohsb',
 'E.D. Oklahoma': 'okeb',
 'N.D. Oklahoma': 'oknb',
 'W.D. Oklahoma': 'okwb',
 'D. Oregon': 'orb',
 'E.D. Pennsylvania': 'paeb',
 'M.D. Pennsylvania': 'pamb',
 'W.D. Pennsylvania': 'pawb',
 'D. Rhode Island': 'rib',
 'D. South Carolina': 'scb',
 'D. South Dakota': 'sdb',
 'E.D. Tennessee': 'tneb',
 'M.D. Tennessee': 'tnmb',
 'W.D. Tennessee': 'tnwb',
 'D. Tennessee (Terminated\xa01801)': 'tennesseeb',
 'E.D. Texas': 'txeb',
 'N.D. Texas': 'txnb',
 'S.D. Texas': 'txsb',
 'W.D. Texas': 'txwb',
 'D. Utah': 'utb',
 'D. Vermont': 'vtb',
 'E.D. Virginia': 'vaeb',
 'W.D. Virginia': 'vawb',
 'E.D. Washington': 'waeb',
 'W.D. Washington': 'wawb',
 'N.D. West Virginia': 'wvnb',
 'S.D. West Virginia': 'wvsb',
 'E.D. Wisconsin': 'wieb',
 'W.D. Wisconsin': 'wiwb',
 'D. Wyoming': 'wyb',
 'D. Guam': 'gub',
 'Northern Mariana Islands': 'nmib',
 'D. Puerto Rico': 'prb',
 'D. Virgin Islands': 'vib'}

# %%
us_state_courts = {'All': None, 
    'Supreme Court of Alabama': 'ala',
 'Alabama Court of Appeals (Terminated\xa01969)': 'alactapp',
 'Court of Criminal Appeals of Alabama': 'alacrimapp',
 'Court of Civil Appeals of Alabama': 'alacivapp',
 'Alaska Supreme Court': 'alaska',
 'Court of Appeals of Alaska': 'alaskactapp',
 'Arizona Supreme Court': 'ariz',
 'Court of Appeals of Arizona': 'arizctapp',
 'Arizona Tax Court': 'ariztaxct',
 'Supreme Court of Arkansas': 'ark',
 'Court of Appeals of Arkansas': 'arkctapp',
 "Arkansas Workers' Compensation Commission": 'arkworkcompcom',
 'Arkansas Attorney General Reports': 'arkag',
 'California Supreme Court': 'cal',
 'California Court of Appeal': 'calctapp',
 'Appellate Division of the Superior Court of California': 'calappdeptsuper',
 'California Attorney General Reports': 'calag',
 'Supreme Court of Colorado': 'colo',
 'Colorado Court of Appeals': 'coloctapp',
 'Colorado Industrial Claim Appeals Office': 'coloworkcompcom',
 'Colorado Attorney General Reports': 'coloag',
 'Supreme Court of Connecticut': 'conn',
 'Connecticut Appellate Court': 'connappct',
 'Connecticut Superior Court': 'connsuperct',
 'Connecticut Compensation Review Board': 'connworkcompcom',
 'Supreme Court of Delaware': 'del',
 'Court of Chancery of Delaware': 'delch',
 "Delaware Orphan's Court (Terminated\xa01970)": 'delorphct',
 'Superior Court of Delaware': 'delsuperct',
 'Delaware Court of Common Pleas': 'delctcompl',
 'Delaware Family Court': 'delfamct',
 'Court on the Judiciary of Delaware': 'deljudct',
 'District of Columbia Court of Appeals': 'dc',
 'Supreme Court of Florida': 'fla',
 'District Court of Appeal of Florida': 'fladistctapp',
 'Florida Attorney General Reports': 'flaag',
 'Supreme Court of Georgia': 'ga',
 'Court of Appeals of Georgia': 'gactapp',
 'Hawaii Supreme Court': 'haw',
 'Hawaii Intermediate Court of Appeals': 'hawapp',
 'Idaho Supreme Court': 'idaho',
 'Idaho Court of Appeals': 'idahoctapp',
 'Illinois Supreme Court': 'ill',
 'Appellate Court of Illinois': 'illappct',
 'Indiana Supreme Court': 'ind',
 'Indiana Court of Appeals': 'indctapp',
 'Indiana Tax Court': 'indtc',
 'Supreme Court of Iowa': 'iowa',
 'Court of Appeals of Iowa': 'iowactapp',
 'Supreme Court of Kansas': 'kan',
 'Court of Appeals of Kansas': 'kanctapp',
 'Kansas Attorney General Reports': 'kanag',
 'Kentucky Supreme Court': 'ky',
 'Court of Appeals of Kentucky': 'kyctapp',
 'Court of Appeals of Kentucky (pre-1976) (Terminated\xa01975)': 'kyctapphigh',
 'Supreme Court of Louisiana': 'la',
 'Louisiana Court of Appeal': 'lactapp',
 'Louisiana Attorney General Reports': 'laag',
 'Supreme Judicial Court of Maine': 'me',
 'Maine Superior': 'mesuperct',
 'Court of Appeals of Maryland': 'md',
 'Court of Special Appeals of Maryland': 'mdctspecapp',
 'Maryland Chancery Ct (Terminated\xa01854)': 'mdch',
 'Maryland Attorney General Reports': 'mdag',
 'Massachusetts Supreme Judicial Court': 'mass',
 'Massachusetts Appeals Court': 'massappct',
 'Massachusetts Superior Court': 'masssuperct',
 'Massachusetts District Court': 'massdistct',
 'Massachusetts Land Court': 'masslandct',
 'Massachusetts Department of Industrial Accidents': 'maworkcompcom',
 'Michigan Supreme Court': 'mich',
 'Michigan Court of Appeals': 'michctapp',
 'Supreme Court of Minnesota': 'minn',
 'Court of Appeals of Minnesota': 'minnctapp',
 'Minnesota Attorney General Reports': 'minnag',
 'Mississippi Supreme Court': 'miss',
 'Court of Appeals of Mississippi': 'missctapp',
 'Supreme Court of Missouri': 'mo',
 'Missouri Court of Appeals': 'moctapp',
 'Missouri Attorney General Reports': 'moag',
 'Montana Supreme Court': 'mont',
 'Montana Tax Appeal Board': 'monttc',
 'Montana Attorney General Reports': 'montag',
 'Nebraska Supreme Court': 'neb',
 'Nebraska Court of Appeals': 'nebctapp',
 'Nebraska Attorney General Reports': 'nebag',
 'Nevada Supreme Court': 'nev',
 'Court of Appeals of Nevada': 'nevapp',
 'Supreme Court of New Hampshire': 'nh',
 'Supreme Court of New Jersey': 'nj',
 'New Jersey Superior Court App Division': 'njsuperctappdiv',
 'New Jersey Tax Court': 'njtaxct',
 'New Jersey Court of Chancery (Terminated\xa01947)': 'njch',
 'New Mexico Supreme Court': 'nm',
 'New Mexico Court of Appeals': 'nmctapp',
 'New York Court of Appeals': 'ny',
 'Appellate Division of the Supreme Court of New York': 'nyappdiv',
 'Appellate Terms of the Supreme Court of New York': 'nyappterm',
 'New York Supreme Court': 'nysupct',
 'New York County Court': 'nycountyctny',
 'New York District Court': 'nydistct',
 'New York Town and Village Courts': 'nyjustct',
 'New York Family Court': 'nyfamct',
 "New York Surrogate's Court": 'nysurct',
 'Civil Court of the City of New York': 'nycivct',
 'Criminal Court of the City of New York': 'nycrimct',
 'New York Attorney General Reports': 'nyag',
 'Supreme Court of North Carolina': 'nc',
 'Court of Appeals of North Carolina': 'ncctapp',
 'Superior Court of North Carolina': 'ncsuperct',
 'North Carolina Industrial Commission': 'ncworkcompcom',
 'North Dakota Supreme Court': 'nd',
 'North Dakota Court of Appeals': 'ndctapp',
 'Ohio Supreme Court': 'ohio',
 'Ohio Court of Appeals': 'ohioctapp',
 'Ohio Court of Claims': 'ohioctcl',
 'Supreme Court of Oklahoma': 'okla',
 'Court of Civil Appeals of Oklahoma': 'oklacivapp',
 'Court of Criminal Appeals of Oklahoma': 'oklacrimapp',
 'Oklahoma Judicial Ethics Advisory Panel': 'oklajeap',
 'Court on the Judiciary of Oklahoma': 'oklacoj',
 'Oklahoma Attorney General Reports': 'oklaag',
 'Oregon Supreme Court': 'or',
 'Court of Appeals of Oregon': 'orctapp',
 'Oregon Tax Court': 'ortc',
 'Supreme Court of Pennsylvania': 'pa',
 'Superior Court of Pennsylvania': 'pasuperct',
 'Commonwealth Court of Pennsylvania': 'pacommwct',
 'Judicial Discipline of Pennsylvania': 'cjdpa',
 'Supreme Court of Rhode Island': 'ri',
 'Superior Court of Rhode Island': 'risuperct',
 'Supreme Court of South Carolina': 'sc',
 'Court of Appeals of South Carolina': 'scctapp',
 'South Dakota Supreme Court': 'sd',
 'Tennessee Supreme Court': 'tenn',
 'Court of Appeals of Tennessee': 'tennctapp',
 'Court of Criminal Appeals of Tennessee': 'tenncrimapp',
 "Tennessee Court of Workers' Comp. Claims": 'tennworkcompcl',
 "Tennessee Workers' Comp. Appeals Board": 'tennworkcompapp',
 'Tennessee Superior Court for Law and Equity (Terminated\xa01809)': 'tennsuperct',
 'Texas Supreme Court': 'tex',
 'Court of Appeals of Texas': 'texapp',
 'Court of Criminal Appeals of Texas': 'texcrimapp',
 'Texas Special Court of Review': 'texreview',
 'Texas Judicial Panel on Multidistrict Litigation': 'texjpml',
 'Texas Attorney General Reports': 'texag',
 'Utah Supreme Court': 'utah',
 'Court of Appeals of Utah': 'utahctapp',
 'Supreme Court of Vermont': 'vt',
 'Vermont Superior Court': 'vtsuperct',
 'Supreme Court of Virginia': 'va',
 'Court of Appeals of Virginia': 'vactapp',
 'Washington Supreme Court': 'wash',
 'Court of Appeals of Washington': 'washctapp',
 'Washington Attorney General Reports': 'washag',
 'Washington Territory (Terminated\xa01889)': 'washterr',
 'West Virginia Supreme Court': 'wva',
 'Int. Ct. of App. of W.Va.': 'wvactapp',
 'Wisconsin Supreme Court': 'wis',
 'Court of Appeals of Wisconsin': 'wisctapp',
 'Wisconsin Attorney General Reports': 'wisag',
 'Wyoming Supreme Court': 'wyo',
 'Supreme Court of Guam': 'guam',
 'Sup. Ct. of the Comm. of the N. Mariana Islands': 'nmariana',
 'Northern Mariana Islands Commonwealth Superior Court': 'cnmisuperct',
 'Northern Mariana Islands Commonwealth Trial Court': 'cnmitrialct',
 'Supreme Court of Puerto Rico': 'prsupreme',
 'Tribunal De Apelaciones De Puerto Rico/Court of Appeals of Puerto Rico': 'prapp',
 'Supreme Court of The Virgin Islands': 'virginislands',
 'High Court of American Samoa': 'amsamoa',
 'American Samoa District Court': 'amsamoatc'}

# %%
us_more_courts = {'All': None, 
'Air Force Court of Criminal Appeals': 'afcca',
 'U S Air Force Court of Military Review': 'usafctmilrev',
 'Court of Appeals for the Armed Forces': 'armfor',
 'United States Court of Military Appeals': 'cma',
 'Army Court of Criminal Appeals': 'acca',
 'U.S. Army Court of Military Review': 'usarmymilrev',
 'U S Coast Guard Court of Criminal Appeals': 'uscgcoca',
 'U S Coast Guard Court of Military Review': 'cgcomilrev',
 'Military Commission Review': 'mc',
 'Navy-Marine Corps Court of Criminal Appeals': 'nmcca',
 'U.S. Navy-Marine Corps Court of Military Review': 'usnmcmilrev',
 'Cherokee Nation Supreme Court': 'cherokee',
 'Cherokee Nation Judicial Appeals Tribunal': 'cherokeeapp',
 'Cherokee Indian Trib. Ct.': 'cherokeetribct',
 'Cheyenne River Sioux Tribal Court of Appeals': 'cheyrsiouxctapp',
 'Colville Confederated Court of Appeals': 'colvctapp',
 'Coquille Indian Tribal Court': 'coquct',
 'Eastern Band of Cherokee Indians Supreme Court': 'echerkokee',
 'Eastern Band of Cherokee Indians Tribal Court': 'echerokeect',
 'Fort McDowell Yavapai Nation Tribal Court of Appeals': 'ftmcdowctapp',
 'Fort McDowell Supreme Court': 'ftmcdowell',
 'Fort Peck Appellate Court': 'ftpeckctapp',
 'Fort Peck Tribal Court': 'ftpecktrialct',
 'Grand Ronde Court of Appeals': 'grrondectapp',
 'Grand Ronde Tribal Court': 'grrondect',
 'Grand Traverse Band of Ottawa & Chippewa Indians Tribal Appellate Court': 'grtravbandctapp',
 'Grand Traverse Band of Ottawa and Chippewa Indians Tribal Court': 'grtravbandct',
 'Ho-Chunk Nation Supreme Court': 'hochunk',
 'Ho-Chunk Nation Trial Court': 'hochunkct',
 'Hopi Appellate Court': 'hopiappct',
 'Leech Lake Band of Ojibwe Tribal Court': 'leechojibtr',
 'Little River Band of Ottawa Indians Tribal Court of Appeals': 'lrbottawactapp',
 'Little River Band of Ottawa Indians Tribal Court': 'lrbottawact',
 'Little Traverse Bay Bands of Odawa Indians Tribal Appellate Court': 'odawactapp',
 'Mohegan Tribal Court of Appeals': 'moheganctapp',
 'Mohegan Trial Court': 'moheganct',
 'Mohegan Gaming Disputes Trial Court': 'mohegangct',
 'Mohegan Gaming Disputes Court of Appeals': 'mohegangctapp',
 'Council of Elders of the Mohegan Tribe': 'moheganelders',
 'Navajo Nation Supreme Court': 'navajo',
 'Navajo Nation Ct. App.': 'navajoctapp',
 'Navajo Nation Family Court': 'navajofamct',
 "Navajo Nation Children's Court": 'navajochildct',
 'Oneida Appellate Court': 'oneidactapp',
 'Oneida Tribal Judicial System, Trial Court': 'oneidatrialct',
 'Sac and Fox Nation Supreme Court': 'sacfoxsupct',
 'Sac and Fox Nation District Court': 'sacfoxdistct',
 'Confederated Salish & Kootenai Court of Appeals': 'salishctapp',
 'Shoshone and Arapaho Tribal Court': 'shoaraphotr',
 'Swinomish Tribal Court of Appeals': 'swinomishappct',
 'Swinomish Tribal Court': 'swinomishtr',
 'Tulalip Court of Appeals': 'tulalipctapp',
 'White Earth Band of Chippewa Tribal Court': 'webchippewatr',
 'Attorneys General': 'ag',
 'Armed Services Board of Contract Appeals': 'asbca',
 'Federal Claims': 'uscfc',
 'U.S. Tax Court': 'tax',
 'Board of Immigration Appeals': 'bia',
 'Office of Legal Counsel': 'olc',
 'Merit Systems Protection Board': 'mspb',
 'Veterans Claims': 'cavc',
 "Board of Veterans' Appeals": 'bva',
 'Foreign Intelligence Surveillance Court of Review': 'fiscr',
 'Foreign Intelligence Surveillance Court': 'fisc',
 'Court of International Trade': 'cit',
 'U.S. Judicial Conference Committee': 'usjc',
 'Judicial Panel on Multidistrict Litigation': 'jpml',
 'Court of Claims (1992)': 'cc',
 'Commerce Court (1913)': 'com',
 'Customs and Patent Appeals (1982)': 'ccpa',
 'U.S. Customs Court (1980)': 'cusc',
 'Board of Tax Appeals (1942)': 'bta',
 'Emergency Court of Appeals (1962)': 'eca',
 'Temporary Emergency Court of Appeals (1992)': 'tecoa',
 'Special Court under the Regional Rail Reorganization Act (1996)': 'reglrailreorgct',
 "Court of King's Bench (1873)": 'kingsbench'}

# %%
#Define format functions for jurisdiction choice, and GPT questions

all_us_jurisdictions = {'Federal Appellate Courts': us_fed_app_courts, 
                    'Federal District Courts': us_fed_dist_courts, 
                    'Federal Historical Courts': us_fed_hist_courts, 
                    'Bankruptcy Courts': us_bankr_courts, 
                    'State and Territory Courts': us_state_courts, 
                    'More Courts': us_more_courts,
                       }

# %%
us_pacer_fed_app_courts = {'All': None,
    'First Circuit': 'ca1',
 'Second Circuit': 'ca2',
 'Third Circuit': 'ca3',
 'Fourth Circuit': 'ca4',
 'Fifth Circuit': 'ca5',
 'Sixth Circuit': 'ca6',
 'Seventh Circuit': 'ca7',
 'Eighth Circuit': 'ca8',
 'Ninth Circuit': 'ca9',
 'Tenth Circuit': 'ca10',
 'Eleventh Circuit': 'ca11',
 'D.C. Circuit': 'cadc',
 'Federal Circuit': 'cafc',
 'District of Columbia': 'dcd'
}

# %%
us_pacer_fed_dist_courts = {'All': None,
    'M.D. Alabama': 'almd',
 'N.D. Alabama': 'alnd',
 'S.D. Alabama': 'alsd',
 'D. Alaska': 'akd',
 'D. Arizona': 'azd',
 'E.D. Arkansas': 'ared',
 'W.D. Arkansas': 'arwd',
 'C.D. California': 'cacd',
 'E.D. California': 'caed',
 'N.D. California': 'cand',
 'S.D. California': 'casd',
 'D. Colorado': 'cod',
 'D. Connecticut': 'ctd',
 'D. Delaware': 'ded',
 'M.D. Florida': 'flmd',
 'N.D. Florida': 'flnd',
 'S.D. Florida': 'flsd',
 'M.D. Georgia': 'gamd',
 'N.D. Georgia': 'gand',
 'S.D. Georgia': 'gasd',
 'D. Hawaii': 'hid',
 'D. Idaho': 'idd',
 'C.D. Illinois': 'ilcd',
 'N.D. Illinois': 'ilnd',
 'S.D. Illinois': 'ilsd',
 'N.D. Indiana': 'innd',
 'S.D. Indiana': 'insd',
 'N.D. Iowa': 'iand',
 'S.D. Iowa': 'iasd',
 'D. Kansas': 'ksd',
 'E.D. Kentucky': 'kyed',
 'W.D. Kentucky': 'kywd',
 'E.D. Louisiana': 'laed',
 'M.D. Louisiana': 'lamd',
 'W.D. Louisiana': 'lawd',
 'D. Maine': 'med',
 'D. Maryland': 'mdd',
 'D. Massachusetts': 'mad',
 'E.D. Michigan': 'mied',
 'W.D. Michigan': 'miwd',
 'D. Minnesota': 'mnd',
 'N.D. Mississippi': 'msnd',
 'S.D. Mississippi': 'mssd',
 'E.D. Missouri': 'moed',
 'W.D. Missouri': 'mowd',
 'D. Montana': 'mtd',
 'D. Nebraska': 'ned',
 'D. Nevada': 'nvd',
 'D. New Hampshire': 'nhd',
 'D. New Jersey': 'njd',
 'D. New Mexico': 'nmd',
 'E.D. New York': 'nyed',
 'N.D. New York': 'nynd',
 'S.D. New York': 'nysd',
 'W.D. New York': 'nywd',
 'E.D. North Carolina': 'nced',
 'M.D. North Carolina': 'ncmd',
 'W.D. North Carolina': 'ncwd',
 'D. North Dakota': 'ndd',
 'N.D. Ohio': 'ohnd',
 'S.D. Ohio': 'ohsd',
 'E.D. Oklahoma': 'oked',
 'N.D. Oklahoma': 'oknd',
 'W.D. Oklahoma': 'okwd',
 'D. Oregon': 'ord',
 'E.D. Pennsylvania': 'paed',
 'M.D. Pennsylvania': 'pamd',
 'W.D. Pennsylvania': 'pawd',
 'D. Rhode Island': 'rid',
 'D. South Carolina': 'scd',
 'D. South Dakota': 'sdd',
 'E.D. Tennessee': 'tned',
 'M.D. Tennessee': 'tnmd',
 'W.D. Tennessee': 'tnwd',
 'E.D. Texas': 'txed',
 'N.D. Texas': 'txnd',
 'S.D. Texas': 'txsd',
 'W.D. Texas': 'txwd',
 'D. Utah': 'utd',
 'D. Vermont': 'vtd',
 'E.D. Virginia': 'vaed',
 'W.D. Virginia': 'vawd',
 'E.D. Washington': 'waed',
 'W.D. Washington': 'wawd',
 'N.D. West Virginia': 'wvnd',
 'S.D. West Virginia': 'wvsd',
 'E.D. Wisconsin': 'wied',
 'W.D. Wisconsin': 'wiwd',
 'D. Wyoming': 'wyd',
 'D. Guam': 'gud',
 'Northern Mariana Islands': 'nmid',
 'D. Puerto Rico': 'prd',
 'Virgin Islands': 'vid'}

# %%
us_pacer_bankr_courts = {'All': None,
    'M.D. Alabama': 'almb',
 'N.D. Alabama': 'alnb',
 'S.D. Alabama': 'alsb',
 'D. Alaska': 'akb',
 'D. Arizona': 'arb',
 'E.D. Arkansas': 'areb',
 'W.D. Arkansas': 'arwb',
 'C.D. California': 'cacb',
 'E.D. California': 'caeb',
 'N.D. California': 'canb',
 'S.D. California': 'casb',
 'D. Colorado': 'cob',
 'D. Connecticut': 'ctb',
 'D. Delaware': 'deb',
 'District of Columbia': 'dcb',
 'M.D. Florida': 'flmb',
 'N.D. Florida': 'flnb',
 'S.D. Florida': 'flsb',
 'M.D. Georgia': 'gamb',
 'N.D. Georgia': 'ganb',
 'S.D. Georgia': 'gasb',
 'D. Hawaii': 'hib',
 'D. Idaho': 'idb',
 'C.D. Illinois': 'ilcb',
 'N.D. Illinois': 'ilnb',
 'S.D. Illinois': 'ilsb',
 'N.D. Indiana': 'innb',
 'S.D. Indiana': 'insb',
 'N.D. Iowa': 'ianb',
 'S.D. Iowa': 'iasb',
 'D. Kansas': 'ksb',
 'E.D. Kentucky': 'kyeb',
 'W.D. Kentucky': 'kywb',
 'E.D. Louisiana': 'laeb',
 'M.D. Louisiana': 'lamb',
 'W.D. Louisiana': 'lawb',
 'D. Maine': 'meb',
 'D. Maryland': 'mdb',
 'D. Massachusetts': 'mab',
 'E.D. Michigan': 'mieb',
 'W.D. Michigan': 'miwb',
 'D. Minnesota': 'mnb',
 'N.D. Mississippi': 'msnb',
 'S.D. Mississippi': 'mssb',
 'E.D. Missouri': 'moeb',
 'W.D. Missouri': 'mowb',
 'D. Montana': 'mtb',
 'D. Nebraska': 'nebraskab',
 'D. Nevada': 'nvb',
 'D. New Hampshire': 'nhb',
 'D. New Jersey': 'njb',
 'D. New Mexico': 'nmb',
 'E.D. New York': 'nyeb',
 'N.D. New York': 'nynb',
 'S.D. New York': 'nysb',
 'W.D. New York': 'nywb',
 'E.D. North Carolina': 'nceb',
 'M.D. North Carolina': 'ncmb',
 'W.D. North Carolina': 'ncwb',
 'D. North Dakota': 'ndb',
 'N.D. Ohio': 'ohnb',
 'S.D. Ohio': 'ohsb',
 'E.D. Oklahoma': 'okeb',
 'N.D. Oklahoma': 'oknb',
 'W.D. Oklahoma': 'okwb',
 'D. Oregon': 'orb',
 'E.D. Pennsylvania': 'paeb',
 'M.D. Pennsylvania': 'pamb',
 'W.D. Pennsylvania': 'pawb',
 'D. Rhode Island': 'rib',
 'D. South Carolina': 'scb',
 'D. South Dakota': 'sdb',
 'E.D. Tennessee': 'tneb',
 'M.D. Tennessee': 'tnmb',
 'W.D. Tennessee': 'tnwb',
 'E.D. Texas': 'txeb',
 'N.D. Texas': 'txnb',
 'S.D. Texas': 'txsb',
 'W.D. Texas': 'txwb',
 'D. Utah': 'utb',
 'D. Vermont': 'vtb',
 'E.D. Virginia': 'vaeb',
 'W.D. Virginia': 'vawb',
 'E.D. Washington': 'waeb',
 'W.D. Washington': 'wawb',
 'N.D. West Virginia': 'wvnb',
 'S.D. West Virginia': 'wvsb',
 'E.D. Wisconsin': 'wieb',
 'W.D. Wisconsin': 'wiwb',
 'D. Wyoming': 'wyb',
 'D. Guam': 'gub',
 'Northern Mariana Islands': 'nmib',
 'D. Puerto Rico': 'prb',
 'D. Virgin Islands': 'vib'}

# %%
us_pacer_more_courts = {'All': None,
'Federal Claims': 'uscfc',
 'Court of International Trade': 'cit',
 'Judicial Panel on Multidistrict Litigation': 'jpml'}

# %%
#Define format functions for jurisdiction choice, and GPT questions

all_us_pacer_jurisdictions = {'Federal Appellate Courts': us_pacer_fed_app_courts, 
                    'Federal District Courts': us_pacer_fed_dist_courts, 
                    'Bankruptcy Courts': us_pacer_bankr_courts, 
                    'More Courts': us_pacer_more_courts,
                       }

# %% [markdown]
# ### Functions

# %%
test = ['1', '2']

for item in []:
    if item in test:
        print('Yes')


# %%
#Court string to list

def us_court_choice_to_list(court_string):

    #Return list if is list already
    if isinstance(court_string, list):
        
        return court_string

    else:

        if court_string:
    
            court_list = court_string.split("; ")
        
            return court_list
    
        else:
            return []
        


# %%
#Fill in each court if 'All' is not chosen for all jurisdictions
def us_court_choice_clean(court_entries_list):

    #Intitial status of False means (every court entry list has 'All') <=> (some court entry list does not have 'All')
    no_all_in_some_list_entry = False

    for entry_list in court_entries_list:

        if ((entry_list == None) or (entry_list == [])):
            
            no_all_in_some_list_entry = True

            break
        
        else:
            
            if 'All' not in entry_list:
                
                no_all_in_some_list_entry = True
                
                break
    
    #Return original court entries as a list if every court entry list has 'All'
    if no_all_in_some_list_entry == False:

        all_court_entries_list = [['All'],['All'],['All'],['All'],['All'],['All']] 
        
        return all_court_entries_list

    else:

        cleaned_court_entries_list = []

        jurisdiction_index = 0

        for entry_list in court_entries_list:

            #st.write(entry_list)

            cleaned_list_entry_list = []

            #If 'All' not chosen
            if 'All' not in entry_list:

                cleaned_list_entry_list = entry_list

            #If 'All' chosen, then add every court for that jurisdiction
            else:
                
                jurisdiction = list(all_us_jurisdictions.keys())[jurisdiction_index]

                #st.write(jurisdiction)

                cleaned_list_entry_list = list(all_us_jurisdictions[jurisdiction].keys())

            #st.write(cleaned_list_entry_list)
            
            cleaned_court_entries_list.append(cleaned_list_entry_list)

            jurisdiction_index += 1

        return cleaned_court_entries_list



# %%
#Fill in each court if 'All' is not chosen for all jurisdictions
def us_court_choice_clean_pacer(court_entries_list):

    #Intitial status of False means (every court entry list has 'All') <=> (some court entry list does not have 'All')
    no_all_in_some_list_entry = False

    for entry_list in court_entries_list:

        if ((entry_list == None) or (entry_list == [])):
            
            no_all_in_some_list_entry = True

            break
        
        else:
            
            if 'All' not in entry_list:
                
                no_all_in_some_list_entry = True
                
                break
    
    #Return original court entries as a list if every court entry list has 'All'
    if no_all_in_some_list_entry == False:

        all_court_entries_list = [['All'],['All'],['All'],['All']] 
        
        return all_court_entries_list

    else:

        cleaned_court_entries_list = []

        jurisdiction_index = 0

        for entry_list in court_entries_list:

            #st.write(entry_list)

            cleaned_list_entry_list = []

            #If 'All' not chosen
            if 'All' not in entry_list:

                cleaned_list_entry_list = entry_list

            #If 'All' chosen, then add every court for that jurisdiction
            else:
                
                jurisdiction = list(all_us_pacer_jurisdictions.keys())[jurisdiction_index]

                #st.write(jurisdiction)

                cleaned_list_entry_list = list(all_us_pacer_jurisdictions[jurisdiction].keys())

            #st.write(cleaned_list_entry_list)
            
            cleaned_court_entries_list.append(cleaned_list_entry_list)

            jurisdiction_index += 1

        return cleaned_court_entries_list



# %%
def us_date(x):
    try:
        return parser.parse(x)
    except:
        return None



# %% [markdown]
# ## Search engine

# %%
from functions.common_functions import link


# %%
class us_search_tool:

    def __init__(self, token, judgment_counter_bound = default_judgment_counter_bound):

        self.token = token
        self.headers = {'Authorization': self.token,
        }
        self.judgment_counter_bound = judgment_counter_bound

        #Essential keys to rename, then drop
        self.renamed_keys = ['caseName', 'citation', 'absolute_url', 'docket_absolute_url', 'court', 'dateFiled', 'dateTerminated', 'judge', 'docketNumber'] #, 'neutralCite', 'recap_documents']

        #Default arguments/values
        self.doc_type = 'o'
        self.params = []
        self.page = None
        self.next_page = None
        self.results = []
        self.results_count = 0
        self.results_to_show = []
        self.results_w_opinions = []
        self.results_w_docs = []
        self.metadata_droppable = []

    #Method for conducting search
    def search(self, 
               doc_type = list(us_collections.keys())[0], 
               fed_app_courts = [], 
              fed_dist_courts = [], 
              fed_hist_courts = [], 
             bankr_courts = [], 
            state_courts = [], 
            more_courts = [], 
             q = '', 
              order_by = list(us_order_by.keys())[0], 
               precedential_status = [list(us_precedential_status.keys())[0]], 
               case_name = None, 
                judge = None, 
               filed_after = None, 
               filed_before = None, 
               cited_gt = None, 
               cited_lt = None, 
               citation = None, 
               neutral_cite = None, 
               docket_number = None, 
               #For PACER only
               description=None, 
                document_number=None,
                attachment_number=None,
                assigned_to=None,
                referred_to=None,
                nature_of_suit=None,
                party_name=None,
                atty_name=None,
                available_only = True,
              ):

        #Determine document type sought
        self.doc_type = us_collections[doc_type]

        #Params for both opinions and PACER docs
        params_raw = [
            ('type', self.doc_type),
            ('q', q), 
            ('type', self.doc_type),
            ('order_by', us_order_by[order_by])
        ]

        if filed_after:
            if len(filed_after) > 0:
                params_raw.append(('filed_after', filed_after))

        if filed_before:
            if len(filed_before) > 0:
                params_raw.append(('filed_before', filed_before))

        if case_name:
            params_raw.append(('case_name', case_name))
        
        if docket_number:
            params_raw.append(('docket_number', docket_number)),
        
        #Params for opinions only
        if self.doc_type == 'o':

            if isinstance(precedential_status, str):
                precedential_status = ast.literal_eval(precedential_status)
            
            for status in precedential_status:
                status_key = us_precedential_status[status]
                params_raw.append((status_key, 'on'))

            if judge:
                params_raw.append(('judge', judge))
    
            if cited_gt:
                params_raw.append(('cited_gt', cited_gt))
    
            if cited_lt:
                params_raw.append(('cited_lt', cited_lt))
    
            if citation:
                params_raw.append(('citation', citation))
            
            if neutral_cite:
                params_raw.append(('neutral_cite', neutral_cite))

            #Deal with courts
            court_entries_list_raw = [fed_app_courts, fed_dist_courts, fed_hist_courts, bankr_courts, state_courts, more_courts]
        
            court_entries_list = us_court_choice_clean(court_entries_list_raw)
            
            fed_app_courts = court_entries_list[0]
        
            fed_dist_courts = court_entries_list[1]
        
            fed_hist_courts = court_entries_list[2]
        
            bankr_courts = court_entries_list[3]
        
            state_courts = court_entries_list[4]
        
            more_courts = court_entries_list[5]
        
            court_list = []
            
            if isinstance(fed_app_courts, str):
                fed_app_courts = ast.literal_eval(fed_app_courts)
    
            for court in fed_app_courts:
                if court != 'All':
                    court_list.append(us_fed_app_courts[court])
    
            if isinstance(fed_dist_courts, str):
                fed_dist_courts = ast.literal_eval(fed_dist_courts)
    
            for court in fed_dist_courts:
                if court != 'All':
                    court_list.append(us_fed_dist_courts[court])
    
            if isinstance(fed_hist_courts, str):
                fed_hist_courts = ast.literal_eval(fed_hist_courts)
    
            for court in fed_hist_courts:
                if court != 'All':
                    court_list.append(us_fed_hist_courts[court])
                
            if isinstance(bankr_courts, str):
                bankr_courts = ast.literal_eval(bankr_courts)
                
            for court in bankr_courts:
                if court != 'All':
                    court_list.append(us_bankr_courts[court])
    
            if isinstance(state_courts, str):
                state_courts = ast.literal_eval(state_courts)
    
            for court in state_courts:
                if court != 'All':
                    court_list.append(us_state_courts[court])
    
            if isinstance(more_courts, str):
                more_courts = ast.literal_eval(more_courts)
    
            for court in more_courts:
                if court != 'All':
                    court_list.append(us_more_courts[court])
    
            #st.write(f"court_list is {court_list}")
            if len(court_list) > 0:
                court_string = ' '.join(court_list)
                params_raw.append(('court', court_string))

        #Params for PACER docs only
        if self.doc_type == 'r':

            if description:
                params_raw.append(('description', description))
    
            if document_number:
                params_raw.append(('document_number', document_number))
    
            if attachment_number:
                params_raw.append(('attachment_number', attachment_number))
    
            if assigned_to:
                params_raw.append(('assigned_to', assigned_to))
    
            if referred_to:
                params_raw.append(('referred_to', referred_to))
    
            if nature_of_suit:
                params_raw.append(('nature_of_suit', nature_of_suit))
    
            if party_name:
                params_raw.append(('party_name', party_name))
    
            if atty_name:
                params_raw.append(('atty_name', atty_name))
    
            if int(float(available_only)) == 1:
                params_raw.append(('available_only', 'on'))

            #Deal with courts
            court_entries_list_raw = [fed_app_courts, fed_dist_courts, bankr_courts, more_courts]
        
            court_entries_list = us_court_choice_clean_pacer(court_entries_list_raw)
            
            fed_app_courts = court_entries_list[0]
        
            fed_dist_courts = court_entries_list[1]
                
            bankr_courts = court_entries_list[2]
                
            more_courts = court_entries_list[3]
        
            court_list = []
            
            if isinstance(fed_app_courts, str):
                fed_app_courts = ast.literal_eval(fed_app_courts)
    
            for court in fed_app_courts:
                if court != 'All':
                    court_list.append(us_pacer_fed_app_courts[court])
    
            if isinstance(fed_dist_courts, str):
                fed_dist_courts = ast.literal_eval(fed_dist_courts)
    
            for court in fed_dist_courts:
                if court != 'All':
                    court_list.append(us_pacer_fed_dist_courts[court])
                    
            if isinstance(bankr_courts, str):
                bankr_courts = ast.literal_eval(bankr_courts)
                
            for court in bankr_courts:
                if court != 'All':
                    court_list.append(us_pacer_bankr_courts[court])
        
            if isinstance(more_courts, str):
                more_courts = ast.literal_eval(more_courts)
    
            for court in more_courts:
                if court != 'All':
                    court_list.append(us_pacer_more_courts[court])
    
            #st.write(f"court_list is {court_list}")
            if len(court_list) > 0:
                court_string = ' '.join(court_list)
                params_raw.append(('court', court_string))
        
        #Save params
        params = urllib.parse.urlencode(params_raw, quote_via=urllib.parse.quote)
        self.params = params

        #API url
        advanced_search = 'https://www.courtlistener.com/api/rest/v4/search/'

        #Save page
        self.page = requests.get(advanced_search, params=self.params, headers=self.headers)

        #Save url to search results
        self.results_url = self.page.url

        #st.write(f"self.results_url is {self.results_url}")
        
        self.results_url_to_show = self.results_url.replace('/api/rest/v4/search', '')

        try:
            page_json = json.loads(self.page.content.decode('utf-8')) 
            
            self.results_count = page_json["count"]
    
            results_raw = page_json['results']

        except Exception as e:
            st.error('No results found.')
            #st.error(e)
            st.error(f"self.page_json is {page_json}")

        result_counter = 1

        while result_counter <= min(self.results_count, self.judgment_counter_bound):
                
            for case_raw in results_raw:

                if result_counter <= min(self.results_count, self.judgment_counter_bound):

                    #Keep first x number of results
                    self.results.append(case_raw)
                    
                    result_counter += 1
                    
            if result_counter <= min(self.results_count, self.judgment_counter_bound):
            #Get results from next page if still under judgment_counter_bound

                next_page_url = page_json['next']

                if type(next_page_url) == str:

                    if advanced_search in next_page_url:
                
                        self.next_page = requests.get(next_page_url, headers=self.headers)
                        
                        next_page_json = json.loads(next_page.content.decode('utf-8'))
        
                        results_raw = next_page_json['results']
                            
        #self.results = results

        #Create results for display
        absolute_url_field = 'absolute_url'
        
        if self.doc_type == 'o': #Opinions
            absolute_url_field = 'absolute_url'

        if self.doc_type == 'r': #PACER docs
            absolute_url_field = 'docket_absolute_url'
            
        for result in self.results:

            result_to_show = {}

            #Add each field if available
            if 'caseName' in result.keys():
                case_name = result['caseName']
                result_to_show.update({'Case name' : case_name})
                
            if 'citation' in result.keys():
                citation = result['citation']
                result_to_show.update({'Citation' : citation})

            hyperlink = f"https://www.courtlistener.com{result[absolute_url_field]}"
            result_to_show.update({'Hyperlink to CourtListener': link(hyperlink)})

            #if 'neutralCite' in result.keys():
                #neutral_cite = result['neutralCite']
                #result_to_show.update({'Neutral citation' : neutral_cite})

            if 'court' in result.keys():
                court =  result['court']
                result_to_show.update({'Court' : court})

            if 'dateFiled' in result.keys():
                filed = result['dateFiled']
                result_to_show.update({'Filed' : filed})

            if 'dateTerminated' in result.keys():
                dateTerminated = result['dateTerminated']
                result_to_show.update({'Terminated' : dateTerminated})
            
            if 'docketNumber' in result.keys():
                docket = result['docketNumber']
                result_to_show.update({'Docket number' : docket})

            if 'judge' in result.keys():
                judge = result['judge']
                result_to_show.update({'Judges' : judge})

            self.results_to_show.append(result_to_show)

    #Function for getting opinion text from opinion_raw
    @st.cache_data
    def clean_opinion_json(_self, opinion_raw, headers):

        opinion_id = opinion_raw['id']
        opinion_url = f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/"
        opinion_page = requests.get(opinion_url, headers=headers)
        #opinion_soup = BeautifulSoup(opinion_page.content, "lxml")
        #opinion_json = json.loads(opinion_soup.text)
        opinion_json = json.loads(opinion_page.content.decode('utf-8'))

        #Placeholders        
        opinion_snippet = ''
        opinion_type = ''
        #opinion_id = ''
        opinion_text = ''

        opinion_json_cleaned = {'snippet': opinion_snippet, 'type': opinion_type, 'text': opinion_text}

        if 'snippet' in opinion_json.keys():
            opinion_snippet = opinion_json['snippet']

        if 'type' in opinion_json.keys():
            opinion_type = opinion_json['type']

        #if 'id' in opinion_json.keys():
            #opinion_id = opinion_json['id']

        #Getting opinion text from sources sorted from worst to best, so the last checked is best
        #See https://www.courtlistener.com/help/api/rest/case-law/#opinion-endpoint
        
        if 'plain_text' in opinion_json.keys():
            if len(opinion_json['plain_text']) > 0:
                opinion_text = opinion_json['plain_text']
        
        if 'html' in opinion_json.keys():
            if len(opinion_json['html']) > 0:
                opinion_text = opinion_json['html']

        if 'html_anon_2020' in opinion_json.keys():
            if len(opinion_json['html_anon_2020']) > 0:
                opinion_text = opinion_json['html_anon_2020']

        if 'xml_harvard' in opinion_json.keys():
            if len(opinion_json['xml_harvard']) > 0:
                opinion_text = opinion_json['xml_harvard']

        if 'html_lawbox' in opinion_json.keys():
            if len(opinion_json['html_lawbox']) > 0:
                opinion_text = opinion_json['html_lawbox']

        if 'html_columbia' in opinion_json.keys():
            if len(opinion_json['html_columbia']) > 0:
                opinion_text = opinion_json['html_columbia']
        
        if 'html_with_citations' in opinion_json.keys():
            if len(opinion_json['html_with_citations']) > 0:
                opinion_text = opinion_json['html_with_citations']

        opinion_json_cleaned = {'snippet': opinion_snippet, 'type': opinion_type, 'text': opinion_text}
        
        if len(opinion_json_cleaned['text']) == 0:
            st.write(f'Opinion id {opinion_id}: no text scraped. Please check {opinion_url}.')

        return opinion_json_cleaned

    #Method for getting all opinions from all results
    def get_opinions(self):

        #Note if doc_type is not opinion
        if self.doc_type != 'o':
            print('Not scraping opinions becase another type of documents is sought.')
        else:
            
            self.results_w_opinions = self.results_to_show.copy()
            
            for result in self.results:
    
                #Create placeholder for 'opinions' instead of 'judgment'
                result_index = self.results.index(result)
                self.results_w_opinions[result_index]['opinions'] = []
                opinion_list_raw = []
                
                #Get a list of opinions
                opinions_list = result['opinions']
                for opinion_raw in opinions_list:
                    opinion_json_cleaned = self.clean_opinion_json(opinion_raw, self.headers)
                    opinion_list_raw.append(opinion_json_cleaned)
                    pause.seconds(np.random.randint(5, 10))

                    #self.results_w_opinions[result_index]['opinions'].append(opinion_json_cleaned)
    
                #Append opinion to result from combined, to leading, to concurrence, to dissent
                for opinion_json_cleaned in opinion_list_raw:
                    if 'combine' in opinion_json_cleaned['type']:
                        self.results_w_opinions[result_index]['opinions'] = [opinion_json_cleaned]
                        break
                        
                    elif 'lead' in opinion_json_cleaned['type']:
                        self.results_w_opinions[result_index]['opinions'].insert(0, opinion_json_cleaned)
                                        
                    elif 'dissent' in opinion_json_cleaned['type']:
                        self.results_w_opinions[result_index]['opinions'].insert(-1, opinion_json_cleaned)
    
                    else: #'concur' in opinion_json_cleaned['type']:
                        self.results_w_opinions[result_index]['opinions'].append(opinion_json_cleaned)
    
                #Add case-specific metadata to results_w_opinions, create list of dropable metadata
                for key in result.keys():
                    if key not in self.renamed_keys:
                        self.results_w_opinions[result_index][key] = result[key]
                        self.metadata_droppable.append(key)

    #Define function for getting PDF from one link
    @st.cache_data
    def clean_doc_json(_self, recap_document, headers):

        headers.update({'User-Agent': 'whatever'})
    
        if ('filepath_local' in recap_document.keys()) and ('is_available' in recap_document.keys()):
            if (('.pdf' in str(recap_document['filepath_local']).lower()) and (str(recap_document['is_available']).lower() == 'true')):
                pdf_url = 'https://storage.courtlistener.com/' + recap_document['filepath_local']
                r = requests.get(pdf_url, headers=headers)
                remote_file_bytes = io.BytesIO(r.content)
                pdfdoc_remote = pypdf.PdfReader(remote_file_bytes)
                text_list = []
            
                for page in pdfdoc_remote.pages:
                    text_list.append(page.extract_text())
    
                recap_document['file_content'] = str(text_list)
        
        return recap_document

    #Method for getting all PDF PACER docs from all results
    def get_docs(self):

        #Note if doc_type is not opinion
        if self.doc_type != 'r':
            print('Not scraping PACER documents because another type of documents is sought.')
        else:
            self.results_w_docs = self.results_to_show.copy()
            
            for result in self.results:
    
                #Create placeholder for 'recap_documents' (instead of 'judgment')
                result_index = self.results.index(result)
                self.results_w_docs[result_index]['recap_documents'] = []
                
                #Get a list of docs
                docs_list = result['recap_documents']

                #Get PDF for each doc json from the list of docs, then append each json with PDF to results_w_docs
                for doc_raw in docs_list:
                    doc_json_cleaned = self.clean_doc_json(doc_raw, self.headers)
                    self.results_w_docs[result_index]['recap_documents'].append(doc_json_cleaned)
                    pause.seconds(np.random.randint(5, 10))

                #Add case-specific metadata key/values to results_w_docs, create list of dropable metadata
                for key in result.keys():
                    if key not in self.renamed_keys:
                        self.results_w_docs[result_index][key] = result[key]
                        self.metadata_droppable.append(key)
                        


# %%
@st.cache_data
def us_search_preview(df_master):
    
    df_master = df_master.fillna('')

    court_listener_token = df_master.loc[0, 'CourtListener API token']

    #st.write(court_listener_token)
    
    us_search = us_search_tool(token = court_listener_token)
    
    #Conduct search
    
    us_search.search(
                doc_type = df_master.loc[0, 'Collection'], 
                fed_app_courts = df_master.loc[0, 'Federal Appellate Courts'], 
                fed_dist_courts = df_master.loc[0, 'Federal District Courts'], 
                fed_hist_courts = df_master.loc[0, 'Federal Historical Courts'], 
                bankr_courts = df_master.loc[0, 'Bankruptcy Courts'], 
                state_courts = df_master.loc[0, 'State and Territory Courts'], 
                more_courts = df_master.loc[0, 'More Courts'] , 
                q = df_master.loc[0, 'Search'], 
                order_by = df_master.loc[0, 'Search results order'], 
                precedential_status = df_master.loc[0, 'Precedential status'], 
                case_name = df_master.loc[0, 'Case name'], 
                judge = df_master.loc[0, 'Judge'], 
                filed_after = df_master.loc[0, 'Filed after'], 
                filed_before = df_master.loc[0, 'Filed before'], 
                cited_gt = df_master.loc[0, 'Min cites'], 
                cited_lt = df_master.loc[0, 'Max cites'], 
                citation = df_master.loc[0, 'Citation'], 
                neutral_cite = df_master.loc[0, 'Neutral citation'], 
                docket_number = df_master.loc[0, 'Docket number'],
                description = df_master.loc[0, 'Document description'],
                document_number = df_master.loc[0, 'Document number'],
                attachment_number = df_master.loc[0, 'Attachment number'],
                assigned_to = df_master.loc[0, 'Assigned to judge'],
                referred_to = df_master.loc[0, 'Referred to judge'],
                nature_of_suit = df_master.loc[0, 'Nature of suit'],
                party_name = df_master.loc[0, 'Party name'],
                atty_name = df_master.loc[0, 'Attorney name'],
                available_only = df_master.loc[0, 'Only show results with PDFs'],
                )
    
    url = us_search.results_url_to_show
    results_count = us_search.results_count
    results_to_show = us_search.results_to_show

    return {'url': url, 'results_count': results_count, 'results_to_show': us_search.results_to_show}


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import question_characters_bound, role_content#, intro_for_GPT
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction

if check_questions_answers() > 0:
    print(f'By default, questions and answers are checked for potential privacy violation.')
else:
    print(f'By default, questions and answers are NOT checked for potential privacy violation.')


# %%
#Jurisdiction specific instruction and functions

system_instruction = role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#Obtain parameters

@st.cache_data
def us_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
        
    court_listener_token = df_master.loc[0, 'CourtListener API token']

    #st.write(f"court_listener_token is {court_listener_token}")

    us_search = us_search_tool(token = court_listener_token, judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']))
    
    #Conduct search
    
    us_search.search(
                doc_type = df_master.loc[0, 'Collection'], 
                fed_app_courts = df_master.loc[0, 'Federal Appellate Courts'], 
                fed_dist_courts = df_master.loc[0, 'Federal District Courts'], 
                fed_hist_courts = df_master.loc[0, 'Federal Historical Courts'], 
                bankr_courts = df_master.loc[0, 'Bankruptcy Courts'], 
                state_courts = df_master.loc[0, 'State and Territory Courts'], 
                more_courts = df_master.loc[0, 'More Courts'] , 
                q = df_master.loc[0, 'Search'], 
                order_by = df_master.loc[0, 'Search results order'], 
                precedential_status = df_master.loc[0, 'Precedential status'], 
                case_name = df_master.loc[0, 'Case name'], 
                judge = df_master.loc[0, 'Judge'], 
                filed_after = df_master.loc[0, 'Filed after'], 
                filed_before = df_master.loc[0, 'Filed before'], 
                cited_gt = df_master.loc[0, 'Min cites'], 
                cited_lt = df_master.loc[0, 'Max cites'], 
                citation = df_master.loc[0, 'Citation'], 
                neutral_cite = df_master.loc[0, 'Neutral citation'], 
                docket_number = df_master.loc[0, 'Docket number'],
                description = df_master.loc[0, 'Document description'],
                document_number = df_master.loc[0, 'Document number'],
                attachment_number = df_master.loc[0, 'Attachment number'],
                assigned_to = df_master.loc[0, 'Assigned to judge'],
                referred_to = df_master.loc[0, 'Referred to judge'],
                nature_of_suit = df_master.loc[0, 'Nature of suit'],
                party_name = df_master.loc[0, 'Party name'],
                atty_name = df_master.loc[0, 'Attorney name'],
                available_only = df_master.loc[0, 'Only show results with PDFs'],
                )

    #If seeking opinions
    if df_master.loc[0, 'Collection'] == list(us_collections.keys())[0]:
    
        us_search.get_opinions()
    
        for judgment_json in us_search.results_w_opinions:
    
            judgments_file.append(judgment_json)

    else:  #If seeking PACER docs

        us_search.get_docs()
    
        for judgment_json in us_search.results_w_docs:
    
            judgments_file.append(judgment_json)
        
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
                        
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o-2024-08-06"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    #Remove 'judgment' column if opinions sought #, or 'recap_documents' column if PACER docs sought
    if 'judgment' in df_updated.columns:
        df_updated.pop('judgment')

    if 'recap_documents' in df_updated.columns:
        df_updated.pop('recap_documents')

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in us_search.metadata_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
#Obtain parameters

@st.cache_data
def us_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    court_listener_token = df_master.loc[0, 'CourtListener API token']

    #st.write(f"court_listener_token is {court_listener_token}")
    
    us_search = us_search_tool(token = court_listener_token, judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']))
    
    #Conduct search
    
    us_search.search(
                doc_type = df_master.loc[0, 'Collection'], 
                fed_app_courts = df_master.loc[0, 'Federal Appellate Courts'], 
                fed_dist_courts = df_master.loc[0, 'Federal District Courts'], 
                fed_hist_courts = df_master.loc[0, 'Federal Historical Courts'], 
                bankr_courts = df_master.loc[0, 'Bankruptcy Courts'], 
                state_courts = df_master.loc[0, 'State and Territory Courts'], 
                more_courts = df_master.loc[0, 'More Courts'] , 
                q = df_master.loc[0, 'Search'], 
                order_by = df_master.loc[0, 'Search results order'], 
                precedential_status = df_master.loc[0, 'Precedential status'], 
                case_name = df_master.loc[0, 'Case name'], 
                judge = df_master.loc[0, 'Judge'], 
                filed_after = df_master.loc[0, 'Filed after'], 
                filed_before = df_master.loc[0, 'Filed before'], 
                cited_gt = df_master.loc[0, 'Min cites'], 
                cited_lt = df_master.loc[0, 'Max cites'], 
                citation = df_master.loc[0, 'Citation'], 
                neutral_cite = df_master.loc[0, 'Neutral citation'], 
                docket_number = df_master.loc[0, 'Docket number'],
                description = df_master.loc[0, 'Document description'],
                document_number = df_master.loc[0, 'Document number'],
                attachment_number = df_master.loc[0, 'Attachment number'],
                assigned_to = df_master.loc[0, 'Assigned to judge'],
                referred_to = df_master.loc[0, 'Referred to judge'],
                nature_of_suit = df_master.loc[0, 'Nature of suit'],
                party_name = df_master.loc[0, 'Party name'],
                atty_name = df_master.loc[0, 'Attorney name'],
                available_only = df_master.loc[0, 'Only show results with PDFs'],
                )

    #If seeking opinions
    if df_master.loc[0, 'Collection'] == list(us_collections.keys())[0]:
    
        us_search.get_opinions()
    
        for judgment_json in us_search.results_w_opinions:
    
            judgments_file.append(judgment_json)

    else:  #If seeking PACER docs

        us_search.get_docs()
    
        for judgment_json in us_search.results_w_docs:
    
            judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)

    #Drop metadata if not wanted

    if int(float(df_master.loc[0, 'Metadata inclusion'])) == 0:
        for meta_label in us_search.metadata_droppable:
            try:
                df_updated.pop(meta_label)
            except Exception as e:
                print(f'{meta_label} not popped.')
                print(e)
    
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o-2024-08-06"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet

    #Need to convert date column to string

    if 'Filed' in df_individual.columns:

        df_individual['Filed'] = df_individual['Filed'].astype(str)
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)
    
    return batch_record_df_individual

