#! /usr/bin/env bash

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install gcloud
curl -LsSf https://sdk.cloud.google.com | bash

# Install Dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install --install-hooks

# gcloud auth login application-default
gcloud auth application-default login
