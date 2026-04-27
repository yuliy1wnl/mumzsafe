import json
import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

COLLECTION_NAME = "mumzsafe_products"
EMBEDDING_MODEL = "nomic-embed-text"

client = QdrantClient(":memory:")


def get_embedding(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
    return response["embedding"]


def build_product_text(product: dict) -> str:
    """Build a rich text representation of a product for embedding."""
    parts = [
        f"Product: {product['product_name']}",
        f"Category: {product['category']}",
        f"Description: {product['description']}",
        f"Age range: {product['age_range']['min_months']} to {product['age_range']['max_months']} months",
    ]

    if product.get("allergen_warnings"):
        parts.append(f"Allergen warnings: {', '.join(product['allergen_warnings'])}")

    if product.get("chemical_warnings"):
        parts.append(f"Chemical warnings: {', '.join(product['chemical_warnings'])}")

    if product.get("doctor_consult_flags"):
        parts.append(f"Doctor consult flags: {', '.join(product['doctor_consult_flags'])}")

    if product.get("contraindications"):
        parts.append(f"Contraindications: {', '.join(product['contraindications'])}")

    if product.get("choking_hazard"):
        parts.append("WARNING: Choking hazard")

    if product.get("small_parts"):
        parts.append("WARNING: Contains small parts")

    return ". ".join(parts)


def index_products(products_path: str = "data/products.json"):
    with open(products_path) as f:
        products = json.load(f)

    # Create collection
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )


    points = []
    for i, product in enumerate(products):
        text = build_product_text(product)
        embedding = get_embedding(text)
        points.append(
            PointStruct(
                id=i,
                vector=embedding,
                payload=product,
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Indexed {len(points)} products into Qdrant.")
    return client


def search_products(query: str, top_k: int = 5) -> list[dict]:
    query_embedding = get_embedding(query)
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=top_k,
        with_payload=True,
    )
    return [hit.payload for hit in results]


if __name__ == "__main__":
    index_products()
    results = search_products("safe lotion for baby with eczema")
    for r in results:
        print(r["product_name"])