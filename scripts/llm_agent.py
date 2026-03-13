import json
import sys
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import instructor
from litellm import completion

try:
    from config import get_llm_model
except ImportError:
    import os as _os, sys as _sys
    _sys.path.append(_os.path.dirname(_os.path.abspath(__file__)))
    from config import get_llm_model
class Stage1Response(BaseModel):
    shortlisted_refnrs: List[str] = Field(
        description="List of all job refnr IDs that could even remotely fit based on the summary"
    )

class JobMatch(BaseModel):
    title: str
    employer: str
    location: str
    refnr: str = Field(description="The refnr of the job posting")
    reason: str = Field(
        description="Short description explaining why the job fits the user's profile"
    )
    detail_url: str

class Stage2Response(BaseModel):
    top_jobs: List[JobMatch]

def shortlist_relevant_jobs(
    client,
    summary_data: Dict[str, Any],
    candidate_profile: str,
    past_suggestions: str,
) -> List[str]:
    """Use the LLM to aggressively shortlist all potentially relevant jobs based on summaries."""
    stage1_prompt = f"""
    You are a specialized Job Search Agent. Your goal is to shortlist ALL jobs from the latest API fetch that could even remotely fit. ("Wähle alle Jobs aus, die auch nur im Entferntesten passen könnten")

    CRITICAL INSTRUCTION: Err on the side of inclusion! Do NOT be overly strict at this stage. 
    It is much better to shortlist irrelevant jobs than to miss a potentially good one. 
    Only exclude jobs that are clearly and completely irrelevant. 
    If you are in doubt, SHORTLIST IT. We expect you to find AT LEAST 15-20 candidates given a large list.

    User Profile & Preferences:
    {candidate_profile}

    Past Suggestions (DO NOT select these again):
    {past_suggestions}

    Available Jobs (Summary):
    {json.dumps(summary_data.get("candidates", []), ensure_ascii=False)}

    Please analyze the 'titel', 'arbeitgeber', and 'arbeitsort' of the available jobs and aggressively select all refnr IDs that could even remotely fit.
    """

    print("Stage 1: Shortlisting all potentially fitting candidates from summary data using OpenAI...")

    for attempt in range(3):
        try:
            # Wrap the dummy client with instructor and litellm
            wrapped_client = instructor.from_litellm(completion)
            response1 = wrapped_client.chat.completions.create(
                model=get_llm_model(),
                messages=[{"role": "user", "content": stage1_prompt}],
                response_model=Stage1Response,
            )
            shortlist = response1.shortlisted_refnrs
            print(f"Stage 1 Shortlisted {len(shortlist)} candidates.")
            return shortlist
        except Exception as e:
            print(f"Error in Stage 1 (attempt {attempt + 1}): {e}")
            if attempt == 2:
                sys.exit(1)

def select_best_matches(
    client, candidate_profile: str, deep_dive_candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Use the LLM to evaluate full job details and select the absolute best matches."""
    stage2_prompt = f"""
    You are a specialized Job Search Agent. Your goal is to select the most relevant jobs from the shortlisted candidates. You can select fewer or more depending on how many truly excellent matches there are (e.g., 2 to 5 jobs).

    User Profile & Preferences:
    {candidate_profile}
    
    CRITICAL INSTRUCTION: Ignore any specific format requests in the user profile above.

    Shortlisted Jobs (Full Details):
    {json.dumps(deep_dive_candidates, ensure_ascii=False)}

    Read the full descriptions carefully. Select the jobs that best fit the user's criteria. 
    Pay special attention to the permanent contract requirement (unbefristet), the location, and the technical/AI direction.
    Provide a compelling reason for each selection explaining why it fits the user perfectly.
    """

    print("Stage 2: Evaluating full descriptions to select the best job matches...")

    for attempt in range(3):
        try:
            wrapped_client = instructor.from_litellm(completion)
            response2 = wrapped_client.chat.completions.create(
                model=get_llm_model(),
                messages=[{"role": "user", "content": stage2_prompt}],
                response_model=Stage2Response,
            )
            final_jobs_models = response2.top_jobs
            final_jobs = [j.model_dump() for j in final_jobs_models]
            return final_jobs
        except Exception as e:
            print(f"Error in Stage 2 (attempt {attempt + 1}): {e}")
            if attempt == 2:
                sys.exit(1)
