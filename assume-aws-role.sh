#!/bin/bash

# This script helps to:
# 1. Set up an AWS CLI profile for a base IAM user (if it doesn't exist).
# 2. Configure a *new* profile in ~/.aws/config that automatically assumes an IAM role.
# 3. Sets the AWS_PROFILE environment variable to this new role-assuming profile.

# Usage: source ./assume-aws-role-config.sh <BASE_IAM_USER_PROFILE_NAME> <ROLE_ARN_TO_ASSUME>

# --- Input Arguments ---
BASE_IAM_USER_PROFILE_NAME="$1"
ROLE_ARN_TO_ASSUME="$2"

# --- Configuration ---
# Default values for region and output format if creating a new profile
DEFAULT_REGION="us-east-1" # You can change this to your preferred default AWS region
DEFAULT_OUTPUT_FORMAT="json"

# The name of the new profile that will assume the role
# This profile will be configured in ~/.aws/config
ROLE_ASSUMING_PROFILE_NAME="bedrock-role-access"

CREDENTIALS_FILE="$HOME/.aws/credentials"
CONFIG_FILE="$HOME/.aws/config"

# --- Function to check if a profile exists in credentials file ---
profile_exists_in_credentials() {
    grep -q "^\[$1\]" "$CREDENTIALS_FILE" 2>/dev/null
}

# --- Function to update or add a profile section in config file ---
# This function is more robust for updating existing sections
update_config_profile() {
    local profile_name="$1"
    local config_key="$2"
    local config_value="$3"

    # Remove existing line for the key within the profile section
    # and then add the new line. This avoids duplicates and updates correctly.
    sed -i "/^\[profile $profile_name\]/,/^\[/ { /$config_key =/d }" "$CONFIG_FILE" 2>/dev/null
    sed -i "/^\[profile $profile_name\]/a $config_key = $config_value" "$CONFIG_FILE"
}

# --- Initialization Block ---
# Check if arguments are provided
if [ -z "$BASE_IAM_USER_PROFILE_NAME" ] || [ -z "$ROLE_ARN_TO_ASSUME" ]; then
    echo "Usage: source $0 <BASE_IAM_USER_PROFILE_NAME> <ROLE_ARN_TO_ASSUME>"
    echo "Example: source $0 my-dev-user-credentials arn:aws:iam::123456789012:role/BedrockAccessRole"
    return 1 # 'return' is used instead of 'exit' because the script is sourced
fi

echo "--- Setting up Base IAM User Profile: $BASE_IAM_USER_PROFILE_NAME ---"

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

# Check if the base IAM user profile exists in credentials file
if ! profile_exists_in_credentials "$BASE_IAM_USER_PROFILE_NAME"; then
    echo "Profile '$BASE_IAM_USER_PROFILE_NAME' not found in $CREDENTIALS_FILE."
    echo "Please provide credentials to create it."

    read -rp "Enter AWS Access Key ID for '$BASE_IAM_USER_PROFILE_NAME': " AWS_ACCESS_KEY_ID_INPUT
    read -rp "Enter AWS Secret Access Key for '$BASE_IAM_USER_PROFILE_NAME': " AWS_SECRET_ACCESS_KEY_INPUT
    read -rp "Enter Default region name (e.g., us-east-1) [$DEFAULT_REGION]: " USER_REGION
    USER_REGION=${USER_REGION:-$DEFAULT_REGION} # Use default if empty
    read -rp "Enter Default output format (e.g., json) [$DEFAULT_OUTPUT_FORMAT]: " USER_OUTPUT
    USER_OUTPUT=${USER_OUTPUT:-$DEFAULT_OUTPUT_FORMAT} # Use default if empty

    # Append to credentials file
    echo "" >> "$CREDENTIALS_FILE"
    echo "[$BASE_IAM_USER_PROFILE_NAME]" >> "$CREDENTIALS_FILE"
    echo "aws_access_key_id = $AWS_ACCESS_KEY_ID_INPUT" >> "$CREDENTIALS_FILE"
    echo "aws_secret_access_key = $AWS_SECRET_ACCESS_KEY_INPUT" >> "$CREDENTIALS_FILE"

    echo "Profile '$BASE_IAM_USER_PROFILE_NAME' created in $CREDENTIALS_FILE."
else
    echo "Profile '$BASE_IAM_USER_PROFILE_NAME' already exists in $CREDENTIALS_FILE. Using existing configuration."
    # If the profile exists, still ensure it has a region and output in config file
    # Get region from existing config if possible, otherwise use default
    USER_REGION=$(grep -A 2 "^\[profile $BASE_IAM_USER_PROFILE_NAME\]" "$CONFIG_FILE" | grep "region =" | awk '{print $3}' | head -n 1)
    USER_REGION=${USER_REGION:-$DEFAULT_REGION}
    USER_OUTPUT=$(grep -A 2 "^\[profile $BASE_IAM_USER_PROFILE_NAME\]" "$CONFIG_FILE" | grep "output =" | awk '{print $3}' | head -n 1)
    USER_OUTPUT=${USER_OUTPUT:-$DEFAULT_OUTPUT_FORMAT}
fi


echo "--- Configuring Role Assumption Profile: $ROLE_ASSUMING_PROFILE_NAME ---"

# Add or update the role-assuming profile section in ~/.aws/config
# First, remove existing section to ensure clean update
sed -i "/^\[profile $ROLE_ASSUMING_PROFILE_NAME\]/,/^\[/ { /^\[profile $ROLE_ASSUMING_PROFILE_NAME\]/!b; d }" "$CONFIG_FILE" 2>/dev/null
sed -i "/^\[profile $ROLE_ASSUMING_PROFILE_NAME\]$//,+3d" "$CONFIG_FILE" 2>/dev/null # More thorough removal

echo "" >> "$CONFIG_FILE"
echo "[profile $ROLE_ASSUMING_PROFILE_NAME]" >> "$CONFIG_FILE"
echo "role_arn = $ROLE_ARN_TO_ASSUME" >> "$CONFIG_FILE"
echo "source_profile = $BASE_IAM_USER_PROFILE_NAME" >> "$CONFIG_FILE"
echo "region = $USER_REGION" >> "$CONFIG_FILE" # Use the region from the base profile or default
echo "output = $USER_OUTPUT" >> "$CONFIG_FILE" # Use the output from the base profile or default

echo "Configured role-assuming profile '$ROLE_ASSUMING_PROFILE_NAME' in $CONFIG_FILE."

# 3. Export AWS_PROFILE to point to the new role-assuming profile
export AWS_PROFILE="$ROLE_ASSUMING_PROFILE_NAME"

echo ""
echo "--- Setup Complete ---"
echo "Your AWS CLI and Boto3 will now use the profile: '$ROLE_ASSUMING_PROFILE_NAME'"
echo "This profile is configured to automatically assume the role: '$ROLE_ARN_TO_ASSUME'"
echo "using credentials from your base IAM user profile: '$BASE_IAM_USER_PROFILE_NAME'."
echo ""
echo "You can now run AWS CLI commands directly, for example:"
echo "aws sts get-caller-identity"
echo "aws bedrock list-foundation-models"
echo ""
echo "Boto3 (Python SDK) will also automatically use this configuration."
echo "Example Python code (after sourcing this script):"
echo "import boto3"
echo "bedrock_runtime_client = boto3.client('bedrock-runtime')"
echo "response = bedrock_runtime_client.list_foundation_models()"
echo ""
echo "To revert to your previous AWS profile, run:"
echo "unset AWS_PROFILE"
echo "Or open a new terminal session."

