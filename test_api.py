import requests
main_url="https://reporting-tool-api-test.onrender.com"
api_key = '24d7f9b5-8325-47cd-9800-5cae89248e8b'
url = f"{main_url}/api/v1/"
headers = {"X-API-KEY": api_key}
response = requests.request("GET", url, headers=headers)
print(response.text)

thread_uuid = "40ff1a87-ad04-4781-a7f4-ccaba07de1a7"

url = f"{main_url}/api/v1/getresponse"
headers = {
  'accept': 'application/json',
  "X-API-KEY": api_key
}
payload = {
    "thread_id": str(thread_uuid),
}
response = requests.post(url, headers=headers, json=payload)
print(response.text)