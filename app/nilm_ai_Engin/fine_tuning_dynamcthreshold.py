import logging
import argparse
import math
import torch
from torch import nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np

from .GRU_BERT_model import GRUBERT
from .threshold import Threshold
from .clustering import HierarchicalClustering

logger = logging.getLogger("SENTRA_Core")

# ... (ConfigArgs, BERTDataset, NILMDataset remain unchanged)
class ConfigArgs:
    def __init__(self, cutoff=400.0, min_on=60, min_off=12):
        self.window_size = 480
        self.drop_out = 0.1
        self.output_size = 1
        self.val_size = 0.1
        self.window_stride = 32
        self.batch_size = 32
        self.threshold_method = 'mp'
        self.n_clusters = 2
        self.cutoff = cutoff
        self.min_on = min_on
        self.min_off = min_off
        self.c0 = 0.05
        self.w = 0.8  
        self.k = 0.0066

class BERTDataset(Dataset):
    def __init__(self, x, y, status, window_size=480, stride=30, mask_prob=0.25):
        self.x = x
        self.y = y
        self.status = status
        self.window_size = window_size
        self.stride = stride
        self.mask_prob = mask_prob

    def __len__(self):
        num_samples = max(0, (len(self.x) - self.window_size))
        return int(np.ceil(num_samples / self.stride) + 1)

    def __getitem__(self, index):
        import random
        start_index = index * self.stride
        end_index = min(len(self.x), start_index + self.window_size)
        x_slice = self.padding_seqs(self.x[start_index : end_index])
        y_slice = self.padding_seqs(self.y[start_index : end_index])
        status_slice = self.padding_seqs(self.status[start_index : end_index])

        tokens = []
        labels = []
        on_offs = []
        for i in range(len(x_slice)):
            prob = random.random()
            if prob < self.mask_prob:
                prob = random.random()
                if prob < 0.8:
                    tokens.append(-1)
                elif prob < 0.9:
                    tokens.append(np.random.normal())
                else:
                    tokens.append(x_slice[i])
                labels.append(y_slice[i])
                on_offs.append(status_slice[i])
            else:
                tokens.append(x_slice[i])
                temp = -1.0
                labels.append(temp)
                on_offs.append(temp)
        return (torch.tensor(tokens, dtype=torch.float64), 
                torch.tensor(labels, dtype=torch.float64).unsqueeze(-1), 
                torch.tensor(on_offs, dtype=torch.float64).unsqueeze(-1))

    def padding_seqs(self, in_array):
        if len(in_array) == self.window_size:
            return in_array
        out_array = np.zeros(self.window_size)
        out_array[:len(in_array)] = in_array
        return out_array

class NILMDataset(Dataset):
    def __init__(self, x, y, status, window_size=480, stride=30):
        self.x = x
        self.y = y
        self.status = status
        self.window_size = window_size
        self.stride = stride

    def __len__(self):
        num_samples = max(0, (len(self.x) - self.window_size))
        return int(np.ceil(num_samples / self.stride) + 1)

    def __getitem__(self, index):
        start_index = index * self.stride
        end_index = min(len(self.x), start_index + self.window_size)
        seq = self.padding_seqs(self.x[start_index : end_index])
        target_energy = self.padding_seqs(self.y[start_index : end_index])
        target_status = self.padding_seqs(self.status[start_index : end_index])
        return (torch.tensor(seq, dtype=torch.float64), 
                torch.tensor(target_energy, dtype=torch.float64).unsqueeze(-1), 
                torch.tensor(target_status, dtype=torch.float64).unsqueeze(-1))

    def padding_seqs(self, in_array):
        if len(in_array) == self.window_size:
            return in_array
        out_array = np.zeros(self.window_size)
        out_array[:len(in_array)] = in_array
        return out_array

class SENTRADataProcessor:
    def __init__(self, csv_filepath, target_col, args, num_rows=100000, pretrained_stats=None):
        self.val_size = args.val_size
        self.window_size = args.window_size
        self.window_stride = args.window_stride
        
        data = pd.read_csv(csv_filepath, nrows=num_rows)
        self.x = data['Aggregate'].values.astype(np.float64)
        self.y = data[target_col].values.astype(np.float64)
        
        if args.threshold_method in ['vs', 'mp']:
            logger.debug("[Data Processor] Using method: %s", args.threshold_method)
            self.thresh_manager = Threshold(appliances=[target_col], method=args.threshold_method, num_status=args.n_clusters)
            self.thresh_manager.update_appliance_threshold(self.y, target_col)
            
        elif args.threshold_method == 'custom':
            logger.debug("[Data Processor] Using Hierarchical Clustering")
            hc_model = HierarchicalClustering(distance="average", n_cluster=args.n_clusters)
            hc_model.perform_clustering(self.y)
            hc_model.compute_thresholds_and_centroids(centroid="median")
            
            self.thresh_manager = Threshold(appliances=[target_col], method="custom")
            self.thresh_manager.set_thresholds_and_centroids(
                np.expand_dims(hc_model.thresh, axis=0),
                np.expand_dims(hc_model.centroids, axis=0)
            )
            
        args.threshold = self.thresh_manager.thresholds[0][1]
        logger.debug("[Data Processor] Dynamic Threshold set to: %.2f Watts", args.threshold)
        
        y_reshaped = self.y.reshape(-1, 1)
        self.status = self.thresh_manager.power_to_status(y_reshaped).flatten().astype(np.float64)
        
        if pretrained_stats is not None:
            self.x_mean, self.x_std = pretrained_stats
        else:
            self.x_mean = np.mean(self.x)
            self.x_std = np.std(self.x)
            
        self.x = (self.x - self.x_mean) / (self.x_std + 1e-6)

    def get_datasets(self):
        val_end = int((1 - self.val_size) * len(self.x))
        train = BERTDataset(self.x[:val_end], self.y[:val_end], self.status[:val_end],
                            self.window_size, self.window_stride)
        val = NILMDataset(self.x[val_end:], self.y[val_end:], self.status[val_end:],
                          self.window_size, self.window_size)
        return train, val

def calculate_f1_fast(pred, status):
    pred = pred.reshape(-1)
    status = status.reshape(-1)
    tp = np.sum((pred == 1) & (status == 1))
    fp = np.sum((pred == 1) & (status == 0))
    fn = np.sum((pred == 0) & (status == 1))
    precision = tp / max((tp + fp), 1e-9)
    recall = tp / max((tp + fn), 1e-9)
    f1 = 2 * (precision * recall) / max((precision + recall), 1e-9)
    return f1

def train_finetune(model, train_loader, val_loader, device, args, save_path, epochs=10):
    for name, param in model.named_parameters():
        if 'linear' in name or 'deconv' in name or 'transformer_blocks.1' in name:
            param.requires_grad = True
        else:
            param.requires_grad = False

    trainable_parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(trainable_parameters, lr=1e-5, weight_decay=1e-4)
    
    mse = nn.MSELoss()
    kl = nn.KLDivLoss(reduction='batchmean')
    l1_on = nn.L1Loss(reduction='sum')
    
    best_combined_score = -float('inf')
    
    for epoch in range(epochs):
        model.train()
        total_train_loss = 0
        
        for batch_idx, (seqs, labels_energy, status) in enumerate(train_loader):
            seqs = seqs.to(device)
            labels_energy = labels_energy.to(device)
            status = status.to(device)
            batch_shape = status.shape
            
            optimizer.zero_grad()
            logits = model(seqs)
            
            labels = labels_energy / args.cutoff
            
            mask = (status >= 0)
            labels_masked = torch.masked_select(labels, mask).view((-1, batch_shape[-1]))
            logits_masked = torch.masked_select(logits, mask).view((-1, batch_shape[-1]))
            
            if logits_masked.numel() == 0:
                continue

            kl_loss = kl(torch.log(F.softmax(logits_masked.squeeze() / 0.1, dim=-1) + 1e-9), 
                         F.softmax(labels_masked.squeeze() / 0.1, dim=-1))
            mse_loss = mse(logits_masked.contiguous().view(-1).double(),
                           labels_masked.contiguous().view(-1).double())
            
            total_loss = kl_loss + mse_loss
            
            logits_energy = logits * args.cutoff
            logits_status = (logits_energy >= args.threshold) * 1.0
            
            on_mask = (status >= 0) * (((status == 1) + (status != logits_status.reshape(status.shape))) >= 1)
            if on_mask.sum() > 0:
                total_size = torch.tensor(on_mask.shape).prod()
                logits_on = torch.masked_select(logits.reshape(on_mask.shape), on_mask)
                labels_on = torch.masked_select(labels.reshape(on_mask.shape), on_mask)
                loss_l1_on = l1_on(logits_on.contiguous().view(-1), labels_on.contiguous().view(-1))
                total_loss += args.c0 * loss_l1_on / total_size
            
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_train_loss += total_loss.item()
            
        avg_train_loss = total_train_loss / len(train_loader)
        
        model.eval()
        all_logits_status = []
        all_status = []
        all_logits_energy = []
        all_labels_energy = []
        
        with torch.no_grad():
            for batch_idx, (seqs, labels_energy, status) in enumerate(val_loader):
                seqs = seqs.to(device)
                logits = model(seqs)
                
                logits_energy = logits * args.cutoff
                logits_energy[logits_energy < 5] = 0
                logits_energy = torch.min(logits_energy, torch.tensor(args.cutoff, device=device).double())
                
                logits_status = (logits_energy >= args.threshold) * 1.0
                logits_energy = logits_energy * logits_status
                
                all_logits_status.append(logits_status.cpu().numpy())
                all_status.append(status.numpy())
                all_logits_energy.append(logits_energy.cpu().numpy())
                all_labels_energy.append(labels_energy.numpy())
                
        all_logits_status = np.concatenate(all_logits_status).reshape(-1)
        all_status = np.concatenate(all_status).reshape(-1)
        all_logits_energy = np.concatenate(all_logits_energy).reshape(-1)
        all_labels_energy = np.concatenate(all_labels_energy).reshape(-1)
        
        current_f1 = calculate_f1_fast(all_logits_status, all_status)
        current_acc = np.mean(all_logits_status == all_status)
        
        temp = np.full(all_labels_energy.shape, 1e-9)
        current_rel_err = np.mean(np.nan_to_num(np.abs(all_labels_energy - all_logits_energy) / np.max((all_labels_energy, all_logits_energy, temp), axis=0)))
        
        current_combined_score = current_f1 + current_acc - current_rel_err
        
        logger.info("Epoch [%d/%d] | Train Loss: %.4f | Val F1: %.4f | Acc: %.4f | MRE: %.4f | Score: %.4f", 
                    epoch+1, epochs, avg_train_loss, current_f1, current_acc, current_rel_err, current_combined_score)
        
        if current_combined_score > best_combined_score:
            best_combined_score = current_combined_score
            torch.save(model.state_dict(), save_path)
            logger.info("--> Saved best model at Epoch %d with Combined Score: %.4f", epoch+1, best_combined_score)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune GRU-BERT for specific appliances and houses.")
    parser.add_argument('--appliance', type=str, required=True, choices=['kettle', 'microwave', 'fridge', 'dishwasher', 'washingmachine'])
    parser.add_argument('--house', type=str, required=True)
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--data_dir', type=str, default='refit')
    parser.add_argument('--num_rows', type=int, default=100000)
    cli_args = parser.parse_args()

    # ... (Dicts remain unchanged)
    APP_CONFIGS = {
        'kettle': {'cutoff': 2850.0, 'min_on': 2, 'min_off': 0},
        'microwave': {'cutoff': 1300.0, 'min_on': 2, 'min_off': 1},
        'fridge': {'cutoff': 400.0, 'min_on': 10, 'min_off': 12},
        'dishwasher': {'cutoff': 2550.0, 'min_on': 30, 'min_off': 30},
        'washingmachine': {'cutoff': 2300.0, 'min_on': 30, 'min_off': 120}
    }

    APP_INDEX = {'kettle': 0, 'microwave': 1, 'fridge': 2, 'dishwasher': 3, 'washingmachine': 4}

    HOUSES_MAP = {
        '1': [10, 10, 1, 10, 5], '2': [8, 5, 1, 10, 2], '3': [9, 8, 2, 10, 6],
        '4': [9, 8, 1, 4, 6], '5': [8, 7, 1, 4, 3], '6': [7, 6, 1, 3, 2],
        '7': [9, 10, 1, 6, 5], '8': [9, 8, 1, 10, 4], '9': [7, 6, 1, 4, 3],
        '10': [10, 8, 4, 6, 5], '12': [6, 5, 1, 10, 10], '15': [10, 7, 1, 4, 3],
        '16': [10, 10, 1, 6, 5], '17': [8, 7, 2, 10, 4], '18': [10, 9, 1, 6, 5],
        '19': [5, 4, 1, 10, 2], '20': [9, 8, 1, 5, 4]
    }

    if cli_args.house not in HOUSES_MAP:
        raise ValueError(f"House {cli_args.house} not found in configuration.")

    target_config = APP_CONFIGS[cli_args.appliance]
    target_idx = APP_INDEX[cli_args.appliance]
    target_channel = HOUSES_MAP[cli_args.house][target_idx]
    target_col = f"Appliance{target_channel}"

    logger.info("--- Configuration Setup ---")
    logger.info("Appliance: %s (Cutoff: %s)", cli_args.appliance.capitalize(), target_config['cutoff'])
    logger.info("Min ON: %s | Min OFF: %s", target_config['min_on'], target_config['min_off'])
    logger.info("House: %s (Target Column: %s)", cli_args.house, target_col)
    logger.info("Rows to load: %s", cli_args.num_rows)

    torch.set_default_dtype(torch.float64)
    args = ConfigArgs(
        cutoff=target_config['cutoff'], 
        min_on=target_config['min_on'], 
        min_off=target_config['min_off']
    )
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = GRUBERT(args)
    
    pretrained_path = f"{cli_args.appliance}.pth"
    try:
        model.load_state_dict(torch.load(pretrained_path, map_location=device))
        logger.info("Successfully loaded pre-trained weights from %s", pretrained_path)
    except FileNotFoundError:
        logger.warning("%s not found. Training will start from scratch.", pretrained_path)
        
    model.to(device)
    
    UK_DALE_MEAN = 418.623901
    UK_DALE_STD = 504.039630
    pretrained_stats = (UK_DALE_MEAN, UK_DALE_STD)
    
    csv_path = f"{cli_args.data_dir}/CLEAN_House{cli_args.house}.csv"
    processor = SENTRADataProcessor(csv_path, target_col, args, num_rows=cli_args.num_rows, pretrained_stats=pretrained_stats)
    train_dataset, val_dataset = processor.get_datasets()
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, pin_memory=True)
    
    save_model_path = f'models/House_{cli_args.house}_{cli_args.appliance}_model.pth'
    logger.info("Model will be saved to: %s", save_model_path)
    logger.info("Starting fine-tuning process...")
    
    train_finetune(model, train_loader, val_loader, device, args, save_path=save_model_path, epochs=cli_args.epochs)