
import time
from openai import OpenAI
import csv
import os.path
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
import shutil
import os
import traceback

CLIENT = None

LOG_PROMPTS = True
MODEL = "gpt-4-turbo"
TEMP = 0.8

pause_event = None
stop_event = None

def llm_query_efficient_parallel(codes_df, responses_df, update_status, iterations, response_limit, threads, model, apikey, pause_ent, stop_ent, output_path):
    
    try:
        global MODEL
        global CLIENT
        global pause_event
        global stop_event

        pause_event = pause_ent
        stop_event = stop_ent

        MODEL = model

        CLIENT = OpenAI(api_key=apikey)

        splits = [responses_df.iloc[i::threads] for i in range(threads)]
        num_responses = len(responses_df)

        # Use ThreadPoolExecutor to run the function in parallel
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(llm_query_efficient, codes_df, split, update_status, iterations, response_limit, num_responses, output_path) for split in splits]
            
            # Gather results (if needed)
            results = [future.result() for future in futures]


        # copy to /output
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        if os.path.exists(f'{output_path}/temp'):
            for item in os.listdir(f'{output_path}/temp'):
                s = os.path.join(f'{output_path}/temp', item)
                d = os.path.join(f'{output_path}', item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

    except Exception as e:
        update_status((f"[ERROR] {e}", 0))
        stop_event.set()
        print(traceback.format_exc())
        return None
    
    return results

def llm_query_efficient(codes_df, responses_df, update_status, iterations, response_limit, num_responses, output_path):

    global LOG_PROMPTS
    
    num_questions = len(responses_df.columns)
    if(response_limit != 0):
            responses_df = responses_df.head(response_limit)

    current_step = 1
    total_steps = (iterations*num_questions*num_responses)

    SHIFT = 0

    for iteration in range(SHIFT + 1, SHIFT + iterations+1):
        
        prompts = []

        # process questions one by one
        for num_q in range(0, num_questions):

            results = []
             
            question_string = responses_df.columns[num_q].split(':')[1].strip()
            codes_for_this_question = codes_df[f'codes_{num_q+1}'].dropna()

            fieldnames = []
            fieldnames.append("response")
            fieldnames.append("iteration")
            for _, code in codes_for_this_question.items():
                fieldnames.append(code)

            # then for each response to the question
            for response_index, response in responses_df.iterrows():
                response_string = response[num_q]

                result = {}
                result['iteration'] = iteration

                result['response'] = response_index+1

                prompt = f'Here are the possible labels for the question "{question_string}" :\n'

                for i in range(0, len(codes_for_this_question)): 
                    code_col = f'codes_{num_q+1}'
                    desc_col = f'descriptions_{num_q+1}'
                    prompt += f'{i+1}. "{codes_df[code_col].iloc[i]}":  {codes_df[desc_col].iloc[i]}\n'

                prompt += f'\nWhich (at least one, possibly multiple) of the most relevant labels that apply to the following response? Respond with a comma separated list of codes and nothing else. E.g. "tag1, tag2, tag3".\nPARTICIPANT:"{response_string}"? '

                if(LOG_PROMPTS):
                    prompts.append({
                        'question': question_string,
                        'response': response_string,
                        'code': code,
                        'prompt': prompt,
                    })

                messages = [{"role": "user", "content": prompt}] 

                while(pause_event.is_set()):
                    time.sleep(1)

                if(stop_event.is_set()):
                    return

                chat = CLIENT.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    temperature=TEMP) 
                chatgpt_response = chat.choices[0].message.content 

                for code_index, code in codes_for_this_question.items():
                    # extract code true/falses from response
                    result[codes_for_this_question[code_index]] = chatgpt_response.lower().find(code) != -1 

                update_status(
                    (
                    f"Iteration {iteration}/{iterations}, question {num_q+1}/{num_questions}, response {response_index+1}/{num_responses}",

                    (current_step*100)/total_steps
                    )
                )

                current_step+= 1
                
                print(f'PROMPT: {prompt}\nCHATGPT ANSWER: {chatgpt_response}\nRESULT: {result}')
                results.append(result)

            file_exists = os.path.isfile(f'{output_path}/temp/codyan_q{num_q+1}.csv')
            # Write results to CSV file
            csv_filename = f'{output_path}/temp/codyan_q{num_q+1}.csv'
            with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(results)

        if(LOG_PROMPTS):
            # Write results to CSV file
            csv_filename = f'{output_path}/temp/prompts.csv'
            file_exists = os.path.isfile(csv_filename)
            with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
                fieldnames = [
                    'question',
                    'response',
                    'code',
                    'prompt',
                    ]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(prompts)
            # Only log for 1st iteration obviously
            LOG_PROMPTS = False

    return results
