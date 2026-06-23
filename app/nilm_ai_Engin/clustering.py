import itertools
from typing import Optional

import numpy as np
from scipy.cluster.hierarchy import cophenet, fcluster, linkage
from scipy.spatial.distance import pdist

class HierarchicalClustering:
    def __init__(
        self, distance: str = "average", n_cluster: int = 2, criterion: str = "maxclust"
    ):
        self.distance = distance
        self.n_cluster = n_cluster
        self.criterion = criterion

        self.x = np.empty(0)  
        self.z = np.empty(0) 

        self.thresh = np.empty(0)
        self.centroids = np.empty(0)

    def perform_clustering(
        self, ser: np.ndarray, distance: Optional[str] = None
    ) -> None:
        self.distance = distance if distance is not None else self.distance
        self.x = np.expand_dims(ser, axis=1)
        self.z = linkage(self.x, method=self.distance)

    @property
    def cophenet(self):
        c, coph_dists = cophenet(self.z, pdist(self.x))
        return c

    def compute_thresholds_and_centroids(
        self,
        n_cluster: Optional[int] = None,
        criterion: Optional[str] = None,
        centroid: str = "median",
    ):
        self.n_cluster = n_cluster if n_cluster is not None else self.n_cluster
        self.criterion = criterion if criterion is not None else self.criterion
        clusters = fcluster(self.z, self.n_cluster, self.criterion)
        
        if centroid == "median":
            fun = np.median
        elif centroid == "mean":
            fun = np.mean
            
        self.centroids = np.array(
            sorted([fun(self.x[clusters == (c + 1)]) for c in range(self.n_cluster)])
        )
        
        x_max = sorted(
            [np.max(self.x[clusters == (c + 1)]) for c in range(self.n_cluster)]
        )
        x_min = sorted(
            [np.min(self.x[clusters == (c + 1)]) for c in range(self.n_cluster)]
        )
        thresh = np.divide(np.array(x_min[1:]) + np.array(x_max[:-1]), 2)
        self.thresh = np.insert(thresh, 0, 0, axis=0)