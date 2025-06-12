import json
from pathlib import Path

def extract_conversation(input_file, output_file):
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract messages from the first conversation
    messages = data[0] if data else []
    
    # Prepare the output content
    output = []
    
    for msg in messages:
        if msg.get('source') == 1:  # User input
            content = ' '.join(part['text'] for part in msg['content'] if part['type'] == 'text')
            output.append(f"USER: {content}")
        elif msg.get('source') == 2:  # Model response
            content = ' '.join(part['text'] for part in msg['content'] if part['type'] == 'text')
            output.append(f"MODEL: {content}")
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(output))

if __name__ == "__main__":
    input_file = 'playground.json'
    output_file = 'conversation_log.txt'
    extract_conversation(input_file, output_file)
    print(f"Conversation extracted and saved to {output_file}")
