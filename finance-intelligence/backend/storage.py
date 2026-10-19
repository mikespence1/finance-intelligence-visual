"""Persistent, isolated browser workspaces: PostgreSQL in Vercel, SQLite locally.

JSON dataframes and conversation records share one atomically versioned row.
There is no pickle deserialization and no filesystem upload storage.
"""
from functools import lru_cache
import gzip
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import time

import pandas as pd
from sqlalchemy import Column, Float, Integer, LargeBinary, MetaData, String, Table, create_engine, delete, insert, select, text, update
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
metadata = MetaData()
workspaces = Table('finance_workspaces', metadata,
    Column('id', String(64), primary_key=True),
    Column('revision', Integer, nullable=False),
    Column('expires', Float, nullable=False, index=True),
    Column('payload', LargeBinary, nullable=False))


class WorkspaceConflict(Exception):
    pass


class WorkspaceTooLarge(Exception):
    pass


class Workspace(dict):
    def __init__(self, data, key, revision, store):
        super().__init__(data)
        self.key, self.revision, self.store = key, revision, store


def encode(state):
    payload = dict(state)
    payload['frames'] = [frame.to_json(orient='split', date_format='iso') for frame in state['frames']]
    raw = json.dumps(payload, allow_nan=False, separators=(',', ':')).encode()
    if len(raw) > 24 * 1024 * 1024:
        raise WorkspaceTooLarge('Workspace exceeds storage capacity')
    return gzip.compress(raw)


def decode(payload):
    state = json.loads(gzip.decompress(payload))
    state['frames'] = tuple(pd.read_json(StringIO(frame), orient='split', convert_dates=False) for frame in state['frames'])
    return state


class WorkspaceStore:
    def __init__(self, url, ttl=7200):
        self.ttl = ttl
        if url.startswith('postgres://'):
            url = 'postgresql+psycopg://' + url[len('postgres://'):]
        elif url.startswith('postgresql://'):
            url = 'postgresql+psycopg://' + url[len('postgresql://'):]
        if not url.startswith(('sqlite:', 'postgresql+psycopg:')):
            raise ValueError('Use a PostgreSQL or SQLite DATABASE_URL')
        connect_args = {'check_same_thread': False, 'timeout': 15} if url.startswith('sqlite:') else {'connect_timeout': 10}
        self.engine = create_engine(url, connect_args=connect_args, poolclass=NullPool, hide_parameters=True)
        with self.engine.begin() as connection:
            if self.engine.dialect.name == 'postgresql':
                # Multiple cold starts must not race while creating the table.
                connection.execute(text('SELECT pg_advisory_xact_lock(723184901)'))
            metadata.create_all(connection)

    @staticmethod
    def key(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self, token, data):
        key, now = self.key(token), time.time()
        payload = encode(data)
        with self.engine.begin() as connection:
            connection.execute(delete(workspaces).where(workspaces.c.expires <= now))
            connection.execute(insert(workspaces).values(id=key, revision=0, expires=now+self.ttl, payload=payload))
        return Workspace(data, key, 0, self)

    def load(self, token):
        key, now = self.key(token), time.time()
        with self.engine.begin() as connection:
            connection.execute(delete(workspaces).where(workspaces.c.expires <= now))
            row = connection.execute(select(workspaces).where(workspaces.c.id == key)).mappings().first()
            if not row:
                return None
            connection.execute(update(workspaces).where(workspaces.c.id == key).values(expires=now+self.ttl))
        return Workspace(decode(row['payload']), key, row['revision'], self)

    def save(self, state):
        payload = encode(state)
        with self.engine.begin() as connection:
            result = connection.execute(update(workspaces).where(
                (workspaces.c.id == state.key) & (workspaces.c.revision == state.revision) &
                (workspaces.c.expires > time.time())).values(payload=payload,
                    revision=state.revision+1, expires=time.time()+self.ttl))
            if result.rowcount != 1:
                raise WorkspaceConflict('Workspace changed in another request')
        state.revision += 1

    def delete(self, token):
        with self.engine.begin() as connection:
            connection.execute(delete(workspaces).where(workspaces.c.id == self.key(token)))

    def check(self):
        with self.engine.connect() as connection:
            connection.execute(select(1))


@lru_cache(maxsize=1)
def get_store():
    url = os.environ.get('DATABASE_URL')
    if not url:
        if os.environ.get('VERCEL'):
            raise RuntimeError('Connect a PostgreSQL database and configure DATABASE_URL in Vercel')
        directory = ROOT / '.local'
        directory.mkdir(exist_ok=True)
        url = 'sqlite:///' + str(directory / 'workspaces.sqlite3')
    elif os.environ.get('VERCEL') and url.startswith('sqlite:'):
        raise RuntimeError('Vercel requires a shared PostgreSQL DATABASE_URL')
    return WorkspaceStore(url)
