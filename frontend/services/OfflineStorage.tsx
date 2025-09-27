import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';
import NetInfo from '@react-native-netinfo/netinfo';

// Storage Keys
const OFFLINE_SALES_KEY = '@offline_sales';
const OFFLINE_PURCHASES_KEY = '@offline_purchases';
const OFFLINE_PRODUCTS_KEY = '@offline_products';
const SYNC_QUEUE_KEY = '@sync_queue';
const LAST_SYNC_KEY = '@last_sync';
const DEVICE_ID_KEY = '@device_id';

// Types
export interface OfflineSale {
  sync_id: string;
  sale_number: string;
  total_amount: number;
  status: string;
  payment_status: string;
  created_at: string;
  completed_at?: string;
  items: Array<{
    product_id: string;
    quantity: number;
    unit_price: number;
    total_price: number;
  }>;
  payments: Array<{
    payment_method_id: string;
    amount: number;
    created_at: string;
  }>;
}

export interface SyncItem {
  sync_id: string;
  data_type: 'sale' | 'purchase' | 'product';
  action: 'create' | 'update' | 'delete';
  data: any;
  timestamp: string;
  retries?: number;
}

export interface NetworkStatus {
  isConnected: boolean;
  isInternetReachable: boolean | null;
}

class OfflineStorageService {
  private static instance: OfflineStorageService;
  private networkStatus: NetworkStatus = { isConnected: false, isInternetReachable: null };
  private syncInProgress = false;
  private deviceId: string = '';

  static getInstance(): OfflineStorageService {
    if (!OfflineStorageService.instance) {
      OfflineStorageService.instance = new OfflineStorageService();
    }
    return OfflineStorageService.instance;
  }

  constructor() {
    this.initializeNetworkListener();
    this.generateDeviceId();
  }

  private async generateDeviceId() {
    try {
      let deviceId = await AsyncStorage.getItem(DEVICE_ID_KEY);
      if (!deviceId) {
        deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await AsyncStorage.setItem(DEVICE_ID_KEY, deviceId);
      }
      this.deviceId = deviceId;
    } catch (error) {
      console.error('Error generating device ID:', error);
    }
  }

  private initializeNetworkListener() {
    NetInfo.addEventListener(state => {
      const wasOffline = !this.networkStatus.isConnected;
      this.networkStatus = {
        isConnected: state.isConnected ?? false,
        isInternetReachable: state.isInternetReachable,
      };

      // Auto sync when coming back online
      if (wasOffline && this.networkStatus.isConnected && this.networkStatus.isInternetReachable) {
        this.autoSync();
      }
    });
  }

  // Network status methods
  getNetworkStatus(): NetworkStatus {
    return this.networkStatus;
  }

  isOnline(): boolean {
    return this.networkStatus.isConnected && this.networkStatus.isInternetReachable !== false;
  }

  // Offline storage methods
  async storeOfflineSale(sale: OfflineSale): Promise<void> {
    try {
      const existingSales = await this.getOfflineSales();
      existingSales.push(sale);
      await AsyncStorage.setItem(OFFLINE_SALES_KEY, JSON.stringify(existingSales));
      
      // Add to sync queue
      await this.addToSyncQueue({
        sync_id: sale.sync_id,
        data_type: 'sale',
        action: 'create',
        data: sale,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error storing offline sale:', error);
      throw error;
    }
  }

  async getOfflineSales(): Promise<OfflineSale[]> {
    try {
      const salesData = await AsyncStorage.getItem(OFFLINE_SALES_KEY);
      return salesData ? JSON.parse(salesData) : [];
    } catch (error) {
      console.error('Error getting offline sales:', error);
      return [];
    }
  }

  async removeOfflineSale(syncId: string): Promise<void> {
    try {
      const existingSales = await this.getOfflineSales();
      const filteredSales = existingSales.filter(sale => sale.sync_id !== syncId);
      await AsyncStorage.setItem(OFFLINE_SALES_KEY, JSON.stringify(filteredSales));
    } catch (error) {
      console.error('Error removing offline sale:', error);
    }
  }

  // Sync queue methods
  async addToSyncQueue(item: SyncItem): Promise<void> {
    try {
      const queue = await this.getSyncQueue();
      queue.push(item);
      await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(queue));
    } catch (error) {
      console.error('Error adding to sync queue:', error);
    }
  }

  async getSyncQueue(): Promise<SyncItem[]> {
    try {
      const queueData = await AsyncStorage.getItem(SYNC_QUEUE_KEY);
      return queueData ? JSON.parse(queueData) : [];
    } catch (error) {
      console.error('Error getting sync queue:', error);
      return [];
    }
  }

  async clearSyncQueue(): Promise<void> {
    try {
      await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify([]));
    } catch (error) {
      console.error('Error clearing sync queue:', error);
    }
  }

  async removeFromSyncQueue(syncId: string): Promise<void> {
    try {
      const queue = await this.getSyncQueue();
      const filteredQueue = queue.filter(item => item.sync_id !== syncId);
      await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(filteredQueue));
    } catch (error) {
      console.error('Error removing from sync queue:', error);
    }
  }

  // Sync methods
  async syncToServer(baseUrl: string, token: string): Promise<{ success: boolean; results: any[] }> {
    if (this.syncInProgress) {
      return { success: false, results: [] };
    }

    if (!this.isOnline()) {
      throw new Error('No internet connection');
    }

    this.syncInProgress = true;

    try {
      const syncQueue = await this.getSyncQueue();
      
      if (syncQueue.length === 0) {
        return { success: true, results: [] };
      }

      // Filter items with too many retries (max 3)
      const validItems = syncQueue.filter(item => (item.retries || 0) < 3);

      if (validItems.length === 0) {
        return { success: true, results: [] };
      }

      const syncBatch = {
        device_id: this.deviceId,
        sync_items: validItems
      };

      const response = await fetch(`${baseUrl}/api/sync/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(syncBatch),
      });

      if (!response.ok) {
        throw new Error(`Sync failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      // Process sync results
      const processedIds = [];
      const failedItems = [];

      for (const syncResult of result.results) {
        if (syncResult.status === 'success') {
          processedIds.push(syncResult.sync_id);
          // Remove successful items
          await this.removeFromSyncQueue(syncResult.sync_id);
          
          // Remove from offline storage if it was a sale
          const originalItem = validItems.find(item => item.sync_id === syncResult.sync_id);
          if (originalItem && originalItem.data_type === 'sale') {
            await this.removeOfflineSale(syncResult.sync_id);
          }
        } else if (syncResult.status === 'conflict') {
          // Handle conflicts - remove from queue but log the conflict
          console.warn('Sync conflict for item:', syncResult.sync_id, syncResult.error_message);
          processedIds.push(syncResult.sync_id);
          await this.removeFromSyncQueue(syncResult.sync_id);
        } else {
          // Handle errors - increment retry count
          const originalItem = validItems.find(item => item.sync_id === syncResult.sync_id);
          if (originalItem) {
            originalItem.retries = (originalItem.retries || 0) + 1;
            failedItems.push(originalItem);
          }
        }
      }

      // Update failed items in queue with retry counts
      if (failedItems.length > 0) {
        const remainingQueue = await this.getSyncQueue();
        for (const failedItem of failedItems) {
          const queueIndex = remainingQueue.findIndex(item => item.sync_id === failedItem.sync_id);
          if (queueIndex >= 0) {
            remainingQueue[queueIndex] = failedItem;
          }
        }
        await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(remainingQueue));
      }

      // Update last sync timestamp
      await AsyncStorage.setItem(LAST_SYNC_KEY, new Date().toISOString());

      return {
        success: processedIds.length > 0,
        results: result.results
      };

    } catch (error) {
      console.error('Sync error:', error);
      throw error;
    } finally {
      this.syncInProgress = false;
    }
  }

  async downloadFromServer(baseUrl: string, token: string): Promise<void> {
    if (!this.isOnline()) {
      throw new Error('No internet connection');
    }

    try {
      const lastSync = await AsyncStorage.getItem(LAST_SYNC_KEY);
      let url = `${baseUrl}/api/sync/download?data_types=products,categories,payment_methods`;
      
      if (lastSync) {
        url += `&last_sync=${encodeURIComponent(lastSync)}`;
      }

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      // Store downloaded data locally
      if (data.data.products) {
        await AsyncStorage.setItem('@cached_products', JSON.stringify(data.data.products));
      }
      
      if (data.data.categories) {
        await AsyncStorage.setItem('@cached_categories', JSON.stringify(data.data.categories));
      }
      
      if (data.data.payment_methods) {
        await AsyncStorage.setItem('@cached_payment_methods', JSON.stringify(data.data.payment_methods));
      }

      // Update last download timestamp
      await AsyncStorage.setItem('@last_download', data.sync_timestamp);

    } catch (error) {
      console.error('Download error:', error);
      throw error;
    }
  }

  // Auto sync when coming back online
  private async autoSync() {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (!token) return;

      const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
      if (!BACKEND_URL) return;

      // Small delay to ensure connection is stable
      setTimeout(async () => {
        try {
          await this.syncToServer(BACKEND_URL, token);
          console.log('Auto sync completed successfully');
        } catch (error) {
          console.error('Auto sync failed:', error);
        }
      }, 2000);

    } catch (error) {
      console.error('Auto sync setup error:', error);
    }
  }

  // Manual sync trigger
  async manualSync(baseUrl: string, token: string): Promise<{ uploadSuccess: boolean; downloadSuccess: boolean; message: string }> {
    if (!this.isOnline()) {
      return {
        uploadSuccess: false,
        downloadSuccess: false,
        message: 'Pas de connexion internet'
      };
    }

    try {
      // Upload pending changes
      const uploadResult = await this.syncToServer(baseUrl, token);
      
      // Download latest data
      let downloadSuccess = true;
      try {
        await this.downloadFromServer(baseUrl, token);
      } catch (downloadError) {
        downloadSuccess = false;
        console.error('Download during manual sync failed:', downloadError);
      }

      const uploadCount = uploadResult.results.filter(r => r.status === 'success').length;
      const conflictCount = uploadResult.results.filter(r => r.status === 'conflict').length;
      const errorCount = uploadResult.results.filter(r => r.status === 'error').length;

      let message = 'Synchronisation terminée';
      if (uploadCount > 0) {
        message += `\n✅ ${uploadCount} éléments synchronisés`;
      }
      if (conflictCount > 0) {
        message += `\n⚠️ ${conflictCount} conflits détectés`;
      }
      if (errorCount > 0) {
        message += `\n❌ ${errorCount} erreurs`;
      }

      return {
        uploadSuccess: uploadResult.success,
        downloadSuccess,
        message
      };

    } catch (error) {
      console.error('Manual sync error:', error);
      return {
        uploadSuccess: false,
        downloadSuccess: false,
        message: `Erreur de synchronisation: ${error instanceof Error ? error.message : 'Erreur inconnue'}`
      };
    }
  }

  // Utility methods
  async getPendingSyncCount(): Promise<number> {
    try {
      const queue = await this.getSyncQueue();
      return queue.length;
    } catch (error) {
      return 0;
    }
  }

  async getLastSyncTime(): Promise<Date | null> {
    try {
      const lastSync = await AsyncStorage.getItem(LAST_SYNC_KEY);
      return lastSync ? new Date(lastSync) : null;
    } catch (error) {
      return null;
    }
  }

  async getCachedData(type: 'products' | 'categories' | 'payment_methods'): Promise<any[]> {
    try {
      const data = await AsyncStorage.getItem(`@cached_${type}`);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error(`Error getting cached ${type}:`, error);
      return [];
    }
  }

  // Clear all offline data (for testing or reset)
  async clearAllOfflineData(): Promise<void> {
    try {
      await AsyncStorage.multiRemove([
        OFFLINE_SALES_KEY,
        OFFLINE_PURCHASES_KEY,
        OFFLINE_PRODUCTS_KEY,
        SYNC_QUEUE_KEY,
        '@cached_products',
        '@cached_categories',
        '@cached_payment_methods'
      ]);
    } catch (error) {
      console.error('Error clearing offline data:', error);
    }
  }
}

export default OfflineStorageService.getInstance();