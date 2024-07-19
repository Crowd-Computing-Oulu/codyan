import glob
import pandas as pd
import nltk
import os.path
import csv
from nltk.metrics import agreement
from nltk.metrics.agreement import AnnotationTask
from nltk.metrics import masi_distance, jaccard_distance, binary_distance
import matplotlib
import matplotlib.pyplot as plt

def process_results(data, p, input_folder, output_folder):
    files = glob.glob(f"{output_folder}/codyan_q*.csv")
    results = {}

    for file in files:
        df = pd.read_csv(file)
        df = df.sort_values(by=['iteration', 'response'])
        question_id = file.split("_q")[1].split(".")[0] 

        question_results = {}
        responses = df['response'].unique()

        for response in responses:
            response_df = df[df['response'] == response]
            iterations_count = response_df['iteration'].nunique()
            true_counts = response_df.drop(columns=['response', 'iteration']).sum()
            ratios = (true_counts / iterations_count).to_dict()

            # Filter out the ratios below 0.95
            filtered_ratios = {code: ratio for code, ratio in ratios.items() if ratio >= p}
            question_results[str(response)] = filtered_ratios

        results[question_id] = question_results

    returnval = {}
    returnval['results'] = results
    try:
        returnval['icr'] = icr(results, input_folder)
    except:
        returnval['icr'] = None
        
    # returnval['icr'] = 0

    csvdata = []
    csv_columns = []
    max_responses = 0

    for question_index, question_responses in results.items():
        csv_columns.append(f'codes_{question_index}')
        csv_columns.append(f'pvalues_{question_index}')
        max_responses = max(max_responses, len(question_responses))

    for i in range(max_responses):
        csvdata.append({})

    for question_index, question_responses in results.items():
        question_index = int(question_index)-1
        for response_index, response in question_responses.items():
            response_index = int(response_index)-1

            codes_array = []
            pvalues_array = []

            for code in response.keys():
                codes_array.append(code)
                pvalues_array.append(response[code])
            codes_string = ','.join(str(v) for v in codes_array)
            pvalues_string = ','.join(str(v) for v in pvalues_array)
            csvdata[int(response_index)][f'codes_{question_index+1}'] = codes_string
            csvdata[int(response_index)][f'pvalues_{question_index+1}'] =  pvalues_string

    for row in csvdata:
        for question_index, question_responses in results.items():
            question_index = int(question_index)-1
            if f'codes_{question_index+1}' not in row:
                row[f'codes_{question_index+1}'] = ''
            if f'pvalues_{question_index+1}' not in row:
                row[f'pvalues_{question_index+1}'] = ''

    csv_filename = f'{output_folder}/results.csv'
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(csvdata)
    
    return returnval

def process_results_binarymatrix(data, p,input_folder, output_folder):
    files = glob.glob("output/codyan_q*.csv")
    results = {}

    codes_df, responses_df, reference_df, questions, codes, reference = data

    for file in files:
        df = pd.read_csv(file)
        df = df.sort_values(by=['iteration', 'response'])
        question_id = int(file.split("_q")[1].split(".")[0])

        codes_for_this_question = [code for c_, code in list(codes_df[f'codes_{question_id}'].dropna().items())]


        question_results = {}
        responses = df['response'].unique()

        for response in responses:
            response_df = df[df['response'] == response]
            iterations_count = response_df['iteration'].nunique()
            true_counts = response_df.drop(columns=['response', 'iteration']).sum()
            ratios = (true_counts / iterations_count).to_dict()

            # Filter out the ratios below the threshold
            filtered_ratios = {code: ratio for code, ratio in ratios.items() if ratio >= p}
            question_results[str(response)] = filtered_ratios

        results[question_id] = question_results

        csvdata = []
        csv_columns = ['response'] + codes_for_this_question

        # Create a binary matrix for each question
        for question_index, question_responses in results.items():
            question_index = int(question_index) - 1
            for response_index, response in question_responses.items():
                response_index = int(response_index) - 1

                if len(csvdata) <= response_index:
                    csvdata.append({'response': response_index + 1})

                for code in codes_for_this_question:
                    csvdata[response_index][code] = code in response

        for row in csvdata:
            for code in codes_for_this_question:
                if code not in row:
                    row[code] = False

        csv_filename = f'output/results_binary_{question_id}.csv'
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerows(csvdata)

    returnval = {}
    returnval['results'] = results
    try:
        returnval['icr'] = icr_alt(codes_df, results, input_folder)
    except:
        returnval['icr'] = None

    return process_results(data,p)



def icr(results, input_folder):
  
    reference_df = pd.read_csv(f'{input_folder}/reference.csv')

    task_data = []
    # num_reference_rows = 10
    num_reference_rows = len(reference_df)
    # print(len(reference_df))

    for col_name in reference_df.columns:
        q_index = int(col_name.split("_")[1])
        question_codes = reference_df[f'question_{q_index}']
        print(len(question_codes))
        for r_index, codeset in enumerate(question_codes):
            try:
                codeset_list = []
                for code in codeset.split(","):
                    codeset_list.append(code.strip())

                task_data.append(
                    ('researcher', f'Q{q_index}R{int(r_index)+1}', frozenset(codeset_list))
                )
            except:
                task_data.append(
                    ('researcher', f'Q{q_index}R{int(r_index)+1}', frozenset())
                )
        

    for question_index, question in results.items():
        question_index = int(question_index)-1

        for response_index, response in question.items():
            response_index = int(response_index)-1

            if(response_index<num_reference_rows):
                task_data.append(
                    ('codyan', f'Q{question_index+1}R{response_index+1}', frozenset(list(response.keys())))
                )

    # task_data = [('coder1','Item0',frozenset(['l1','l2'])),
    # ('coder2','Item0',frozenset(['l1'])),
    # ('coder1','Item1',frozenset(['l1','l2'])),
    # ('coder2','Item1',frozenset(['l1','l2'])),
    # ('coder1','Item2',frozenset(['l1'])),
    # ('coder2','Item2',frozenset(['l1']))]

    task_data_empties_handled = []

    for coder, doc, labels in task_data:
        if(len(labels) == 0):
            task_data_empties_handled.append(
                (coder, doc, None)
                # (coder, doc, frozenset([]))
            )
        else:
            task_data_empties_handled.append(
                (coder, doc, labels)
            )


    # for task in task_data_empties_handled:
    #     print(task)

    # jaccard_task = AnnotationTask(data=task_data_empties_handled,distance = jaccard_distance)
    masi_task = AnnotationTask(data=task_data_empties_handled,distance = masi_distance)
    jaccard_task = AnnotationTask(data=task_data_empties_handled,distance = jaccard_distance)

   
    # print(f"Fleiss's Kappa using MASI: {masi_task.multi_kappa()}")
    # print(f"Fleiss's Kappa using Jaccard: {jaccard_task.multi_kappa()}")
    # print(f"Krippendorff's Alpha using MASI: {masi_task.alpha()}")
    # try:
    #     print(f".alpha() using MASI: {masi_task.alpha()}")
    # except:
    #     print("oopsie")
    # try:
    #     print(f".kappa() using MASI: {masi_task.kappa()}")
    # except:
    #     print("oopsie")
    # try:
    #     print(f".kappa_pairwise() using MASI: {masi_task.kappa_pairwise()}")
    # except:
    #     print("oopsie")
    # try:
    #     print(f".multi_kappa() using MASI: {masi_task.multi_kappa()}")
    # except:
    #     print("oopsie")
    # try:
    #     print(f".avg_Ao using MASI: {masi_task.avg_Ao()}")
    # except:
    #     print("oopsie")
    # try:
    #     print(f".pi() using MASI: {masi_task.pi()}")
    # except:
    #     print("oopsie")
    # try:
    #     print(f".S() using MASI: {masi_task.S()}")
    # except:
    #     print("oopsie")
    # print(f"Krippendorff's Alpha using Jaccard: {jaccard_task.alpha()}")

    return masi_task.alpha()

def icr_alt(codes_df, results,input_folder, output_folder):

    # ICRss = []
    # for i in range(1, 50):
    ICRs = {}

    for file in glob.glob(f"{output_folder}/codyan_q*.csv"):
        question_id = int(file.split("_q")[1].split(".")[0])

        reference_df = pd.read_csv(f"{input_folder}/reference.csv")

        task_data = []
        num_reference_rows = len(reference_df)

        question_codes = reference_df[f'question_{question_id}']
        for r_index, codeset in enumerate(question_codes):
            try:
                codeset_list = []
                for code in codeset.split(","):
                    codeset_list.append(code.strip())

                task_data.append(
                    ('researcher', f'Q{question_id}R{int(r_index)+1}', frozenset(codeset_list))
                )
            except:
                task_data.append(
                    ('researcher', f'Q{question_id}R{int(r_index)+1}', frozenset())
                )

        for question_index, question in results.items():
            if(question_index == question_id):
                question_index = int(question_index)-1

                for response_index, response in question.items():
                    response_index = int(response_index)-1

                    if(response_index<num_reference_rows):
                        task_data.append(
                            ('codyan', f'Q{question_index+1}R{response_index+1}', frozenset(list(response.keys())))
                        )

        task_data_empties_handled = []

        for coder, doc, labels in task_data:
            if(len(labels) == 0):
                task_data_empties_handled.append(
                    (coder, doc, None)
                )
            else:
                task_data_empties_handled.append(
                    (coder, doc, labels)
                )

        binary = []
        codes_for_this_question = [code for c_, code in list(codes_df[f'codes_{question_id}'].dropna().items())]
        for coder, doc, labels in task_data:
            binary_row = []
            for code in codes_for_this_question:
                if(code in labels):
                    binary_row.append(1)
                else:
                    binary_row.append(0)

            binary.append(
                (coder, doc, tuple(binary_row))
            )

        masi_task = AnnotationTask(data=binary,distance = binary_distance)

        print(f'QUESTION {question_id}')
        for task in binary:
            print(task)
        print(masi_task.alpha())
        ICRs[question_id] = masi_task.alpha()

    # ICRss.append((ICRs[1], ICRs[2], ICRs[3]))
    print(ICRs)
    return ICRs


    # Unpacking the tuples into separate lists
    # x_values, y_values, z_values = zip(*ICRss)

    # matplotlib.use('agg')

    # # Creating the plot
    # plt.figure()
    # plt.plot(x_values, label='Series 1')
    # plt.plot(y_values, label='Series 2')
    # plt.plot(z_values, label='Series 3')
    # plt.title('S')
    # # plt.title('Kappa - Davies and Fleiss')
    # plt.xlabel('Index')
    # plt.ylabel('Values')
    # plt.legend()

    # Save the plot to a file
    # plt.savefig('value_series_plot3.png')

    # Optionally, display the plot
    # plt.show()

    # return ICRs

