import debugpy
debugpy.listen(("0.0.0.0", 5678))
debugpy.wait_for_client()
import json
import os
from langchain_aws import BedrockLLM
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain


# Local embeddings for both agents
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def load_or_create_db(name):
    path = f"{name}_memory"
    if os.path.exists(path):
        return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    texts = ["",name]
    return FAISS.from_texts(texts, embeddings)

airline_memory = load_or_create_db("airline")
payment_memory = load_or_create_db("payment")

# Bedrock LLaMA model
llm = BedrockLLM(
    model_id="meta.llama3-8b-instruct-v1:0",
    temperature=0.2
)

# MCP-style prompts
airline_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an Airline Booking Agent.
    Respond ONLY in JSON: {{"tool": "<tool_name>", "args": {{...}}}}
    Tools you can use:
    1. search_flights(destination, date)
    2. book_flight(flight_id)
    3. request_payment(amount, currency)
    Memory:
    {memory}"""),
    ("human", "{input}")
])

payment_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a Payment Processing Agent.
    Respond ONLY in JSON: {{"tool": "<tool_name>", "args": {{...}}}}
    Tools you can use:
    1. process_payment(amount, currency, method)
    2. confirm_payment(transaction_id)
    Memory:
    {memory}"""),
    ("human", "{input}")
])

airline_chain = LLMChain(llm=llm, prompt=airline_prompt)
payment_chain = LLMChain(llm=llm, prompt=payment_prompt)

# Simulated tools
def search_flights(destination, date):
    return [{"id": "F123", "route": f"NYC → {destination}", "date": date, "price": 450}]

def book_flight(flight_id):
    return {"booking_id": "B789", "status": "confirmed"}

def request_payment(amount, currency):
    # Agent-to-agent call: hand over to payment agent
    return run_payment_agent(f"Please process payment of {amount} {currency} via credit card.")

def process_payment(amount, currency, method):
    return {"transaction_id": "T456", "status": "paid"}

def confirm_payment(transaction_id):
    return {"status": "confirmed", "transaction_id": transaction_id}

# Agent logic
def run_airline_agent(user_input):
    results = airline_memory.similarity_search(user_input, k=3)
    memory_text = "\n".join([r.page_content for r in results])
    output = airline_chain.run(input=user_input, memory=memory_text)
    airline_memory.add_texts([user_input + "\n" + output])
    airline_memory.save_local("airline_memory")
    return handle_tool_call(output, "airline")

def run_payment_agent(user_input):
    results = payment_memory.similarity_search(user_input, k=3)
    memory_text = "\n".join([r.page_content for r in results])
    output = payment_chain.run(input=user_input, memory=memory_text)
    payment_memory.add_texts([user_input + "\n" + output])
    payment_memory.save_local("payment_memory")
    return handle_tool_call(output, "payment")

# Tool call handler
def handle_tool_call(json_str, agent_type):
    try:
        call = json.loads(json_str)
        tool = call.get("tool")
        args = call.get("args", {})

        if agent_type == "airline":
            if tool == "search_flights":
                return search_flights(**args)
            elif tool == "book_flight":
                return book_flight(**args)
            elif tool == "request_payment":
                return request_payment(**args)

        elif agent_type == "payment":
            if tool == "process_payment":
                return process_payment(**args)
            elif tool == "confirm_payment":
                return confirm_payment(**args)

        return {"error": "Unknown tool"}

    except json.JSONDecodeError:
        return {"error": "Invalid JSON from agent"}

# CLI loop
print("MCP-Style Multi-Agent CLI (type 'quit' to exit)")
while True:
    user_msg = input("You: ")
    if user_msg.lower() in ["quit", "exit"]:
        break

    if "flight" in user_msg.lower() or "airline" in user_msg.lower():
        response = run_airline_agent(user_msg)
    elif "pay" in user_msg.lower() or "payment" in user_msg.lower():
        response = run_payment_agent(user_msg)
    else:
        response = "Please specify 'flight' or 'payment'."

    print(f"Agent: {response}")
