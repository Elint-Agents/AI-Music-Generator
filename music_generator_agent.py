import os
from uuid import uuid4
import requests
import streamlit as st
from typing import TypedDict, Any

from agno.agent import Agent, RunResponse
from agno.models.groq import Groq  # ✅ correct model
from agno.tools.models_labs import FileType, ModelsLabTools
from langgraph.graph import StateGraph

# === Sidebar: API Keys ===
st.sidebar.title("API Key Configuration")
groq_api_key = st.sidebar.text_input("Enter your Groq API Key", type="password")
models_lab_api_key = st.sidebar.text_input("Enter your ModelsLab API Key", type="password")

# === UI ===
st.title("🎶 LangGraph + Groq Music Generator")
prompt = st.text_area("Enter a music generation prompt:", "Generate a 30 second lo-fi chill beat", height=100)

# === Setup when keys are present ===
if groq_api_key and models_lab_api_key:

    # Initialize ModelsLab Tool
    modelslab_tool = ModelsLabTools(
        api_key=models_lab_api_key,
        wait_for_completion=True,
        file_type=FileType.MP3
    )

    # ✅ Create Groq-based Agent
    music_agent = Agent(
        name="Groq Music Agent",
        agent_id="groq_music_agent_v1",
        model=Groq(api_key=groq_api_key, id="llama3-70b-8192"),  # ✅ Groq model
        tools=[modelslab_tool],
        description="Agent that generates music using ModelsLab via Groq",
        markdown=True,
        debug_mode=True,
    )

    # LangGraph State
    class MusicState(TypedDict):
        prompt: str
        result: Any

    # Node function
    def generate_music_node(state: MusicState) -> MusicState:
        input_text = state["prompt"]
        music: RunResponse = music_agent.run(input_text)
        urls = [a.url for a in music.audio] if music.audio else []
        return {"result": urls, "prompt": input_text}

    # LangGraph Workflow
    workflow = StateGraph(state_schema=MusicState)
    workflow.add_node("generate_music", generate_music_node)
    workflow.set_entry_point("generate_music")
    workflow.set_finish_point("generate_music")
    graph = workflow.compile()

    # Button
    if st.button("Generate Music 🎼"):
        with st.spinner("Generating music using Groq + ModelsLab..."):
            try:
                result = graph.invoke({"prompt": prompt})
                urls = result["result"]

                if urls and isinstance(urls, list) and urls[0].startswith("http"):
                    audio_url = urls[0]
                    save_dir = "audio_generations"
                    os.makedirs(save_dir, exist_ok=True)
                    filename = f"{save_dir}/music_{uuid4()}.mp3"

                    response = requests.get(audio_url)
                    with open(filename, "wb") as f:
                        f.write(response.content)

                    audio_bytes = open(filename, "rb").read()
                    st.success("Music generated successfully! 🎵")
                    st.audio(audio_bytes, format="audio/mp3")
                    st.download_button("Download Music", data=audio_bytes, file_name="generated_music.mp3", mime="audio/mp3")
                else:
                    st.error("No valid audio URL returned.")
                    st.write("Full result:", result)
            except Exception as e:
                st.error(f"Error: {e}")

else:
    st.sidebar.warning("Please enter both the Groq and ModelsLab API keys.")
