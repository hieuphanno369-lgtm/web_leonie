# modules/ml_pipeline/unsupervised_trainer.py
import numpy as np
import polars as pl
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from kneed import KneeLocator


def _pca2d(X_scaled):
    pca = PCA(n_components=min(2, X_scaled.shape[1]))
    return pca.fit_transform(X_scaled)


def _run_kmeans(X_scaled):
    max_k = min(11, len(X_scaled))
    ks = list(range(2, max_k))
    inertias = []
    for k in ks:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
    kneedle = KneeLocator(ks, inertias, curve="convex", direction="decreasing")
    best_k = kneedle.knee or 3
    model = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = model.fit_predict(X_scaled)
    sil = float(silhouette_score(X_scaled, labels)) if best_k > 1 else 0.0
    return model, labels, {
        "silhouette": sil, "inertia": float(model.inertia_), "k": best_k,
        "elbow_ks": ks, "elbow_inertias": inertias,
    }, best_k


def _run_dbscan(X_scaled, eps, min_samples):
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(X_scaled)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    sil = 0.0
    if n_clusters > 1:
        mask = labels != -1
        if mask.sum() > 1:
            # Relabel to consecutive integers for safe silhouette computation
            clean_labels = labels[mask].copy()
            unique = sorted(set(clean_labels))
            remap = {old: new for new, old in enumerate(unique)}
            clean_labels = np.array([remap[l] for l in clean_labels])
            sil = float(silhouette_score(X_scaled[mask], clean_labels))
    return model, labels, {
        "silhouette": sil, "n_clusters": n_clusters,
        "elbow_ks": [], "elbow_inertias": [],
    }, n_clusters


def _run_hierarchical(X_scaled, n_clusters):
    model = AgglomerativeClustering(n_clusters=n_clusters)
    labels = model.fit_predict(X_scaled)
    sil = float(silhouette_score(X_scaled, labels)) if n_clusters > 1 else 0.0
    return model, labels, {
        "silhouette": sil, "n_clusters": n_clusters,
        "elbow_ks": [], "elbow_inertias": [],
    }, n_clusters


def run(
    df: pl.DataFrame,
    features: list[str],
    algorithms: list[str],
    dbscan_eps: float = 0.5,
    dbscan_min_samples: int = 5,
    hierarchical_k: int = 3,
) -> dict:
    if not algorithms:
        raise ValueError("algorithms list must not be empty")
    clean = df.select(features).drop_nulls()
    X = clean.to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_2d = _pca2d(X_scaled)

    results = {}
    for algo in algorithms:
        if algo == "kmeans":
            model, labels, metrics, k = _run_kmeans(X_scaled)
        elif algo == "dbscan":
            model, labels, metrics, k = _run_dbscan(X_scaled, dbscan_eps, dbscan_min_samples)
        elif algo == "hierarchical":
            model, labels, metrics, k = _run_hierarchical(X_scaled, hierarchical_k)
        else:
            raise ValueError(f"Unknown algorithm: {algo}")
        results[algo] = {
            "model": model,
            "metrics": metrics,
            "cluster_labels": labels,
            "k": k,
            "X_2d": X_2d,
            "feature_names": features,
            "problem_type": "clustering",
            "y_pred": labels,
            "y_test": labels,
        }

    winner = max(results, key=lambda a: results[a]["metrics"]["silhouette"])
    return {"results": results, "winner": winner, "problem_type": "clustering"}
