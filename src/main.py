from apify import Actor
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = 'https://il.healthinspections.us/lake'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
date_threshold = datetime.now() - timedelta(days=30)

formatted_date1 = date_threshold.strftime('%m/%d/%Y')
formatted_date2 = datetime.now().strftime('%m/%d/%Y')
data = []

# Function to parse date
def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%m/%d/%Y')
    except ValueError:
        return None

def fetch_inspections(inspections_number):
    url = f'{BASE_URL}/search.cfm?start={inspections_number}&searchStartDate={formatted_date1}&searchEndDate={formatted_date2}'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        inspections = soup.find_all('div', style=lambda x: x and 'border-bottom:1px dotted' in x)
        
        if not inspections:
            return False  

        for inspection in inspections:
            facility_tag = inspection.find('a', href=True)
            facility_name = facility_tag.get_text(strip=True) if facility_tag else "N/A"
            address_tag = inspection.find('i')
            address = address_tag.get_text(separator=' ', strip=True) if address_tag else "N/A"

            

            # Extract inspection date and detail link
            date_link_tag = inspection.find('a', class_='GEI_Link')
            if date_link_tag:
                date_str = date_link_tag.get_text(strip=True)
                date_value = parse_date(date_str)
                print(f"Facility Name: {facility_name} | Inspection Date: {date_str}")
                if date_value and date_value >= date_threshold:
                    inspection_link = 'https://il.healthinspections.us/' + date_link_tag['href'].lstrip('/')

                    detail_response = requests.get(inspection_link, headers=HEADERS)
                    detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                    pic_tag = detail_soup.find('strong', string=lambda s: s and "Person In Charge" in s)
                    if pic_tag:
                        person_in_charge = pic_tag.find_parent('td').get_text(separator=' ', strip=True).replace(pic_tag.text, '').strip()
                    else:
                        person_in_charge = "N/A"
                                
                    violations = detail_soup.find_all(string=lambda text: text and 'gasket' in text.lower()) or []
                    comment =[]
                    for comment in violations:
                        comment = comment.strip()

                    if comment and len(comment) > 0:
                        facility_name = facility_name if facility_name else ""
                        address = address if address else ""
                        date_str = date_str if date_str else ""
                        person_in_charge = person_in_charge if person_in_charge else ""
                        comment = comment if comment else "" 
                        return facility_name, address, date_str, person_in_charge, comment
                            
async def main(): 
    async with Actor:
        inspection_number = 1
        page_start = 1
        while True:
            facility_name, address, date_str, person_in_charge, comment = fetch_inspections(inspection_number)
            if not facility_name:
                break
            else:
                await Actor.push_data(
                    {
                        "Facility Name": facility_name,
                        "Address": address,
                        "Inspection Date": date_str,
                        "Person in Charge": person_in_charge,
                        "Gasket Violations": comment
                    }
                )
            page_start += 1 # Go to the next page
            inspection_number += 25 
        print("Scraping completed!")
