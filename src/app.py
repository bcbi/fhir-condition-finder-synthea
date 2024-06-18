import requests
import os
from flask import Flask, request, render_template, redirect, url_for
from dotenv import load_dotenv

app = Flask(__name__)

FHIR_SERVER_BASE_URL="http://pwebmedcit.services.brown.edu:9091/fhir"

load_dotenv()

username = os.getenv("FHIR_USERNAME")
password = os.getenv("FHIR_PASSWORD")

patients_data = []

def request_patient(patient_id, credentials):
    req = requests.get(FHIR_SERVER_BASE_URL + "/Patient/" + str(patient_id), auth=credentials)
    if req.status_code == 200:
        return req.json()
    else:
        print(f"Request failed for patient {patient_id} with status code: {req.status_code}")
        return None

def search_patients_by_condition(condition_id, credentials):
    search_url = f"{FHIR_SERVER_BASE_URL}/Condition?code={condition_id}"
    patients = []

    while search_url:
        req = requests.get(search_url, auth=credentials)
        if req.status_code == 200:
            response = req.json()
            conditions = response.get('entry', [])
            patient_ids = [entry['resource']['subject']['reference'].split('/')[-1] for entry in conditions]
            
            for patient_id in patient_ids:
                patient = request_patient(patient_id, credentials)
                if patient:
                    patients.append(patient)

            search_url = None
            if 'link' in response:
                for link in response['link']:
                    if link['relation'] == 'next':
                        search_url = link['url']
                        break
        else:
            return []

    unique_patients = list(set(
        (patient['id'], patient['name'][0]['given'][0], patient['name'][0]['family'], patient['gender'], patient['birthDate'])
        for patient in patients
    ))
    return unique_patients

@app.route('/', methods=['GET', 'POST'])
def index():
    global patients_data
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if request.method == 'POST':
        condition_id = request.form['condition_id']
        credentials = (username, password)
        patients_data = search_patients_by_condition(condition_id, credentials)
        page = 1
        return redirect(url_for('index', page=page))

    total_pages = (len(patients_data) - 1) // per_page + 1 if patients_data else 1
    start = (page - 1) * per_page
    end = start + per_page
    patients_to_show = patients_data[start:end] if patients_data else []

    return render_template('index.html', patients=patients_to_show, page=page, total_pages=total_pages, total_patients=len(patients_data))

if __name__ == '__main__':
    port_str = os.environ['FHIR_PORT']
    port_int = int(port_str)
    app.run(debug=True, port=port_int)
