#!/bin/bash

# --- Configuration Variables ---
IAM_USER_NAME="TravelBotUser"
IAM_ROLE_NAME="BedrockAccessRole"
AWS_PROFILE_NAME="travelBot"
TRUST_POLICY_TEMPLATE="trust-policy-template.json" # New template file
TRUST_POLICY_FILE="trust-policy.json"             # Generated file from template
REGION="us-east-1" # You can change this to your desired AWS region

echo "Starting AWS TravelBot setup..."

# --- 1. Get AWS Account ID ---
echo "Retrieving AWS Account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: Could not retrieve AWS Account ID. Ensure AWS CLI is configured and authenticated."
    exit 1
fi
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# --- 2. Prepare the Trust Policy file from template ---
# Reads the template, replaces the placeholder, and saves to a new file.
echo "Preparing trust policy file from template: $TRUST_POLICY_TEMPLATE..."
if [ ! -f "$TRUST_POLICY_TEMPLATE" ]; then
    echo "Error: Trust policy template file '$TRUST_POLICY_TEMPLATE' not found."
    echo "Please ensure '$TRUST_POLICY_TEMPLATE' is in the same directory as the script."
    exit 1
fi

sed "s/<YOUR_AWS_ACCOUNT_ID_PLACEHOLDER>/${AWS_ACCOUNT_ID}/g; s/<IAM_USER_NAME_PLACEHOLDER>/${IAM_USER_NAME}/g" "$TRUST_POLICY_TEMPLATE" > "$TRUST_POLICY_FILE"

# --- 3. Create the IAM Role for Bedrock Access ---
echo "Creating IAM Role: $IAM_ROLE_NAME with trust policy from $TRUST_POLICY_FILE..."
CREATE_ROLE_OUTPUT=$(aws iam create-role \
    --role-name "$IAM_ROLE_NAME" \
    --assume-role-policy-document "file://${TRUST_POLICY_FILE}" \
    --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    if echo "$CREATE_ROLE_OUTPUT" | grep -q "EntityAlreadyExists"; then
        echo "IAM Role '$IAM_ROLE_NAME' already exists. Skipping creation."
        # If the role already exists, we need to get its ARN
        IAM_ROLE_ARN=$(aws iam get-role --role-name "$IAM_ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null)
        if [ -z "$IAM_ROLE_ARN" ]; then
            echo "Error: Role '$IAM_ROLE_NAME' exists but could not retrieve its ARN. Please check permissions."
            rm -f "$TRUST_POLICY_FILE" # Clean up generated trust policy
            exit 1
        fi
    else
        echo "Error creating IAM Role '$IAM_ROLE_NAME'."
        echo "$CREATE_ROLE_OUTPUT"
        rm -f "$TRUST_POLICY_FILE" # Clean up generated trust policy
        exit 1
    fi
else
    IAM_ROLE_ARN=$(echo "$CREATE_ROLE_OUTPUT" | jq -r '.Role.Arn')
    echo "IAM Role '$IAM_ROLE_NAME' created successfully."
fi

echo "IAM Role ARN: $IAM_ROLE_ARN"

# --- 4. Attach Bedrock Full Access Policy to the Role ---
# Using the AWS managed policy for Bedrock full access.
# Note: The Bedrock policy itself is an AWS managed policy, so its content doesn't need to be in a separate file.
# We just reference its ARN.
BEDROCK_POLICY_ARN="arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
echo "Attaching policy '$BEDROCK_POLICY_ARN' to role '$IAM_ROLE_NAME'..."
ATTACH_POLICY_OUTPUT=$(aws iam attach-role-policy \
    --role-name "$IAM_ROLE_NAME" \
    --policy-arn "$BEDROCK_POLICY_ARN" 2>&1)

if [ $? -ne 0 ]; then
    if echo "$ATTACH_POLICY_OUTPUT" | grep -q "NoSuchEntityException"; then
        echo "Warning: Policy '$BEDROCK_POLICY_ARN' not found. This might indicate an issue with your AWS environment or policy name."
    elif echo "$ATTACH_POLICY_OUTPUT" | grep -q "LimitExceededException"; then
        echo "Warning: Cannot attach policy to role. Limit exceeded."
    elif echo "$ATTACH_POLICY_OUTPUT" | grep -q "InvalidInputException"; then
        echo "Warning: Invalid input when attaching policy. Check policy ARN or role name."
    else
        echo "Error attaching policy to role '$IAM_ROLE_NAME'."
        echo "$ATTACH_POLICY_OUTPUT"
        # Not exiting here as user creation might still be useful
    fi
else
    echo "Policy '$BEDROCK_POLICY_ARN' attached to role '$IAM_ROLE_NAME' successfully."
fi

# --- 5. Create the IAM User ---
echo "Creating IAM User: $IAM_USER_NAME..."
CREATE_USER_OUTPUT=$(aws iam create-user \
    --user-name "$IAM_USER_NAME" \
    --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    if echo "$CREATE_USER_OUTPUT" | grep -q "EntityAlreadyExists"; then
        echo "IAM User '$IAM_USER_NAME' already exists. Skipping creation."
    else
        echo "Error creating IAM User '$IAM_USER_NAME'."
        echo "$CREATE_USER_OUTPUT"
        rm -f "$TRUST_POLICY_FILE" # Clean up generated trust policy
        exit 1
    fi
else
    echo "IAM User '$IAM_USER_NAME' created successfully."
fi

# --- 6. Create Access Keys for the IAM User ---
echo "Creating access keys for '$IAM_USER_NAME'..."
CREATE_ACCESS_KEY_OUTPUT=$(aws iam create-access-key \
    --user-name "$IAM_USER_NAME" \
    --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "Error creating access keys for '$IAM_USER_NAME'."
    echo "$CREATE_ACCESS_KEY_OUTPUT"
    rm -f "$TRUST_POLICY_FILE" # Clean up generated trust policy
    exit 1
fi

ACCESS_KEY_ID=$(echo "$CREATE_ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$CREATE_ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.SecretAccessKey')

echo ""
echo "--- IMPORTANT: SAVE THESE CREDENTIALS NOW ---"
echo "IAM User Access Key ID:     $ACCESS_KEY_ID"
echo "IAM User Secret Access Key: $SECRET_ACCESS_KEY"
echo "----------------------------------------------"
echo ""

# --- 7. Configure AWS CLI Profile for the IAM User's credentials (source profile) ---
# This profile will hold the direct credentials of the IAM user.
echo "Configuring AWS CLI source profile '${IAM_USER_NAME}-credentials'..."
aws configure set aws_access_key_id "$ACCESS_KEY_ID" --profile "${IAM_USER_NAME}-credentials"
aws configure set aws_secret_access_key "$SECRET_ACCESS_KEY" --profile "${IAM_USER_NAME}-credentials"
aws configure set region "$REGION" --profile "${IAM_USER_NAME}-credentials"
aws configure set output json --profile "${IAM_USER_NAME}-credentials"

# --- 8. Configure AWS CLI Profile to Assume the Role ---
# This creates the 'travelBot' profile that will assume the BedrockAccessRole
echo "Configuring AWS CLI profile '$AWS_PROFILE_NAME' to assume role '$IAM_ROLE_NAME'..."

# Append to ~/.aws/config or create it if it doesn't exist
CONFIG_FILE="$HOME/.aws/config"
if [ ! -f "$CONFIG_FILE" ]; then
    touch "$CONFIG_FILE"
fi

# Check if profile already exists and remove if it does to prevent duplicates
sed -i "/^\[profile ${AWS_PROFILE_NAME}\]/,/^\[/ { /^\[profile ${AWS_PROFILE_NAME}\]/!b; d }" "$CONFIG_FILE"
sed -i "/^\[profile ${AWS_PROFILE_NAME}\]$/,+3d" "$CONFIG_FILE" # Remove header and next 3 lines if found

cat <<EOF >> "$CONFIG_FILE"

[profile ${AWS_PROFILE_NAME}]
role_arn = ${IAM_ROLE_ARN}
source_profile = ${IAM_USER_NAME}-credentials
region = ${REGION}
output = json
EOF

echo ""
echo "--- Setup Complete ---"
echo "IAM User '$IAM_USER_NAME' created."
echo "IAM Role '$IAM_ROLE_NAME' with Bedrock access created."
echo "Role ARN (for EC2, ECS, EKS usage): $IAM_ROLE_ARN"
echo "AWS CLI profile '${AWS_PROFILE_NAME}' configured."
echo ""
echo "To use the 'travelBot' profile (which assumes the BedrockAccessRole), run:"
echo "aws --profile ${AWS_PROFILE_NAME} sts get-caller-identity"
echo "Then, you can use any AWS CLI command with this profile, e.g.:"
echo "aws --profile ${AWS_PROFILE_NAME} bedrock list-foundation-models"
echo ""

# --- Cleanup ---
rm -f "$TRUST_POLICY_FILE" # Clean up generated trust policy
echo "Temporary file '$TRUST_POLICY_FILE' removed."
