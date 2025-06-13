#!/bin/bash

# This script helps to set up an AWS CLI profile (if it doesn't exist)
# and then assume an IAM role, making the temporary credentials available
# in the current shell session via environment variables.

# Usage: source ./assume-aws-role.sh <PROFILE_NAME> <ROLE_ARN>

# --- Input Arguments ---
PROFILE_NAME="$1"
ROLE_ARN="$2"

# --- Configuration ---
# Default values for region and output format if creating a new profile
DEFAULT_REGION="us-east-1" # You can change this to your preferred default AWS region
DEFAULT_OUTPUT_FORMAT="json"

CREDENTIALS_FILE="$HOME/.aws/credentials"
CONFIG_FILE="$HOME/.aws/config"

# --- Function to check if a profile exists ---
# Checks if the profile exists in the credentials file.
# We'll assume if it's in credentials, it's sufficient for this script's purpose.
profile_exists() {
    grep -q "^\[$1\]" "$CREDENTIALS_FILE" 2>/dev/null
}

# --- Initialization Block ---
# Check if arguments are provided
if [ -z "$PROFILE_NAME" ] || [ -z "$ROLE_ARN" ]; then
    echo "Usage: source $0 <PROFILE_NAME> <ROLE_ARN>"
    echo "Example: source $0 my-dev-user-credentials arn:aws:iam::123456789012:role/BedrockAccessRole"
    return 1 # 'return' is used instead of 'exit' because the script is sourced
fi

echo "--- Initializing AWS Profile: $PROFILE_NAME ---"

# Check if the credentials file exists, create if not
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Creating $CREDENTIALS_FILE..."
    mkdir -p "$HOME/.aws"
    touch "$CREDENTIALS_FILE"
    chmod 600 "$CREDENTIALS_FILE" # Set secure permissions
fi

# Check if the config file exists, create if not
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating $CONFIG_FILE..."
    mkdir -p "$HOME/.aws"
    touch "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE" # Set secure permissions
fi

# Check if the profile exists in credentials file
if ! profile_exists "$PROFILE_NAME"; then
    echo "Profile '$PROFILE_NAME' not found in $CREDENTIALS_FILE."
    echo "Please provide credentials to create it."

    read -rp "Enter AWS Access Key ID: " AWS_ACCESS_KEY_ID_INPUT
    read -rp "Enter AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY_INPUT
    read -rp "Enter Default region name (e.g., us-east-1) [$DEFAULT_REGION]: " USER_REGION
    USER_REGION=${USER_REGION:-$DEFAULT_REGION} # Use default if empty
    read -rp "Enter Default output format (e.g., json) [$DEFAULT_OUTPUT_FORMAT]: " USER_OUTPUT
    USER_OUTPUT=${USER_OUTPUT:-$DEFAULT_OUTPUT_FORMAT} # Use default if empty

    # Append to credentials file
    echo "" >> "$CREDENTIALS_FILE"
    echo "[$PROFILE_NAME]" >> "$CREDENTIALS_FILE"
    echo "aws_access_key_id = $AWS_ACCESS_KEY_ID_INPUT" >> "$CREDENTIALS_FILE"
    echo "aws_secret_access_key = $AWS_SECRET_ACCESS_KEY_INPUT" >> "$CREDENTIALS_FILE"

    # Append to config file (or update if already exists)
    # This section removes any existing profile definition and then adds it
    # This is a bit more robust than just appending.
    sed -i "/^\[profile $PROFILE_NAME\]/,/^\[/ { /^\[profile $PROFILE_NAME\]/!b; d }" "$CONFIG_FILE" 2>/dev/null
    sed -i "/^\[profile $PROFILE_NAME\]$//,+3d" "$CONFIG_FILE" 2>/dev/null # Attempt to remove old entry more thoroughly

    echo "" >> "$CONFIG_FILE"
    echo "[profile $PROFILE_NAME]" >> "$CONFIG_FILE"
    echo "region = $USER_REGION" >> "$CONFIG_FILE"
    echo "output = $USER_OUTPUT" >> "$CONFIG_FILE"

    echo "Profile '$PROFILE_NAME' created and configured."
else
    echo "Profile '$PROFILE_NAME' already exists. Using existing configuration."
fi

echo "--- Assuming Role: $ROLE_ARN ---"

# 2. Assume the role using the provided profile
# Using --output text to get a tab-separated string for easy parsing with awk
ASSUME_ROLE_OUTPUT=$(aws sts assume-role \
    --profile "$PROFILE_NAME" \
    --role-arn "$ROLE_ARN" \
    --role-session-name "${PROFILE_NAME}-session" \
    --duration-seconds 3600 \
    --output text 2>&1)

# Check for errors from assume-role command
if echo "$ASSUME_ROLE_OUTPUT" | grep -q "An error occurred"; then
    echo "Error assuming role:"
    echo "$ASSUME_ROLE_OUTPUT"
    echo "Please ensure: "
    echo "  - Your IAM user ('$PROFILE_NAME') has 'sts:AssumeRole' permission on '$ROLE_ARN'."
    echo "  - The trust policy of '$ROLE_ARN' allows assumption by your user."
    echo "  - The profile credentials for '$PROFILE_NAME' are valid."
    return 1
fi

# 3. Parse the output to extract temporary credentials using awk
# The output format for --output text is typically:
# CREDENTIALS    <AccessKeyId>    <SecretAccessKey>    <Expiration>    <SessionToken>
AWS_ACCESS_KEY_ID=$(echo "$ASSUME_ROLE_OUTPUT" | awk '{print $2}')
AWS_SECRET_ACCESS_KEY=$(echo "$ASSUME_ROLE_OUTPUT" | awk '{print $3}')
AWS_SESSION_TOKEN=$(echo "$ASSUME_ROLE_OUTPUT" | awk '{print $5}')

# 4. Export these as environment variables
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN

# 5. Set AWS_PROFILE to the original profile name
# IMPORTANT NOTE ON CREDENTIAL PRECEDENCE:
# When AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN
# environment variables are set, Boto3 (Python SDK) and AWS CLI (v2)
# will prioritize these temporary credentials over any profile set via AWS_PROFILE
# or in the shared credential/config files.
# Setting AWS_PROFILE here is primarily for conceptual clarity or for
# tools that might specifically look for AWS_PROFILE before checking temporary env vars.
export AWS_PROFILE="$PROFILE_NAME"


echo ""
echo "--- Role Assumption Complete ---"
echo "Temporary credentials for role '$ROLE_ARN' have been set as environment variables."
echo "Access Key ID: $AWS_ACCESS_KEY_ID"
echo "Secret Access Key: (hidden for security)"
echo "Session Token: (hidden for security)"
echo "AWS_PROFILE environment variable set to: $AWS_PROFILE (referencing your source profile)"
echo ""
echo "These credentials will expire in 1 hour (3600 seconds) by default."
echo "You can now run AWS CLI commands using these temporary permissions, e.g.:"
echo "aws sts get-caller-identity"
echo "aws bedrock list-foundation-models"
echo ""
echo "To revert to your previous AWS configuration, run:"
echo "unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_PROFILE"
echo "Or open a new terminal session."

