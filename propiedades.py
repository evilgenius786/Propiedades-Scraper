# -*- coding: latin-1 -*-

import csv
import json
import os.path
import re
import time
import traceback
from datetime import datetime
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

t = 1
timeout = 10

debug = True
encoding = 'latin-1'
headless = False
images = False
max = False
test = False
incognito = False
price_min = 500000
price_max = 5000000
p_url = f'https://propiedades.com/nuevo-leon/residencial-venta#precio-min={price_min}&precio-max={price_max}'
headers = ["ID", 'lat', 'long', "operacion", "precio", "recamaras", "banos", "cant_estacionamiento", "m2_construccion",
           "m2_terreno", "antiguedad", "pisos_numero_piso", "amueblado", "direccion", "coordenadas", "nombre",
           "descripcion", "terraza", "tamaño_jardin", "jardines", "alberca", "gimnasio", "hvac", "calefacción",
           "seguridad_24_hora", "fraccionamiento", "mascotas", "elevador", "lavanderia", "cuarto_de_servicio", "foto1",
           "foto2", "foto3", "foto4", "foto5", "foto6", "foto7", "foto8", "foto9", "foto10", "foto11", "foto12",
           "foto13", "foto14", "foto15", "foto16", "foto17", "foto18", "foto19", "foto20", "publicacion_url"]

s = requests.Session()
s.headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/101.0.4951.67 Safari/537.36'
}


# url = 'https://propiedades.com/nuevo-leon/residencial-venta?pagina=64?pagina=63#precio-min=500000&precio-max=5000000'
# input()

def processData(data, soup):
    # print(f"Processing data for {data['nombre']}")
    row = {}
    for key in ['ID', 'lat', 'long', 'publicacion_url', 'operacion', 'precio', 'direccion', 'nombre', 'descripcion']:
        row[key] = data[key]
    hdrs = {
        "recamaras": "Recámaras",
        "banos": "Baños ",
        "cant_estacionamiento": "Estacionamiento",
        'm2_construccion': 'Tamaño de construcción',
        'm2_terreno': 'Tamaño del terreno ',
        "antiguedad": "Edad del inmueble",
        'pisos_numero_piso': 'No. de pisos',
        'tamaño_jardin': 'Jardín',
    }
    for hdr in hdrs.keys():
        try:
            span = soup.find('span', string=hdrs[hdr]).parent.find_all('span')[1].text.replace('m2', '').strip()
            try:
                row[hdr] = int(span)
            except:
                row[hdr] = span
        except:
            row[hdr] = 0
    for i in range(min(len(data['foto']), 20)):
        row[f"foto{i + 1}"] = data['foto'][i]
    trans = {
        "Aire acondicionado": 'hvac',
        "Seguridad privada": 'seguridad_24_hora',
        "Zona privada": "fraccionamiento",
        'Cuarto de servicio': 'cuarto_de_servicio',
        "Lavandería": 'lavanderia'
    }
    for word in ['amueblado', 'coordenadas', 'terraza', 'jardines', 'alberca', 'gimnasio', 'Aire acondicionado',
                 'Seguridad privada', "Zona privada", 'mascotas', 'elevador', 'lavanderia', 'cuarto_de_servicio']:
        if word.lower() in soup.text.lower():
            row[trans.get(word, word)] = word.title()
    print(json.dumps(row, indent=4))
    try:
        with open('Propiedades.csv', 'a', encoding=encoding, newline='') as pfile:
            csv.DictWriter(pfile, fieldnames=headers).writerow(row)
    except:
        with open('Propiedades.csv', 'a', encoding='utf8', newline='') as pfile:
            csv.DictWriter(pfile, fieldnames=headers).writerow(row)


def getData(driver, row):
    url: str = row['url']
    print(f"Working on {url} {row}")
    filename = unquote(urlparse(url).path.split("/")[-1])
    if os.path.isfile('index.html') and test:
        with open('index.html') as ifile:
            soup = BeautifulSoup(ifile.read(), 'lxml')
    else:
        res = getHtml(driver, url)
        soup = BeautifulSoup(res, 'lxml')
        if test:
            with open('index.html', 'w') as ifile:
                ifile.write(soup.prettify())
    try:
        addr = soup.find('h1', {"itemprop": "streetAddress"}).text.strip().replace('\t', ' ')
    except:
        addr = ""
    desc = "subsection-content"
    try:
        data = {
            "ID": soup.find('strong', {'style': "color:#666"}).text.split(': ')[1].strip(),
            'lat': row['lat'],
            'long': row['long'],
            "publicacion_url": url,
            "operacion": getText(soup, 'p', "label-type-property"),
            "precio": getText(soup, 'span', "price"),
            "descripcion": soup.find('div', {"class": desc}).find_all('p', {'class': None})[-1].text.strip(),
            "services": [li.text.strip() for li in soup.find_all('ul', {'class': 'carac-large'})[1].find_all('li')]
            if len(soup.find_all('ul', {'class': 'carac-large'})) > 1 else "",
            "characteristics": [f"{li.find('span').text.strip()}: {li.find_all('span')[1].text.strip()}" for li in
                                soup.find_all('ul', {'class': 'carac-large'})[0].find_all('li')],
            "direccion": " ".join([line for line in addr.splitlines() if line.strip()]),
            "nombre": getText(soup, 'h2', 'title-preview'),
            "foto": [img['content'] for img in soup.find_all("meta", {"itemprop": "contentUrl"})]
        }
        print(json.dumps(data, indent=4))
        file = f"./json_files/{filename}.json"
        if not os.path.isfile(file):
            with open(file, 'w') as ofile:
                json.dump(data, ofile, indent=4)
        processData(data, soup)
        if test:
            input("Done...")
    except:
        traceback.print_exc()
        with open('Error.txt', 'a') as efile:
            efile.write(f"{url}\n")


def getListings():
    scraped_pages = []
    if os.path.isfile('scraped_pages.txt'):
        with open('scraped_pages.txt') as sfile:
            scraped_pages = [int(x) for x in sfile.read().splitlines()]
    else:
        with open('scraped_pages.txt', 'w') as sfile:
            sfile.write('')
    driver = getChromeDriver()
    # if "propiedades" not in driver.current_url:
    driver.get(p_url)
    time.sleep(2)
    click(driver, '//div[@class="lista tab_interfaz"]')
    try:
        driver.find_element(By.XPATH, '//div[@class="lista tab_interfaz active"]')
    except:
        click(driver, '//div[@class="lista tab_interfaz"]')
        getElement(driver, '//div[@class="list-new"]/div')
    time.sleep(5)
    soup = getSoup(driver)
    page_count = int(soup.find('div', {"id": "pagination_content"}).find_all('li')[-2].text)
    print(f"Total pages: {page_count}")
    lat_long_headers = ['lat', 'long', 'url']
    scraped = []
    if not os.path.isfile('data.csv'):
        with open('data.csv', encoding=encoding, newline='', mode='w') as dfile:
            csv.DictWriter(dfile, fieldnames=lat_long_headers).writeheader()
    else:
        with open('data.csv', encoding=encoding, newline='', mode='r') as dfile:
            datafile = csv.DictReader(dfile, fieldnames=lat_long_headers)
            next(datafile)
            for div in datafile:
                scraped.append(div['url'])
    print(f"Already scraped entries: {len(scraped)}")
    print(f"Total entries: {soup.find('div', {'class': 'title-result resultados_title'}).text.split()[0]}")
    # try:
    #     with open("page.txt") as pfile:
    #         start = int(pfile.read())
    #         print(f"Resuming from page {start}")
    #         waitCaptcha(driver, start)
    # except:
    #     start = 2
    start = 2
    pages = [x for x in range(start, page_count) if x not in scraped_pages]
    publicacion_urls = []
    if os.path.isfile('Propiedades.csv'):
        with open('Propiedades.csv', encoding=encoding) as pfile:
            reader = csv.DictReader(pfile, fieldnames=headers)
            next(reader)
            for line in reader:
                publicacion_urls.append(line['publicacion_url'])
    while len(pages) > 0:
        print(f"Scraped pages {scraped_pages}")
        i = pages[0]
        if i in scraped_pages:
            print(f"Already scraped page {i}")
            continue
        divs = []
        # print(driver.current_url)
        for div in soup.find('div', {"class": "list-new"}).find_all('div')[1:]:
            try:
                if div['data-href'] not in scraped:
                    data = {
                        "lat": div.find('meta', {"itemprop": "latitude"})['content'],
                        "long": div.find('meta', {"itemprop": "longitude"})['content'],
                        "url": div['data-href']
                    }
                    # print(json.dumps(data, indent=4))
                    divs.append(data)
                    scraped.append(div['data-href'])
                # elif div['data-href'] in publicacion_urls:
                #     return
                else:
                    # pass
                    print(f"{div['data-href']} already exist!")
            except:
                pass
                # print(div)
                # traceback.print_exc()
                # input()
        print(f"Found {len(divs)} divs...")
        with open('data.csv', encoding=encoding, newline='', mode='a') as dfile:
            csv.DictWriter(dfile, fieldnames=lat_long_headers).writerows(divs)
        with open('scraped_pages.txt', 'w') as sfile:
            pageno = int(re.findall(r"\d+", driver.current_url)[0])
            if pageno not in scraped_pages and pageno < page_count:
                scraped_pages.append(pageno)
                pages.remove(pageno)
            scraped_pages = sorted(set(scraped_pages))
            sfile.write("\n".join([f"{sp}" for sp in scraped_pages]))
        # divs.clear()
        # with open('page.txt', 'w') as pfile:
        #     pfile.write(f"{i}")
        waitCaptcha(driver, i)
        soup = getSoup(driver)


def getHtml(driver, url):
    res = s.get(url)
    if '<title>ShieldSquare Captcha' not in res.text:
        print('Request without browser!')
        return res.text
    # print("Title:", BeautifulSoup(res.text, 'lxml').find('title').text)
    driver.get(url)
    time.sleep(1)
    while '<title>ShieldSquare Captcha' in driver.page_source:
        print('Waiting for captcha...')
        time.sleep(2)
    for cookie in driver.get_cookies():
        s.cookies.set(cookie['name'], cookie['value'])
    return driver.page_source


def scrape():
    driver = getChromeDriver()
    scraped_urls = []
    if not os.path.isfile("Propiedades.csv"):
        with open('Propiedades.csv', encoding=encoding, mode='w', newline='') as pfile:
            csv.DictWriter(pfile, fieldnames=headers).writeheader()
    else:
        with open('Propiedades.csv', encoding=encoding, mode='r') as pfile:
            for row in csv.DictReader(pfile, fieldnames=headers):
                scraped_urls.append(row['publicacion_url'])
    with open('data.csv', encoding=encoding) as dfile:
        rows = csv.DictReader(dfile)
        next(rows)
        for row in rows:
            if row['url'] not in scraped_urls:
                getData(driver, row)
            else:
                print(f"Already scraped {row['url']}")


def main():
    logo()
    time.sleep(1)
    if not os.path.isdir("json_files"):
        os.mkdir('json_files')
    while True:
        choice = input("1. Scrape fresh listings\n"
                       "2. Scrape listings detail\n"
                       "3. Exit\n")
        if choice == '1':
            print("Fetching listings...")
            getListings()
        elif choice == '2':
            print('Scraping...')
            if os.path.isfile('index.html'):
                row = {"lat": "123.456",
                       "long": "321.654",
                       "url": "https://propiedades.com/inmuebles/casa-en-venta-san-jose-san-juan-nuevo_leon-25033979"
                              "#tipos=residencial-venta&area=nuevo-leon&precio-min=500000&precio-max=5000000&pos=3"
                       }
                getData(getChromeDriver(), row)
            else:
                scrape()

        else:
            break


def getText(soup, tag, class_):
    try:
        return soup.find(tag, {'class': class_}).text.strip()
    except:
        return ""


def waitCaptcha(driver: WebDriver, pagenumber: int):
    while True:
        try:
            try:
                driver.find_element(By.XPATH, '//div[@class="lista tab_interfaz active"]')
            except:
                click(driver, '//div[@class="lista tab_interfaz"]')
            getElement(driver, '//div[@class="list-new"]/div')
            for i in range(5):
                try:
                    driver.execute_script("arguments[0].setAttribute(arguments[1], arguments[2]);",
                                          getElement(driver, "//a[@data-value]"), "data-value", f"{pagenumber}")
                    time.sleep(1)
                    click(driver, f'//a[@data-value="{pagenumber}"]')
                    break
                except:
                    pass
            time.sleep(1)
            getElement(driver, '//div[@class="list-new"]/div')
            print(f"Page {pagenumber - 1} {driver.current_url}")
            break
        except:
            traceback.print_exc()
            driver.get(p_url)


def getSoup(driver: WebDriver):
    return BeautifulSoup(driver.page_source, 'lxml')


def pprint(msg):
    try:
        print(f"{datetime.now()}".split(".")[0], msg)
    except:
        traceback.print_exc()


def click(driver, xpath, js=False):
    if js:
        driver.execute_script("arguments[0].click();", getElement(driver, xpath))
    else:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()


def getElement(driver, xpath):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))


def getElements(driver, xpath):
    return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((By.XPATH, xpath)))


def sendkeys(driver, xpath, keys, js=False):
    if js:
        driver.execute_script(f"arguments[0].value='{keys}';", getElement(driver, xpath))
    else:
        getElement(driver, xpath).send_keys(keys)


def getChromeDriver(proxy=None):
    options = webdriver.ChromeOptions()
    if debug:
        # print("Connecting existing Chrome for debugging...")
        options.debugger_address = "127.0.0.1:9222"
    else:
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--user-data-dir=C:/Selenium1/ChromeProfile')
    if not images:
        # print("Turning off images to save bandwidth")
        options.add_argument("--blink-settings=imagesEnabled=false")
    if headless:
        # print("Going headless")
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
    if max:
        # print("Maximizing Chrome ")
        options.add_argument("--start-maximized")
    if proxy:
        # print(f"Adding proxy: {proxy}")
        options.add_argument(f"--proxy-server={proxy}")
    if incognito:
        # print("Going incognito")
        options.add_argument("--incognito")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def getFirefoxDriver():
    options = webdriver.FirefoxOptions()
    if not images:
        # print("Turning off images to save bandwidth")
        options.set_preference("permissions.default.image", 2)
    if incognito:
        # print("Enabling incognito mode")
        options.set_preference("browser.privatebrowsing.autostart", True)
    if headless:
        # print("Hiding Firefox")
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
    return webdriver.Firefox(options)


def logo():
    print(r"""
                                   .__             .___            .___               
    ______ _______   ____  ______  |__|  ____    __| _/_____     __| _/ ____    ______
    \____ \\_  __ \ /  _ \ \____ \ |  |_/ __ \  / __ | \__  \   / __ |_/ __ \  /  ___/
    |  |_> >|  | \/(  <_> )|  |_> >|  |\  ___/ / /_/ |  / __ \_/ /_/ |\  ___/  \___ \ 
    |   __/ |__|    \____/ |   __/ |__| \___  >\____ | (____  /\____ | \___  >/____  >
    |__|                   |__|             \/      \/      \/      \/     \/      \/ 
============================================================================================
              propiedades properties scraper by github.com/evilgenius786
============================================================================================
[+] Automated
[+] Fast
[+] CSV output
____________________________________________________________________________________________
""")


if __name__ == "__main__":
    main()
