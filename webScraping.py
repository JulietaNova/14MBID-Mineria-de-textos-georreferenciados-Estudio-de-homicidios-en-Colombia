"""
@author:  Ingrid Rodriguez
"""
#librerias
from datetime import datetime
from lxml import html
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

import os
import pandas as pd
import requests
import time

origen = "ElTiempo"

# Invocar el servicio webArchive para obtener los resultados del historico
url = 'https://web.archive.org/cdx/search/cdx'
parametros = {'url': 'www.eltiempo.com', 'from': '20170401', 'to': '20170420' }
headers = {'Accept': '*/*'}

rtaWebArchive = ''
try:
    respuesta = requests.get(url, params=parametros, timeout=100)

    if respuesta.status_code == 200:
        rtaWebArchive = respuesta.text
    else:
        raise Exception(f"Error: Código de estado {respuesta.status_code}")

except requests.exceptions.RequestException as e:
    raise Exception(f"Error en la solicitud: {e}")


lstSnapWebArchive = rtaWebArchive.strip().split('\n')

# sdfgh
snapShotsWebArchive = {}
for snap in lstSnapWebArchive:
    snapFecha = snap.split(' ')[1]
    fecha = datetime.strptime(snapFecha, "%Y%m%d%H%M%S")
    snapShotsWebArchive[fecha.date()] = snapFecha

urlsArticulos = {}
urlsArticulosV1 = {}
errores = 0
snapError = []
start_time = datetime.now()
# Extracción y almacenamiento de datos de cada página
for fecha, item in snapShotsWebArchive.items():
    
    print(f"Fecha: {fecha}, Último item: {item}")
    
    rtaHtmlSeccionJusticia = ''
    
    linkArticulo = 'https://web.archive.org/web/' + item + '/https://www.eltiempo.com/justicia'
    try:
        respuesta = requests.get(linkArticulo, timeout=100)

        if respuesta.status_code == 200:
            rtaHtmlSeccionJusticia = html.fromstring(respuesta.text)
        else:
            errores += 1
            snapError.append(f"item: {item}")
            print(f"item Error: {item}")
            continue

    except requests.exceptions.RequestException as e:
        errores += 1
        snapError.append(f"item: {item}")
        print(f"item Error: {item}")
        time.sleep(30)
        continue
    
    # Obtener todos los link de la sección
    enlacesEncontrados = rtaHtmlSeccionJusticia.xpath('//a')
    
    # Filtrar URLs en los links que contengan la raíz de palabra ó palabras clave
    palabras_clave = ["asesin", "masacre", "homicidio"]#, "feminicidio"]

    linksInteres = [
        element.get('href') 
        for element in enlacesEncontrados 
        if any(palabra in element.text_content().lower() for palabra in palabras_clave)
    ]

    # Referencias de las páginas 
    for link in linksInteres:
        urlsArticulos[link[link.find('http'):]] = item
        
    ####################################
    linksAsesin_ = [element.get('href') for element in enlacesEncontrados if "asesin" in element.text_content()]
    linksMasacre = [element.get('href') for element in enlacesEncontrados if "masacre" in element.text_content()]
    linksHomis = [element.get('href') for element in enlacesEncontrados if "homicidio" in element.text_content()]

    # Referencias de las páginas 
    for link in linksAsesin_:
        urlsArticulosV1[link[link.find('http'):]] = item
    
    for link in linksMasacre:
        urlsArticulosV1[link[link.find('http'):]] = item
            
    for link in linksHomis:
        urlsArticulosV1[link[link.find('http'):]] = item
    ####################################

archivoControl = []
for articulo, snap in urlsArticulos.items():
    archivoControl.append(f"Fecha: {snap}, Artículo: {articulo}")
    
df = pd.DataFrame({'':archivoControl})
df.to_csv('log_ejecuciones/archivoControl2017.csv', index=False)

archivoControlV1 = []
for articulo, snap in urlsArticulosV1.items():
    archivoControlV1.append(f"Fecha: {snap}, Artículo: {articulo}")

df = pd.DataFrame({'':archivoControlV1})
df.to_csv('log_ejecuciones/archivoControl2017V1.csv', index=False)

df2 = pd.DataFrame({'':snapError})
df2.to_csv('log_ejecuciones/errores2017.csv', index=False)

end_time = datetime.now()
print('Duration Extraccion Urls: {}'.format(end_time - start_time))

# Inicializa webDriver Chrome 
options = webdriver.ChromeOptions()
options.add_argument('--disable-extensions')
options.add_argument('--blink-settings=imagesEnabled=false')

s = Service(os.path.dirname(os.path.abspath(__file__)) + '/chromedriver.exe')
driver = webdriver.Chrome(options= options, service = s)
count = 0

for articulo, snap in urlsArticulos.items():
    linkArticulo = 'https://web.archive.org/web/' + snap +'/'+ articulo
    try:
        # Link de la página
        driver.get(linkArticulo)
        time.sleep(10)
    except TimeoutException:
        pass
    
    # definicion variables de trabajo
    titulo = "NONE"
    subtitulo = "NONE"
    contenido = "NONE"
    articulo = []

    try:
        titulo = (driver.find_element(By.TAG_NAME, "h1")).text
    except NoSuchElementException:
        subtitulo = (driver.find_element(By.TAG_NAME, "h2")).text
    
    contenido = (driver.find_elements(By.CLASS_NAME, "contenido"))
    
    if not contenido:
        contenido = (driver.find_elements(By.CLASS_NAME, "paragraph"))

    # construcción listado con los elementos encontrados
    articulo.append(titulo)
    articulo.append(subtitulo)
    for itemContenido in contenido:
        textoContenido = itemContenido.text.strip()
        if not textoContenido.startswith('(') and not textoContenido.endswith(')'):
            articulo.append(itemContenido.text)
    
    # exportar datos a .csv
    df = pd.DataFrame({'texto':articulo})
    df.to_csv('articulos_x_procesar/%s_%s_%i.csv' % (origen, snap, count), index=False)
    count += 1
    
driver.quit()
