#!/bin/bash

set -eu

/action/autofill_readme.py \
  --github-api-url "$GITHUB_API_URL" \
  --github-repository "$GITHUB_REPOSITORY" \
  --github-token "$INPUT_GITHUB_TOKEN" \
  --openai-api-key "$INPUT_OPENAI_API_KEY" \
  --azure-openai-api-key "$INPUT_AZURE_OPENAI_API_KEY" \
  --azure-openai-endpoint "$INPUT_AZURE_OPENAI_ENDPOINT" \
  --azure-openai-version "$INPUT_AZURE_OPENAI_VERSION" \

