from pydantic import BaseModel, Field


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class TeamResponse(BaseModel):
    id: str
    name: str
    created_by: str


class TeamMemberAddRequest(BaseModel):
    user_id: str
    role: str = Field(pattern="^(owner|admin|editor|viewer)$")


class TeamMemberRoleUpdateRequest(BaseModel):
    role: str = Field(pattern="^(owner|admin|editor|viewer)$")


class TeamMemberResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: str
