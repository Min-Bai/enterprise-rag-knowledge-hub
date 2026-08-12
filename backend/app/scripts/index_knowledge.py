from ..services.vector_store import rebuild_knowledge_index


if __name__ == "__main__":
    count = rebuild_knowledge_index()
    print(f"Indexed {count} knowledge chunks.")
