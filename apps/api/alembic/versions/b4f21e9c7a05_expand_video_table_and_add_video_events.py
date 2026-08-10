"""expand video table and add video_events

Revision ID: b4f21e9c7a05
Revises: 7dce215c5ef5
Create Date: 2026-08-06 10:12:03.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b4f21e9c7a05'
down_revision = '7dce215c5ef5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('videos', sa.Column('description', sa.Text(), nullable=False, server_default=''), schema='video')
    op.add_column('videos', sa.Column('content_type', sa.String(length=100), nullable=False, server_default='video/mp4'), schema='video')
    op.add_column('videos', sa.Column('visibility', sa.String(length=20), nullable=False, server_default='draft'), schema='video')
    op.add_column('videos', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True), schema='video')
    op.add_column('videos', sa.Column('transcript_segments', sa.JSON(), nullable=True), schema='video')
    op.add_column('videos', sa.Column('summary_notes', sa.Text(), nullable=True), schema='video')
    op.add_column('videos', sa.Column('key_points', sa.JSON(), nullable=True), schema='video')
    op.add_column('videos', sa.Column('quiz', sa.JSON(), nullable=True), schema='video')

    op.create_table('video_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('video_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.String(length=30), nullable=False),
    sa.Column('watch_duration_seconds', sa.Float(), nullable=True),
    sa.Column('completion_pct', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ),
    sa.ForeignKeyConstraint(['video_id'], ['video.videos.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='video'
    )
    op.create_index(op.f('ix_video_video_events_user_id'), 'video_events', ['user_id'], unique=False, schema='video')
    op.create_index(op.f('ix_video_video_events_video_id'), 'video_events', ['video_id'], unique=False, schema='video')
    op.create_index(op.f('ix_video_video_events_created_at'), 'video_events', ['created_at'], unique=False, schema='video')


def downgrade() -> None:
    op.drop_index(op.f('ix_video_video_events_created_at'), table_name='video_events', schema='video')
    op.drop_index(op.f('ix_video_video_events_video_id'), table_name='video_events', schema='video')
    op.drop_index(op.f('ix_video_video_events_user_id'), table_name='video_events', schema='video')
    op.drop_table('video_events', schema='video')

    op.drop_column('videos', 'quiz', schema='video')
    op.drop_column('videos', 'key_points', schema='video')
    op.drop_column('videos', 'summary_notes', schema='video')
    op.drop_column('videos', 'transcript_segments', schema='video')
    op.drop_column('videos', 'published_at', schema='video')
    op.drop_column('videos', 'visibility', schema='video')
    op.drop_column('videos', 'content_type', schema='video')
    op.drop_column('videos', 'description', schema='video')
