"""Add candidate profile fields, education table, and resume version enhancements

Revision ID: c8f3e1a2d5e6
Revises: b7f2c9a1e4d0
Create Date: 2026-10-10 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8f3e1a2d5e6'
down_revision = 'b7f2c9a1e4d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # UserProfile additions
    op.add_column('user_profiles', sa.Column('preferred_name', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('website', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('specialization', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('coursework', sa.JSON(), nullable=True))
    op.add_column('user_profiles', sa.Column('current_semester_or_year', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('user_profiles', sa.Column('availability', sa.String(), nullable=True))

    # CandidateEducation table
    op.create_table(
        'candidate_educations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('institution', sa.String(), nullable=False),
        sa.Column('degree', sa.String(), nullable=True),
        sa.Column('specialization', sa.String(), nullable=True),
        sa.Column('start_year', sa.Integer(), nullable=True),
        sa.Column('graduation_year', sa.Integer(), nullable=True),
        sa.Column('cgpa', sa.Float(), nullable=True),
        sa.Column('coursework', sa.JSON(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('is_visible', sa.Boolean(), server_default='1', nullable=False),
    )

    # CandidateExperience additions
    op.add_column('candidate_experiences', sa.Column('location', sa.String(), nullable=True))
    op.add_column('candidate_experiences', sa.Column('technologies', sa.JSON(), nullable=True))
    op.add_column('candidate_experiences', sa.Column('highlights', sa.JSON(), nullable=True))
    op.add_column('candidate_experiences', sa.Column('is_visible', sa.Boolean(), server_default='1', nullable=False))

    # CandidateProject additions
    op.add_column('candidate_projects', sa.Column('role', sa.String(), nullable=True))
    op.add_column('candidate_projects', sa.Column('start_date', sa.String(), nullable=True))
    op.add_column('candidate_projects', sa.Column('end_date', sa.String(), nullable=True))
    op.add_column('candidate_projects', sa.Column('highlights', sa.JSON(), nullable=True))
    op.add_column('candidate_projects', sa.Column('is_visible', sa.Boolean(), server_default='1', nullable=False))

    # UserSkill additions
    op.add_column('user_skills', sa.Column('category', sa.String(), server_default='General', nullable=False))
    op.add_column('user_skills', sa.Column('is_visible', sa.Boolean(), server_default='1', nullable=False))

    # Achievement additions
    op.add_column('candidate_achievements', sa.Column('url', sa.String(), nullable=True))
    op.add_column('candidate_achievements', sa.Column('is_visible', sa.Boolean(), server_default='1', nullable=False))

    # Course additions
    op.add_column('candidate_courses', sa.Column('credential_id', sa.String(), nullable=True))
    op.add_column('candidate_courses', sa.Column('expiry_date', sa.String(), nullable=True))
    op.add_column('candidate_courses', sa.Column('is_visible', sa.Boolean(), server_default='1', nullable=False))

    # UserPreference additions
    op.add_column('user_preferences', sa.Column('availability_duration', sa.String(), nullable=True))

    # ResumeVersion additions
    op.add_column('resume_versions', sa.Column('is_master', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('resume_versions', sa.Column('target_role', sa.String(), nullable=True))
    op.add_column('resume_versions', sa.Column('version_number', sa.Integer(), server_default='1', nullable=False))
    op.add_column('resume_versions', sa.Column('latex_source', sa.Text(), nullable=True))
    op.add_column('resume_versions', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('resume_versions', sa.Column('selected_projects', sa.JSON(), nullable=True))
    op.add_column('resume_versions', sa.Column('selected_experiences', sa.JSON(), nullable=True))
    op.add_column('resume_versions', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_table('candidate_educations')
    op.drop_column('user_profiles', 'preferred_name')
    op.drop_column('user_profiles', 'website')
    op.drop_column('user_profiles', 'specialization')
    op.drop_column('user_profiles', 'coursework')
    op.drop_column('user_profiles', 'current_semester_or_year')
    op.drop_column('user_profiles', 'bio')
    op.drop_column('user_profiles', 'availability')
    op.drop_column('candidate_experiences', 'location')
    op.drop_column('candidate_experiences', 'technologies')
    op.drop_column('candidate_experiences', 'highlights')
    op.drop_column('candidate_experiences', 'is_visible')
    op.drop_column('candidate_projects', 'role')
    op.drop_column('candidate_projects', 'start_date')
    op.drop_column('candidate_projects', 'end_date')
    op.drop_column('candidate_projects', 'highlights')
    op.drop_column('candidate_projects', 'is_visible')
    op.drop_column('user_skills', 'category')
    op.drop_column('user_skills', 'is_visible')
    op.drop_column('candidate_achievements', 'url')
    op.drop_column('candidate_achievements', 'is_visible')
    op.drop_column('candidate_courses', 'credential_id')
    op.drop_column('candidate_courses', 'expiry_date')
    op.drop_column('candidate_courses', 'is_visible')
    op.drop_column('user_preferences', 'availability_duration')
    op.drop_column('resume_versions', 'is_master')
    op.drop_column('resume_versions', 'target_role')
    op.drop_column('resume_versions', 'version_number')
    op.drop_column('resume_versions', 'latex_source')
    op.drop_column('resume_versions', 'notes')
    op.drop_column('resume_versions', 'selected_projects')
    op.drop_column('resume_versions', 'selected_experiences')
    op.drop_column('resume_versions', 'updated_at')
