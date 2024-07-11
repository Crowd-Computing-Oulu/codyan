from flask import Flask, render_template, jsonify, send_file, request
import pandas as pd
import time
import threading
from llm_query import llm_query_efficient_parallel
from llm_batch import llm_batch_parallel
from process_results import process_results, process_results_binarymatrix
import logging
import os.path

app = Flask(__name__)
app.logger.setLevel(logging.ERROR)

# Placeholder for the process status
process_status = {"running": False, "progress": 0, "string" : ' - '}

BATCH = False

def read_data():
    codes_df = pd.read_csv('input/codes.csv')
    responses_df = pd.read_csv('input/responses.csv')

    questions = []
    for col in responses_df.columns:
        if 'question_' in col:
            question_text = col.split(':')[1].strip()
            question_num = col.split(':')[0].split('_')[1]
            codes_column = f'codes_{question_num}'
            has_codes = codes_column in responses_df.columns
            num_responses = responses_df[col].count()
            questions.append({
                'number': question_num,
                'text': question_text,
                'has_codes': has_codes,
                'num_responses': num_responses
            })
    
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
    
    return codes_df, responses_df, questions, codes

data = read_data()
result = []

# Background process simulation
def background_process(limit, iterations, threads, model, apikey):
    global process_status
    process_status["running"] = True
    codes_df, responses_df, _, _ = data
    def progress_callback(progress):
        (string, percentage) = progress
        global progress_status
        process_status["string"] = string
        process_status["progress"] = percentage

    if(BATCH):
        llm_batch_parallel(codes_df, responses_df, progress_callback, int(iterations), int(limit), int(threads), model, apikey)
    else:
        llm_query_efficient_parallel(codes_df, responses_df, progress_callback, int(iterations), int(limit), int(threads), model, apikey)
    process_status["running"] = False

@app.route('/')
def index():
    _, _, questions, codes = data
    return render_template('index.html', questions=questions, codes=codes)

@app.route('/get_results', methods=['GET'])
def get_results():
    p_value = float(request.args.get('pvalue', 0.95))
    results = process_results_binarymatrix(data, p_value)
    # results = process_results(data, p_value)
    return jsonify(results)

@app.route('/start_process', methods=['POST'])
def start_process():
    data = request.get_json()
    iterations = data.get('iterations', 1)  
    limit = data.get('limit', 0) 
    threads = data.get('threads', 1) 
    model = data.get('model', 'gpt-3.5-turbo') 
    apikey = data.get('apikey', None ) 

    if not process_status["running"]:
        thread = threading.Thread(target=background_process, args=(limit,iterations, threads, model, apikey))
        thread.start()
    
    return jsonify(success=True)
    
@app.route('/stop_process')
def stop_process():
    global process_status
    process_status["running"] = False
    return jsonify(process_status)

@app.route('/process_status')
def get_process_status():
    return jsonify(process_status)

@app.route('/download_results')
def download_results():
    # This should point to the actual result file
    return send_file('path/to/results.csv', as_attachment=True)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
