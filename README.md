# llmqc-app
Large Language Model Qualitative Coder Application.


## Usage

1. Make a copy of `/input_sample` directory named `/input`
2. Update the files inside the `/input` directory with your data
   1. Enter your codebook in `codes.csv`
   2. Enter the data you want to code in `responses.csv`
   3. Enter your reference, human-coded lines, if you have any, in `reference.csv`
3. Install dependencies with `pip install -r requirements.txt`
4. Run the LLMQC with `python app.py`
5. [Obtain](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key) and enter your OpenAI API key
6. Follow the on-screen instructions to load your input data, your codeset, perform coding and analyse your results
7. Find your results in the `/output` folder and on-screen. The used prompts are also saved in `/output/prompts.csv`

With any questions, feel free to contact me at [daniel.szabo@oulu.fi](mailto:daniel.szabo@oulu.fi)