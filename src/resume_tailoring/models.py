from pydantic import BaseModel


class TailoredResumeOutput(BaseModel):
    tailored_tex_content: str
    changes_summary: str


# Test instantiation (for reference, not executed here)
# output = TailoredResumeOutput(
#     tailored_tex_content="\\section{Experience} ...",
#     changes_summary="Kept main research project, updated skills for job requirements, added leadership section."
# )
