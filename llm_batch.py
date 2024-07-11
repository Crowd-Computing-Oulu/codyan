
import time
from openai import OpenAI
import csv
import os.path
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

CLIENT = None

MODEL = "gpt-4-turbo"
TEMP = 0.8

def llm_batch_parallel(codes_df, responses_df, update_status, iterations, response_limit, threads, model, apikey):
    
    global MODEL

    global CLIENT

    MODEL = model

    CLIENT = OpenAI(api_key=apikey)

    splits = [responses_df.iloc[i::threads] for i in range(threads)]
    num_responses = len(responses_df)

    # Use ThreadPoolExecutor to run the function in parallel
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(llm_batch, codes_df, split, update_status, iterations, response_limit, num_responses) for split in splits]
        
        # Gather results (if needed)
        results = [future.result() for future in futures]
    
    return results

def llm_batch(codes_df, responses_df, update_status, iterations, response_limit, num_responses):

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
                response_string = ' '.join(response[num_q].splitlines()).replace("\"", "\\\"")

                result = {}
                result['iteration'] = iteration

                result['response'] = response_index+1

                prompt = f'Here are the possible labels for the question {question_string} : '

                for i in range(0, len(codes_for_this_question)): 
                    code_col = f'codes_{num_q+1}'
                    desc_col = f'descriptions_{num_q+1}'
                    prompt += f'{i+1}. \\"{codes_df[code_col].iloc[i]}\\":  {codes_df[desc_col].iloc[i]}, '

                prompt += f' Which (at least one, possibly multiple) of the most relevant labels that apply to the following response? Respond with a comma separated list of codes and nothing else. E.g. tag1, tag2, tag3. PARTICIPANT: \\"{response_string}\\"? '


                req_id = f'I{iteration}Q{num_q+1}R{response_index+1}'

                append_text = f'{{"custom_id": "{req_id}", "method": "POST", "url": "/v1/chat/completions", "body": {{"model": "{MODEL}", "messages": [{{"role": "user", "content": "{prompt}"}}],"temperature": {TEMP}}}}}\n'


                file = f'output/batch.jsonl'
                with open(file, mode='a', newline='', encoding='utf-8') as file:
                    file.write(append_text)
               
                update_status(
                    (
                    f"Iteration {iteration}/{iterations}, question {num_q+1}/{num_questions}, response {response_index+1}/{num_responses}",

                    (current_step*100)/total_steps
                    )
                )
                    
                current_step+= 1

    return results
