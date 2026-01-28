"""Initial schema - cards, deals, and sets tables

Revision ID: 001_initial
Revises:
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pokemon Sets table
    op.create_table(
        'pokemon_sets',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('series', sa.String(255), nullable=False, index=True),
        sa.Column('total_cards', sa.Integer, nullable=True),
        sa.Column('release_date', sa.String(20), nullable=True),
        sa.Column('logo_url', sa.Text, nullable=True),
        sa.Column('symbol_url', sa.Text, nullable=True),
        sa.Column('era', sa.String(50), nullable=True, index=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Cards table
    op.create_table(
        'cards',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('set_id', sa.String(50), nullable=False, index=True),
        sa.Column('set_name', sa.String(255), nullable=False),
        sa.Column('number', sa.String(20), nullable=False),
        sa.Column('rarity', sa.String(50), nullable=True),
        sa.Column('image_small', sa.Text, nullable=True),
        sa.Column('image_large', sa.Text, nullable=True),
        sa.Column('market_value_nm', sa.Float, nullable=True),
        sa.Column('market_value_lp', sa.Float, nullable=True),
        sa.Column('market_value_mp', sa.Float, nullable=True),
        sa.Column('market_value_hp', sa.Float, nullable=True),
        sa.Column('ebay_sold_avg', sa.Float, nullable=True),
        sa.Column('cardmarket_low', sa.Float, nullable=True),
        sa.Column('cardmarket_trend', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_cards_set_name', 'cards', ['set_id', 'name'])

    # Deals table
    op.create_table(
        'deals',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('platform', sa.Enum('ebay', 'cardmarket', 'vinted', 'facebook',
                                       'magicmadhouse', 'chaoscards', name='platform'),
                  nullable=False, index=True),
        sa.Column('url', sa.Text, nullable=False),
        sa.Column('card_id', sa.String(50), sa.ForeignKey('cards.id'), nullable=True, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('condition', sa.Enum('NM', 'LP', 'MP', 'HP', 'DMG', name='condition'),
                  nullable=True),
        sa.Column('listing_price', sa.Float, nullable=False),
        sa.Column('shipping_cost', sa.Float, default=0.0),
        sa.Column('platform_fee', sa.Float, default=0.0),
        sa.Column('total_cost', sa.Float, nullable=False),
        sa.Column('market_value', sa.Float, nullable=True),
        sa.Column('deal_score', sa.Float, nullable=True, index=True),
        sa.Column('seller_name', sa.String(255), nullable=True),
        sa.Column('image_url', sa.Text, nullable=True),
        sa.Column('is_buy_now', sa.Boolean, default=True),
        sa.Column('is_active', sa.Boolean, default=True, index=True),
        sa.Column('found_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_deals_platform_external', 'deals', ['platform', 'external_id'], unique=True)
    op.create_index('ix_deals_active_score', 'deals', ['is_active', 'deal_score'])
    op.create_index('ix_deals_found_at_active', 'deals', ['found_at', 'is_active'])

    # Deal History table
    op.create_table(
        'deal_history',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('deal_id', sa.Integer, sa.ForeignKey('deals.id'), nullable=False, index=True),
        sa.Column('listing_price', sa.Float, nullable=False),
        sa.Column('market_value', sa.Float, nullable=True),
        sa.Column('deal_score', sa.Float, nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('deal_history')
    op.drop_table('deals')
    op.drop_table('cards')
    op.drop_table('pokemon_sets')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS platform')
    op.execute('DROP TYPE IF EXISTS condition')
