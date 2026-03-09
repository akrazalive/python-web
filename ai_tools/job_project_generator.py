# ai_tools/job_project_generator.py
import openai
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

class JobToProjectGenerator:
    """
    AI ENGINEER: This class takes job descriptions and turns them into real projects
    You're building a tool that saves hours of manual work!
    """
    
    def generate_projects_from_job(self, job_description, num_projects=3):
        """
        Generate multiple project ideas from a single job description
        """
        prompt = f"""
        You are a senior developer creating portfolio projects based on real job requirements.
        
        Job Description:
        {job_description}
        
        Create {num_projects} different portfolio projects that would demonstrate the exact skills this job requires.
        
        For each project, provide:
        1. Title (catchy, professional)
        2. Description (detailed, showing the technologies mentioned)
        3. Category (web, mobile, design, consulting, other)
        4. Client (a realistic company name that would need this)
        5. Technologies used (comma separated)
        6. Key features (bullet points)
        7. Why this matches the job (brief explanation)
        
        Return as JSON array with this structure:
        [
            {{
                "title": "...",
                "description": "...",
                "category": "...",
                "client": "...",
                "technologies": "...",
                "features": "...",
                "job_match": "..."
            }}
        ]
        
        Make the descriptions rich and detailed - these will be actual portfolio projects.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",  # Using 16k for longer job descriptions
                messages=[
                    {"role": "system", "content": "You are an expert at identifying job requirements and creating matching portfolio projects."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            # Extract JSON from the response (in case there's extra text)
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                projects_data = json.loads(content[json_start:json_end])
                return projects_data
            else:
                return []
                
        except Exception as e:
            print(f"AI Error: {str(e)}")
            return []
    
    def format_for_display(self, projects_data):
        """Format AI response for nice display"""
        formatted = []
        for i, project in enumerate(projects_data, 1):
            formatted.append(f"""
### Project {i}: {project.get('title', 'Untitled')}

**Description:** {project.get('description', '')}

**Category:** {project.get('category', 'web')}
**Client:** {project.get('client', 'Startup Company')}
**Technologies:** {project.get('technologies', '')}

**Key Features:**
{project.get('features', '')}

**Why this matches the job:**
{project.get('job_match', '')}

---
            """)
        return "\n".join(formatted)