#!/usr/bin/env python3
import sys
import requests
import argparse
import json
import openai
from openai import AzureOpenAI
import os
import base64

SAMPLE_PROMPT = """
Write a pull request description focusing on the motivation behind the change and why it improves the project.
Go straight to the point.

The title of the pull request is "Enable valgrind on CI" and the following changes took place:

Changes in file .github/workflows/build-ut-coverage.yml: @@ -24,6 +24,7 @@ jobs:
         run: |
           sudo apt-get update
           sudo apt-get install -y lcov
+          sudo apt-get install -y valgrind
           sudo apt-get install -y ${{ matrix.compiler.cc }}
           sudo apt-get install -y ${{ matrix.compiler.cxx }}
       - name: Checkout repository
@@ -48,3 +49,7 @@ jobs:
         with:
           files: coverage.info
           fail_ci_if_error: true
+      - name: Run valgrind
+        run: |
+          valgrind --tool=memcheck --leak-check=full --leak-resolution=med \
+            --track-origins=yes --vgdb=no --error-exitcode=1 ${build_dir}/test/command_parser_test
Changes in file test/CommandParserTest.cpp: @@ -566,7 +566,7 @@ TEST(CommandParserTest, ParsedCommandImpl_WhenArgumentIsSupportedNumericTypeWill
     unsigned long long expectedUnsignedLongLong { std::numeric_limits<unsigned long long>::max() };
     float expectedFloat { -164223.123f }; // std::to_string does not play well with floating point min()
     double expectedDouble { std::numeric_limits<double>::max() };
-    long double expectedLongDouble { std::numeric_limits<long double>::max() };
+    long double expectedLongDouble { 123455678912349.1245678912349L };

     auto command = UnparsedCommand::create(expectedCommand, "dummyDescription"s)
                        .withArgs<int, long, unsigned long, long long, unsigned long long, float, double, long double>();
"""

GOOD_SAMPLE_RESPONSE = """
Currently, our CI build does not include Valgrind as part of the build and test process. Valgrind is a powerful tool for detecting memory errors, and its use is essential for maintaining the integrity of our project.
This pull request adds Valgrind to the CI build, so that any memory errors will be detected and reported immediately. This will help to prevent undetected memory errors from making it into the production build.

Overall, this change will improve the quality of the project by helping us detect and prevent memory errors.
"""

COMPLETION_PROMPT = f"""
Write a pull request description focusing on the motivation behind the change and why it improves the project.
Go straight to the point. The following changes took place: \n
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
        "--pull-request-id",
        type=int,
        required=True,
        help="The pull request ID",
    )
    parser.add_argument(
        "--pull-request-url",
        type=str,
        required=True,
        help="The pull request URL",
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
    pull_request_id = args.pull_request_id
    pull_request_url = args.pull_request_url
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

    # Filter out .git, .devcontainer, .github, .venv, *.yml, Dockerfile, and .env files
    files = [
        file for file in files
        if not (
            file.endswith(".git")
            or file.endswith(".devcontainer")
            or file.endswith(".github")
            or file.endswith(".venv")
            or file.endswith(".yml")
            or file.endswith("Dockerfile")
            or file.endswith(".env")
        )
    ]

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
                # Get first 10 lines of the function
                function_lines = lines[index:index+100]
                completion_prompt += f"Function lines: {function_lines}\n"

            # for Golang, we can use the keyword 'func' to identify functions
            elif line.strip().startswith("func "):
                function_name = line.strip().split("(")[0][5:]
                completion_prompt += f"Function: {function_name}\n"
                function_lines = lines[index:index+100]
                completion_prompt += f"Function lines: {function_lines}\n"

    print(f"Completion prompt: {completion_prompt}")


    #completion_prompt += f"Changes in file {filename}: {patch}\n"
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

    redundant_prefix = "This pull request "
    if generated_pr_description.startswith(redundant_prefix):
        generated_pr_description = generated_pr_description[len(
            redundant_prefix):]
        generated_pr_description = (
            generated_pr_description[0].upper() + generated_pr_description[1:]
        )
    print(f"Generated pull request description: '{generated_pr_description}'")

    title = "## Description\n\n"
    generated_pr_description = title + generated_pr_description

    # We will prepend the pull_request_url.
    if pull_request_url != "":
        pull_request_url = f"Access the Pull Request environment [here]({pull_request_url})\n\n"
        generated_pr_description = pull_request_url + generated_pr_description
        title = "## Live Environment\n\n"
        generated_pr_description = title + generated_pr_description

    issues_url = "%s/repos/%s/issues/%s" % (
        github_api_url,
        repo,
        pull_request_id,
    )
    update_pr_description_result = requests.patch(
        issues_url,
        headers=authorization_header,
        json={"body": generated_pr_description},
    )

    if update_pr_description_result.status_code != requests.codes.ok:
        print(
            "Request to update pull request description failed: "
            + str(update_pr_description_result.status_code)
        )
        print("Response: " + update_pr_description_result.text)
        return 1


if __name__ == "__main__":
    sys.exit(main())
