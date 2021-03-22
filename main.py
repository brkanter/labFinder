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

def scrapeGmapCoords(df_USA):
    """Use Chrome to search Google Maps"""
    
    from selenium import webdriver
    
    Url_With_Coordinates = []
    
    option = webdriver.ChromeOptions()
    prefs = {'profile.default_content_setting_values': {'images':2, 'javascript':2}}
    option.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome("chromedriver.exe", options=option)
    
    for url in df_USA.Map_URL:
        driver.get(url)
        Url_With_Coordinates.append(driver.find_element_by_css_selector('meta[itemprop=image]').get_attribute('content'))
        
    driver.close()
    
    df_USA['Url_With_Coordinates'] = Url_With_Coordinates
    
    return df_USA, Url_With_Coordinates

def getWebsites(url):
    """Find institution website from Wikipedia page"""
    
    try:
        r = requests.get(url, auth=('user', 'pass'))
        website = r.text
        db = pd.read_html(website,match='Website',encoding="UTF-8")
        db = pd.DataFrame(db[0])
        db.columns = ['Label','Data']
        return 'https://' + db.loc[(db.loc[:,'Label'] == 'Website'),'Data'].iloc[0]
        
    except:
        print('FAIL: ' + url)

# %% get list of schools from Wikipedia and find them on GoogleMaps
url = 'https://en.wikipedia.org/wiki/List_of_research_universities_in_the_United_States'
R1 = pd.read_html(url)[0]
R2 = pd.read_html(url)[1]
R1['R_rating'] = 1;
R2['R_rating'] = 2;
df_USA = pd.concat([R1,R2]).reset_index()

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
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Nevada, Reno'),'Lat'] = 39.533
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Nevada, Reno'),'Long'] = -119.813
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Washington'),'Lat'] = 47.656
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Washington'),'Long'] = -122.311

# get school websites      
df_USA['Website'] = [ getWebsites(url) for url in df_USA['Wiki'] ]

df_USA.loc[(df_USA.loc[:,'Institution'] == 'Air Force Institute of Technology Graduate School of Engineering & Management'),'Website'] = 'http://www.afit.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'Arizona State University SkySong campus'),'Website'] = 'http://www.asu.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'Kent State University at Kent'),'Website'] = 'http://www.kent.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'Ohio University-Main Campus'),'Website'] = 'http://www.ohio.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Akron Main Campus'),'Website'] = 'http://www.uakron.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of New England'),'Website'] = 'https://www.une.edu/'
df_USA.loc[(df_USA.loc[:,'Institution'] == 'University of Colorado Denver/Anschutz-Medical Campus'),'Website'] = 'https://www.cuanschutz.edu/'

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
        if schools.loc[j,'ORGANIZATION NAME'].lower().startswith(df_USA.loc[i,'Institution'].lower()):
            if schools.loc[j,'CITY'].lower().startswith(df_USA.loc[i,'City'].lower()):
                money += schools.loc[j,'FUNDING']
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

# %% nonUSA map
df_nonUSA = pd.read_excel(r"C:\Users\benjamka\GitHub\labFinder\institutes.xlsx", sheet_name=0)
df_nonUSA['Lat'] = 0
df_nonUSA['Long'] = 0
for i, url in enumerate(df_nonUSA['Url_With_Coordinates']):
    try:
        df_nonUSA['Lat'].iloc[i] = url.split('/@')[1].split(',')[0]
        df_nonUSA['Long'].iloc[i] = url.split('/@')[1].split(',')[1].split(',')[0]
    except:
        print(i)
    
pickle.dump(df_nonUSA, open("nonUSA_map.pkl","wb"))

# %% make world map

with open('USA_map.pkl', 'rb') as pickl:
    df_USA = pickle.load(pickl)
with open('nonUSA_map.pkl', 'rb') as pickl:
    df_nonUSA = pickle.load(pickl)
    
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

m = folium.Map(location=[40, -40], zoom_start=2)

# markers for USA
for _, df in df_USA.iterrows():
    if df.R_rating == 1:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                '<a href="' + df.Website + '" target="_blank">' 
                + df.Institution + '</a><br><br>R1: Very high research<br>NIH 2019 = ' 
                + locale.currency(df.Funding, grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([df.Lat, df.Long], radius = 10, fill=True, popup=popup, 
                            color='darkblue', opacity=0.6).add_to(m) 
    elif df.R_rating == 2:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                '<a href="' + df.Website + '" target="_blank">' 
                + df.Institution + '</a><br><br>R1: Very high research<br>NIH 2019 = ' 
                + locale.currency(df.Funding, grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([df.Lat, df.Long], radius = 7, fill=True, popup=popup, 
                            color='#990000', opacity=0.6).add_to(m) 

# markers outside USA
for _, df in df_nonUSA.iterrows():
    html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
            '<a href="' + df.Website + '" target="_blank">' 
            + df.Institution + '</a><br><br>Population = ' + format(df.Population, ",d") + '</p>' )
    el = branca.element.IFrame(html=html, width=250, height=105)
    popup = folium.Popup(el)
    folium.CircleMarker([df.Lat, df.Long], radius = 10, fill=True, popup=popup, 
                        color='#4C0099', opacity=0.7).add_to(m) 
     
df_world = pd.concat([df_USA, df_nonUSA], sort=False)
outputFile = "labFinder.html"
m.save(outputFile)
pickle.dump(df_world, open("world_map.pkl","wb"))
webbrowser.open(outputFile, new=2)