# AWS Bedrock Llama Setup Guide

## Overview
AWS Bedrock provides access to foundation models including Meta's Llama models. This guide helps you set up Bedrock with your TripBot application.

## Prerequisites
- AWS Account with Bedrock access
- IAM permissions for Bedrock operations
- Enabled foundation models in your AWS region

## Step 1: AWS Account Setup

### Enable Bedrock Access
1. Log into AWS Console
2. Navigate to Amazon Bedrock service
3. Select "Model access" in the left sidebar
4. Request access to Meta Llama models:
   - Llama 2 Chat 13B
   - Llama 2 Chat 70B
   - Or other available Llama variants
5. Wait for approval (usually immediate for most regions)

## Step 2: IAM Configuration

### Create IAM User
1. Navigate to IAM → Users → Create User
2. User name: `tripbot-bedrock-user`
3. Select "Provide user access to the AWS Management Console" (optional)

### Attach Policies
Create a custom policy with these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": "*"
        }
    ]
}
```

### Generate Access Keys
1. Select your user
2. Go to "Security credentials" tab
3. Create access key → Application running outside AWS
4. Download the CSV or copy the keys

## Step 3: Environment Configuration

Add these variables to your `.env` file:
```bash
AWS_ACCESS_KEY_ID=AKIA...your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=us-east-1
```

## Step 4: Configure TripBot

### Set Preferred LLM
In `routes.py`, change the initialization:
```python
trip_bot = TripPlannerBot(preferred_llm="bedrock")
```

### Available Bedrock Models
The adapter supports these Llama model IDs:
- `meta.llama2-13b-chat-v1` (default)
- `meta.llama2-70b-chat-v1` (more capable, higher cost)
- `meta.llama3-8b-instruct-v1` (if available)
- `meta.llama3-70b-instruct-v1` (if available)

To change the model, edit `llm_adapters.py`:
```python
model_id = "meta.llama2-70b-chat-v1"  # Change this line
```

## Regional Availability

Bedrock is available in these regions:
- us-east-1 (N. Virginia) - Recommended
- us-west-2 (Oregon)
- ap-southeast-1 (Singapore)
- eu-west-1 (Ireland)

Check AWS documentation for the latest regional availability.

## Cost Considerations

Bedrock pricing is pay-per-use:
- Input tokens: ~$0.00065 per 1K tokens
- Output tokens: ~$0.0026 per 1K tokens

For a typical trip planning conversation (10-15 exchanges), expect costs under $0.10.

## Troubleshooting

### Common Issues

**"No credentials found"**
- Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set
- Check the IAM user has proper permissions

**"Access denied to model"**
- Ensure model access is granted in Bedrock console
- Verify IAM policy includes bedrock:InvokeModel permission

**"Model not found"**
- Check if the model ID is available in your region
- Some models require additional approval

### Testing Connection
```bash
# Test AWS credentials
aws bedrock list-foundation-models --region us-east-1

# If AWS CLI is not installed, the application will show connection status in logs
```

## Security Best Practices

1. **Least Privilege**: Only grant necessary Bedrock permissions
2. **Key Rotation**: Regularly rotate access keys
3. **Environment Variables**: Never commit keys to version control
4. **Region Selection**: Use regions closest to your users
5. **Monitoring**: Enable CloudTrail for API call logging

## Integration Benefits

- **No API Limits**: Unlike OpenAI/Gemini, no rate limiting
- **Data Privacy**: Requests don't leave AWS infrastructure
- **Model Variety**: Access to multiple Llama variants
- **Enterprise Features**: VPC endpoints, encryption, compliance
- **Cost Control**: Pay only for actual usage

Your TripBot now supports three AI providers for maximum reliability and flexibility!
