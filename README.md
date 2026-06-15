# payments - %projectname%

# install and run
```bash
docker compose up
```
```bash
uv sync
python -m payments
```
alembic
```bash
alembic revision --autogenerate -m "migration_name"
```
```bash
alembic downgrade -1
```