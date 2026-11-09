import time
import uuid

import numpy as np
import redis
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer

PREFIX = "s0571"
INDEX = f"{PREFIX}:answer_idx"
KEY_PREFIX = f"{PREFIX}:answer:"
DIM = 384


class SemanticCache:
    def __init__(self):
        self.redis_client = redis.Redis(host="localhost", port=6379)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.create_index()

    def create_index(self):
        try:
            self.redis_client.ft(INDEX).info()
        except redis.ResponseError:
            schema = (
                TextField("query"),
                TagField("data_version"),
                VectorField("embedding", "FLAT", {"TYPE": "FLOAT32", "DIM": DIM, "DISTANCE_METRIC": "COSINE"}),
            )
            definition = IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.HASH)
            self.redis_client.ft(INDEX).create_index(schema, definition=definition)

    def embed(self, text):
        return self.model.encode(text, normalize_embeddings=True).astype(np.float32)

    def nearest(self, embedding):
        query = (
            Query("*=>[KNN 1 @embedding $vec AS distance]")
            .return_fields("query", "answer", "codes", "data_version", "distance")
            .dialect(2)
        )
        result = self.redis_client.ft(INDEX).search(query, query_params={"vec": embedding.tobytes()})
        if not result.docs:
            return None
        doc = result.docs[0]
        return {
            "key": doc.id,
            "query": doc.query,
            "answer": doc.answer,
            "codes": doc.codes.split(",") if doc.codes else [],
            "data_version": doc.data_version,
            "similarity": 1 - float(doc.distance),
        }

    def store(self, query, embedding, answer, codes, version):
        key = KEY_PREFIX + uuid.uuid4().hex[:12]
        self.redis_client.hset(key, mapping={
            "query": query,
            "embedding": embedding.tobytes(),
            "answer": answer,
            "codes": ",".join(codes),
            "data_version": version,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        return key

    def delete(self, key):
        self.redis_client.delete(key)

    def clear(self):
        for key in self.redis_client.scan_iter(f"{KEY_PREFIX}*"):
            self.redis_client.delete(key)
