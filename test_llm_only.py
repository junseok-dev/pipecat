import asyncio
import os
import sys
from dotenv import load_dotenv

from pipecat.frames.frames import (
    TextFrame, 
    LLMMessagesUpdateFrame,
    EndFrame,
    StartFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openai.llm import OpenAILLMService

load_dotenv(override=True)

class LogSink(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if isinstance(frame, TextFrame):
            print(f"BOT: {frame.text}", flush=True)
        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            print("\n[LLM FINISHED]")
            await task.queue_frame(EndFrame())
        await super().process_frame(frame, direction)

async def main():
    print(">>> Starting LLM-ONLY test...")
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAILLMService.Settings(model="gpt-4o-mini")
    )
    sink = LogSink()
    pipeline = Pipeline([llm, sink])
    
    global task
    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=True)
    
    # 2초 후 질문 던지기
    async def trigger():
        await asyncio.sleep(2)
        print(">>> Sending prompt...")
        messages = [{"role": "user", "content": "Say 'It works!'"}]
        await task.queue_frame(LLMMessagesUpdateFrame(messages, run_llm=True))

    await asyncio.gather(runner.run(task), trigger())

if __name__ == "__main__":
    asyncio.run(main())
