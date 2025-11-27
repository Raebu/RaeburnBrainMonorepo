# AI-Powered Code Developer
import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load AI Model
model_name = "deepseek-ai/DeepSeek-Coder-V2-Base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def generate_code(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    output = model.generate(**inputs)
    return tokenizer.decode(output[0])

# Gradio UI
demo = gr.Interface(fn=generate_code, inputs="text", outputs="text")
demo.launch()
