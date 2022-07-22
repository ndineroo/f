import re
import urllib.request
response = urllib.request.urlopen('https://stockx.com/')
html = response.read()
text = html.decode()
re.findall('(.*?)',text)