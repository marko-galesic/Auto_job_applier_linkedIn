import csv
import os
from collections import deque
from typing import Any, Dict

from datetime import datetime
from modules.helpers import (
    get_chromedriver_log_path,
    get_latest_screenshot_path,
    get_log_path,
)
from modules.job_store import JobStore
from modules.job_worker import JobWorker
from werkzeug.utils import secure_filename

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

app = Flask(__name__)

allowed_origin = os.getenv("ALLOWED_ORIGIN") or os.getenv("RENDER_EXTERNAL_URL") or "*"
CORS(app, resources={r"/*": {"origins": allowed_origin}}, methods=["GET", "PUT", "POST", "OPTIONS"])

PATH = 'all excels/'
JOBS_DB_PATH = os.getenv('JOBS_DB_PATH', os.path.join('data', 'jobs.db'))
RESUME_UPLOAD_PATH = os.getenv('DEFAULT_RESUME_PATH', os.path.join('all resumes', 'uploaded', 'resume.pdf'))
ALLOWED_RESUME_EXTENSIONS = {'.pdf', '.doc', '.docx'}
LOG_PATH = get_log_path()
CHROMEDRIVER_LOG_PATH = get_chromedriver_log_path()

job_store = JobStore(JOBS_DB_PATH)
job_worker = JobWorker(job_store, poll_interval=5)


def get_history_csv_path() -> str:
    """Return absolute path to the applied jobs history CSV."""
    from config.settings import file_name

    return os.path.join(os.getcwd(), file_name)


def _ensure_resume_directory():
    os.makedirs(os.path.dirname(RESUME_UPLOAD_PATH), exist_ok=True)


def _validate_resume_file(upload):
    if not upload or upload.filename == '':
        return "No resume file uploaded"

    extension = os.path.splitext(upload.filename)[1].lower()
    if extension not in ALLOWED_RESUME_EXTENSIONS:
        return f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_RESUME_EXTENSIONS))}"
    return None


def _serialize_job_run(job: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Prepare a job record for the dashboard and detail views.
    '''
    ##> ------ OpenAI Assistant : openai-assistant@example.com - Feature ------
    payload = job.get('payload', {}) if isinstance(job.get('payload'), dict) else {}
    return {
        'id': job.get('id'),
        'status': job.get('status'),
        'progress': job.get('progress', 0),
        'created_at': job.get('created_at'),
        'updated_at': job.get('updated_at'),
        'profile_name': payload.get('profileName'),
        'personal': payload.get('personal', {}),
        'screening': payload.get('screening', {}),
        'filters': payload.get('filters', {}),
        'parameters': payload.get('parameters', {}),
    }
    ##<
##> ------ Karthik Sarode : karthik.sarode23@gmail.com - UI for excel files ------
@app.route('/')
def home():
    """Displays the home page of the application."""
    api_base_url = (os.getenv("API_BASE_URL") or "").rstrip("/")
    return render_template('index.html', api_base_url=api_base_url)


@app.route('/job-runs/<run_id>/view', methods=['GET'])
def view_job_run(run_id: str):
    """Render a lightweight details page for a specific job run."""
    return render_template('job_detail.html', run_id=run_id)


@app.route('/job-runs', methods=['GET'])
def list_job_runs():
    """Return current job runs with their latest status and progress."""
    jobs = job_store.list_jobs()
    job_runs = [_serialize_job_run(job) for job in jobs]
    return jsonify(job_runs)


@app.route('/job-runs', methods=['POST'])
def create_job_run():
    """Create a new job run entry to track on the dashboard."""
    payload = request.get_json(force=True, silent=True) or {}
    job_id = job_store.create_job(payload)
    job_worker.enqueue(job_id)

    job = job_store.get_job(job_id)
    job_run = _serialize_job_run(job) if job else {}
    return jsonify(job_run), 201


def _get_job_run(run_id: str) -> Dict[str, Any] | None:
    """Retrieve a single job run entry by ID."""
    job = job_store.get_job(run_id)
    if not job:
        return None
    return _serialize_job_run(job)


@app.route('/job-runs/<run_id>', methods=['GET'])
def get_job_run_details(run_id: str):
    run = _get_job_run(run_id)
    if not run:
        return jsonify({"error": "Job run not found"}), 404
    return jsonify(run)


@app.route('/job-runs/<run_id>/logs', methods=['GET'])
def get_job_run_logs(run_id: str):
    _ = _get_job_run(run_id)
    if not _:
        return jsonify({"error": "Job run not found"}), 404

    if not os.path.exists(LOG_PATH):
        return jsonify({"logs": [], "message": "Log file not found"})

    try:
        with open(LOG_PATH, 'r', encoding='utf-8') as file:
            tail_lines = list(deque(file, maxlen=200))
        return jsonify({"logs": tail_lines})
    except Exception as exc:  # pragma: no cover - defensive logging
        return jsonify({"error": str(exc)}), 500


@app.route('/job-runs/<run_id>/chromedriver-logs', methods=['GET'])
def get_job_run_chromedriver_logs(run_id: str):
    _ = _get_job_run(run_id)
    if not _:
        return jsonify({"error": "Job run not found"}), 404

    if not os.path.exists(CHROMEDRIVER_LOG_PATH):
        return jsonify({"logs": [], "message": "ChromeDriver log file not found"})

    try:
        with open(CHROMEDRIVER_LOG_PATH, 'r', encoding='utf-8') as file:
            tail_lines = list(deque(file, maxlen=200))
        return jsonify({"logs": tail_lines})
    except Exception as exc:  # pragma: no cover - defensive logging
        return jsonify({"error": str(exc)}), 500


@app.route('/job-runs/<run_id>/chromedriver-screenshot', methods=['GET'])
def get_job_run_chromedriver_screenshot(run_id: str):
    _ = _get_job_run(run_id)
    if not _:
        return jsonify({"error": "Job run not found"}), 404

    latest = get_latest_screenshot_path()
    if not latest:
        return jsonify({"message": "No ChromeDriver screenshots available yet"}), 404

    try:
        response = send_file(latest, mimetype='image/png')
        response.headers['Cache-Control'] = 'no-store'
        return response
    except Exception as exc:  # pragma: no cover - defensive logging
        return jsonify({"error": str(exc)}), 500


@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    """Accept and persist a resume for the automation worker to reuse."""
    upload = request.files.get('file')
    validation_error = _validate_resume_file(upload)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    _ensure_resume_directory()
    extension = os.path.splitext(upload.filename)[1].lower()
    destination_filename = f"resume{extension}"
    destination_path = os.path.join(os.path.dirname(RESUME_UPLOAD_PATH), secure_filename(destination_filename))

    upload.save(destination_path)

    return jsonify({
        "message": "Resume uploaded successfully",
        "path": destination_path,
        "filename": destination_filename,
    }), 201

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


def _validate_job_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in ("personals", "questions", "search_filters"):
        if key in body:
            if not isinstance(body[key], (dict, list)):
                raise ValueError(f"'{key}' must be an object or list")
            payload[key] = body[key]
    return payload


@app.route('/jobs', methods=['POST'])
def create_job():
    try:
        body = request.get_json(force=True, silent=True) or {}
        payload = _validate_job_payload(body)
        job_id = job_store.create_job(payload)
        job_worker.enqueue(job_id)
        return jsonify({"id": job_id, "status": "queued"}), 202
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/jobs', methods=['GET'])
def list_jobs():
    jobs = job_store.list_jobs()
    return jsonify(jobs), 200


@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    job = job_store.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200


@app.route('/jobs/<job_id>', methods=['PATCH'])
def update_job(job_id):
    try:
        body = request.get_json(force=True, silent=True) or {}
        payload_updates = _validate_job_payload(body)
        job = job_store.update_payload(job_id, payload_updates)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        if body.get("restart", False):
            job_store.update_status(job_id, status="queued", progress=0)
            job_worker.enqueue(job_id)
            job["status"] = "queued"
            job["progress"] = 0
        return jsonify(job), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

##<