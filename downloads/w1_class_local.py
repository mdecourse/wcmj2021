import requests
import bs4

'''
url:  'class_ajax.php',
data: { pselyr: pselyr, pselclss: pselclss
'''
semester = '1092'
classno = '42311'
column = True

if semester == None:
    semester = '1091'
if classno == None:
    # 42311 is 設一甲
    classno = '42311'
    
headers = {'X-Requested-With': 'XMLHttpRequest'}

url = 'https://qry.nfu.edu.tw/class_ajax.php'
post_var = {'pselyr': semester, 'pselclss': classno}

result = requests.post(url, data = post_var, headers = headers)

soup = bs4.BeautifulSoup(result.content, 'lxml')
table = soup.find('table', {'class': 'tbcls'})

output = "<table border='1'>"
for i in table.contents:
    output += str(i).replace("&amp;nbsp", "&nbsp")
output += "</table>"
print(output)
