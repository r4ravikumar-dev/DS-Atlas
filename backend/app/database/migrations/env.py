import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.database.session import Base, uses_transaction_pooler
from app.database.supabase import lockdown
import app.models  # noqa: F401  (register models)

config = context.config
# Migrations prefer a direct/session connection (Supabase: port 5432) when MIGRATION_DATABASE_URL is set; DATABASE_URL otherwise.
_url = os.environ.get("MIGRATION_DATABASE_URL") or get_settings().database_url
config.set_main_option("sqlalchemy.url", _url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args = {"prepare_threshold": None} if uses_transaction_pooler(_url, get_settings().db_pool_mode) else {}
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool,
                                     connect_args=connect_args)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
            # Supabase: keep the auto-generated Data API closed to the app's tables (no-op on plain PostgreSQL).
            lockdown(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
