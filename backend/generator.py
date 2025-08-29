from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
from dotenv import load_dotenv
import PyPDF2
from docx import Document
from typing import List, Union, Tuple
import hashlib
import json
import re # Import the regular expression module

load_dotenv()

# Initialize Groq LLM with lower temperature for more consistent and accurate outputs
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="gemma2-9b-it",
    temperature=0.2,  # Reduced for better focus and accuracy
    max_tokens=4096  # Increased to handle more detailed responses
)



validation_prompt = PromptTemplate(
    input_variables=["input_text"],
    template="""
You are a senior business analyst. Your task is to validate if the provided text contains coherent software requirements, user stories, or functional specifications. Do not generate test cases.

The input should describe a feature, user action, or system behavior. It should not be random text, a question, a generic statement, or a conversation or numbers or just alphabets or string of numbers.

Analyze the following text:
---
{input_text}
---

Respond with a single JSON object with two keys:
1.  "is_valid": a boolean (true if the text is a valid requirement, false otherwise).
2.  "reason": a brief explanation for your decision. If it is valid, say "The input appears to be a valid software requirement."

Example of a valid input:
"As a user, I want to be able to log in with my username and password so that I can access my account."

Example of an invalid input:
"hello how are you today"

Your entire output must be only the JSON object.

JSON Response:
"""
)




generate_prompt = PromptTemplate(
    input_variables=["input_text"],
    template="""
You are an expert QA engineer specializing in test case generation. Given the following application requirements, user stories, or functional specifications:

{input_text}

Your task is to generate a comprehensive JSON array of test case objects. Each object in the array should represent a single test case and strictly adhere to the following structure:

[
  {{
    "id": <unique_integer_id>,
    "title": "<Concise title for the test case>",
    "type": "<positive|negative|edge|boundary>",
    "description": "<Brief overview of what the test case verifies>",
    "preconditions": "<Setup needed for the test case to be executed, or leave empty if none>",
    "testSteps": [
      "<Step 1>",
      "<Step 2>",
      ...
    ],
    "expectedResult": "<What should happen after executing the test steps>",
    "priority": "<High|Medium|Low>"
  }},
  // ... more test case objects
]

Ensure the following:
1.  **Unique IDs**: Assign a unique integer `id` to each test case, starting from 1.
2.  **Comprehensive Coverage**: Generate every possible relevant test case, including positive, negative, edge cases, and boundary conditions. Do not skip any possible scenario that can be derived from the requirements.
3.  **Clarity**: Descriptions, preconditions, test steps, and expected results should be clear, concise, and unambiguous.
4.  **Priority**: Assign `High`, `Medium`, or `Low` priority appropriately.
5.  **No Extra Text**: Your entire output must be a valid JSON array. Do not include any introductory or concluding text, explanations, or commentary outside the JSON structure.
6.  **Grouping (Implied by structure)**: While the JSON is a flat array, ensure that related test cases are generated together to reflect logical grouping from the original requirements.

Example of a single test case object:
{{
  "id": 1,
  "title": "Successful Login with Valid Credentials",
  "type": "positive",
  "description": "Verify that a user can log in with correct username and password.",
  "preconditions": "User has a valid account.",
  "testSteps": [
    "Navigate to the login page.",
    "Enter valid username and password.",
    "Click the login button."
  ],
  "expectedResult": "User is redirected to the home page/dashboard.",
  "priority": "High"
}}

Generate the JSON array now:
"""
)

review_prompt = PromptTemplate(
    input_variables=["input_text", "generated_test_cases"],
    template="""
You are a senior QA reviewer. Review the following JSON array of generated test cases for completeness, accuracy, and adherence to the specified JSON format, against the original requirements:

Original requirements: {input_text}

Generated test cases (JSON):
{generated_test_cases}

Think step-by-step:
1. Check if the JSON is well-formed and follows the specified structure (id, title, type, description, preconditions, testSteps, expectedResult, priority).
2. Ensure `id`s are unique and sequential.
3. Verify that all requirements from the `original requirements` are covered by at least one test case.
4. Check for accuracy and relevance of each test case (title, description, steps, expected result) against the original requirements.
5. Identify any missing positive, negative, edge, or boundary cases.
6. Check for consistency in `type` and `priority` assignments.

If any issues are found, provide a concise list of suggested improvements or missing test cases. If significant revisions are needed, provide the corrected JSON array. If the JSON is perfect, state "No revisions needed."
"""
)

test_data_prompt = PromptTemplate(
    input_variables=["input_text", "reviewed_test_cases_json_string"],
    template="""
You are a QA data specialist. Based on the following original requirements and the JSON array of reviewed test cases:

Original requirements: {input_text}

Reviewed test cases (JSON array):
{reviewed_test_cases_json_string}

Your task is to generate a JSON array of objects, where each object represents a distinct functional area or user story.
Each object must strictly adhere to the following structure:
{{
  "user_story": "<Name of the User Story or Functional Area>",
  "test_cases": [
    {{
      "type": "<Positive|Negative|Edge|Boundary>",
      "description": "<The description of the test case>",
      "sample_data": "<Realistic, scenario-appropriate sample data>",
      "notes": "<Brief notes on the expected outcome>"
    }},
    // ... more test case objects for this user story
  ]
}}

Example of the final output format:
[
  {{
    "user_story": "Login Functionality",
    "test_cases": [
      {{
        "type": "Positive",
        "description": "Successful Login with Valid Credentials",
        "sample_data": "User: `user123`, Pass: `Pass@123`",
        "notes": "Redirected to home page/dashboard"
      }},
      {{
        "type": "Negative",
        "description": "Invalid Username Login",
        "sample_data": "User: `wronguser`, Pass: `Pass@123`",
        "notes": "Error message: 'Invalid username'"
      }}
    ]
  }},
  {{
    "user_story": "Password Change Functionality",
    "test_cases": [
      {{
        "type": "Positive",
        "description": "Successful Password Change",
        "sample_data": "Current Pass: `Pass@123`, New Pass: `NewPass123`",
        "notes": "Password changed successfully"
      }}
    ]
  }}
]

Do NOT include any introductory or summary text. Your entire output must be a single, valid JSON array.
Generate the JSON array now:
"""
)



# Chains
validation_chain = LLMChain(llm=llm, prompt=validation_prompt, output_key="validation_result")
generate_chain = LLMChain(llm=llm, prompt=generate_prompt, output_key="generated_test_cases")
review_chain = LLMChain(llm=llm, prompt=review_prompt, output_key="reviewed_test_cases")
test_data_chain = LLMChain(llm=llm, prompt=test_data_prompt, output_key="test_data_table")

def extract_text_from_files(uploaded_files: List[Union[bytes, str]]) -> str:
    extracted_text = []
    print("Extracting text from files...")
    # Ensure uploaded_files is iterable even if it's a single file_storage object
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    for file in uploaded_files:
        try:
            # FastAPI's UploadFile object uses '.file', not '.stream'
            file.file.seek(0) 
            file_name = file.filename.lower()
            print(f"Processing file: {file_name}")
            if file_name.endswith('.pdf'):
                # Pass the file-like object directly
                pdf_reader = PyPDF2.PdfReader(file.file) 
                text = ''.join(page.extract_text() or '' for page in pdf_reader.pages)
            elif file_name.endswith('.docx') or file_name.endswith('.doc'):
                 # Pass the file-like object directly
                doc = Document(file.file)
                text = '\n'.join(para.text for para in doc.paragraphs)
            elif file_name.endswith('.txt'):
                # Read from the file-like object
                text = file.file.read().decode('utf-8')
                print(text)
            else:
                continue
            extracted_text.append(text.strip())
        except Exception as e:
            return f"Error parsing file {file.filename}: {str(e)}"
    return '\n\n'.join(extracted_text) if extracted_text else ''

def get_file_hashes(uploaded_files: List) -> Tuple:
    # ... function content remains the same
    hashes = []
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]
    for file in uploaded_files or []:
        file.stream.seek(0)
        content = file.stream.read()
        file.stream.seek(0)
        hashes.append((file.filename, hashlib.md5(content).hexdigest()))
    return tuple(hashes)


def generate_test_cases(input_text: str, uploaded_files: List = None,model:str=None) -> dict:
    print("Generating test cases...")
    
    MAX_RETRIES = 3
    print(model)
    try:
        file_text = ""
        if uploaded_files:
            file_text = extract_text_from_files(uploaded_files)
            if "Error parsing" in file_text:
                return {"error": file_text}

        combined_input = f"{input_text.strip()}\n\n{file_text.strip()}".strip()

        if not combined_input:
            return {"error": "Please provide input via text or files."}
        

        print("Validating input...")
        try:
            validation_result_str = validation_chain({"input_text": combined_input})["validation_result"]
      
            validation_json = json.loads(validation_result_str)
            if not validation_json.get("is_valid"):
                reason = validation_json.get("reason", "The provided input does not appear to be a valid user story or requirement.")
                print(f"Input validation failed: {reason}")
                return {"error": f"Invalid Input: {reason}"}
        except json.JSONDecodeError:
            print("Warning: Could not parse validation response. Proceeding with generation.")
        
        print("Input validated successfully. Proceeding to generate test cases.")

        # --- TEST CASE GENERATION AND VALIDATION LOOP ---
        parsed_test_cases = None
        cleaned_json_string = ""
        for attempt in range(MAX_RETRIES):
            print(f"Test Case Generation attempt {attempt + 1}...")
            result_gen = generate_chain({"input_text": combined_input})
            llm_output_string = result_gen["generated_test_cases"]

            try:
                cleaned_json_string = re.sub(r',\s*([\]}])', r'\1', llm_output_string)
                parsed_test_cases = json.loads(cleaned_json_string)
                print("Successfully generated and validated test case JSON.")
                break # Exit loop on success
            except json.JSONDecodeError as e:
                print(f"Attempt {attempt + 1} failed: Invalid test case JSON. Error: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {"error": f"Failed to get valid test case JSON after {MAX_RETRIES} attempts.", "raw_output": llm_output_string}

        # --- TEST DATA GENERATION AND VALIDATION LOOP ---
        parsed_test_data = None
        for attempt in range(MAX_RETRIES):
            print(f"Test Data Generation attempt {attempt + 1}...")
            result_data = test_data_chain({
                "input_text": combined_input,
                "reviewed_test_cases_json_string": cleaned_json_string
            })
            test_data_output = result_data["test_data_table"]
            
            try:
                # The LLM output should now be a JSON string, so we parse it directly
                parsed_test_data = json.loads(test_data_output)
                print("Successfully generated and validated test data JSON.")
                break # Exit loop on success
            except json.JSONDecodeError as e:
                print(f"Attempt {attempt + 1} failed: Invalid test data JSON. Error: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {"error": f"Failed to get valid test data JSON after {MAX_RETRIES} attempts.", "raw_output": test_data_output}
        
        # --- RETURN STRUCTURED DATA ---
        return {
            "test_cases": parsed_test_cases,
            "test_data_table": parsed_test_data # This is now a Python object (list of dicts)
        }

    except Exception as e:
        return {"error": f"An unexpected error occurred during generation: {str(e)}"}