# -*- coding: utf-8 -*-
"""
Created Apr 2020

@author: Benjamin R. Kanter
"""

import numpy as np
import pandas as pd
import csv
import requests

scrapeCoords = True # True to scrap GoogleMap coordinates, False to read them from csv file

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
df = pd.concat([R1,R2])

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

# fix coords that were retrieved incorrectly
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
df = df.drop(columns=['Institution+','Institution_','Map_URL','Wiki'])

#%% make the map
import folium
import webbrowser
import branca
import pickle

m = folium.Map(location=[38, -97], zoom_start=5)

# popup school website links 
for lat, long, name, site, rating in zip(df.Lat, df.Long, df.Institution, df.Website, df.R_rating):
    
    if rating == 1:
        html = '<p style="font-size:105%;font-name:Arial;text-align:left;"> <a href="' + site + '" target="_blank">' + name + '</a><br><br>R1: Very high research</p>'
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.Marker([lat, long], popup=popup, icon=folium.Icon(color='darkblue',icon='circle')).add_to(m)
    elif rating == 2:
        html = '<p style="font-size:105%;font-name:Arial;text-align:left;"> <a href="' + site + '" target="_blank">' + name + '</a><br><br>R2: High research</p>'
        el = branca.element.IFrame(html=html, width=250, height=105)
        popup = folium.Popup(el)
        folium.Marker([lat, long], popup=popup, icon=folium.Icon(color='darkred',icon='circle')).add_to(m) 

# write and open
outputFile = "USA_map.html"
m.save(outputFile)
pickle.dump(df,open("USA_map.pkl","wb"))
webbrowser.open(outputFile, new=2)