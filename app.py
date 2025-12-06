import csv
import json
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PATH = 'all excels/'
JOB_RUNS_FILE = 'job_runs.json'


def load_job_runs():
    """Load job runs from the JSON file."""
    if not os.path.exists(JOB_RUNS_FILE):
        return []
    try:
        with open(JOB_RUNS_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_job_runs(job_runs):
    """Persist job runs to the JSON file."""
    with open(JOB_RUNS_FILE, 'w', encoding='utf-8') as file:
        json.dump(job_runs, file, indent=2)


def refresh_job_runs(job_runs):
    """
    Update progress for queued/running job runs based on elapsed time.

    This simulates backend processing so the dashboard can poll for updates.
    """
    now = datetime.now(timezone.utc)
    updated = False

    for run in job_runs:
        if run.get('status') in {'queued', 'running'}:
            started_at = run.get('started_at')
            if started_at:
                start_time = datetime.fromisoformat(started_at)
            else:
                # Move queued jobs into running state when first seen
                run['started_at'] = now.isoformat()
                start_time = now
                run['status'] = 'running'
                updated = True

            elapsed_seconds = max((now - start_time).total_seconds(), 0)
            # Increase progress by 5% per second, cap at 100
            progress = min(100, int(elapsed_seconds * 5))

            if progress != run.get('progress', 0):
                run['progress'] = progress
                updated = True

            if progress >= 100 and run.get('status') != 'completed':
                run['status'] = 'completed'
                run['completed_at'] = now.isoformat()
                updated = True

    if updated:
        save_job_runs(job_runs)

    return job_runs
##> ------ Karthik Sarode : karthik.sarode23@gmail.com - UI for excel files ------
@app.route('/')
def home():
    """Displays the home page of the application."""
    return render_template('index.html')


@app.route('/job-runs', methods=['GET'])
def list_job_runs():
    """Return job runs with simulated progress updates for the dashboard."""
    job_runs = refresh_job_runs(load_job_runs())
    return jsonify(job_runs)


@app.route('/job-runs', methods=['POST'])
def create_job_run():
    """Create a new job run entry to track on the dashboard."""
    payload = request.get_json(force=True)
    now = datetime.now(timezone.utc).isoformat()
    job_runs = load_job_runs()

    run_id = f"run-{len(job_runs) + 1}-{int(datetime.now().timestamp())}"
    new_run = {
        'id': run_id,
        'status': 'queued',
        'progress': 0,
        'created_at': now,
        'started_at': None,
        'completed_at': None,
        'personal': payload.get('personal', {}),
        'screening': payload.get('screening', {}),
        'filters': payload.get('filters', {}),
        'parameters': payload.get('parameters', {}),
    }

    job_runs.append(new_run)
    save_job_runs(job_runs)

    return jsonify(new_run), 201

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
        with open(PATH + 'all_applied_applications_history.csv', 'r', encoding='utf-8') as file:
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
    except FileNotFoundError:
        return jsonify({"error": "No applications history found"}), 404
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
        csvPath = PATH + 'all_applied_applications_history.csv'
        
        if not os.path.exists(csvPath):
            return jsonify({"error": f"CSV file not found at {csvPath}"}), 404
            
        # Read current CSV content
        with open(csvPath, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldNames = reader.fieldnames
            found = False
            for row in reader:
                if row['Job ID'] == job_id:
                    row['Date Applied'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    found = True
                data.append(row)
        
        if not found:
            return jsonify({"error": f"Job ID {job_id} not found"}), 404

        with open(csvPath, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldNames)
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