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
#import pypdf
import io
from io import BytesIO
import ast
import urllib

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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # Canada search engine

# %%
from functions.common_functions import link

# %% [markdown]
# ## Definitions

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
ca_court_tribunal_types = {'All courts and tribunals': '', 
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
all_subjects = ['Access to information and privacy', 'Administrative remedies', 'Appeal', 'Arbitration', 'Bankruptcy and insolvency', 'Business', 'Child custody and access', 'Child protection', 'Citizenship and immigration', 'Commerce and industry', 'Constitution', 'Contracts', 'Creditors and debtors', 'Criminal or statutory infractions', 'Damages', 'Defences', 'Environment', 'Evidence', 'Family', 'Guardianship', 'Health and safety', 'Indigenous peoples', 'Insurance', 'Intellectual property', 'International', 'Interpretation', 'Judicial review', 'Labour and employment', 'Motor vehicles', 'Municipalities', 'Negligence', 'Practice and procedure', 'Professions and occupations', 'Property and trusts', 'Public administration', 'Residential tenancies', 'Rights and freedoms', 'Search and seizure', 'Sentencing', 'Support and maintenance', 'Taxation', 'Torts', 'Wills and estates', 'Young offenders'] #, '']

# %%
ca_meta_labels_droppable = ["Decision date", "Collection", "Jurisdiction", "Keywords", "Subjects", 'Court', 'File number', 'Other citations', 'Most recent unfavourable mention']


# %%
ca_meta_dict = {
 'Case name': 'lbh-title',
    #'Hyperlink to CanLII': 'lbh-document-url',
 'Medium neutral citation': 'lbh-citation',
 'Decision date': 'lbh-decision-date',
 'Court': 'lbh-collection',
 'Jurisdiction': 'lbh-jurisdiction',
 'Keywords': 'lbh-keywords',
 'Subjects': 'lbh-subjects'}

# %% [markdown]
# ## Search engine

# %%
from functions.common_functions import running_locally_dir, get_uc_driver

#For downloading judgments
download_dir = f"{os.getcwd()}/CA_PDFs"

#Headless mode?
if running_locally_dir in os.getcwd(): 

    headless = False

else:
    
    from pyvirtualdisplay import Display
    
    display = Display(visible=0, size=(1200, 1600))  
    display.start()

# %%
#Get uc modules
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
from selenium.common.exceptions import ElementClickInterceptedException


# %%
#Function turning search terms to search results url
#@st.cache_data(show_spinner = False)

class ca_search_tool:

    def __init__(self, 
                jurisdiction  =  'All', 
                court = 'All', 
                phrase = None, 
                case_name_mnc= None, 
                court_tribunal_type = 'All courts and tribunals', 
                subjects = [], 
                on_this_date = None,
                after_date = None,
                before_date = None,
                 judgment_counter_bound = default_judgment_counter_bound
                ):
        
        self.jurisdiction  = jurisdiction 
        self.court = court
        self.phrase = phrase
        self.case_name_mnc= case_name_mnc
        self.court_tribunal_type = court_tribunal_type
        self.subjects = subjects
        self.on_this_date = on_this_date
        self.after_date = after_date
        self.before_date = before_date

        self.judgment_counter_bound = judgment_counter_bound
    
        self.results_count = 0
    
        self.results_url = ''
        
        self.case_infos = []

        #Selenium objects
        self.browser = None
        self.elements = None
    
    def search(self):

        #Reset infos of cases found
        self.case_infos = []
                
        #Default base url with self.jurisdiction and self.court to remove if not entered
        base_url = f'https://www.canlii.org/jurisdiction_param/?origLang=en#search/type=decision&jId=jurisdiction_param,unspecified'
        
        #Add self.jurisdiction, self.court or year; these appear before or after #search/type=decision in url depending on whether a juirsdiction is chosen
        if self.jurisdiction != 'All':
    
            base_url = base_url.replace('jurisdiction_param', f'{all_ca_jurisdictions[self.jurisdiction]}')
            
        else:
            
            base_url = base_url.replace('&jId=jurisdiction_param,unspecified', '').replace('jurisdiction_param/', '')
    
        if self.court != 'All':
    
            base_url = f'https://www.canlii.org/jurisdiction_param/court_param/?origLang=en#search/type=decision&ccId=ccid_param'
    
            base_url = base_url.replace('jurisdiction_param', f'{all_ca_jurisdictions[self.jurisdiction]}')
    
            if self.court == 'Supreme self.court of Canada':
                
                ccID = 'csc-scc'
    
            elif self.court == 'Supreme self.court of Canada - Applications for Leave':
    
                ccID = 'csc-scc-al'
    
            else:
                
                ccID = all_ca_jurisdiction_court_pairs[self.jurisdiction][self.court]
    
            base_url = base_url.replace('court_param', f'{all_ca_jurisdiction_court_pairs[self.jurisdiction][self.court]}')
            
            base_url = base_url.replace('ccid_param', ccID)
        
        else:
            
            base_url = base_url.replace('&ccId=court_param', '').replace('court_param/', '')
    
        #D/W about year as it is a browse function

        #Add seasrch params

        params = {}
        
        #Add self.court or tribunal type
    
        if ca_court_tribunal_types[self.court_tribunal_type] != None:

            params.update({'ccType': ca_court_tribunal_types[self.court_tribunal_type]})
                
        #Add dates
    
        if self.before_date != None:

            params.update({'endDate': self.before_date})
                
        if self.after_date != None:

            params.update({'startDate': self.after_date})
        
        if self.on_this_date != None:
            
            params.update({'date': self.on_this_date})
    
        #Add topics 
        if len(self.subjects) > 0:

            if isinstance(self.subjects, str):

                self.subjects = ast.literal_eval(self.subjects)
    
            subjects_text = ",".join(self.subjects)

            params.update({'topics': subjects_text})
    
        #Add search terms
        
        if self.phrase != None:

            params.update({'text': self.phrase})
    
        if self.case_name_mnc != None:

            params.update({'id': self.case_name_mnc})
    
        #Can't get noteup/discussion to work given dynamic
    
        #return url
    
        self.results_url = base_url + '&' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote, safe=',')
        
        #Load page
            
        self.browser = get_uc_driver(download_dir = download_dir, headless = headless)

        self.browser.get(self.results_url)

        #Accept cookies
        try:
            
            accept_cookies = Wait(self.browser, 15).until(EC.presence_of_element_located((By.XPATH, "//button[@id='understandCookieConsent' or @id='cookieConsentBlocker']"))) 

            accept_cookies.click()
            
            print(f"Clicked accept_cookies")

        except ElementClickInterceptedException as e:

            print(f"Did not click accept_cookies due to error: {e}")            

            try:
            
                print("Trying to click accept_cookies again")
                
                self.browser.execute_script("arguments[0].click()", accept_cookies)
            
            except Exception as e:

                print(f"Did not click accept_cookies due to error: {e}")            

        pause.seconds(np.random.randint(scraper_pause_mean, scraper_pause_mean + 10))                

        #click on search button
        try:

            search_button = Wait(self.browser, 15).until(EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Start a search']")))

            print("search_button found")
            
            search_button.click()

            print(f"search_button clicked")
                    
        except ElementClickInterceptedException as e:

            print(f"Did not click search_button due to error: {e}")

            try:
            
                print("Trying to click search_button again")

                self.browser.execute_script("arguments[0].click()", search_button)

                print(f"Slicked search_button")
            
            except Exception as e:
                
                print(f"Did not click search_button due to error: {e}")
            
        #Check if any cases found
        try:
            
            #Get all cases from current page    
            self.elements = Wait(self.browser, 15).until(EC.presence_of_all_elements_located((By.XPATH, "//li[@class='result ']")))
            
            #Get number of results
            results_count_raw = self.browser.find_element(By.XPATH, '//span[@id="typeFacetText-decision"]')
    
            results_count_list = re.findall(r'(\d+)', results_count_raw.get_attribute('innerHTML').replace(',', ''))
        
            if len(results_count_list) > 0:
            
                results_count = results_count_list[0]
            
                if isinstance(results_count, tuple):
            
                    results_count = results_count[0]
    
                self.results_count = int(float(results_count))

        except Exception as e:

            print(f"No cases found due to error: {e}")

        print(f"self.results_count == {self.results_count}")

        if self.results_count > 0:

            #Get number of results from current page   
            case_num = len(self.elements)
                    
            while case_num < min(self.judgment_counter_bound, self.results_count):

                pause.seconds(np.random.randint(scraper_pause_mean, scraper_pause_mean + 10))                        

                print(f"Number of cases on current page  == {case_num}")

                if '<div id="loadMoreResults" class="d-print-none" style="display:none;">' not in self.browser.page_source:
            
                    try:
        
                        load_more = Wait(self.browser, 15).until(EC.visibility_of_element_located((By.ID, "loadMoreResults")))
                        
                        self.browser.execute_script("arguments[0].click();", load_more);
                                                
                        self.elements = Wait(self.browser, 15).until(EC.presence_of_all_elements_located((By.XPATH, "//li[@class='result ']")))

                        if len(self.elements) > case_num:
                            
                            case_num = len(self.elements)

                        else:
    
                            break

                    except Exception as e:
                        
                        print(f"Can't load more results due to error: {e}")

                        break

                else:
                    
                    break
            
            #Start collecting case_infos
            counter = 0
                        
            for element in self.elements:
                
                if counter < min(self.judgment_counter_bound, self.results_count):

                    #Get html attrs for case
                    case_soup = BeautifulSoup(element.get_attribute('innerHTML'), "lxml")

                    case_soup_attrs_raw = case_soup.find('div', class_ = 'searchResult data_caselaw col px-0')

                    case_soup_attrs = case_soup_attrs_raw.attrs
                    
                    #Initialise default return dict
                    case_info = {'Case name': '', 
                                 'Medium neutral citation': '',
                                  'Hyperlink to CanLII': '',
                                  'Other citations': '',
                                'Court': '',
                                'Decision date': '',
                                 'Keywords': '',
                                 'Subjects': ''
                                }

                    #Get citations
                    citations = case_soup_attrs['data-lbh-citation']

                    citations_list = citations.split(', ')

                    mnc = ''

                    other_citations_list = []

                    other_citations = ''
                    
                    if len(citations_list) > 0:

                        for citation in citations_list:

                            if 'CanLII' in citation:

                                mnc = citation

                            else:

                                other_citations_list.append(citation)
                    
                    else:

                        mnc = citations

                    other_citations = ', '.join(other_citations)

                    case_info['Medium neutral citation'] = mnc
                    case_info['Other citations'] = other_citations

                    #Get other metadata                    
                    
                    #Define correspondence of LawtoData keys and CanLII keys
                    case_info_meta = {'Case name': 'data-lbh-title', 
                                  'Hyperlink to CanLII': 'data-lbh-document-url',
                                'Court': 'data-lbh-collection',
                                'Date': 'data-lbh-decision-date',
                                 'Keywords': 'data-lbh-keywords',
                                 'Subjects': 'data-lbh-subjects'
                                }

                    for key in case_info_meta.keys():

                        canlii_key = case_info_meta[key]

                        if canlii_key in case_soup_attrs.keys():

                            case_info[key] = case_soup_attrs[canlii_key]   
                    
                    self.case_infos.append(case_info)
                    
                    counter += 1

                else:
                    
                    break
        
    #Get judgment text from each case
    def attach_judgment(self, case_info, judgment_html):
        
        judgment_url = case_info['Hyperlink to CanLII']
    
        #Make link clickable
        case_info['Hyperlink to CanLII'] = link(case_info['Hyperlink to CanLII'])
    
        #Add default values for additional metadata
        case_info.update({'File number': '', 
                         'Most recent unfavourable mention': '', 
                         'judgment': ''
                             }
                            )
    
        try:

            #Get judgment text and additional metadata

            soup = BeautifulSoup(judgment_html, "lxml")

            #Judgment text
        
            judgment_text = soup.find('div', class_ ='documentcontent').get_text(strip = True)
        
            case_info.update({'judgment': judgment_text})
            
            #Attach metadata
            
            meta_tags = soup.find_all("meta")
            
            for meta in ca_meta_dict.keys():
                try:
                    meta_content = soup.select(f'meta[name={ca_meta_dict[meta]}]')[0].attrs["content"]
                except:
                    meta_content = ''
                case_info.update({meta: meta_content})
        
            #Date, case number, citations
            
            extra_metas = soup.find_all('div', class_ = "row py-1")
            
            for meta in extra_metas:
                #if 'date:' in meta.text.lower():
                    #case_info.update({'Date': meta.text})
            
                if 'file number:' in meta.text.lower():
                    case_info.update({'File number': meta.text.replace('\n', '').replace('File number:', '').replace('File numbers:', '')})
            
                #if 'citation:' in meta.text.lower():
                    #case_info.update({'Citation': meta.text})
            
                if 'other citation' in meta.text.lower():
                    case_info.update({'Other citations': meta.text.replace('\n', '').replace('Other citation:', '').replace('Other citations:', '')})
        
                if 'Most recent unfavourable mention' in meta.text.lower():
                    case_info.update({'Most recent unfavourable mention': meta.text.replace('\n', '').replace('Most recent unfavourable mention:', '')})
        
        except Exception as e:
            
            print(f"{case_info['Case name']}: judgment not scrapped")
            print(e)

        return case_info
    
    #get judgments
    def get_judgments(self):

        self.case_infos_w_judgments = []

        #Search if not done yet
        if len(self.case_infos) == 0:

            self.search()

        #Get judgment text and metadata for all relevant cases
        
        for case_info in self.case_infos:

            #Pause to avoid getting kicked out
            pause.seconds(np.random.randint(scraper_pause_mean, scraper_pause_mean + 10))

            #Get search results from self.browser

            self.elements = Wait(self.browser, 15).until(EC.presence_of_all_elements_located((By.XPATH, "//li[@class='result ']")))
            
            #Click on relevant case name on self.browser
            element = self.elements[len(self.case_infos_w_judgments)]

            case_name_button = element.find_element(By.CLASS_NAME, "name")
            
            case_name_button.click()

            #Get judgment text and metadata

            judgment_present = Wait(self.browser, 15).until(EC.presence_of_element_located((By.XPATH, "//div[@class='documentcontent']")))

            judgment_html = self.browser.page_source

            judgment_dict = self.attach_judgment(case_info, judgment_html)

            #Add to case_infos_w_judgments 
            self.case_infos_w_judgments.append(judgment_dict)

            #Pause to avoid getting kicked out
            pause.seconds(np.random.randint(scraper_pause_mean, scraper_pause_mean + 10))

            #Go back to search results page
            self.browser.back()

            #Report status
            print(f"Scrapped {len(self.case_infos_w_judgments)}/{self.judgment_counter_bound} judgments.")

        #Quit self.browser when done
        self.quit_browser()
            
    #Quit self.browser when done
    def quit_browser(self):

        self.browser.delete_all_cookies()
        self.browser.quit()



# %%
def ca_search_preview(df_master):
    
    df_master = df_master.fillna('')
        
    #Conduct search
    
    ca_search = ca_search_tool(jurisdiction  = df_master.loc[0, 'Jurisdiction'],
                                   court = df_master.loc[0, 'Courts'], 
                                   phrase = df_master.loc[0, 'Document text'], 
                                   case_name_mnc= df_master.loc[0, 'Case name, citation or docket'],
                                  subjects = df_master.loc[0, 'Subjects'],
                                   court_tribunal_type = df_master.loc[0, 'Court or tribunal type'], 
                                   on_this_date = df_master.loc[0, 'Decision date is'],
                                    after_date = df_master.loc[0, 'Decision date is after'],
                                    before_date = df_master.loc[0, 'Decision date is before'], 
                                judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']),
                                   #cited = '', 
                                   #year = ''
                                  )
    
    ca_search.search()
    
    results_count = ca_search.results_count
    case_infos = ca_search.case_infos

    results_url = ca_search.results_url

    ca_search.quit_browser()
    
    return {'results_url': results_url, 'results_count': results_count, 'case_infos': case_infos}


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json, gpt_batch_input
#Import variables
from functions.gpt_functions import basic_model#, flagship_model#, role_content


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def ca_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    ca_search = ca_search_tool(jurisdiction  = df_master.loc[0, 'Jurisdiction'],
                                   court = df_master.loc[0, 'Courts'], 
                                   phrase = df_master.loc[0, 'Document text'], 
                                   case_name_mnc= df_master.loc[0, 'Case name, citation or docket'],
                                  subjects = df_master.loc[0, 'Subjects'],
                                   court_tribunal_type = df_master.loc[0, 'Court or tribunal type'], 
                                   on_this_date = df_master.loc[0, 'Decision date is'],
                                    after_date = df_master.loc[0, 'Decision date is after'],
                                    before_date = df_master.loc[0, 'Decision date is before'], 
                                  judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                                   #cited = '', 
                                   #year = ''
                                  )

    ca_search.get_judgments()
    
    for judgment_json in ca_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)

    #Instruct GPT
    
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)

    #Drop judgment if wanted to
    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in ca_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def ca_batch(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
        
    ca_search = ca_search_tool(jurisdiction  = df_master.loc[0, 'Jurisdiction'],
                                   court = df_master.loc[0, 'Courts'], 
                                   phrase = df_master.loc[0, 'Document text'], 
                                   case_name_mnc= df_master.loc[0, 'Case name, citation or docket'],
                                  subjects = df_master.loc[0, 'Subjects'],
                                   court_tribunal_type = df_master.loc[0, 'Court or tribunal type'], 
                                   on_this_date = df_master.loc[0, 'Decision date is'],
                                    after_date = df_master.loc[0, 'Decision date is after'],
                                    before_date = df_master.loc[0, 'Decision date is before'], 
                                  judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                                   #cited = '', 
                                   #year = ''
                                  )

    ca_search.get_judgments()
    
    for judgment_json in ca_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)

    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

    df_individual = pd.read_json(json_individual)

    #Instruct GPT
    
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's judgment spreadsheet

    #Need to convert date column to string
    if 'Date' in df_individual.columns:

        df_individual['Date'] = df_individual['Date'].astype(str)
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Send batch input to gpt
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)
    
    return batch_record_df_individual
