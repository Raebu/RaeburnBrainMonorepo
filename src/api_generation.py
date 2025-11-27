# AI-Powered API Generation
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "garage-bAInd/Platypus2-13B-Gorilla"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def generate_api_call(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    output = model.generate(**inputs)
    return tokenizer.decode(output[0])
