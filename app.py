from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import csv
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

APPLICATION_HISTORY_DIR = os.getenv('APPLICATION_HISTORY_DIR', 'all excels')
APPLICATION_HISTORY_FILE = os.getenv('APPLICATION_HISTORY_FILE', 'all_applied_applications_history.csv')

os.makedirs(APPLICATION_HISTORY_DIR, exist_ok=True)


def get_history_csv_path() -> str:
    '''
    Returns the absolute path of the applications history CSV file.

    The directory and filename are configurable through the environment variables
    `APPLICATION_HISTORY_DIR` and `APPLICATION_HISTORY_FILE`.
    '''

    return os.path.join(APPLICATION_HISTORY_DIR, APPLICATION_HISTORY_FILE)
##> ------ Karthik Sarode : karthik.sarode23@gmail.com - UI for excel files ------
@app.route('/')
def home():
    """Displays the home page of the application."""
    return render_template('index.html')

@app.route('/applied-jobs', methods=['GET'])
def get_applied_jobs():
    '''
    Retrieves a list of applied jobs from the applications history CSV file.
    
    Returns a JSON response containing a list of jobs, each with details such as 
    Job ID, Title, Company, HR Name, HR Link, Job Link, External Job link, and Date Applied.
    
    If the CSV file is not found, returns a 404 error with a relevant message.
    If any other exception occurs, returns a 500 error with the exception message.
    '''

    try:
        jobs = []
        csv_path = get_history_csv_path()

        if not os.path.exists(csv_path):
            return jsonify(jobs)

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                jobs.append({
                    'Job_ID': row['Job ID'],
                    'Title': row['Title'],
                    'Company': row['Company'],
                    'HR_Name': row['HR Name'],
                    'HR_Link': row['HR Link'],
                    'Job_Link': row['Job Link'],
                    'External_Job_link': row['External Job link'],
                    'Date_Applied': row['Date Applied']
                })
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/applied-jobs/<job_id>', methods=['PUT'])
def update_applied_date(job_id):
    """
    Updates the 'Date Applied' field of a job in the applications history CSV file.

    Args:
        job_id (str): The Job ID of the job to be updated.

    Returns:
        A JSON response with a message indicating success or failure of the update
        operation. If the job is not found, returns a 404 error with a relevant
        message. If any other exception occurs, returns a 500 error with the
        exception message.
    """
    try:
        data = []
        csv_path = get_history_csv_path()

        if not os.path.exists(csv_path):
            return jsonify({"error": f"CSV file not found at {csv_path}"}), 404

        # Read current CSV content
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            field_names = reader.fieldnames
            found = False
            for row in reader:
                if row['Job ID'] == job_id:
                    row['Date Applied'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    found = True
                data.append(row)

        if not found:
            return jsonify({"error": f"Job ID {job_id} not found"}), 404

        with open(csv_path, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(data)

        return jsonify({"message": "Date Applied updated successfully"}), 200
    except Exception as e:
        print(f"Error updating applied date: {str(e)}")  # Debug log
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

##<