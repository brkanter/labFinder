# -*- coding: utf-8 -*-
"""
Created Apr 2020

@author: Benjamin R. Kanter
"""

# %% init
import numpy as np
import pandas as pd
import csv
import requests
import folium
import webbrowser
import branca
import pickle
import locale

scrapeCoords = False # True to scrap GoogleMap coordinates, False to read them from csv file

def scrapeGmapCoords(df):
    """Use Chrome to search Google Maps"""
    
    from selenium import webdriver
    
    Url_With_Coordinates = []
    
    option = webdriver.ChromeOptions()
    prefs = {'profile.default_content_setting_values': {'images':2, 'javascript':2}}
    option.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome(r"C:\Users\benjamka\Downloads\chromedriver_win32\chromedriver.exe", options=option)
    
    for url in df.Map_URL:
        driver.get(url)
        Url_With_Coordinates.append(driver.find_element_by_css_selector('meta[itemprop=image]').get_attribute('content'))
        
    driver.close()
    
    df['Url_With_Coordinates'] = Url_With_Coordinates
    
    return df, Url_With_Coordinates

def getWebsites(url):
    """Find institution website from Wikipedia page"""
    
    try:
        r = requests.get(url, auth=('user', 'pass'))
        website = r.text
        db = pd.read_html(website, match='Website', encoding="UTF-8")
        db = pd.DataFrame(db[0])
        db.columns = ['Label','Data']
        return 'https://' + db.loc[(db.loc[:,'Label'] == 'Website'),'Data'].iloc[0]
        
    except:
        print('FAIL: ' + url)
        
def getPopulation(df):
    """Use Chrome to search city population on Google and return result from the answer box"""
    
    from selenium import webdriver
    import re
       
    option = webdriver.ChromeOptions()
    option.add_argument("--headless");
    prefs = {'profile.default_content_setting_values': {'images':2, 'javascript':2}, 'intl.accept_languages': 'en,en_US'}
    option.add_experimental_option('prefs', prefs)  
    driver = webdriver.Chrome(r"C:\Users\benjamka\Downloads\chromedriver_win32\chromedriver.exe", options=option)
 
    # import pdb; pdb.set_trace()
    population = []
    for city in df.City:
        url = 'https://www.google.com/search?q=' + city + '+population&safe=active'
        driver.get(url)
        # answer = driver.execute_script("return document.elementFromPoint(350, 230);").text
        answer = driver.execute_script("return document.elementFromPoint(0, 0);").text
        # answer = answer.split(city)[1].split('\n')[1]
        try:
            answer = answer.split('\n')[9]
            if answer.find('millioner') != -1:
                answer = re.sub(",", "", str.split(answer)[0].split()[0]) + '000'
            elif answer.find('(') != -1:
                answer = answer.split('(')[0][:-1]
            pop = int(re.sub("\s+", "", answer))
        except Exception as e:
            print(city)
            print(str(e))
            pop = 0
        population.append(pop)
        
    driver.close()
    
    df['Population'] = population
    
    return df

# %% scrap ALBA network
from bs4 import BeautifulSoup
n_pg = 37
institute_ls = list()
country_ls = list()
for p in range(n_pg):
    url = r"http://www.alba.network/network?search_api_fulltext=&page=" + str(p)
    print(url)
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    conts = soup.find_all(class_='container')
    for c in range(len(conts)):
        try:
            institute_ls.append(conts[c].prettify().split(' at ')[1].split('\n')[0])
            if institute_ls[-1].find('&amp;#039;') == -1:
                institute_ls[-1] = institute_ls[-1].replace('&amp;#039;', "'")
        except:
            print('')
    countries = soup.find_all(class_='country')
    for c in range(len(countries)):
        try:
            country_ls.append(countries[c].prettify().split('\n')[1][1:])
        except:
            print('')  
          
print(len(institute_ls))

# %% alba network

df_alba = pd.DataFrame([country_ls, institute_ls]).transpose()
df_alba.columns = ['Country', 'Institution']
df_alba['Institution+'] = df_alba['Institution']
df_alba['Institution+'] = [ i.replace(" ", "+") for i in df_alba['Institution']]
df_alba['Map_URL'] = ['https://www.google.com/maps/search/' + i + '+' + j for i, j in zip(df_alba['Institution+'], df_alba['Country']) ]
df_alba, Url_With_Coordinates = scrapeGmapCoords(df_alba)
    
df_alba['Lat'] = np.empty((len(df_alba), 1))
df_alba['Long'] = np.empty((len(df_alba), 1))
for i in range(len(Url_With_Coordinates)):
    try:
        url = Url_With_Coordinates[i]
        df_alba['Lat'].iloc[i] = url.split('?center=')[1].split('&zoom=')[0].split('%2C')[0]
        df_alba['Long'].iloc[i] = url.split('?center=')[1].split('&zoom=')[0].split('%2C')[1]
    except:
        print(i)

# correct GPS errors
df_alba['Map_URL'].iloc[3] = 'https://www.google.com/maps/place/University+of+Science,+Malaysia/@5.3443068,100.2911741,14.5z/data=!4m8!1m2!2m1!1suniversiti+sains+malaysia!3m4!1s0x304ac1a836ae7e53:0x835ac54fe8f4d95a!8m2!3d5.3559337!4d100.3025177?hl=en'
df_alba['Lat'].iloc[3] = 5.3443068
df_alba['Long'].iloc[3] = 100.2911741

df_alba['Map_URL'].iloc[417] = 'https://www.google.com/maps/place/Instytut+Biologii+Do%C5%9Bwiadczalnej+im.+M.+Nenckiego+PAN/@52.2134611,20.9814754,17.75z/data=!4m5!3m4!1s0x471eccbba32cb2fd:0xc39abac296669a11!8m2!3d52.2135238!4d20.982649?hl=en'
df_alba['Lat'].iloc[417] = 52.2134611
df_alba['Long'].iloc[417] = 20.9814754
df_alba = df_alba.drop(index=[129, 497])

# drop exact match institutions
df_alba = df_alba.drop_duplicates(subset=['Country', 'Institution', 'Map_URL'])

pickle.dump(df_alba, open("ALBA_map.pkl","wb"))

# %% get list of schools from Wikipedia and find them on GoogleMaps
url = 'https://en.wikipedia.org/wiki/List_of_research_universities_in_the_United_States'
R1 = pd.read_html(url)[0]
R2 = pd.read_html(url)[1]
R1['R_rating'] = 1;
R2['R_rating'] = 2;
df_USA = pd.concat([R1, R2]).reset_index()

# create URLs
df_USA['Institution+'] = df_USA['Institution']
df_USA['Institution+'] = [ i.replace(" ", "+") for i in df_USA['Institution']]
df_USA['Institution_'] = df_USA['Institution']
df_USA['Institution_'] = [ i.replace(" ", "_") for i in df_USA['Institution']]
df_USA['Map_URL'] = ['https://www.google.com/maps/search/' + i for i in df_USA['Institution+'] ]
df_USA['Wiki'] = ['https://en.wikipedia.org/wiki/' + i for i in df_USA['Institution_'] ]

# get GoogleMap coords
if scrapeCoords:
    
    df_USA, Url_With_Coordinates = scrapeGmapCoords(df_USA)
    
    with open('Url_With_Coordinates.csv','w') as file:
        wr = csv.writer(file)
        wr.writerow(Url_With_Coordinates)
    
else:
    with open('Url_With_Coordinates.csv', 'r') as file:
        reader = csv.reader(file, delimiter=',')
        for i in reader:
            Url_With_Coordinates = i
            break
        df_USA['Url_With_Coordinates'] = Url_With_Coordinates

df_USA['Lat'] = [ url.split('?center=')[1].split('&zoom=')[0].split('%2C')[0] for url in df_USA['Url_With_Coordinates'] ]
df_USA['Long'] = [url.split('?center=')[1].split('&zoom=')[0].split('%2C')[1] for url in df_USA['Url_With_Coordinates'] ]

# fix coords that are retrieved incorrectly
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Nevada, Reno'), 'Lat'] = 39.533
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Nevada, Reno'), 'Long'] = -119.813
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Washington'), 'Lat'] = 47.656
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Washington'), 'Long'] = -122.311

# get school websites      
df_USA['Website'] = [ getWebsites(url) for url in df_USA['Wiki'] ]

df_USA.loc[(df_USA.loc[:,'Institution'] == 'Air Force Institute of Technology Graduate School of Engineering & Management'), 'Website'] = 'http://www.afit.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'Arizona State University SkySong campus'), 'Website'] = 'http://www.asu.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'Kent State University at Kent'), 'Website'] = 'http://www.kent.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'Ohio University-Main Campus'), 'Website'] = 'http://www.ohio.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Akron Main Campus'), 'Website'] = 'http://www.uakron.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of New England'), 'Website'] = 'https://www.une.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Colorado Denver/Anschutz-Medical Campus'), 'Website'] = 'https://www.cuanschutz.edu/'

# drop unneeded columns
df_USA = df_USA.drop(columns=['Institution+','Institution_','Map_URL','Wiki','index'])

# %% funding info
dfe = pd.read_excel(r"C:\Users\benjamka\GitHub\labFinder\Worldwide2019.xls", sheet_name=0)
dfepiv = dfe.pivot_table(values=['FUNDING'],index=['ORGANIZATION NAME','CITY','STATE OR COUNTRY NAME'], aggfunc='sum')
flattened = pd.DataFrame(dfepiv.to_records())
schools = flattened[flattened['ORGANIZATION NAME'].str.contains('UNIVERSITY') | flattened['ORGANIZATION NAME'].str.contains('COLLEGE')]
schools = schools.reset_index()
schools = schools.drop(columns=['index'])

# make sure school and city match
for i in range(np.shape(df_USA)[0]):
    money = 0
    for j in range(np.shape(schools)[0]):
        if schools.loc[j, 'ORGANIZATION NAME'].lower().startswith(df_USA.loc[i, 'Institution'].lower()):
            if schools.loc[j, 'CITY'].lower().startswith(df_USA.loc[i, 'City'].lower()):
                money += schools.loc[j, 'FUNDING']
    if money > 0:
        df_USA.loc[i,'Funding'] = money
    else:
        df_USA.loc[i,'Funding'] = None
        
# scale funding amounts to suit marker size
df_USA['Funding_scaled'] = df_USA['Funding']
df_USA['Funding_scaled'] = ( ((30 * (df_USA['Funding'] - np.min(df_USA['Funding']))
                         / (np.max(df_USA['Funding']) - np.min(df_USA['Funding']))) ) + 3 )

# %% write data
pickle.dump(df_USA, open("USA_map.pkl","wb"))

# %% manual map
df_manual = pd.read_excel(r"C:\Users\benjamka\GitHub\labFinder\institutes.xlsx", sheet_name=0)
df_manual['Lat'] = 0
df_manual['Long'] = 0
for i, url in enumerate(df_manual['Url_With_Coordinates']):
    try:
        df_manual['Lat'].iloc[i] = url.split('/@')[1].split(',')[0]
        df_manual['Long'].iloc[i] = url.split('/@')[1].split(',')[1].split(',')[0]
    except:
        print(i)
    
pickle.dump(df_manual, open("manual_map.pkl","wb"))

# %% make world map

with open('USA_map.pkl', 'rb') as pickl:
    df_USA = pickle.load(pickl)
with open('manual_map.pkl', 'rb') as pickl:
    df_manual = pickle.load(pickl)
with open('ALBA_map.pkl', 'rb') as pickl:
    df_alba = pickle.load(pickl)
    
df_manual['R_rating'] = 0
df_alba['R_rating'] = -1
df_world = pd.concat([df_USA, df_manual, df_alba], sort=False)
df_world = df_world.drop_duplicates(subset=['Institution']).reset_index()
df_world = df_world.drop(index=[461, 786]).reset_index()

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

m = folium.Map(location=[40, -40], zoom_start=2)

# markers
for _, df in df_world.iterrows():
    # alba network
    if df.R_rating == -1:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                  + df.Institution + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([df.Lat, df.Long], radius = 10, fill=True, popup=popup, 
                            color='darkorange', opacity=0.7, zIndexOffset=0).add_to(m) 
    # manual list
    elif df.R_rating == 0:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                 '<a href="' + df.Website + '" target="_blank">' 
                 + df.Institution + '</a><br><br>Population = ' + format(int(df.Population), ",d") + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([df.Lat, df.Long], radius = 10, fill=True, popup=popup, 
                            color='#4C0099', opacity=0.7, zIndexOffset=1).add_to(m)   
    # wiki R2
    elif df.R_rating == 2:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                 '<a href="' + df.Website + '" target="_blank">' 
                 + df.Institution + '</a><br><br>R1: Very high research<br>NIH 2019 = ' 
                 + locale.currency(df.Funding, grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([df.Lat, df.Long], radius = 7, fill=True, popup=popup, 
                            color='#990000', opacity=0.6, zIndexOffset=2).add_to(m) 
    # wiki R1
    elif df.R_rating == 1:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                 '<a href="' + df.Website + '" target="_blank">' 
                 + df.Institution + '</a><br><br>R1: Very high research<br>NIH 2019 = ' 
                 + locale.currency(df.Funding, grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([df.Lat, df.Long], radius = 10, fill=True, popup=popup, 
                            color='darkblue', opacity=0.6, zIndexOffset=3).add_to(m) 
     
outputFile = "labFinder.html"
m.save(outputFile)
pickle.dump(df_world, open("world_map.pkl","wb"))
webbrowser.open(outputFile, new=2)