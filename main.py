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
    
    driver = webdriver.Chrome("chromedriver.exe", options=option)
    
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
        db = pd.read_html(website,match='Website',encoding="UTF-8")
        db = pd.DataFrame(db[0])
        db.columns = ['Label','Data']
        # print('success: ' + url)
        return 'https://' + db.loc[(db.loc[:,'Label'] == 'Website'),'Data'].iloc[0]
        
    except:
        print('FAIL: ' + url)

#%% get list of schools from Wikipedia and find them on GoogleMaps
url = 'https://en.wikipedia.org/wiki/List_of_research_universities_in_the_United_States'
R1 = pd.read_html(url)[0]
R2 = pd.read_html(url)[1]
R1['R_rating'] = 1;
R2['R_rating'] = 2;
df = pd.concat([R1,R2]).reset_index()

# create URLs
df['Institution+'] = df['Institution']
df['Institution+'] = [ i.replace(" ", "+") for i in df['Institution']]
df['Institution_'] = df['Institution']
df['Institution_'] = [ i.replace(" ", "_") for i in df['Institution']]
df['Map_URL'] = ['https://www.google.com/maps/search/' + i for i in df['Institution+'] ]
df['Wiki'] = ['https://en.wikipedia.org/wiki/' + i for i in df['Institution_'] ]

# get GoogleMap coords
if scrapeCoords:
    
    df, Url_With_Coordinates = scrapeGmapCoords(df)
    
    with open('Url_With_Coordinates.csv','w') as file:
        wr = csv.writer(file)
        wr.writerow(Url_With_Coordinates)
    
else:
    with open('Url_With_Coordinates.csv', 'r') as file:
        reader = csv.reader(file, delimiter=',')
        for i in reader:
            Url_With_Coordinates = i
            break
        df['Url_With_Coordinates'] = Url_With_Coordinates

df['Lat'] = [ url.split('?center=')[1].split('&zoom=')[0].split('%2C')[0] for url in df['Url_With_Coordinates'] ]
df['Long'] = [url.split('?center=')[1].split('&zoom=')[0].split('%2C')[1] for url in df['Url_With_Coordinates'] ]

# fix coords that are retrieved incorrectly
df.loc[(df.loc[:,'Institution'] == 'University of Nevada, Reno'),'Lat'] = 39.533
df.loc[(df.loc[:,'Institution'] == 'University of Nevada, Reno'),'Long'] = -119.813
df.loc[(df.loc[:,'Institution'] == 'University of Washington'),'Lat'] = 47.656
df.loc[(df.loc[:,'Institution'] == 'University of Washington'),'Long'] = -122.311

# get school websites      
df['Website'] = [ getWebsites(url) for url in df['Wiki'] ]

df.loc[(df.loc[:,'Institution'] == 'Air Force Institute of Technology Graduate School of Engineering & Management'),'Website'] = 'http://www.afit.edu/'
df.loc[(df.loc[:,'Institution'] == 'Arizona State University SkySong campus'),'Website'] = 'http://www.asu.edu/'
df.loc[(df.loc[:,'Institution'] == 'Kent State University at Kent'),'Website'] = 'http://www.kent.edu/'
df.loc[(df.loc[:,'Institution'] == 'Ohio University-Main Campus'),'Website'] = 'http://www.ohio.edu/'
df.loc[(df.loc[:,'Institution'] == 'University of Akron Main Campus'),'Website'] = 'http://www.uakron.edu/'
df.loc[(df.loc[:,'Institution'] == 'University of New England'),'Website'] = 'https://www.une.edu/'
df.loc[(df.loc[:,'Institution'] == 'University of Colorado Denver/Anschutz-Medical Campus'),'Website'] = 'https://www.cuanschutz.edu/'

# drop unneeded columns
df = df.drop(columns=['Institution+','Institution_','Map_URL','Wiki','index'])

#%% funding info
dfe = pd.read_excel(r"C:\Users\benjamka\GitHub\labFinder\Worldwide2019.xls", sheet_name=0)
dfepiv = dfe.pivot_table(values=['FUNDING'],index=['ORGANIZATION NAME','CITY','STATE OR COUNTRY NAME'], aggfunc='sum')
flattened = pd.DataFrame(dfepiv.to_records())
schools = flattened[flattened['ORGANIZATION NAME'].str.contains('UNIVERSITY') | flattened['ORGANIZATION NAME'].str.contains('COLLEGE')]
schools = schools.reset_index()
schools = schools.drop(columns=['index'])

# make sure school and city match
for i in range(np.shape(df)[0]):
    money = 0
    for j in range(np.shape(schools)[0]):
        if schools.loc[j,'ORGANIZATION NAME'].lower().startswith(df.loc[i,'Institution'].lower()):
            if schools.loc[j,'CITY'].lower().startswith(df.loc[i,'City'].lower()):
                money += schools.loc[j,'FUNDING']
    if money > 0:
        df.loc[i,'Funding'] = money
    else:
        df.loc[i,'Funding'] = None
        
# scale funding amounts to suit marker size
df['Funding_scaled'] = df['Funding']
df['Funding_scaled'] = ( ((30 * (df['Funding'] - np.min(df['Funding']))
                         / (np.max(df['Funding']) - np.min(df['Funding']))) ) + 3 )

#%% make the map
locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )

m = folium.Map(location=[38, -97], zoom_start=5)

with open('USA_map.pkl', 'rb') as pickl:
    df = pickle.load(pickl)
    
fundPlt = df['Funding_scaled'].copy().fillna(value=3)

# popup school website links and funding info
for lat, long, name, site, rating, dollas, funding in zip(df.Lat, df.Long, df.Institution, df.Website, df.R_rating, df.Funding, fundPlt):
    
    if rating == 1:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                '<a href="' + site + '" target="_blank">' 
                + name + '</a><br><br>R1: Very high research<br>NIH 2019 = ' + locale.currency(dollas,grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([lat, long], radius = funding, fill=True,popup=popup, color='darkblue').add_to(m) 
    elif rating == 2:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                '<a href="' + site + '" target="_blank">'
                + name + '</a><br><br>R2: High research<br>NIH 2019 = ' + locale.currency(dollas,grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([lat, long], radius = funding, fill=True,popup=popup, color='darkred').add_to(m) 

# write and open
outputFile = "USA_map.html"
# m.save(outputFile)
# pickle.dump(df,open("USA_map.pkl","wb"))
webbrowser.open(outputFile, new=2)

# %% europe

df_euro = pd.read_excel(r"C:\Users\benjamka\GitHub\labFinder\european_institutes.xlsx", sheet_name=0)
df_euro['Lat'] = 0
df_euro['Long'] = 0
for i, url in enumerate(df_euro['Url_With_Coordinates']):
    try:
        df_euro['Lat'].iloc[i] = url.split('/@')[1].split(',')[0]
        df_euro['Long'].iloc[i] = url.split('/@')[1].split(',')[1].split(',')[0]
    except:
        print(i)
        
locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )

m = folium.Map(location=[56, 10], zoom_start=4)

# with open('Euro_map.pkl', 'rb') as pickl:
#     df = pickle.load(pickl)
    
# popup school website links 
for lat, long, name, site, pop in zip(df_euro.Lat, df_euro.Long, df_euro.Institution, df_euro.Website, df_euro.Population):
    
    pop_str = "%.0f" % pop
    html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
            '<a href="' + site + '" target="_blank">' 
            + name + '</a><br><br>Population = ' + pop_str + '</p>' )
    el = branca.element.IFrame(html=html, width=250, height=105)
    popup = folium.Popup(el)
    folium.CircleMarker([lat, long], radius = 10, fill=True,popup=popup, color='darkblue').add_to(m) 
    
outputFile = "Euro_map.html"
m.save(outputFile)
pickle.dump(df, open("Euro_map.pkl","wb"))
webbrowser.open(outputFile, new=2)

# %% world

# df_world = pd.concat([df, df_euro])

locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )

m = folium.Map(location=[35, -40], zoom_start=3)

# with open('World_map.pkl', 'rb') as pickl:
#     df = pickle.load(pickl)
    
# popup school website links and funding info
for lat, long, name, site, rating, dollas, funding in zip(df.Lat, df.Long, df.Institution, df.Website, df.R_rating, df.Funding, fundPlt):
    
    if rating == 1:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                '<a href="' + site + '" target="_blank">' 
                + name + '</a><br><br>R1: Very high research<br>NIH 2019 = ' + locale.currency(dollas,grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([lat, long], radius = funding, fill=True,popup=popup, color='darkblue').add_to(m) 
    elif rating == 2:
        html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
                '<a href="' + site + '" target="_blank">'
                + name + '</a><br><br>R2: High research<br>NIH 2019 = ' + locale.currency(dollas,grouping=True)[:-3] + '</p>' )
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.CircleMarker([lat, long], radius = funding, fill=True,popup=popup, color='darkred').add_to(m) 

# popup school website links 
for lat, long, name, site, pop in zip(df_euro.Lat, df_euro.Long, df_euro.Institution, df_euro.Website, df_euro.Population):
    
    pop_str = "%.0f" % pop
    html = ( '<p style="font-size:105%;font-name:Arial;text-align:left;"> '
            '<a href="' + site + '" target="_blank">' 
            + name + '</a><br><br>Population = ' + pop_str + '</p>' )
    el = branca.element.IFrame(html=html, width=250, height=105)
    popup = folium.Popup(el)
    folium.CircleMarker([lat, long], radius = 10, fill=True,popup=popup, color='purple').add_to(m) 
    
outputFile = "World_map.html"
m.save(outputFile)
pickle.dump(df, open("World_map.pkl","wb"))
webbrowser.open(outputFile, new=2)