import logging
import numpy as np
from sklearn.cluster import KMeans

class Threshold:
    def __init__(
        self,
        appliances: list = None,
        method: str = "mp",
        num_status: int = 2,
    ):
        # Format the appliances list correctly without external dependencies
        if appliances is None:
            self.appliances = ["App"]
        elif isinstance(appliances, str):
            self.appliances = [appliances]
        else:
            self.appliances = list(appliances)
            
        self.num_apps = len(self.appliances)
        self.method = method
        self.num_status = num_status
        self._status_fun = self._compute_status

        self.thresholds = np.zeros((self.num_apps, self.num_status)) 
        self.centroids = np.zeros((self.num_apps, self.num_status)) 
        self.use_std = False

        self._initialize_params()

    def __repr__(self):
        return f"Threshold | Method: {self.method} | Statuses: {self.num_status}"

    def _initialize_params(self):
        if self.method == "vs":
            self.use_std = True
        elif self.method == "mp":
            pass
        elif self.method == "custom":
            pass
        else:
            raise ValueError(
                f"Method {self.method} doesnt exist. Use one of the following: vs, mp, custom"
            )

    def _compute_cluster_centroids(self, ser: np.ndarray):
        ser = ser.copy()
        kmeans = KMeans(n_clusters=self.num_status, n_init=10).fit(ser.reshape(-1, 1))
        centroid = kmeans.cluster_centers_.reshape(self.num_status)

        labels = kmeans.labels_
        std = np.zeros(self.num_status)
        for split in range(self.num_status):
            std[split] = ser[labels == split].std()

        return centroid, std

    def _compute_thresholds(self, ser: np.ndarray):
        centroid, std = self._compute_cluster_centroids(ser)

        sigma = (
            np.nan_to_num(np.divide(std[:-1], std[:-1] + std[1:]))
            if self.use_std
            else np.repeat([0.5], self.num_status - 1)
        )
        threshold = np.zeros(self.num_status)
        threshold[1:] = centroid[:-1] + np.multiply(sigma, centroid[1:] - centroid[:-1])

        if self.num_status == 2:
            mask_on = ser >= threshold[1]
            centroid[0] = ser[~mask_on].mean()
            centroid[1] = ser[mask_on].mean()

        return threshold, centroid

    def update_appliance_threshold(self, ser: np.ndarray, appliance: str):
        threshold, centroid = self._compute_thresholds(ser.flatten())
        idx = self.appliances.index(appliance)
        self.thresholds[idx, :] = threshold
        self.centroids[idx, :] = centroid
        logging.info(f"Appliance '{appliance}' thresholds have been updated")

    def _compute_status(self, ser: np.ndarray) -> np.ndarray:
        ser_bin = (
            np.argmin((ser[:, :, None] - self.thresholds[None, :, :]) >= 0, axis=2) - 1
        )
        ser_bin[ser_bin < 0] = self.num_status - 1
        return ser_bin

    def power_to_status(self, ser: np.ndarray) -> np.ndarray:
        ser = ser.copy()
        ser_bin = self._status_fun(ser).astype(int)
        return ser_bin

    def status_to_power(self, ser: np.ndarray) -> np.ndarray:
        return np.take_along_axis(self.centroids, ser.T, axis=1).T

    def set_thresholds_and_centroids(self, thresholds: np.ndarray, centroids: np.ndarray):
        assert len(thresholds.shape) == 2, "Array must have two dimensions"
        assert thresholds.shape[0] == self.num_apps, f"Axis 0 must have length {self.num_apps}"
        assert thresholds.shape == centroids.shape, "Both arrays must have same dimension"
        
        self.num_status = thresholds.shape[1]
        self.thresholds = thresholds
        self.centroids = centroids
        self.method = "custom"
        self._status_fun = self._compute_status