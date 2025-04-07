#!/usr/bin/env python3
import sys
import requests
import argparse
import os
import base64

SAMPLE_PROMPT = """
Write a README file that contains the following sections:
- repository name
- overview (what is this repository about)
- List of features
- How to run the project, instructions (typically cloning the repository and running it, have a look at the .vscode directory)
- Testing instructions (how to run the tests; if there are any)
- How to contribute to the project
- License
"""

GOOD_SAMPLE_RESPONSE = """
# cedricve/llm-generated-readme

## Overview
This project is designed to provide a comprehensive and user-friendly README template for your projects, generated using a language model. It aims to help developers quickly set up, understand, and contribute to their repositories with ease.

## List of Features
- **Automated README Generation**: Generate a detailed README file with essential sections for your repository.
- **Clear Instructions**: Provides clear instructions on how to run the project and tests.
- **Contribution Guidelines**: Offers guidelines on how to contribute to the project effectively.
- **License Information**: Includes license details to ensure proper use and distribution.

## How to Run the Project
To run the project, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/cedricve/llm-generated-readme.git
   cd llm-generated-readme
   ```

3. **Run the Project**:
    ```bash
    python main.py
    ```

## Testing Instructions
To run the tests for the project, follow these steps:

1. **Navigate to the Tests Directory**:
   ```bash
   cd tests
   ```

2. **Run the Tests**:
   Use the following command to run the tests:
   ```bash
   python -m unittest discover
   ```

## How to Contribute to the Project
We welcome contributions to the `cedricve/llm-generated-readme` project! To contribute, please follow these guidelines:

1. **Fork the Repository**:
   Click the "Fork" button on the repository page to create a copy of the repository in your GitHub account.

2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/llm-generated-readme.git
   cd llm-generated-readme
   ```

3. **Create a New Branch**:
   ```bash
   git checkout -b feature-branch
   ```

4. **Make Your Changes**:
   Implement your changes or additions.

5. **Commit and Push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature-branch
   ```

6. **Create a Pull Request**:
   Navigate to the original repository and click "New Pull Request". Provide a detailed description of your changes and submit the pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
"""

COMPLETION_PROMPT = f"""
Write a README file focusing on the motivation behind the entire repository and why it improves the project.
Go straight to the point. The following files are included in the repository: \n
"""

def main():

    parser = argparse.ArgumentParser(
        description="Use ChatGPT to generate a description for a pull request."
    )
    parser.add_argument(
        "--github-api-url", type=str, required=True, help="The GitHub API URL"
    )
    parser.add_argument(
        "--github-repository", type=str, required=True, help="The GitHub repository"
    )
    parser.add_argument(
        "--github-token",
        type=str,
        required=True,
        help="The GitHub token",
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        required=True,
        help="The OpenAI API key",
    )
    parser.add_argument(
        "--azure-openai-api-key",
        type=str,
        required=True,
        help="The Azure OpenAI API key",
    )
    parser.add_argument(
        "--azure-openai-endpoint",
        type=str,
        required=True,
        help="The Azure OpenAI endpoint",
    )
    parser.add_argument(
        "--azure-openai-version",
        type=str,
        required=True,
        help="The Azure OpenAI API version",
    )
    parser.add_argument(
        "--allowed-users",
        type=str,
        required=False,
        help="A comma-separated list of GitHub usernames that are allowed to trigger the action, empty or missing means all users are allowed",
    )
    args = parser.parse_args()

    github_api_url = args.github_api_url
    repo = args.github_repository
    github_token = args.github_token
    openai_api_key = args.openai_api_key
    azure_openai_api_key = args.azure_openai_api_key
    azure_openai_endpoint = args.azure_openai_endpoint
    azure_openai_version = args.azure_openai_version

    allowed_users = os.environ.get("INPUT_ALLOWED_USERS", "")
    if allowed_users:
        allowed_users = allowed_users.split(",")

    open_ai_model = "gpt-4o"  # os.environ.get("INPUT_OPENAI_MODEL", "gpt-4o")
    max_prompt_tokens = int(os.environ.get("INPUT_MAX_TOKENS", "1000"))
    model_temperature = float(os.environ.get("INPUT_TEMPERATURE", "0.6"))
    model_sample_prompt = os.environ.get(
        "INPUT_MODEL_SAMPLE_PROMPT", SAMPLE_PROMPT)
    model_sample_response = os.environ.get(
        "INPUT_MODEL_SAMPLE_RESPONSE", GOOD_SAMPLE_RESPONSE
    )
    completion_prompt = os.environ.get(
        "INPUT_COMPLETION_PROMPT", COMPLETION_PROMPT)
    authorization_header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": "token %s" % github_token,
    }

    # Get all files in the main branch
    repo_contents_url = f"{github_api_url}/repos/{repo}/contents"
    files = []

    def fetch_files(url):
        response = requests.get(url, headers=authorization_header)
        if response.status_code != 200:
            print(f"Failed to fetch files: {response.status_code}, {response.text}")
            return 
        items = response.json()
        for item in items:
            if item["type"] == "file":
                files.append(item["path"])
            elif item["type"] == "dir":
                fetch_files(item["url"])

    fetch_files(repo_contents_url)

    # Filter out .git, .devcontainer, .github, .venv, *.yml, Dockerfile, and .env files or directories
    files = [
        file for file in files
        if not (
            file.startswith(".git")
            or file.startswith(".devcontainer")
            or file.startswith(".github")
            or file.startswith(".venv")
            or file.endswith(".yml")
            or file.endswith("Dockerfile")
            or file.endswith(".env")
        )
    ]

    print(f"Files to process: {files}")

    decoded_files = []
    for file in files:
        # Get the content of the file
        file_url = f"{github_api_url}/repos/{repo}/contents/{file}"
        file_response = requests.get(file_url, headers=authorization_header)
        if file_response.status_code != 200:
            print(f"Failed to fetch file: {file_response.status_code}, {file_response.text}")
            continue
        file_content = file_response.json()
        file_content_decoded = base64.b64decode(file_content["content"]).decode("utf-8")
        decoded_files.append(file_content_decoded)

    # Extract functions from the files
    for file in decoded_files:
        # Extract functions from the file content
        lines = file.split("\n")
        for index, line in enumerate(lines):
            # for Python, we can use the keyword 'def' to identify functions
            if line.strip().startswith("def "):
                function_name = line.strip().split("(")[0][4:]
                completion_prompt += f"Function: {function_name}\n"

            # for Golang, we can use the keyword 'func' to identify functions
            elif line.strip().startswith("func "):
                function_name = line.strip().split("(")[0][5:]
                completion_prompt += f"Function: {function_name}\n"

    print(f"Completion prompt: {completion_prompt}")

    max_allowed_tokens = 8000
    characters_per_token = 4  # The average number of characters per token
    max_allowed_characters = max_allowed_tokens * characters_per_token
    if len(completion_prompt) > max_allowed_characters:
        completion_prompt = completion_prompt[:max_allowed_characters]

    generated_pr_description = ""
    if openai_api_key != "":
        openai_client = openai.OpenAI(api_key=openai_api_key)
        openai_response = openai_client.chat.completions.create(
            model=open_ai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant who writes a readmme file",
                },
                {"role": "user", "content": model_sample_prompt},
                {"role": "assistant", "content": model_sample_response},
                {
                    "role": "user",
                    "content": "Title of the readme file: " + repo,
                },
                {"role": "user", "content": completion_prompt},
            ],
            temperature=model_temperature,
            max_tokens=max_prompt_tokens,
        )
        generated_pr_description = openai_response.choices[0].message.content

    elif azure_openai_api_key != "":
        azure_openai_client = AzureOpenAI(
            api_key=azure_openai_api_key,
            azure_endpoint=azure_openai_endpoint,
            api_version=azure_openai_version
        )
        azure_openai_response = azure_openai_client.chat.completions.create(
            model=open_ai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant who writes a readmme file",
                },
                {"role": "user", "content": model_sample_prompt},
                {"role": "assistant", "content": model_sample_response},
                {
                    "role": "user",
                    "content": "Title of the readme file: " + repo,
                },
                {"role": "user", "content": completion_prompt},
            ],
            temperature=model_temperature,
            max_tokens=max_prompt_tokens,
        )
        generated_pr_description = azure_openai_response.choices[0].message.content

    # Get SHA of the main branch
    branches_url = f"{github_api_url}/repos/{repo}/branches"
    branches_response = requests.get(branches_url, headers=authorization_header)
    if branches_response.status_code != 200:
        print(f"Failed to fetch branches: {branches_response.status_code}, {branches_response.text}")
        return
    branches = branches_response.json()
    main_branch_sha = None
    for branch in branches:
        if branch["name"] == "main":
            main_branch_sha = branch["commit"]["sha"]
            break
    if main_branch_sha is None:
        print("Main branch not found")
        return
    print(f"Main branch SHA: {main_branch_sha}")

    # Create a new branch for the pull request
    branch_name = "feature/add-readme-file"
    branch_url = f"{github_api_url}/repos/{repo}/git/refs"
    branch_data = {
        "ref": f"refs/heads/{branch_name}",
        "sha": main_branch_sha,
    }
    branch_response = requests.post(branch_url, headers=authorization_header, json=branch_data)
    if branch_response.status_code != 201:
        print(f"Failed to create branch: {branch_response.status_code}, {branch_response.text}")
        return
    branch_sha = branch_response.json()["object"]["sha"]
    print(f"Branch created: {branch_name}")

    # Create a new file in the new branch
    file_path = "README.md"
    file_url = f"{github_api_url}/repos/{repo}/contents/{file_path}"
    file_data = {
        "message": "Add README file",
        "content": base64.b64encode(generated_pr_description.encode("utf-8")).decode("utf-8"),
        "branch": branch_name,
    }
    file_response = requests.put(file_url, headers=authorization_header, json=file_data)
    if file_response.status_code != 201:
        print(f"Failed to create file: {file_response.status_code}, {file_response.text}")
        return
    file_sha = file_response.json()["content"]["sha"]
    print(f"File created: {file_path}")

    # We will create a new pull request with the generated description in a new README.md file
    pr_title = f"Add README file for {repo}"
    pr_body = generated_pr_description
    pr_branch = "feature/add-readme-file"
    pr_base = "main"
    pr_head = pr_branch
    pr_url = f"{github_api_url}/repos/{repo}/pulls"
    pr_data = {
        "title": pr_title,
        "body": pr_body,
        "head": pr_head,
        "base": pr_base,
    }
    pr_response = requests.post(pr_url, headers=authorization_header, json=pr_data)
    if pr_response.status_code != 201:
        print(f"Failed to create pull request: {pr_response.status_code}, {pr_response.text}")
        return
    pr_number = pr_response.json()["number"]
    pr_url = pr_response.json()["html_url"]
    print(f"Pull request created: {pr_url}")
    
if __name__ == "__main__":
    sys.exit(main())
