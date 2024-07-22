from flask import Flask, render_template, jsonify, send_file, request, send_from_directory, session, redirect, url_for
import uuid
import pandas as pd
import time
import threading
from llm_query import llm_query_efficient_parallel
from llm_batch import llm_batch_parallel
from process_results import process_results, process_results_binarymatrix
import logging
import os.path
import os 
import zipfile
from io import BytesIO

app = Flask(__name__)
app.logger.setLevel(logging.ERROR)
app.secret_key = 'codyan2024'

BATCH = False

VERSION = "v24.7.22 ALPHA"

# possible statuses
NOT_STARTED = 0
RUNNING = 1
PAUSED = 2
FINISHED = 3
STOPPED = 4

states = {}


def read_input(input_folder):

    codes_df = None
    responses_df = None
    reference_df = None
    codes = None
    questions = None
    reference = None

    try:
        responses_df = pd.read_csv(f'{input_folder}/responses.csv')
        questions = []
        for col in responses_df.columns:
            if 'question_' in col:
                question_text = col.split(':')[1].strip()
                question_num = col.split(':')[0].split('_')[1]
                num_responses = responses_df[col].count()
                questions.append({
                    'number': question_num,
                    'text': question_text,
                    'num_responses': num_responses
                })
    except:
        pass
        
    try:
        codes_df = pd.read_csv(f'{input_folder}/codes.csv')
        # Detect number of code columns
        num_code_columns = 0
        while f'codes_{num_code_columns + 1}' in codes_df.columns:
            num_code_columns += 1
        codes = {}
        for i in range(1, num_code_columns + 1):
            code_col = f'codes_{i}'
            desc_col = f'descriptions_{i}'
            codes[f'codes_{i}'] = []
            if code_col in codes_df.columns and desc_col in codes_df.columns:
                for code, desc in zip(codes_df[code_col], codes_df[desc_col]):
                    if pd.notna(code) and pd.notna(desc) and code and desc:
                        codes[f'codes_{i}'].append({
                            'code': code,
                            'description': desc
                        })
    except:
        pass

    try:
        reference_df = pd.read_csv(f'{input_folder}/reference.csv')
        reference_df = reference_df.replace({float('nan'): None})
        reference = {}
        for col_name in reference_df.columns:
            reference[col_name] = []
            for r_index, codeset in enumerate(reference_df[col_name].items()):
                reference[col_name].append(codeset)

    except Exception as error:
        pass


    return codes_df, responses_df, reference_df, questions, codes, reference


# Background process simulation
def background_process(limit, iterations, threads, model, apikey, session_id, input_folder, output_folder):
    global process_status
    states[session_id]['process_status']["status"] = 1
    codes_df, responses_df, reference_df, questions, codes, reference = input_data = read_input(input_folder)
    def progress_callback(progress):
        (string, percentage) = progress
        global progress_status
        states[session_id]['process_status']["string"] = string
        states[session_id]['process_status']["progress"] = percentage

    if(BATCH):
        llm_batch_parallel(codes_df, responses_df, progress_callback, int(iterations), int(limit), int(threads), model, apikey, states[session_id]['pause_event'], states[session_id]['stop_event'])
    else:
        print(codes_df)
        print(responses_df)

        llm_query_efficient_parallel(codes_df, responses_df, progress_callback, int(iterations), int(limit), int(threads), model, apikey,  states[session_id]['pause_event'], states[session_id]['stop_event'], output_folder)
    states[session_id]['process_status']["status"] = 3

@app.route('/')
def index():

    input_data = read_input(get_input_folder())

    
    result_data_exists = os.path.exists(f'{get_output_folder()}')
    session_id = get_session_id()

    if(input_data):
        codes_df, responses_df, reference_df, questions, codes, reference = input_data
        enable_process_results = os.path.exists(f'{get_output_folder()}')
        return render_template('index.html', 
            questions=questions,
            codes=codes,
            reference=reference,
            result_data_exists=result_data_exists,
            session_id = session_id,
            version = VERSION)
    else:
        return render_template('index.html', questions=None, codes=None,  reference = None, version = VERSION)


@app.route('/remove', methods=['GET'])
def remove_file():


    file_name = request.args.get('file')
    
    if file_name:
        file_path = os.path.join(f'{get_input_folder()}', file_name + '.csv')
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return jsonify({"message": f"File '{file_name}' deleted successfully."}), 200
            else:
                return jsonify({"error": f"File '{file_name}' not found."}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "File parameter is missing."}), 400


@app.route('/upload', methods=['POST'])
def upload_file():

    if 'responsescsv' in request.files:
        file = request.files['responsescsv']
        filename = "responses.csv"
    if 'referencecsv' in request.files:
        file = request.files['referencecsv']
        filename = "reference.csv"
    if 'codebookcsv' in request.files:
        file = request.files['codebookcsv']
        filename = "codes.csv"
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.csv'):
        # Ensure the directory exists
        os.makedirs(f'{get_input_folder()}', exist_ok=True)
        # Save the file
        file.save(os.path.join(f'{get_input_folder()}', filename))
        return jsonify({'success': 'File uploaded successfully'}), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400

@app.route('/download_llm_output', methods=['GET'])
def download_llm_output():
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(f'{get_output_folder()}'):
            for file in files:
                if file.startswith('codyan_q'):
                    file_path = os.path.join(root, file)
                    zip_file.write(file_path, os.path.relpath(file_path, f'{get_output_folder()}'))
    
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='llm_output.zip')

@app.route('/download_results', methods=['GET'])
def download_results():
    results_path = f'{get_output_folder()}/results.csv'
    if os.path.exists(results_path):
        return send_from_directory(directory=f'{get_output_folder()}', path='results.csv', as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404



@app.route('/instructions')
def instructions():
        return render_template('instructions.html', version = VERSION)

@app.route('/about')
def about():
        return render_template('about.html', version = VERSION)

@app.route('/set_session_id', methods=['POST'])
def set_session_id():
    session_id = request.form.get('session_id_input')
    if session_id:
        if session_id in states:
            session['session_id'] = session_id
            output_folder = f'.data/output_{session_id}'
            # Ensure the user's output directory exists
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
        else:
            return redirect(url_for('index'))
    return redirect(url_for('index'))



@app.route('/get_results', methods=['GET'])
def get_results():
    p_value = float(request.args.get('pvalue', 0.95))
    # results = process_results_binarymatrix(input_data, p_value)
    results = process_results(read_input(get_input_folder()), p_value, get_input_folder(), get_output_folder())
    return jsonify(results)

@app.route('/start_process', methods=['POST'])
def start_process():

    if(states[get_session_id()]['pause_event'].is_set()):
        states[get_session_id()]['pause_event'].clear()
        states[get_session_id()]['process_status']["status"] = RUNNING
        return jsonify(success=True)
    
    input_data = read_input(get_input_folder())

    codes_df, responses_df, _, _, _, _ = input_data
    
    if  len(codes_df) == 0 or len(responses_df) == 0:
        states[get_session_id()]['process_status']["status"] = 4
        states[get_session_id()]['process_status']["string"] = "[ERROR] Missing input files!"
        return jsonify(success=True)


    input_data = request.get_json()
    iterations = input_data.get('iterations', 1)  
    limit = input_data.get('limit', 0) 
    threads = input_data.get('threads', 1) 
    model = input_data.get('model', 'gpt-3.5-turbo') 
    apikey = input_data.get('apikey', None ) 

    states[get_session_id()]['pause_event'].clear()
    states[get_session_id()]['stop_event'].clear()

    # Ensure the /output_temp directory exists
    output_dir = f'{get_output_folder()}/temp'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    global process_thread

    if states[get_session_id()]['process_status']["status"] not in [RUNNING, PAUSED]:
        process_thread = threading.Thread(target=background_process, args=(limit, iterations, threads, model, apikey, get_session_id(), get_input_folder(), get_output_folder()))
        process_thread.start()
    
    states[get_session_id()]['process_status']["status"] = RUNNING

    return jsonify(success=True)
    
@app.route('/stop_process')
def stop_process():
    global process_status
    states[get_session_id()]['process_status']["status"] = STOPPED
    states[get_session_id()]['process_status']["string"] = f"{states[get_session_id()]['process_status']['string']}"
    states[get_session_id()]['stop_event'].set()
    return jsonify(states[get_session_id()]['process_status'])

@app.route('/pause_process')
def pause_process():
    global process_status
    states[get_session_id()]['process_status']["status"] = PAUSED
    states[get_session_id()]['process_status']["string"] = f"{states[get_session_id()]['process_status']['string']}"
    states[get_session_id()]['pause_event'].set()
    return jsonify(states[get_session_id()]['process_status'])


@app.route('/process_status')
def get_process_status():
    if(states[get_session_id()]['pause_event'].is_set()):
        states[get_session_id()]['process_status']["status"] = PAUSED

    if(states[get_session_id()]['stop_event'].is_set()):
        states[get_session_id()]['process_status']["status"] = STOPPED

    return jsonify(states[get_session_id()]['process_status'])

def get_session_id():
    global states

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']

    if session_id not in states:
        states[session_id] = {}
        states[session_id]['process_status'] = {"status": NOT_STARTED, "progress": 0, "string" : ''}
        states[session_id]['process_thread'] = None
        states[session_id]['pause_event'] = threading.Event()
        states[session_id]['stop_event'] = threading.Event()
    
    return session_id

def get_output_folder():
    output_folder = f'./data/{get_session_id()}/output'
    return output_folder

def get_input_folder():
    input_folder = f'./data/{get_session_id()}/input'
    return input_folder

if __name__ == '__main__':
    app.run(port=8000, debug=True)
