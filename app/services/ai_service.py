import json
import os
from typing import List

from dotenv import load_dotenv
from app.schemas.checkin_response_schema import CheckInAnalyticsRequest
from google import genai
load_dotenv()

class AiService:
    def __init__(self):
       self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))  # updated to current Gemini model

    def process_response(
        self, 
        responses: List[CheckInAnalyticsRequest], 
        description: str
    ) -> dict:
        res_json = json.dumps([response.model_dump() for response in responses], indent=2)

        prompt = f"""
            You are an AI assistant helping a product team derive insights from daily check-ins. Given a list of responses to what each person (identified by email) did yesterday, what they’re doing today, and any blockers — along with the product description — generate the following insights:

            summary: A concise, synthesized summary of the work completed and planned, attributed by email.

            blockers: A clear list of blockers, also attributed by email.

            diversion_range: One of "on track", "slightly off", or "significantly off", based on how aligned the updates are with the product description.

            diversion_context: A short explanation for why the updates are on or off track.

            Inputs:

            Product Description:
            {description}

            Check-in Responses:
            {res_json}

            Output (in JSON format):
            {{
            "summary": "...",
            "blockers": "...",
            "diversion_range": "...",
            "diversion_context": "..."
            }}
        """

        response = self.client.models.generate_content(
            model='gemini-2.0-flash-001', contents=prompt
        )
        # Handle output formatting
        json_str = response.text.strip().replace("```json", "").replace("```", "")
        json_obj = json.loads(json_str)

        #print(json_obj)
        return json_obj

    def generate_content(self, 
                         summaries: List[str],
                         description: str 
    ) -> str:
        """
        Generate a summary of the provided summaries.
        """
        prompt = f"""
        You are an AI assistant helping a product team create engaging behind-the-scenes content from their daily check-ins.

        Given a list of update summaries, write a detailed narrative that highlights the process, 
        struggles, problem-solving, and milestones the team experienced while building the product. 
        The content should feel like a blog post that tells the story of the team's journey—showcasing their challenges, 
        how they tackled them, and the progress they made.

        Summaries:
        {summaries}

        Product Description:
        {description}

        Please provide your output in JSON format with the following structure:
        {{
            "summary": "A detailed, story-driven behind-the-scenes blog post that captures the journey, challenges, and solutions."
        }}
        """

        #print(prompt)

        response = self.client.models.generate_content(
            model='gemini-2.0-flash-001', contents=prompt
        )
        
        # Handle output formatting
        json_str = response.text.strip().replace("```json", "").replace("```", "")
        print(json_str)
        json_obj = json.loads(json_str)

        return json_obj.get("summary", "")
